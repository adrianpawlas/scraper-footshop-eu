import requests
import torch
from PIL import Image
from transformers import AutoProcessor, AutoModel
from typing import List, Optional, Tuple
import io
import os
import hashlib
from config import IMAGE_SIZE, EMBEDDING_DIM, REQUEST_TIMEOUT
from scraper.utils import retry_on_failure, RateLimiter
import logging

logger = logging.getLogger(__name__)

class ImageProcessor:
    """Handles image downloading and embedding generation using SigLIP."""

    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Using device: {self.device}")
        self.rate_limiter = RateLimiter(requests_per_second=2.0)  # Higher rate for images

        # Initialize SigLIP model
        try:
            self.processor = AutoProcessor.from_pretrained("google/siglip-base-patch16-384")
            self.model = AutoModel.from_pretrained("google/siglip-base-patch16-384")
            self.model.to(self.device)
            self.model.eval()
            logger.info("SigLIP model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load SigLIP model: {e}")
            raise

    @retry_on_failure(max_attempts=3)
    def download_image(self, image_url: str) -> Optional[Image.Image]:
        """Download image from URL and return PIL Image."""
        try:
            logger.debug(f"Downloading image: {image_url}")
            self.rate_limiter.wait_if_needed_sync()
            response = requests.get(image_url, timeout=REQUEST_TIMEOUT, stream=True)
            response.raise_for_status()

            # Convert to PIL Image
            image = Image.open(io.BytesIO(response.content))

            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')

            return image

        except requests.RequestException as e:
            logger.warning(f"Failed to download image {image_url}: {e}")
            return None
        except Exception as e:
            logger.warning(f"Failed to process image {image_url}: {e}")
            return None

    def generate_embedding(self, image: Image.Image) -> Optional[List[float]]:
        """Generate 768-dimensional embedding for an image."""
        try:
            # Preprocess image
            inputs = self.processor(images=image, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Generate embedding
            with torch.no_grad():
                outputs = self.model(**inputs)
                # Use the pooled output for image embeddings
                embedding = outputs.pooler_output.squeeze().cpu().numpy()

            # Ensure correct dimension
            if embedding.shape[0] != EMBEDDING_DIM:
                logger.warning(f"Unexpected embedding dimension: {embedding.shape[0]}, expected {EMBEDDING_DIM}")
                return None

            return embedding.tolist()

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None

    def process_product_images(self, image_urls: List[str]) -> Tuple[Optional[str], Optional[List[float]]]:
        """
        Process product images: download first available image and generate embedding.
        Returns (image_url, embedding)
        """
        if not image_urls:
            return None, None

        # Try to download and process each image until successful
        for image_url in image_urls:
            image = self.download_image(image_url)
            if image:
                # Resize image to required size
                image = image.resize(IMAGE_SIZE, Image.Resampling.LANCZOS)

                # Generate embedding
                embedding = self.generate_embedding(image)

                if embedding:
                    logger.info(f"Successfully processed image: {image_url}")
                    return image_url, embedding
                else:
                    logger.warning(f"Failed to generate embedding for image: {image_url}")
            else:
                logger.warning(f"Failed to download image: {image_url}")

        logger.warning("Failed to process any images for product")
        return None, None

    def create_compressed_image_url(self, image_url: str) -> str:
        """Create a compressed version URL (if Footshop provides one)."""
        # Footshop might have different image sizes, try to create a compressed version
        # This is a simple approach - in practice, you'd need to check what sizes are available
        if 'static.ftshp.digital' in image_url:
            # Replace full_product with a smaller size if available
            compressed_url = image_url.replace('full_product', 'medium_product')
            return compressed_url
        return image_url

    def generate_image_hash(self, image_url: str) -> str:
        """Generate a hash for the image URL for caching purposes."""
        return hashlib.md5(image_url.encode()).hexdigest()
