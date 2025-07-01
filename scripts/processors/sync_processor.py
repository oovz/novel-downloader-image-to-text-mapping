"""
Sync processor module for coordinating validation, image downloading, and hash creation.

This module implements the main synchronization logic between filename mappings and
hash mappings, handling missing images by downloading them and creating hashes.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from ..config.domain_configs import get_domain_config
from ..models.validation_result import ValidationResult
from ..processors.image_downloader import ImageDownloader
from ..processors.image_hasher import ImageHasher
from ..utils.file_utils import read_json_file, write_json_file
from ..utils.logger import log_progress, log_result

logger = logging.getLogger(__name__)


class SyncProcessor:
    """Synchronizes filename mappings with hash mappings by downloading and hashing missing images."""
    
    def __init__(self, temp_dir: Path = Path("temp")):
        """
        Initialize the sync processor.
        
        Args:
            temp_dir: Directory for temporary files and downloaded images
        """
        self.temp_dir = temp_dir
        self.temp_dir.mkdir(exist_ok=True)
        
        # Initialize processors
        self.downloader = ImageDownloader(temp_dir=temp_dir)
        self.hasher = ImageHasher()
        
    def load_mappings(self, domain: str, mappings_dir: Path) -> Tuple[Dict[str, str], Dict[str, str]]:
        """
        Load filename and hash mappings for a domain.
        
        Args:
            domain: Domain name (e.g., 'www.xiguashuwu.com')
            mappings_dir: Base directory containing mapping subdirectories
            
        Returns:
            Tuple of (filename_mapping, hash_mapping)
        """
        filename_file = mappings_dir / "filename-mappings" / f"{domain}.json"
        hash_file = mappings_dir / "hash-mappings" / f"{domain}.json"
        
        filename_mapping = {}
        hash_mapping = {}
        
        # Load filename mapping
        if filename_file.exists():
            filename_mapping = read_json_file(filename_file) or {}
            logger.info(f"Loaded {len(filename_mapping)} filename mappings for {domain}")
        else:
            logger.warning(f"Filename mapping file not found: {filename_file}")
        
        # Load hash mapping
        if hash_file.exists():
            hash_mapping = read_json_file(hash_file) or {}
            logger.info(f"Loaded {len(hash_mapping)} hash mappings for {domain}")
        else:
            logger.warning(f"Hash mapping file not found: {hash_file}")
        
        return filename_mapping, hash_mapping
    
    def find_missing_hashes(
        self, 
        filename_mapping: Dict[str, str], 
        hash_mapping: Dict[str, str]
    ) -> Set[str]:
        """
        Find characters that exist in filename mapping but not in hash mapping.
        
        Args:
            filename_mapping: Dictionary mapping filenames to characters
            hash_mapping: Dictionary mapping hashes to characters
            
        Returns:
            Set of characters missing from hash mapping
        """
        filename_characters = set(filename_mapping.values())
        hash_characters = set(hash_mapping.values())
        
        missing_characters = filename_characters - hash_characters
        
        if missing_characters:
            logger.info(f"Found {len(missing_characters)} characters in filename mapping but not in hash mapping")
            logger.debug(f"Missing characters: {sorted(missing_characters)}")
        else:
            logger.info("All characters from filename mapping exist in hash mapping")
        
        return missing_characters
    
    def get_filenames_for_characters(
        self, 
        filename_mapping: Dict[str, str], 
        characters: Set[str]
    ) -> Dict[str, List[str]]:
        """
        Get filenames associated with specific characters.
        
        Args:
            filename_mapping: Dictionary mapping filenames to characters
            characters: Set of characters to find filenames for
            
        Returns:
            Dictionary mapping characters to lists of filenames
        """
        char_to_filenames: Dict[str, List[str]] = {}
        
        for filename, character in filename_mapping.items():
            if character in characters:
                if character not in char_to_filenames:
                    char_to_filenames[character] = []
                char_to_filenames[character].append(filename)
        
        return char_to_filenames
    
    def process_missing_characters(
        self, 
        domain: str, 
        char_to_filenames: Dict[str, List[str]]
    ) -> ValidationResult:
        """
        Process missing characters by downloading images and creating hashes.
        
        Args:
            domain: Domain name
            char_to_filenames: Dictionary mapping characters to filenames
            
        Returns:
            ValidationResult with processing statistics
        """
        if not char_to_filenames:
            result = ValidationResult(success=True)
            result.details = {"message": "No missing characters to process"}
            return result
        
        # Check domain configuration
        config = get_domain_config(domain)
        if not config:
            result = ValidationResult(success=False)
            result.add_error(f"No configuration found for domain: {domain}")
            return result
        
        log_progress(f"Processing {len(char_to_filenames)} missing characters for domain {domain}")
        
        # Collect all filenames to download
        all_filenames: List[str] = []
        for filenames in char_to_filenames.values():
            all_filenames.extend(filenames)
        
        # Remove duplicates while preserving order
        unique_filenames: List[str] = []
        seen: Set[str] = set()
        for filename in all_filenames:
            if filename not in seen:
                unique_filenames.append(filename)
                seen.add(filename)
        
        logger.info(f"Need to download {len(unique_filenames)} unique images")
        
        # Download images
        download_result = self.downloader.download_images_sync(domain, unique_filenames)
        
        if not download_result.success:
            logger.error("Image download failed, cannot proceed with hash creation")
            return download_result
        
        # Create hashes for successfully downloaded images
        hash_results: Dict[str, str] = {}
        failed_hashes: List[str] = []
        
        for character, filenames in char_to_filenames.items():
            # Try to create hash for the first available image of this character
            character_hash = None
            
            for filename in filenames:
                image_path = self.downloader.get_downloaded_image_path(domain, filename)
                if image_path and image_path.exists():
                    try:
                        character_hash = self.hasher.hash_image_file(str(image_path))
                        if character_hash:
                            hash_results[character_hash] = character
                            logger.debug(f"Created hash for character '{character}' from file '{filename}': {character_hash}")
                            break
                    except Exception as e:
                        logger.warning(f"Failed to hash image {filename} for character '{character}': {e}")
                        continue
            
            if character_hash is None:
                failed_hashes.append(character)
                logger.error(f"Failed to create hash for character '{character}' (tried {len(filenames)} files)")
        
        # Create result
        result = ValidationResult(success=len(failed_hashes) == 0)
        result.processed_files = len(hash_results)
        result.total_files = len(char_to_filenames)
        result.details = {
            'domain': domain,
            'characters_processed': len(char_to_filenames),
            'hashes_created': len(hash_results),
            'failed_characters': len(failed_hashes),
            'download_stats': download_result.details
        }
        
        # Add errors for failed characters
        for character in failed_hashes:
            result.add_error(f"Failed to create hash for character: {character}")
        
        if len(failed_hashes) > 0:
            result.add_warning(f"Failed to create hashes for {len(failed_hashes)} characters")
        
        # Store hash results for use by caller
        result.details['hash_results'] = hash_results
        
        log_result(f"Hash Creation for {domain}", result)
        return result
    
    def update_hash_mapping(
        self, 
        hash_file: Path, 
        new_hashes: Dict[str, str]
    ) -> ValidationResult:
        """
        Update hash mapping file with new hashes.
        
        Args:
            hash_file: Path to hash mapping file
            new_hashes: Dictionary of new hashes to add (hash -> character)
            
        Returns:
            ValidationResult indicating success/failure
        """
        if not new_hashes:
            result = ValidationResult(success=True)
            result.details = {"message": "No new hashes to add"}
            return result
        
        # 备份功能已禁用 - 在git环境中不需要备份
        logger.debug("备份功能已禁用（使用git版本控制）")
        
        # Load existing mapping
        existing_mapping = {}
        if hash_file.exists():
            existing_mapping = read_json_file(hash_file) or {}
        
        # Check for conflicts
        conflicts = []
        for hash_value, character in new_hashes.items():
            if hash_value in existing_mapping and existing_mapping[hash_value] != character:
                conflicts.append(f"Hash {hash_value} maps to '{existing_mapping[hash_value]}' but trying to add '{character}'")
        
        if conflicts:
            result = ValidationResult(success=False)
            for conflict in conflicts:
                result.add_error(conflict)
            return result
        
        # Merge mappings
        updated_mapping = existing_mapping.copy()
        updated_mapping.update(new_hashes)
        
        # Save updated mapping
        try:
            write_json_file(hash_file, updated_mapping)
            
            result = ValidationResult(success=True)
            result.processed_files = len(new_hashes)
            result.total_files = len(updated_mapping)
            result.details = {
                'file': str(hash_file),
                'existing_hashes': len(existing_mapping),
                'new_hashes': len(new_hashes),
                'total_hashes': len(updated_mapping)
            }
            
            logger.info(f"Updated hash mapping: {len(existing_mapping)} -> {len(updated_mapping)} entries")
            return result
            
        except Exception as e:
            result = ValidationResult(success=False)
            result.add_error(f"Failed to save hash mapping file: {e}")
            return result
    
    def sync_domain(self, domain: str, mappings_dir: Path) -> ValidationResult:
        """
        Synchronize filename and hash mappings for a specific domain.
        
        Args:
            domain: Domain name (e.g., 'www.xiguashuwu.com')
            mappings_dir: Base directory containing mapping subdirectories
            
        Returns:
            ValidationResult with synchronization statistics
        """
        log_progress(f"Starting synchronization for domain: {domain}")
        
        # Load mappings
        try:
            filename_mapping, hash_mapping = self.load_mappings(domain, mappings_dir)
        except Exception as e:
            result = ValidationResult(success=False)
            result.add_error(f"Failed to load mappings for domain {domain}: {e}")
            return result
        
        # Find missing characters
        missing_characters = self.find_missing_hashes(filename_mapping, hash_mapping)
        
        if not missing_characters:
            result = ValidationResult(success=True)
            result.details = {
                'domain': domain,
                'message': 'All characters from filename mapping exist in hash mapping',
                'filename_entries': len(filename_mapping),
                'hash_entries': len(hash_mapping)
            }
            log_result(f"Sync for {domain}", result)
            return result
        
        # Get filenames for missing characters
        char_to_filenames = self.get_filenames_for_characters(filename_mapping, missing_characters)
        
        # Process missing characters (download images and create hashes)
        process_result = self.process_missing_characters(domain, char_to_filenames)
        
        if not process_result.success:
            return process_result
        
        # Update hash mapping file with new hashes
        new_hashes = process_result.details.get('hash_results', {})
        if new_hashes:
            hash_file = mappings_dir / "hash-mappings" / f"{domain}.json"
            update_result = self.update_hash_mapping(hash_file, new_hashes)
            
            if not update_result.success:
                return update_result
        
        # Create final result
        result = ValidationResult(success=True)
        result.processed_files = len(new_hashes)
        result.total_files = len(missing_characters)
        result.details = {
            'domain': domain,
            'missing_characters': len(missing_characters),
            'hashes_created': len(new_hashes),
            'filename_entries': len(filename_mapping),
            'hash_entries_before': len(hash_mapping),
            'hash_entries_after': len(hash_mapping) + len(new_hashes),
            'process_details': process_result.details
        }
        
        if len(new_hashes) < len(missing_characters):
            failed_count = len(missing_characters) - len(new_hashes)
            result.add_warning(f"Failed to create hashes for {failed_count} characters")
        
        log_result(f"Sync for {domain}", result)
        return result
    
    def sync_all_domains(self, mappings_dir: Path) -> Dict[str, ValidationResult]:
        """
        Synchronize all domains found in the mappings directory.
        
        Args:
            mappings_dir: Base directory containing mapping subdirectories
            
        Returns:
            Dictionary mapping domain names to their ValidationResults
        """
        filename_dir = mappings_dir / "filename-mappings"
        
        if not filename_dir.exists():
            logger.error(f"Filename mappings directory not found: {filename_dir}")
            return {}
        
        # Find all domain JSON files (exclude minified and backup files)
        domain_files = list(filename_dir.glob("*.json"))
        # Filter out non-domain files like .min.json, .backup, etc.
        domains = []
        for f in domain_files:
            # Skip minified files (.min.json), backup files (.backup), and other non-domain files
            if not (f.name.endswith('.min.json') or '.backup' in f.name or f.name.startswith('.')):
                domains.append(f.stem)
        
        if not domains:
            logger.warning(f"No domain files found in {filename_dir}")
            return {}
        
        log_progress(f"Starting synchronization for {len(domains)} domains: {', '.join(domains)}")
        
        results = {}
        for domain in domains:
            try:
                result = self.sync_domain(domain, mappings_dir)
                results[domain] = result
            except Exception as e:
                logger.error(f"Error synchronizing domain {domain}: {e}")
                error_result = ValidationResult(success=False)
                error_result.add_error(f"Exception during sync: {e}")
                results[domain] = error_result
        
        # Log summary
        successful = sum(1 for r in results.values() if r.success)
        total = len(results)
        
        logger.info(f"Synchronization completed: {successful}/{total} domains successful")
        
        return results


def sync_domain_mappings(domain: str, mappings_dir: Path = Path(".")) -> ValidationResult:
    """
    Convenience function to synchronize a specific domain.
    
    Args:
        domain: Domain name to synchronize
        mappings_dir: Base directory containing mapping subdirectories
        
    Returns:
        ValidationResult with synchronization statistics
    """
    processor = SyncProcessor()
    return processor.sync_domain(domain, mappings_dir)


def sync_all_domain_mappings(mappings_dir: Path = Path(".")) -> Dict[str, ValidationResult]:
    """
    Convenience function to synchronize all domains.
    
    Args:
        mappings_dir: Base directory containing mapping subdirectories
        
    Returns:
        Dictionary mapping domain names to their ValidationResults
    """
    processor = SyncProcessor()
    return processor.sync_all_domains(mappings_dir)
