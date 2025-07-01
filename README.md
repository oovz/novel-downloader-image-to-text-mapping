When you commit changes to the mapping JSON files, the repository automatically runs validation, cleaning, sorting, synchronization, and minification.

## How It Works

1. **Commit Changes**: Push mapping file changes to the `master` branch
2. **Automatic Processing**: GitHub Actions automatically runs the processing pipeline
3. **Auto-Commit Results**: Processed files are automatically committed back to the repository

## Repository Structure

```
.
├── filename-mappings/
│   ├── www.domain1.com.json         # Image filename to character mappings
│   ├── www.domain1.com.min.json     # minified version of filename mappings
│   └── www.domain2.com.json
├── hash-mappings/
│   ├── www.domain1.com.json         # Image hash to character mappings
│   └── www.domain2.com.json
└── .github/workflows/
    └── validate-mappings.yml        # Automatic processing workflow
```

## File Formats

### Filename Mapping Format
```json
{
    "image1.png": "字",
    "image2.jpg": "符", 
    "image3.gif": "文"
}
```

### Hash Mapping Format
```json
{
    "0110100110010110100110010110100110010110100110010110100110010110": "字",
    "1001011010011001011010011001011010011001011010011001011010011001": "符"
}
```

## Automatic Processing Pipeline

When you commit changes, the system automatically:

1. **Validates JSON**: Checks file format and structure
2. **Removes Duplicates**: Cleans duplicate entries from filename mappings
3. **Sorts Mappings**: Groups by character, then sorts by filename
4. **Validates Hashes**: Ensures hash uniqueness 
5. **Generates Minified Files**: Creates compressed versions (`.min.json`)
6. **Synchronizes Data**: Downloads missing images and generates hashes for new characters

## Manual Execution (Optional)

If you need to run the pipeline manually for development or testing:
### Prerequisites for Manual Execution
- Python 3.11 or higher
- [uv](https://docs.astral.sh/uv/) package manager

### Setup for Manual Execution
1. Clone the repository
2. Install uv:
   ```bash
   # On Windows
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   
   # On macOS/Linux  
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
3. Install dependencies:
   ```bash
   uv sync
   ```

### Manual Commands
```bash
# Run full pipeline
uv run validate-mappings --full-pipeline

# Validation only
uv run validate-mappings --validate-only

# Sync only (download images and generate hashes)
uv run validate-mappings --sync-only

# Specific domains
uv run validate-mappings --domains www.example.com --full-pipeline

# Dry run (see what would be done)
uv run validate-mappings --dry-run --full-pipeline
```

## Adding New Domains

To add support for a new domain, create a configuration in `scripts/config/domain_configs.py`:

```python
DOMAIN_CONFIGS = {
    "www.newdomain.com": DomainConfig(
        domain="www.newdomain.com",
        image_url_pattern="https://www.newdomain.com/images/{filename}",
        headers={
            "User-Agent": "Mozilla/5.0 ...",
            "Referer": "https://www.newdomain.com/"
        },
        rate_limit_delay=1.0,
        max_retries=3,
        timeout=30
    )
}
```

## License

MIT License - see LICENSE file for details.
