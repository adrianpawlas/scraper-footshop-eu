import os
from dotenv import load_dotenv

load_dotenv()

# Footshop URLs
SITEMAP_URL = "https://sitemaps.footshop.eu/sitemaps/sitemap_products_6_1.xml"
BASE_URL = "https://www.footshop.eu"

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Scraping Configuration
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
CONCURRENT_REQUESTS = 5
RATE_LIMIT_DELAY = 1  # seconds between requests

# Image Processing
IMAGE_SIZE = (384, 384)  # Required for siglip-base-patch16-384
EMBEDDING_DIM = 768

# Database
TABLE_NAME = "products"
