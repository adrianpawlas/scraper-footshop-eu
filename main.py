#!/usr/bin/env python3
"""
Footshop EU Product Scraper
Scrapes all products from Footshop EU, generates image embeddings, and stores in Supabase.
"""

import asyncio
import logging
import time
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
import argparse

from scraper.sitemap_parser import SitemapParser
from scraper.product_scraper import ProductScraper
from scraper.image_processor import ImageProcessor
from scraper.supabase_client import SupabaseClient
from scraper.data_mapper import DataMapper
from config import CONCURRENT_REQUESTS, RATE_LIMIT_DELAY

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FootshopScraper:
    """Main orchestrator for the Footshop EU scraping pipeline."""

    def __init__(self):
        self.sitemap_parser = SitemapParser()
        self.product_scraper = ProductScraper()
        self.image_processor = ImageProcessor()
        self.supabase_client = SupabaseClient()
        self.data_mapper = DataMapper()

    async def scrape_product_batch(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Scrape a batch of products asynchronously."""
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=CONCURRENT_REQUESTS) as executor:
            # Scrape products
            logger.info(f"Scraping {len(urls)} products...")
            product_futures = [
                loop.run_in_executor(executor, self.product_scraper.scrape_product, url)
                for url in urls
            ]

            # Wait for all product scraping to complete
            raw_products = await asyncio.gather(*product_futures, return_exceptions=True)

            # Filter out exceptions and None results
            valid_products = [
                product for product in raw_products
                if product is not None and not isinstance(product, Exception)
            ]

            logger.info(f"Successfully scraped {len(valid_products)} products")

            # Process images and generate embeddings
            processed_products = []
            for product_data in valid_products:
                if not product_data:
                    continue

                # Extract image URLs
                image_urls = self._extract_image_urls(product_data)
                logger.debug(f"Extracted {len(image_urls)} image URLs for product: {product_data.get('name', 'Unknown')}")
                if not image_urls:
                    logger.warning(f"No image URLs found in product data keys: {list(product_data.keys())}")
                    # Let's see what image-related fields exist
                    image_fields = ['image', 'images', 'gallery', 'gallery_images', 'photos', 'pictures']
                    for field in image_fields:
                        if field in product_data and product_data[field]:
                            logger.warning(f"Found {field}: {product_data[field]}")

                try:
                    # Process images and generate SigLIP embedding (REQUIRED)
                    image_url, embedding = self.image_processor.process_product_images(image_urls)

                    # Map data to database schema
                    mapped_product = self.data_mapper.map_product_data(
                        product_data, image_url, embedding
                    )

                    processed_products.append(mapped_product)
                except RuntimeError as e:
                    logger.error(f"CRITICAL: Failed to generate embedding for product {product_data.get('name', 'Unknown')}: {e}")
                    logger.error("Skipping product - embeddings are mandatory")
                    continue

                # Rate limiting
                await asyncio.sleep(RATE_LIMIT_DELAY)

            return processed_products

    def _extract_image_urls(self, product_data: Dict[str, Any]) -> List[str]:
        """Extract all available image URLs from product data."""
        image_urls = []

        # Handle Footshop's specific image structure
        images_data = product_data.get('images')
        if images_data and isinstance(images_data, dict):
            # Add cover image
            cover_image = images_data.get('cover_image')
            if cover_image:
                image_urls.append(cover_image)

            # Add images from 'other' array
            other_images = images_data.get('other', [])
            if isinstance(other_images, list):
                for img_obj in other_images:
                    if isinstance(img_obj, dict):
                        # Prefer mobile_image for full resolution, fallback to image
                        img_url = img_obj.get('mobile_image') or img_obj.get('image')
                        if img_url and img_url not in image_urls:
                            image_urls.append(img_url)

        # Try other image fields as fallback
        image_fields = ['gallery_images', 'product_images']
        for field in image_fields:
            images = product_data.get(field, [])
            if images and isinstance(images, list):
                image_urls.extend(images)

        # Add main image if not already included
        main_image = product_data.get('image') or product_data.get('last_image')
        if main_image and main_image not in image_urls:
            image_urls.insert(0, main_image)

        # Check variants for additional images
        variants = product_data.get('variants') or product_data.get('color_variations', [])
        if isinstance(variants, list):
            for variant in variants:
                if isinstance(variant, dict):
                    variant_images = variant.get('images') or variant.get('image')
                    if variant_images:
                        if isinstance(variant_images, list):
                            image_urls.extend(variant_images)
                        elif isinstance(variant_images, str):
                            image_urls.append(variant_images)

        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in image_urls:
            if url and url not in seen:
                seen.add(url)
                unique_urls.append(url)

        return unique_urls

    async def scrape_all_products(self, batch_size: int = 10, limit: Optional[int] = None) -> int:
        """Scrape all products from Footshop EU."""
        logger.info("Starting full Footshop EU scrape")

        # Get all product URLs from sitemap
        try:
            all_urls = self.sitemap_parser.get_product_urls()
            if limit:
                all_urls = all_urls[:limit]
        except Exception as e:
            logger.error(f"Failed to get product URLs from sitemap: {e}")
            return 0

        logger.info(f"Found {len(all_urls)} products to scrape")

        total_processed = 0

        # Process in batches
        for i in range(0, len(all_urls), batch_size):
            batch_urls = all_urls[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(len(all_urls) + batch_size - 1)//batch_size}")

            try:
                # Scrape batch
                processed_products = await self.scrape_product_batch(batch_urls)

                # Insert into database
                if processed_products:
                    successful_inserts = self.supabase_client.insert_products_batch(processed_products)
                    total_processed += successful_inserts
                    logger.info(f"Batch completed: {successful_inserts}/{len(processed_products)} products inserted")

                # Small delay between batches
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Error processing batch {i//batch_size + 1}: {e}")
                continue

        logger.info(f"Scraping completed. Total products processed: {total_processed}")
        return total_processed

    async def scrape_single_product(self, url: str) -> bool:
        """Scrape a single product for testing."""
        logger.info(f"Scraping single product: {url}")

        # Scrape product
        raw_product = self.product_scraper.scrape_product(url)
        if not raw_product:
            logger.error("Failed to scrape product")
            return False

        # Process images and generate SigLIP embedding (REQUIRED)
        image_urls = self._extract_image_urls(raw_product)
        try:
            image_url, embedding = self.image_processor.process_product_images(image_urls)
        except RuntimeError as e:
            logger.error(f"CRITICAL: Failed to generate SigLIP embedding: {e}")
            logger.error("Cannot continue - embeddings are mandatory")
            return False

        # Map data
        mapped_product = self.data_mapper.map_product_data(raw_product, image_url, embedding)

        # Insert into database
        success = self.supabase_client.insert_product(mapped_product)

        if success:
            logger.info("Successfully scraped and inserted product")
        else:
            logger.error("Failed to insert product")

        return success

    def get_scraping_stats(self) -> Dict[str, Any]:
        """Get scraping statistics."""
        total_products = self.supabase_client.get_product_count()
        footshop_products = len(self.supabase_client.get_products_by_source('footshop_eu', limit=1000))

        return {
            'total_products_in_db': total_products,
            'footshop_products': footshop_products
        }

async def main():
    parser = argparse.ArgumentParser(description='Footshop EU Product Scraper')
    parser.add_argument('--mode', choices=['full', 'single', 'stats'],
                       default='stats', help='Scraping mode')
    parser.add_argument('--url', help='Single product URL for single mode')
    parser.add_argument('--batch-size', type=int, default=5,
                       help='Batch size for full scraping')
    parser.add_argument('--limit', type=int,
                       help='Limit number of products to scrape')

    args = parser.parse_args()

    scraper = FootshopScraper()

    if args.mode == 'full':
        total_processed = await scraper.scrape_all_products(
            batch_size=args.batch_size,
            limit=args.limit
        )
        print(f"Scraping completed. Processed {total_processed} products.")

    elif args.mode == 'single':
        if not args.url:
            print("Error: --url is required for single mode")
            return
        success = await scraper.scrape_single_product(args.url)
        print(f"Single product scraping {'successful' if success else 'failed'}")

    elif args.mode == 'stats':
        stats = scraper.get_scraping_stats()
        print("Scraping Statistics:")
        print(f"Total products in database: {stats['total_products_in_db']}")
        print(f"Footshop EU products: {stats['footshop_products']}")

if __name__ == '__main__':
    asyncio.run(main())
