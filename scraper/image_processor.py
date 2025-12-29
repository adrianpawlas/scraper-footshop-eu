import requests
import torch
from PIL import Image
from transformers import AutoProcessor, AutoModel, SiglipImageProcessor
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

        # Initialize SigLIP model - REQUIRED for embeddings
        model_name = "google/siglip-base-patch16-384"

        try:
            logger.info(f"Loading SigLIP model: {model_name}")

            # Try SigLIP-specific processor first
            try:
                self.processor = SiglipImageProcessor.from_pretrained(model_name)
                logger.info("Using SigLIP-specific image processor")
            except Exception as proc_e:
                logger.warning(f"SigLIP-specific processor failed: {proc_e}, trying AutoProcessor")
                # Fallback to AutoProcessor
                self.processor = AutoProcessor.from_pretrained(model_name)
                logger.info("Using AutoProcessor for SigLIP")

            self.model = AutoModel.from_pretrained(model_name)
            self.model.to(self.device)
            self.model.eval()
            self.model_type = "SigLIP"
            logger.info("SigLIP model loaded successfully - embeddings will be generated")

        except Exception as e:
            logger.error(f"CRITICAL: Failed to load SigLIP model {model_name}: {e}")
            logger.error("Embeddings are REQUIRED - scraper cannot continue without SigLIP")
            raise RuntimeError(f"SigLIP model loading failed: {e}. Embeddings are mandatory for this scraper.")

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

    def generate_embedding(self, image: Image.Image) -> List[float]:
        """Generate 768-dimensional SigLIP embedding for an image. REQUIRED - no fallbacks."""
        if self.model is None or self.processor is None:
            raise RuntimeError("SigLIP model not loaded - embeddings are mandatory")

        if self.model_type != "SigLIP":
            raise RuntimeError("Only SigLIP embeddings are supported - no fallbacks allowed")

        try:
            # Preprocess image
            inputs = self.processor(images=image, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Generate SigLIP embedding
            with torch.no_grad():
                outputs = self.model(**inputs)
                # Use the pooled output for image embeddings
                embedding = outputs.pooler_output.squeeze().cpu().numpy()

            # Ensure we have a 1D array
            if embedding.ndim > 1:
                embedding = embedding.flatten()

            # Verify correct dimension (768 for siglip-base-patch16-384)
            if len(embedding) != EMBEDDING_DIM:
                raise ValueError(f"SigLIP embedding dimension mismatch: got {len(embedding)}, expected {EMBEDDING_DIM}")

            logger.debug(f"Generated SigLIP embedding with {len(embedding)} dimensions")
            return embedding.tolist()

        except Exception as e:
            logger.error(f"CRITICAL: Failed to generate SigLIP embedding: {e}")
            raise RuntimeError(f"SigLIP embedding generation failed: {e}")

    def process_product_images(self, image_urls: List[str]) -> Tuple[str, List[float]]:
        """
        Process product images: download first available image and generate SigLIP embedding.
        REQUIRED - fails if no embedding can be generated.
        Returns (image_url, embedding)
        """
        if not image_urls:
            raise RuntimeError("No image URLs provided - cannot generate embeddings")

        # Try to download and process each image until successful
        for image_url in image_urls:
            image = self.download_image(image_url)
            if image:
                # Resize image to required size for SigLIP
                image = image.resize(IMAGE_SIZE, Image.Resampling.LANCZOS)

                try:
                    # Generate SigLIP embedding (required)
                    embedding = self.generate_embedding(image)
                    logger.info(f"Successfully generated SigLIP embedding for image: {image_url}")
                    return image_url, embedding
                except Exception as e:
                    logger.warning(f"Failed to generate SigLIP embedding for image {image_url}: {e}")
                    continue
            else:
                logger.warning(f"Failed to download image: {image_url}")

        # If we get here, no images worked
        raise RuntimeError(f"CRITICAL: Failed to generate SigLIP embeddings for any of the {len(image_urls)} image URLs. Embeddings are mandatory.")

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
