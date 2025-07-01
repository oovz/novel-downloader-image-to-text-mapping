#!/usr/bin/env python3
"""
Main orchestrator script for the novel downloader image-to-text mapping validation pipeline.

This script coordinates all validation, cleaning, sorting, synchronization, and minification
operations for the filename and hash mapping JSON files.
"""

import argparse
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

from .utils.logger import get_logger, log_progress, log_result
from .validators.json_validator import validate_json_files
from .validators.duplicate_remover import remove_duplicates_from_files
from .validators.sorter import sort_mappings_files
from .validators.hash_validator import validate_hash_files
from .validators.minifier import minify_json_files
from .processors.sync_processor import sync_all_domain_mappings
from .models.validation_result import ValidationResult

logger = get_logger(__name__)


def setup_argument_parser() -> argparse.ArgumentParser:
    """Set up command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Validation and synchronization pipeline for image-to-text mappings",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m scripts.main --validate-only
  python -m scripts.main --sync-only
  python -m scripts.main --full-pipeline
  python -m scripts.main --domains www.example.com --skip-minify
        """
    )
    
    parser.add_argument(
        "--mappings-dir",
        type=Path,
        default=Path("."),
        help="Base directory containing filename-mappings/ and hash-mappings/ subdirectories (default: current directory)"
    )
    
    parser.add_argument(
        "--temp-dir",
        type=Path,
        default=Path("temp"),
        help="Directory for temporary files and downloaded images (default: temp/)"
    )
    
    parser.add_argument(
        "--domains",
        nargs="+",
        help="Specific domains to process (e.g., www.example.com). If not specified, all domains are processed."
    )
    
    # Operation modes
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--validate-only",
        action="store_true",
        help="Only run validation steps (JSON format, duplicates, sorting, hash validation)"
    )
    
    mode_group.add_argument(
        "--sync-only",
        action="store_true",
        help="Only run synchronization (download missing images and create hashes)"
    )
    
    mode_group.add_argument(
        "--full-pipeline",
        action="store_true",
        help="Run complete pipeline: validation, cleaning, sorting, sync, and minification"
    )
    
    # Individual step controls
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip JSON format validation"
    )
    
    parser.add_argument(
        "--skip-duplicate-removal",
        action="store_true",
        help="Skip duplicate removal step"
    )
    
    parser.add_argument(
        "--skip-sorting",
        action="store_true",
        help="Skip sorting step"
    )
    
    parser.add_argument(
        "--skip-hash-validation",
        action="store_true",
        help="Skip hash validation step"
    )
    
    parser.add_argument(
        "--skip-minify",
        action="store_true",
        help="Skip minification step"
    )
    
    parser.add_argument(
        "--skip-sync",
        action="store_true",
        help="Skip synchronization step"
    )
    
    # Logging options
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--log-file",
        type=Path,
        help="Write logs to file in addition to console"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    
    return parser


def validate_directories(mappings_dir: Path) -> bool:
    """
    Validate that required directories exist.
    
    Args:
        mappings_dir: Base directory containing mapping subdirectories
        
    Returns:
        True if directories are valid, False otherwise
    """
    filename_dir = mappings_dir / "filename-mappings"
    hash_dir = mappings_dir / "hash-mappings"
    
    if not filename_dir.exists():
        logger.error(f"Filename mappings directory not found: {filename_dir}")
        return False
    
    if not hash_dir.exists():
        logger.error(f"Hash mappings directory not found: {hash_dir}")
        return False
    
    if not any(filename_dir.glob("*.json")):
        logger.error(f"No JSON files found in filename mappings directory: {filename_dir}")
        return False
    
    logger.info(f"Directory structure validated: {mappings_dir}")
    return True


