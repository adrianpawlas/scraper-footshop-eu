import requests
import json
import re
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional, List
from config import REQUEST_TIMEOUT, BASE_URL
from scraper.utils import retry_on_failure, RateLimiter, sanitize_string
import logging

logger = logging.getLogger(__name__)

class ProductScraper:
    """Scrapes individual product pages to extract product data."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        })
        self.rate_limiter = RateLimiter(requests_per_second=1.0)

    @retry_on_failure(max_attempts=3)
    def scrape_product(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape a single product page and extract product data."""
        try:
            logger.info(f"Scraping product: {url}")
            self.rate_limiter.wait_if_needed_sync()
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()

            # Extract JSON data from script tags
            soup = BeautifulSoup(response.content, 'html.parser')

            # Find the ProductDetail script tag
            product_script = soup.find('script', {
                'type': 'application/json',
                'data-hypernova-key': 'ProductDetail'
            })

            if not product_script:
                logger.warning(f"No product data found for URL: {url}")
                return None

            # Extract and parse JSON
            json_text = product_script.string
            if json_text.startswith('<!--') and json_text.endswith('-->'):
                json_text = json_text[4:-3]

            data = json.loads(json_text)
            product_data = data.get('data', {}).get('product_data', {})

            if not product_data:
                logger.warning(f"No product_data found in JSON for URL: {url}")
                return None

            # Extract additional data from HTML
            additional_data = self._extract_additional_data(soup, url)

            # Combine data
            full_product_data = {**product_data, **additional_data}

            logger.info(f"Successfully scraped product: {product_data.get('name', 'Unknown')}")
            return full_product_data

        except requests.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed for {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error scraping {url}: {e}")
            return None

    def _extract_additional_data(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extract additional data from HTML that might not be in JSON."""
        additional_data = {}

        # Extract description if available
        description_elem = soup.find('div', {'data-testid': 'product-description'})
        if description_elem:
            # Get text content and clean it up
            description_text = description_elem.get_text(separator='\n', strip=True)
            additional_data['description'] = sanitize_string(description_text)

        # Extract breadcrumb category information
        breadcrumbs = soup.find('ul', class_=re.compile(r'Breadcrumbs_breadcrumbs'))
        if breadcrumbs:
            breadcrumb_links = breadcrumbs.find_all('a')
            if len(breadcrumb_links) >= 2:
                # Usually: Home > Category > Subcategory
                category = breadcrumb_links[-1].get_text(strip=True)
                additional_data['category'] = category

        # Extract gender from URL or breadcrumbs
        if '/mens-' in url.lower() or '/men-s-' in url.lower():
            additional_data['gender'] = 'men'
        elif '/womens-' in url.lower() or '/women-s-' in url.lower():
            additional_data['gender'] = 'women'
        elif '/unisex-' in url.lower():
            additional_data['gender'] = 'unisex'

        # Extract country (always 'EU' for footshop.eu)
        additional_data['country'] = 'EU'

        # Extract product URL
        additional_data['product_url'] = url

        # Set source
        additional_data['source'] = 'footshop_eu'

        return additional_data

    def scrape_products_batch(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Scrape multiple products and return successful results."""
        results = []
        for url in urls:
            product_data = self.scrape_product(url)
            if product_data:
                results.append(product_data)
        return results
