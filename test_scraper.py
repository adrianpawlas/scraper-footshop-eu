#!/usr/bin/env python3
"""
Test script for Footshop EU scraper
"""

import asyncio
import logging
from scraper.sitemap_parser import SitemapParser
from scraper.product_scraper import ProductScraper
from scraper.image_processor import ImageProcessor
from scraper.data_mapper import DataMapper

# Configure logging for testing
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_sitemap_parser():
    """Test sitemap parser."""
    print("Testing Sitemap Parser...")
    parser = SitemapParser()

    try:
        urls = parser.get_product_urls_paginated(limit=5)
        print(f"✓ Found {len(urls)} product URLs")
        if urls:
            print(f"  Sample URL: {urls[0]}")
        return urls
    except Exception as e:
        print(f"✗ Sitemap parser failed: {e}")
        return []

async def test_product_scraper():
    """Test product scraper with a single product."""
    print("\nTesting Product Scraper...")
    scraper = ProductScraper()

    # Use a known product URL
    test_url = "https://www.footshop.eu/en/mens-shoes/397888-air-jordan-11-retro-gamma-blue-black-gamma-blue-black-varsity-maize.html"

    try:
        product_data = scraper.scrape_product(test_url)
        if product_data:
            print("✓ Product scraping successful")
            print(f"  Title: {product_data.get('name', 'Unknown')}")
            print(f"  Brand: {product_data.get('manufacturer', {}).get('name', 'Unknown')}")
            print(f"  Price: {product_data.get('price', {}).get('value', 'Unknown')}")
            return product_data
        else:
            print("✗ Product scraping returned None")
            return None
    except Exception as e:
        print(f"✗ Product scraper failed: {e}")
        return None

async def test_image_processor():
    """Test image processor."""
    print("\nTesting Image Processor...")
    processor = ImageProcessor()

    # Test with a known image URL
    test_image_url = "https://static.ftshp.digital/img/p/1/6/6/0/2/9/7/1660297-full_product.jpg"

    try:
        # Test image download
        image = processor.download_image(test_image_url)
        if image:
            print("✓ Image download successful")
            print(f"  Image size: {image.size}")

            # Test embedding generation
            embedding = processor.generate_embedding(image)
            if embedding:
                print("✓ Embedding generation successful")
                print(f"  Embedding dimension: {len(embedding)}")
                return embedding
            else:
                print("✗ Embedding generation failed")
                return None
        else:
            print("✗ Image download failed")
            return None
    except Exception as e:
        print(f"✗ Image processor failed: {e}")
        return None

async def test_data_mapper():
    """Test data mapper."""
    print("\nTesting Data Mapper...")
    mapper = DataMapper()

    # Create mock product data
    mock_data = {
        'id': 397888,
        'name': 'Test Product',
        'manufacturer': {'name': 'Test Brand'},
        'price': {'value': 99.99, 'currency_code': 'EUR'},
        'image': 'https://example.com/image.jpg',
        'product_url': 'https://example.com/product',
        'source': 'footshop_eu',
        'country': 'EU'
    }

    try:
        mapped_data = mapper.map_product_data(mock_data)
        print("✓ Data mapping successful")
        print(f"  Mapped ID: {mapped_data.get('id')}")
        print(f"  Mapped title: {mapped_data.get('title')}")
        print(f"  Mapped price: {mapped_data.get('price')}")
        return mapped_data
    except Exception as e:
        print(f"✗ Data mapper failed: {e}")
        return None

async def test_full_pipeline():
    """Test the complete pipeline with one product."""
    print("\nTesting Full Pipeline...")

    try:
        # Get one product URL
        parser = SitemapParser()
        urls = parser.get_product_urls_paginated(limit=1)

        if not urls:
            print("✗ No product URLs found")
            return

        url = urls[0]
        print(f"Testing with URL: {url}")

        # Scrape product
        scraper = ProductScraper()
        raw_product = scraper.scrape_product(url)

        if not raw_product:
            print("✗ Product scraping failed")
            return

        print("✓ Product scraped successfully")

        # Process images
        processor = ImageProcessor()
        image_urls = [raw_product.get('image')] if raw_product.get('image') else []
        image_url, embedding = processor.process_product_images(image_urls)

        print(f"✓ Image processing completed (embedding: {'✓' if embedding else '✗'})")

        # Map data
        mapper = DataMapper()
        mapped_product = mapper.map_product_data(raw_product, image_url, embedding)

        print("✓ Data mapping completed")
        print(f"  Final product ID: {mapped_product.get('id')}")
        print(f"  Has embedding: {mapped_product.get('embedding') is not None}")

        print("✓ Full pipeline test completed successfully")
        return mapped_product

    except Exception as e:
        print(f"✗ Full pipeline test failed: {e}")
        return None

async def main():
    """Run all tests."""
    print("🧪 Footshop EU Scraper Tests")
    print("=" * 50)

    # Test individual components
    await test_sitemap_parser()
    await test_product_scraper()
    await test_image_processor()
    await test_data_mapper()

    # Test full pipeline
    await test_full_pipeline()

    print("\n" + "=" * 50)
    print("Testing completed!")
    print("\nTo run the full scraper:")
    print("  python main.py --mode full --batch-size 5 --limit 10")
    print("\nTo run with a single product:")
    print("  python main.py --mode single --url 'https://www.footshop.eu/en/mens-shoes/397888-air-jordan-11-retro-gamma-blue-black-gamma-blue-black-varsity-maize.html'")

if __name__ == '__main__':
    asyncio.run(main())