def run_validation_pipeline(
    mappings_dir: Path,
    domains: Optional[List[str]] = None,
    skip_validation: bool = False,
    skip_duplicate_removal: bool = False,
    skip_sorting: bool = False,
    skip_hash_validation: bool = False,
    dry_run: bool = False
) -> Dict[str, ValidationResult]:
    """
    Run the validation pipeline.
    
    Args:
        mappings_dir: Base directory containing mapping subdirectories
        domains: Specific domains to process, or None for all
        skip_validation: Skip JSON format validation
        skip_duplicate_removal: Skip duplicate removal
        skip_sorting: Skip sorting
        skip_hash_validation: Skip hash validation
        dry_run: Show what would be done without making changes
        
    Returns:
        Dictionary of step results
    """
    results: Dict[str, ValidationResult] = {}
    
    # JSON format validation
    if not skip_validation:
        log_progress("Running JSON format validation")
        filename_dir = mappings_dir / "filename-mappings"
        hash_dir = mappings_dir / "hash-mappings"
        
        if domains:
            filename_files = [filename_dir / f"{domain}.json" for domain in domains]
            hash_files = [hash_dir / f"{domain}.json" for domain in domains]
            # Filter to only existing files
            filename_files = [f for f in filename_files if f.exists()]
            hash_files = [f for f in hash_files if f.exists()]
        else:
            filename_files = list(filename_dir.glob("*.json"))
            hash_files = list(hash_dir.glob("*.json"))
        
        if not dry_run:
            validation_result = validate_json_files([str(f) for f in filename_files + hash_files])
            results["json_validation"] = validation_result
            log_result("JSON Validation", validation_result)
            
            if not validation_result.success:
                logger.error("JSON validation failed, stopping pipeline")
                return results
        else:
            logger.info(f"DRY RUN: Would validate {len(filename_files + hash_files)} JSON files")
    
    # Duplicate removal
    if not skip_duplicate_removal:
        log_progress("Running duplicate removal")
        filename_dir = mappings_dir / "filename-mappings"
        
        if domains:
            filename_files = [filename_dir / f"{domain}.json" for domain in domains if (filename_dir / f"{domain}.json").exists()]
        else:
            filename_files = list(filename_dir.glob("*.json"))
        
        if not dry_run:
            duplicate_result = remove_duplicates_from_files([str(f) for f in filename_files])
            results["duplicate_removal"] = duplicate_result
            log_result("Duplicate Removal", duplicate_result)
        else:
            logger.info(f"DRY RUN: Would remove duplicates from {len(filename_files)} files")
    
    # Sorting
    if not skip_sorting:
        log_progress("Running sorting")
        filename_dir = mappings_dir / "filename-mappings"
        
        if domains:
            filename_files = [filename_dir / f"{domain}.json" for domain in domains if (filename_dir / f"{domain}.json").exists()]
        else:
            filename_files = list(filename_dir.glob("*.json"))
        
        if not dry_run:
            sort_result = sort_mappings_files([str(f) for f in filename_files])
            results["sorting"] = sort_result
            log_result("Sorting", sort_result)
        else:
            logger.info(f"DRY RUN: Would sort {len(filename_files)} files")
    
    # Hash validation
    if not skip_hash_validation:
        log_progress("Running hash validation")
        hash_dir = mappings_dir / "hash-mappings"
        
        if domains:
            hash_files = [hash_dir / f"{domain}.json" for domain in domains if (hash_dir / f"{domain}.json").exists()]
        else:
            hash_files = list(hash_dir.glob("*.json"))
        
        if not dry_run:
            hash_result = validate_hash_files([str(f) for f in hash_files])
            results["hash_validation"] = hash_result
            log_result("Hash Validation", hash_result)
        else:
            logger.info(f"DRY RUN: Would validate {len(hash_files)} hash files")
    
    return results


def run_minification(
    mappings_dir: Path,
    domains: Optional[List[str]] = None,
    dry_run: bool = False
) -> ValidationResult:
    """
    Run minification step.
    
    Args:
        mappings_dir: Base directory containing mapping subdirectories
        domains: Specific domains to process, or None for all
        dry_run: Show what would be done without making changes
        
    Returns:
        Minification result
    """
    log_progress("Running minification")
    
    # Collect all JSON files (excluding already minified files)
    all_files: List[Path] = []
    for subdir in ["filename-mappings", "hash-mappings"]:
        json_dir = mappings_dir / subdir
        if json_dir.exists():
            if domains:
                # For specific domains, ensure we don't process .min domains
                valid_domains = [d for d in domains if not d.endswith('.min')]
                domain_files = [json_dir / f"{domain}.json" for domain in valid_domains if (json_dir / f"{domain}.json").exists()]
                all_files.extend(domain_files)
            else:
                # Get all .json files but exclude .min.json files
                json_files = [f for f in json_dir.glob("*.json") if not f.name.endswith(".min.json")]
                all_files.extend(json_files)
    
    if not dry_run:
        minify_result = minify_json_files([str(f) for f in all_files])
        log_result("Minification", minify_result)
        return minify_result
    else:
        logger.info(f"DRY RUN: Would minify {len(all_files)} files")
        result = ValidationResult(success=True)
        result.details = {"message": "Dry run - no files minified"}
        return result


