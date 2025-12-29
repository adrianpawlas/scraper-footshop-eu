from supabase import create_client, Client
from typing import List, Dict, Any, Optional
from config import SUPABASE_URL, SUPABASE_KEY, TABLE_NAME
import logging

logger = logging.getLogger(__name__)

class SupabaseClient:
    """Handles Supabase database operations."""

    def __init__(self):
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")

        # Create client with explicit options to avoid proxy issues
        try:
            self.client: Client = create_client(
                SUPABASE_URL,
                SUPABASE_KEY,
                options={"auto_refresh_token": False, "persist_session": False}
            )
        except (TypeError, Exception) as e:
            logger.warning(f"Supabase client creation failed: {e}")
            logger.warning("Attempting fallback client creation...")

            try:
                # Try creating client without options
                from supabase import Client
                self.client = Client(SUPABASE_URL, SUPABASE_KEY)
                logger.info("Fallback client creation successful")
            except Exception as fallback_e:
                logger.error(f"Fallback client creation also failed: {fallback_e}")
                logger.error("Supabase client initialization failed - scraper cannot continue")
                raise RuntimeError(f"Cannot initialize Supabase client: {e} -> {fallback_e}")

        self.table_name = TABLE_NAME

    def insert_product(self, product_data: Dict[str, Any]) -> bool:
        """Insert a single product into the database."""
        try:
            # Check if product already exists (using unique constraint)
            existing = self.client.table(self.table_name).select("id").eq("source", product_data.get("source")).eq("product_url", product_data.get("product_url")).execute()

            if existing.data:
                logger.info(f"Product already exists: {product_data.get('product_url')}")
                # Update instead of insert
                return self.update_product(product_data)

            # Insert new product
            result = self.client.table(self.table_name).insert(product_data).execute()

            if result.data:
                logger.info(f"Successfully inserted product: {product_data.get('title', 'Unknown')}")
                return True
            else:
                logger.error(f"Failed to insert product: {product_data.get('title', 'Unknown')}")
                return False

        except Exception as e:
            logger.error(f"Error inserting product: {e}")
            return False

    def insert_products_batch(self, products_data: List[Dict[str, Any]]) -> int:
        """Insert multiple products into the database."""
        successful_inserts = 0

        for product_data in products_data:
            if self.insert_product(product_data):
                successful_inserts += 1

        logger.info(f"Batch insert completed: {successful_inserts}/{len(products_data)} products inserted")
        return successful_inserts

    def update_product(self, product_data: Dict[str, Any]) -> bool:
        """Update an existing product."""
        try:
            # Update based on source and product_url
            result = self.client.table(self.table_name)\
                .update(product_data)\
                .eq("source", product_data.get("source"))\
                .eq("product_url", product_data.get("product_url"))\
                .execute()

            if result.data:
                logger.info(f"Successfully updated product: {product_data.get('title', 'Unknown')}")
                return True
            else:
                logger.warning(f"No product found to update: {product_data.get('product_url')}")
                return False

        except Exception as e:
            logger.error(f"Error updating product: {e}")
            return False

    def get_product_count(self) -> int:
        """Get total count of products in database."""
        try:
            result = self.client.table(self.table_name).select("id", count="exact").execute()
            return result.count
        except Exception as e:
            logger.error(f"Error getting product count: {e}")
            return 0

    def get_products_by_source(self, source: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get products by source."""
        try:
            result = self.client.table(self.table_name)\
                .select("*")\
                .eq("source", source)\
                .limit(limit)\
                .execute()
            return result.data
        except Exception as e:
            logger.error(f"Error getting products by source: {e}")
            return []

    def delete_product(self, source: str, product_url: str) -> bool:
        """Delete a product by source and product_url."""
        try:
            result = self.client.table(self.table_name)\
                .delete()\
                .eq("source", source)\
                .eq("product_url", product_url)\
                .execute()

            if result.data:
                logger.info(f"Successfully deleted product: {product_url}")
                return True
            else:
                logger.warning(f"No product found to delete: {product_url}")
                return False

        except Exception as e:
            logger.error(f"Error deleting product: {e}")
            return False
