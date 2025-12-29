import requests
import xml.etree.ElementTree as ET
from typing import List, Dict, Any
from config import SITEMAP_URL, REQUEST_TIMEOUT
import logging

logger = logging.getLogger(__name__)

class SitemapParser:
    """Parses Footshop EU sitemap to extract product URLs."""

    def __init__(self):
        self.sitemap_url = SITEMAP_URL

    def get_product_urls(self) -> List[str]:
        """Fetch and parse sitemap to get all product URLs."""
        try:
            logger.info(f"Fetching sitemap from {self.sitemap_url}")
            response = requests.get(self.sitemap_url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()

            # Parse XML
            root = ET.fromstring(response.content)

            # Extract URLs from sitemap
            urls = []
            for url_element in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
                loc_element = url_element.find('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                if loc_element is not None and loc_element.text:
                    urls.append(loc_element.text)

            logger.info(f"Found {len(urls)} product URLs in sitemap")
            return urls

        except requests.RequestException as e:
            logger.error(f"Failed to fetch sitemap: {e}")
            raise
        except ET.ParseError as e:
            logger.error(f"Failed to parse sitemap XML: {e}")
            raise

    def get_product_urls_paginated(self, limit: int = None, offset: int = 0) -> List[str]:
        """Get product URLs with pagination support."""
        urls = self.get_product_urls()
        if limit:
            return urls[offset:offset + limit]
        return urls[offset:]