def run_synchronization(
    mappings_dir: Path,
    temp_dir: Path,
    domains: Optional[List[str]] = None,
    dry_run: bool = False
) -> Dict[str, ValidationResult]:
    """
    Run synchronization step.
    
    Args:
        mappings_dir: Base directory containing mapping subdirectories
        temp_dir: Directory for temporary files
        domains: Specific domains to process, or None for all
        dry_run: Show what would be done without making changes
        
    Returns:
        Dictionary of domain sync results
    """
    log_progress("Running synchronization")
    
    if dry_run:
        logger.info("DRY RUN: Would synchronize filename and hash mappings")
        return {}
    
    if domains:
        from .processors.sync_processor import SyncProcessor
        processor = SyncProcessor(temp_dir=temp_dir)
        
        results = {}
        for domain in domains:
            log_progress(f"Synchronizing domain: {domain}")
            result = processor.sync_domain(domain, mappings_dir)
            results[domain] = result
            log_result(f"Sync {domain}", result)
        
        return results
    else:
        sync_results = sync_all_domain_mappings(mappings_dir)
        
        # Log results
        for domain, result in sync_results.items():
            log_result(f"Sync {domain}", result)
        
        return sync_results


def main():
    """Main entry point."""
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    # Configure logging
    global logger
    logger = get_logger(
        __name__,
        log_level=args.log_level,
        log_file=str(args.log_file) if args.log_file else None
    )
    
    # Validate directories
    if not validate_directories(args.mappings_dir):
        sys.exit(1)
    
    # Create temp directory if needed
    if not args.dry_run:
        args.temp_dir.mkdir(exist_ok=True)
    
    # Determine what to run
    if args.validate_only:
        run_validation = True
        run_minify = False
        run_sync = False
    elif args.sync_only:
        run_validation = False
        run_minify = False
        run_sync = True
    elif args.full_pipeline:
        run_validation = True
        run_minify = True
        run_sync = True
    else:
        # Default: run validation and minification, but not sync
        run_validation = True
        run_minify = not args.skip_minify
        run_sync = not args.skip_sync
    
    start_time = time.time()
    all_results = {}
    
    try:
        # Run validation pipeline
        if run_validation:
            validation_results = run_validation_pipeline(
                args.mappings_dir,
                domains=args.domains,
                skip_validation=args.skip_validation,
                skip_duplicate_removal=args.skip_duplicate_removal,
                skip_sorting=args.skip_sorting,
                skip_hash_validation=args.skip_hash_validation,
                dry_run=args.dry_run
            )
            all_results.update(validation_results)
            
            # Check if validation passed
            if not args.dry_run:
                validation_passed = all(result.success for result in validation_results.values())
                if not validation_passed:
                    logger.error("Validation failed, stopping pipeline")
                    sys.exit(1)
        
        # Run synchronization BEFORE minification
        # This ensures new hash mappings are created before minified files
        if run_sync:
            sync_results = run_synchronization(
                args.mappings_dir,
                args.temp_dir,
                domains=args.domains,
                dry_run=args.dry_run
            )
            all_results.update(sync_results)
        
        # Run minification AFTER synchronization
        if run_minify:
            minify_result = run_minification(
                args.mappings_dir,
                domains=args.domains,
                dry_run=args.dry_run
            )
            all_results["minification"] = minify_result
    
    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Pipeline failed with error: {e}")
        sys.exit(1)
    
    # Summary
    end_time = time.time()
    duration = end_time - start_time
    
    logger.info("=" * 60)
    logger.info("PIPELINE SUMMARY")
    logger.info("=" * 60)
    
    successful_steps = sum(1 for result in all_results.values() if hasattr(result, 'success') and result.success)
    total_steps = len(all_results)
    
    logger.info(f"Total execution time: {duration:.2f} seconds")
    logger.info(f"Steps completed: {successful_steps}/{total_steps}")
    
    if total_steps > 0:
        for step_name, result in all_results.items():
            if hasattr(result, 'success'):
                status = "✅ PASS" if result.success else "❌ FAIL"
                logger.info(f"  {step_name}: {status}")
            else:
                logger.info(f"  {step_name}: Completed")
    
    # Exit with appropriate code
    if total_steps > 0 and successful_steps < total_steps:
        logger.error("Some steps failed!")
        sys.exit(1)
    else:
        logger.info("All steps completed successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()
