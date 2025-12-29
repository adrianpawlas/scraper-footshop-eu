from typing import Dict, Any, List, Optional
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DataMapper:
    """Maps scraped product data to database schema."""

    def map_product_data(self, raw_data: Dict[str, Any], image_url: Optional[str] = None,
                        embedding: Optional[List[float]] = None) -> Dict[str, Any]:
        """Map raw scraped data to database schema."""

        # Generate unique ID
        product_id = self._generate_product_id(raw_data)

        # Extract basic information
        mapped_data = {
            'id': product_id,
            'source': raw_data.get('source', 'footshop_eu'),
            'product_url': raw_data.get('product_url'),
            'affiliate_url': None,  # Footshop doesn't provide affiliate URLs
            'image_url': image_url or self._extract_main_image(raw_data),
            'brand': self._extract_brand(raw_data),
            'title': self._extract_title(raw_data),
            'description': self._extract_description(raw_data),
            'category': self._extract_category(raw_data),
            'gender': self._extract_gender(raw_data),
            'price': self._extract_price(raw_data),
            'currency': self._extract_currency(raw_data),
            'created_at': datetime.now().isoformat(),
            'metadata': self._extract_metadata(raw_data),
            'size': None,  # Size information is per variant, not product
            'second_hand': False,  # Footshop is primarily new items
            'embedding': embedding,
            'country': raw_data.get('country', 'EU'),
            'compressed_image_url': self._create_compressed_image_url(image_url or self._extract_main_image(raw_data)),
            'tags': self._extract_tags(raw_data),
            'search_vector': None,  # Will be computed by PostgreSQL
            'search_tsv': None  # Will be computed by PostgreSQL
        }

        return mapped_data

    def _generate_product_id(self, raw_data: Dict[str, Any]) -> str:
        """Generate a unique product ID."""
        # Use the product's internal ID if available, otherwise create from URL
        product_id = raw_data.get('id') or raw_data.get('code')

        if product_id:
            return f"footshop_eu_{product_id}"
        else:
            # Fallback: hash the product URL
            import hashlib
            url = raw_data.get('product_url', '')
            return f"footshop_eu_{hashlib.md5(url.encode()).hexdigest()[:16]}"

    def _extract_main_image(self, raw_data: Dict[str, Any]) -> Optional[str]:
        """Extract the main product image URL."""
        # Try different possible image fields
        image_fields = ['image', 'main_image', 'primary_image']

        for field in image_fields:
            if raw_data.get(field):
                return raw_data[field]

        # Check for images array
        images = raw_data.get('images', [])
        if images and isinstance(images, list):
            return images[0]

        # Check for variants with images
        variants = raw_data.get('variants', [])
        if variants and isinstance(variants, list):
            for variant in variants:
                if variant.get('image'):
                    return variant['image']

        return None

    def _extract_brand(self, raw_data: Dict[str, Any]) -> Optional[str]:
        """Extract brand/manufacturer information."""
        brand_fields = ['manufacturer', 'brand', 'brand_name']

        for field in brand_fields:
            brand_data = raw_data.get(field)
            if brand_data:
                if isinstance(brand_data, dict):
                    return brand_data.get('name')
                elif isinstance(brand_data, str):
                    return brand_data

        return None

    def _extract_title(self, raw_data: Dict[str, Any]) -> str:
        """Extract product title."""
        title_fields = ['name', 'title', 'product_name']

        for field in title_fields:
            title = raw_data.get(field)
            if title:
                return str(title)

        return "Unknown Product"

    def _extract_description(self, raw_data: Dict[str, Any]) -> Optional[str]:
        """Extract product description."""
        return raw_data.get('description')

    def _extract_category(self, raw_data: Dict[str, Any]) -> Optional[str]:
        """Extract product category."""
        # Try direct category field
        if raw_data.get('category'):
            return raw_data['category']

        # Try main_category
        main_category = raw_data.get('main_category')
        if main_category:
            if isinstance(main_category, dict):
                return main_category.get('name_en') or main_category.get('name')
            elif isinstance(main_category, str):
                return main_category

        return None

    def _extract_gender(self, raw_data: Dict[str, Any]) -> Optional[str]:
        """Extract gender information."""
        return raw_data.get('gender')

    def _extract_price(self, raw_data: Dict[str, Any]) -> Optional[float]:
        """Extract product price."""
        price_data = raw_data.get('price')

        if not price_data:
            return None

        if isinstance(price_data, dict):
            # Try different price fields
            price_fields = ['value', 'amount', 'price']
            for field in price_fields:
                price = price_data.get(field)
                if price is not None:
                    try:
                        return float(price)
                    except (ValueError, TypeError):
                        continue
        elif isinstance(price_data, (int, float)):
            return float(price_data)

        return None

    def _extract_currency(self, raw_data: Dict[str, Any]) -> Optional[str]:
        """Extract currency information."""
        price_data = raw_data.get('price')

        if isinstance(price_data, dict):
            currency_fields = ['currency_code', 'currency', 'code']
            for field in currency_fields:
                currency = price_data.get(field)
                if currency:
                    return str(currency)

        return 'EUR'  # Default for Footshop EU

    def _extract_metadata(self, raw_data: Dict[str, Any]) -> Optional[str]:
        """Extract additional metadata as JSON string."""
        # Include fields that don't have dedicated columns
        metadata_fields = [
            'code', 'type', 'color', 'color_en', 'variants', 'specifications',
            'materials', 'care_instructions', 'weight', 'dimensions'
        ]

        metadata = {}
        for field in metadata_fields:
            if raw_data.get(field) is not None:
                metadata[field] = raw_data[field]

        if metadata:
            try:
                return json.dumps(metadata, ensure_ascii=False)
            except Exception as e:
                logger.warning(f"Failed to serialize metadata: {e}")
                return None

        return None

    def _create_compressed_image_url(self, image_url: Optional[str]) -> Optional[str]:
        """Create a compressed version of the image URL."""
        if not image_url:
            return None

        # Footshop uses static.ftshp.digital for images
        # Try to create a smaller version
        if 'static.ftshp.digital' in image_url:
            # Replace with smaller size if available
            compressed_url = image_url.replace('full_product', 'medium_product')
            return compressed_url

        return image_url

    def _extract_tags(self, raw_data: Dict[str, Any]) -> Optional[List[str]]:
        """Extract tags for the product."""
        tags = []

        # Add brand as tag
        brand = self._extract_brand(raw_data)
        if brand:
            tags.append(brand.lower().replace(' ', '_'))

        # Add category as tag
        category = self._extract_category(raw_data)
        if category:
            tags.append(category.lower().replace(' ', '_'))

        # Add gender as tag
        gender = self._extract_gender(raw_data)
        if gender:
            tags.append(f"gender_{gender}")

        # Add color as tag if available
        color = raw_data.get('color_en') or raw_data.get('color')
        if color:
            tags.append(color.lower().replace(' ', '_'))

        return tags if tags else None
