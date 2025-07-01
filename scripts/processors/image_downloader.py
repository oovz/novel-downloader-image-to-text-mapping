"""
Image downloader module for downloading images from various domains.

This module handles downloading images from different domains using domain-specific
configurations including custom headers, URL transformations, and retry logic.
"""

import asyncio
import io
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urlparse

import aiohttp  # type: ignore
from aiohttp import ClientTimeout  # type: ignore
from PIL import Image  # type: ignore

from ..config.domain_configs import get_domain_config
from ..models.validation_result import ValidationResult
from ..utils.logger import log_progress, log_result

logger = logging.getLogger(__name__)


class ImageDownloader:
    """Downloads images from various domains with domain-specific configurations."""
    
    def __init__(self, temp_dir: Path = Path("temp"), max_concurrent: int = 5):
        """
        Initialize the image downloader.
        
        Args:
            temp_dir: Directory to store temporary downloaded images
            max_concurrent: Maximum number of concurrent downloads
        """
        self.temp_dir = temp_dir
        self.max_concurrent = max_concurrent
        self.temp_dir.mkdir(exist_ok=True)
        
        # Session configuration
        self.session_timeout = ClientTimeout(total=30, connect=10)
        self.max_retries = 3
        self.retry_delay = 1.0
        
        # Download statistics
        self.stats: Dict[str, Any] = {
            'downloaded': 0,
            'failed': 0,
            'cached': 0,
            'errors': []
        }
    
    def construct_image_url(self, domain: str, filename: str) -> Optional[str]:
        """
        Construct the full image URL from domain and filename.
        
        Args:
            domain: Domain name (e.g., 'www.xiguashuwu.com')
            filename: Image filename (e.g., 'image.png')
            
        Returns:
            Full image URL or None if domain not supported
        """
        try:
            config = get_domain_config(domain)
            if not config:
                logger.warning(f"No configuration found for domain: {domain}")
                return None
            
            # Apply URL pattern transformation
            url = config.build_image_url(filename)
            
            # Validate URL
            try:
                parsed = urlparse(url)
                if not parsed.scheme or not parsed.netloc:
                    logger.error(f"Invalid URL constructed: {url}")
                    return None
            except Exception as parse_error:
                logger.error(f"URL parse error for {url}: {parse_error}")
                return None
            
            return url
            
        except Exception as e:
            logger.error(f"Error constructing URL for {domain}/{filename}: {e}")
            return None
    
    def get_cached_image_path(self, domain: str, filename: str) -> Path:
        """Get the path where the cached image would be stored."""
        safe_filename = "".join(c for c in filename if c.isalnum() or c in ".-_")
        return self.temp_dir / f"{domain}_{safe_filename}"
    
    def is_image_cached(self, domain: str, filename: str) -> bool:
        """Check if image is already cached locally."""
        cache_path = self.get_cached_image_path(domain, filename)
        return cache_path.exists() and cache_path.stat().st_size > 0
    
    async def download_image_async(
        self, 
        session: Any,  # aiohttp.ClientSession 
        domain: str, 
        filename: str
    ) -> Tuple[str, bool, Optional[str]]:
        """
        Download a single image asynchronously.
        
        Args:
            session: aiohttp session
            domain: Domain name
            filename: Image filename
            
        Returns:
            Tuple of (filename, success, error_message)
        """
        # Check cache first
        if self.is_image_cached(domain, filename):
            self.stats['cached'] += 1
            return filename, True, None
        
        url = self.construct_image_url(domain, filename)
        if not url:
            error_msg = f"Could not construct URL for {domain}/{filename}"
            self.stats['errors'].append(error_msg)
            self.stats['failed'] += 1
            return filename, False, error_msg
        
        cache_path = self.get_cached_image_path(domain, filename)
        config = get_domain_config(domain)
        
        for attempt in range(self.max_retries):
            try:
                # Add delay between retries
                if attempt > 0:
                    await asyncio.sleep(self.retry_delay * attempt)
                
                async with session.get(url, headers=config.headers if config else {}) as response:
                    if response.status == 200:
                        # Validate content type
                        content_type = response.headers.get('Content-Type', '')
                        if not content_type.startswith('image/'):
                            error_msg = f"Invalid content type: {content_type} for {url}"
                            logger.warning(error_msg)
                        
                        # Download and save
                        content = await response.read()
                        if len(content) == 0:
                            raise Exception("Empty response")
                        
                        # Verify it's a valid image by trying to open it
                        try:
                            image = Image.open(io.BytesIO(content))
                            image.verify()  # Verify it's a valid image
                        except Exception as e:
                            raise Exception(f"Invalid image data: {e}")
                        
                        # Save to cache
                        with open(cache_path, 'wb') as f:
                            f.write(content)
                        
                        self.stats['downloaded'] += 1
                        logger.debug(f"Downloaded: {url} -> {cache_path}")
                        return filename, True, None
                    
                    else:
                        error_msg = f"HTTP {response.status} for {url}"
                        if attempt == self.max_retries - 1:
                            logger.error(error_msg)
                            self.stats['errors'].append(error_msg)
                            self.stats['failed'] += 1
                            return filename, False, error_msg
                        else:
                            logger.warning(f"{error_msg} (attempt {attempt + 1}/{self.max_retries})")
            
            except asyncio.TimeoutError:
                error_msg = f"Timeout downloading {url}"
                if attempt == self.max_retries - 1:
                    logger.error(error_msg)
                    self.stats['errors'].append(error_msg)
                    self.stats['failed'] += 1
                    return filename, False, error_msg
                else:
                    logger.warning(f"{error_msg} (attempt {attempt + 1}/{self.max_retries})")
            
            except Exception as e:
                error_msg = f"Error downloading {url}: {e}"
                if attempt == self.max_retries - 1:
                    logger.error(error_msg)
                    self.stats['errors'].append(error_msg)
                    self.stats['failed'] += 1
                    return filename, False, error_msg
                else:
                    logger.warning(f"{error_msg} (attempt {attempt + 1}/{self.max_retries})")
        
        # Should not reach here, but just in case
        return filename, False, "Max retries exceeded"
    
    async def download_images_batch_async(
        self, 
        domain: str, 
        filenames: List[str]
    ) -> ValidationResult:
        """
        Download a batch of images asynchronously.
        
        Args:
            domain: Domain name
            filenames: List of image filenames to download
            
        Returns:
            ValidationResult with download statistics
        """
        if not filenames:
            result = ValidationResult(success=True)
            result.details = {"message": "No images to download"}
            return result
        
        log_progress(f"Starting download of {len(filenames)} images from {domain}")
        
        # Reset stats
        self.stats: Dict[str, Any] = {
            'downloaded': 0,
            'failed': 0,
            'cached': 0,
            'errors': []
        }
        
        # Check domain configuration
        config = get_domain_config(domain)
        if not config:
            result = ValidationResult(success=False)
            result.add_error(f"No configuration found for domain: {domain}")
            result.details = {"domain": domain, "error": "Unsupported domain"}
            return result
        
        # Create semaphore for concurrent downloads
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def download_with_semaphore(session: Any, filename: str):  # aiohttp.ClientSession
            async with semaphore:
                return await self.download_image_async(session, domain, filename)
        
        # Download images
        connector = aiohttp.TCPConnector(limit=self.max_concurrent)  # type: ignore
        async with aiohttp.ClientSession(  # type: ignore
            connector=connector,
            timeout=self.session_timeout
        ) as session:
            tasks = [
                download_with_semaphore(session, filename)
                for filename in filenames
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        successful_downloads: List[str] = []
        failed_downloads: List[str] = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_msg = f"Exception downloading {filenames[i]}: {result}"
                logger.error(error_msg)
                self.stats['errors'].append(error_msg)
                self.stats['failed'] += 1
                failed_downloads.append(filenames[i])
            else:
                filename, success, error = result
                if success:
                    successful_downloads.append(filename)
                else:
                    failed_downloads.append(filename)
        
        # Create result
        total_processed = self.stats['downloaded'] + self.stats['failed'] + self.stats['cached']
        success = self.stats['failed'] == 0
        
        message_parts: List[str] = []
        if self.stats['downloaded'] > 0:
            message_parts.append(f"Downloaded: {self.stats['downloaded']}")
        if self.stats['cached'] > 0:
            message_parts.append(f"Cached: {self.stats['cached']}")
        if self.stats['failed'] > 0:
            message_parts.append(f"Failed: {self.stats['failed']}")
        
        message = f"Image download for {domain}: " + ", ".join(message_parts)
        
        result = ValidationResult(success=success)
        result.processed_files = total_processed
        result.total_files = len(filenames)
        result.details = {
            'message': message,
            'domain': domain,
            'downloaded': self.stats['downloaded'],
            'cached': self.stats['cached'],
            'failed': self.stats['failed'],
            'success_rate': (self.stats['downloaded'] + self.stats['cached']) / len(filenames) * 100
        }
        
        # Add errors (limit to first 10)
        for error in self.stats['errors'][:10]:
            result.add_error(error)
        
        # Add warning for failed downloads
        if not success:
            result.add_warning(f"Failed to download {len(failed_downloads)} images")
        
        log_result("Image Download", result)
        return result
    
    def download_images_sync(self, domain: str, filenames: List[str]) -> ValidationResult:
        """
        Synchronous wrapper for downloading images.
        
        Args:
            domain: Domain name
            filenames: List of image filenames to download
            
        Returns:
            ValidationResult with download statistics
        """
        try:
            # Check if we're already in an event loop
            try:
                asyncio.get_running_loop()
                # We're in an async context, use asyncio.create_task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.download_images_batch_async(domain, filenames))
                    return future.result()
            except RuntimeError:
                # No running loop, we can use asyncio.run
                return asyncio.run(self.download_images_batch_async(domain, filenames))
        
        except Exception as e:
            logger.error(f"Error in sync download wrapper: {e}")
            result = ValidationResult(success=False)
            result.add_error(f"Error downloading images: {e}")
            return result
    
    def get_downloaded_image_path(self, domain: str, filename: str) -> Optional[Path]:
        """
        Get the path to a downloaded image if it exists.
        
        Args:
            domain: Domain name
            filename: Image filename
            
        Returns:
            Path to downloaded image or None if not found
        """
        cache_path = self.get_cached_image_path(domain, filename)
        if cache_path.exists():
            return cache_path
        return None
    
    def cleanup_cache(self, max_age_hours: int = 24) -> int:
        """
        Clean up old cached images.
        
        Args:
            max_age_hours: Maximum age of cached images in hours
            
        Returns:
            Number of files cleaned up
        """
        if not self.temp_dir.exists():
            return 0
        
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        cleaned_count = 0
        
        try:
            for file_path in self.temp_dir.iterdir():
                if file_path.is_file():
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > max_age_seconds:
                        file_path.unlink()
                        cleaned_count += 1
                        logger.debug(f"Cleaned up old cache file: {file_path}")
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} old cache files")
        
        except Exception as e:
            logger.error(f"Error cleaning up cache: {e}")
        
        return cleaned_count




def download_images_for_domain(
    domain: str, 
    filenames: List[str], 
    temp_dir: Path = Path("temp"),
    max_concurrent: int = 5
) -> ValidationResult:
    """
    Convenience function to download images for a specific domain.
    
    Args:
        domain: Domain name
        filenames: List of image filenames to download
        temp_dir: Directory to store temporary images
        max_concurrent: Maximum concurrent downloads
        
    Returns:
        ValidationResult with download statistics
    """
    downloader = ImageDownloader(temp_dir=temp_dir, max_concurrent=max_concurrent)
    return downloader.download_images_sync(domain, filenames)
