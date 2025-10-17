#!/usr/bin/env python3
"""
TTAB Bulk Data Downloader

Downloads TTAB XML bulk data files from the USPTO Open Data Portal.
Supports both daily (TTABTDXF) and annual (TTABYR) datasets.
"""

import argparse
import logging
import os
import requests
import sys
from pathlib import Path
from datetime import datetime, timedelta
import json
import time
import zipfile

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TTABDownloader:
    """Downloads TTAB XML files from USPTO Open Data Portal."""
    
    # New USPTO Open Data Portal endpoints
    API_BASE_URL = "https://api.uspto.gov/api/v1/datasets/products"
    DAILY_PRODUCT_ID = "TTABTDXF"  # Daily TTAB dataset (current year)
    ANNUAL_PRODUCT_ID = "TTABYR"   # Annual TTAB dataset (historical)
    
    def __init__(self, output_dir="./ttab_data", api_key=None):
        """
        Initialize the downloader.
        
        Args:
            output_dir (str): Directory to save downloaded files
            api_key (str): USPTO Open Data Portal API key (optional)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Get API key from parameter, environment variable, or None
        self.api_key = api_key or os.environ.get('USPTO_API_KEY')
        
        # Setup session with headers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'TTAB-Bulk-Data-Downloader/2.0'
        })
        
        # Add API key to headers if available
        if self.api_key:
            self.session.headers.update({
                'X-API-KEY': self.api_key
            })
            logger.info("Using USPTO API key for authentication")
        else:
            logger.warning("No USPTO API key found. Set USPTO_API_KEY environment variable for API access.")
            logger.warning("Visit https://data.uspto.gov/myodp to obtain an API key.")
    
    def get_product_info(self, product_id):
        """
        Get product information from USPTO Open Data Portal API.
        
        Args:
            product_id (str): Product identifier (TTABTDXF or TTABYR)
            
        Returns:
            dict: Product information including file list, or None on error
        """
        try:
            url = f"{self.API_BASE_URL}/{product_id}"
            logger.info(f"Fetching product info for: {product_id}")
            
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 403:
                logger.error("API access forbidden. Please set your USPTO_API_KEY environment variable.")
                logger.error("Visit https://data.uspto.gov/myodp to obtain an API key.")
                return None
            
            response.raise_for_status()
            data = response.json()
            
            # Extract product information
            if 'bulkDataProductBag' in data and len(data['bulkDataProductBag']) > 0:
                product_info = data['bulkDataProductBag'][0]
                logger.info(f"Product: {product_info.get('productTitleText', 'Unknown')}")
                logger.info(f"Files available: {product_info.get('productFileTotalQuantity', 0)}")
                return product_info
            else:
                logger.error("No product information found in API response")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Error fetching product info: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing API response: {e}")
            return None
    
    def get_file_list(self, product_id, start_date=None, end_date=None):
        """
        Get list of files for a product, optionally filtered by date range.
        
        Args:
            product_id (str): Product identifier (TTABTDXF or TTABYR)
            start_date (datetime, optional): Start date for filtering files
            end_date (datetime, optional): End date for filtering files
            
        Returns:
            list: List of file information dictionaries
        """
        product_info = self.get_product_info(product_id)
        if not product_info:
            return []
        
        # Extract file data bag
        product_file_bag = product_info.get('productFileBag', {})
        file_data_bag = product_file_bag.get('fileDataBag', [])
        
        if not file_data_bag:
            logger.warning("No files found in product")
            return []
        
        # Filter by date if specified
        if start_date or end_date:
            filtered_files = []
            for file_info in file_data_bag:
                file_date_str = file_info.get('fileDataFromDate') or file_info.get('fileDate')
                if file_date_str:
                    try:
                        # Parse date (format: YYYY-MM-DD)
                        file_date = datetime.strptime(file_date_str[:10], '%Y-%m-%d').date()
                        
                        # Convert start_date and end_date to date objects for comparison
                        start = start_date.date() if start_date else None
                        end = end_date.date() if end_date else None
                        
                        # Check if file is within date range
                        if start and file_date < start:
                            continue
                        if end and file_date > end:
                            continue
                        
                        filtered_files.append(file_info)
                    except ValueError:
                        # If date parsing fails, include the file
                        filtered_files.append(file_info)
                else:
                    # If no date found, include the file
                    filtered_files.append(file_info)
            
            logger.info(f"Filtered to {len(filtered_files)} files in date range")
            return filtered_files
        
        return file_data_bag
    
    def download_file(self, file_info, force_redownload=False):
        """
        Download a single file using file information from API.
        
        Args:
            file_info (dict): File information dictionary from API
            force_redownload (bool): Whether to redownload existing files
            
        Returns:
            bool: True if download was successful
        """
        filename = file_info.get('fileName', 'unknown')
        download_uri = file_info.get('fileDownloadURI')
        file_size = file_info.get('fileSize', 0)
        
        try:
            if not filename or filename == 'unknown' or not download_uri:
                logger.error(f"Missing filename or download URI in file info")
                return False
            
            output_path = self.output_dir / filename
            
            # Skip if file already exists and not forcing redownload
            if output_path.exists() and not force_redownload:
                logger.info(f"File already exists, skipping: {filename}")
                return True
            
            logger.info(f"Downloading: {filename} ({file_size:,} bytes)")
            
            # Stream download to handle large files
            response = self.session.get(download_uri, stream=True, timeout=300)
            response.raise_for_status()
            
            # Get actual file size from response if not in file info
            total_size = int(response.headers.get('content-length', file_size))
            downloaded_size = 0
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # Show progress for large files (every 5%)
                        if total_size > 0 and downloaded_size % (total_size // 20 + 1) < 8192:
                            progress = (downloaded_size / total_size) * 100
                            logger.info(f"Progress: {progress:.1f}% ({downloaded_size:,} / {total_size:,} bytes)")
            
            logger.info(f"Successfully downloaded: {filename} ({downloaded_size:,} bytes)")
            
            # Extract ZIP file contents
            if filename.lower().endswith('.zip'):
                try:
                    logger.info(f"Extracting ZIP archive: {filename}")
                    with zipfile.ZipFile(output_path, 'r') as zip_ref:
                        # Get list of files in the archive
                        file_list = zip_ref.namelist()
                        logger.info(f"Found {len(file_list)} file(s) in archive")
                        
                        # Extract all files to the output directory
                        for file_in_zip in file_list:
                            zip_ref.extract(file_in_zip, self.output_dir)
                            extracted_path = self.output_dir / file_in_zip
                            logger.info(f"Extracted: {file_in_zip} ({extracted_path.stat().st_size:,} bytes)")
                        
                    # Delete the ZIP file after successful extraction
                    output_path.unlink()
                    logger.info(f"Removed ZIP archive: {filename}")
                    
                except zipfile.BadZipFile as e:
                    logger.error(f"Invalid ZIP file {filename}: {e}")
                    return False
                except Exception as e:
                    logger.error(f"Error extracting {filename}: {e}")
                    return False
            
            return True
            
        except requests.RequestException as e:
            logger.error(f"Error downloading {filename}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error downloading {filename}: {e}")
            return False
    
    def download_recent_daily(self, days=7, force_redownload=False):
        """
        Download recent daily TTAB files from the last N days.
        
        Args:
            days (int): Number of recent days to download
            force_redownload (bool): Whether to redownload existing files
            
        Returns:
            int: Number of files successfully downloaded
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        logger.info(f"Downloading daily TTAB files from {start_date.date()} to {end_date.date()}")
        
        files = self.get_file_list(self.DAILY_PRODUCT_ID, start_date, end_date)
        
        if not files:
            logger.warning("No files found for the specified date range")
            return 0
        
        logger.info(f"Found {len(files)} files to download")
        
        successful_downloads = 0
        for i, file_info in enumerate(files, 1):
            logger.info(f"Processing file {i}/{len(files)}")
            
            if self.download_file(file_info, force_redownload):
                successful_downloads += 1
            
            # Small delay to respect rate limits (4 downloads/min for bulk files)
            time.sleep(15)
        
        return successful_downloads
    
    def download_all_daily(self, year=None, force_redownload=False):
        """
        Download all daily TTAB files for current year or specified year.
        
        Args:
            year (int, optional): Specific year (only works for current year in daily dataset)
            force_redownload (bool): Whether to redownload existing files
            
        Returns:
            int: Number of files successfully downloaded
        """
        if year and year != datetime.now().year:
            logger.warning(f"Daily dataset only contains current year ({datetime.now().year})")
            logger.warning(f"For historical data, use --annual flag")
            return 0
        
        logger.info(f"Downloading all daily TTAB files for {datetime.now().year}")
        
        files = self.get_file_list(self.DAILY_PRODUCT_ID)
        
        if not files:
            logger.warning("No files found")
            return 0
        
        logger.info(f"Found {len(files)} files to download")
        
        successful_downloads = 0
        for i, file_info in enumerate(files, 1):
            logger.info(f"Processing file {i}/{len(files)}")
            
            if self.download_file(file_info, force_redownload):
                successful_downloads += 1
            
            # Small delay to respect rate limits
            time.sleep(15)
        
        logger.info(f"Download complete: {successful_downloads}/{len(files)} files successful")
        return successful_downloads
    
    def download_annual(self, force_redownload=False):
        """
        Download the annual TTAB dataset (historical backfile).
        
        Args:
            force_redownload (bool): Whether to redownload existing files
            
        Returns:
            int: Number of files successfully downloaded
        """
        logger.info("Downloading annual TTAB dataset (1951-2024 backfile)")
        
        files = self.get_file_list(self.ANNUAL_PRODUCT_ID)
        
        if not files:
            logger.warning("No files found")
            return 0
        
        logger.info(f"Found {len(files)} file(s) to download")
        logger.warning("Note: Annual dataset files can be very large (>100MB)")
        
        successful_downloads = 0
        for i, file_info in enumerate(files, 1):
            logger.info(f"Processing file {i}/{len(files)}")
            
            if self.download_file(file_info, force_redownload):
                successful_downloads += 1
            
            # Small delay to respect rate limits
            time.sleep(15)
        
        logger.info(f"Download complete: {successful_downloads}/{len(files)} files successful")
        return successful_downloads


def main():
    """Main command-line interface."""
    parser = argparse.ArgumentParser(
        description="Download TTAB XML bulk data files from USPTO Open Data Portal",
        epilog="Requires USPTO_API_KEY environment variable. Visit https://data.uspto.gov/myodp to obtain an API key."
    )
    
    parser.add_argument(
        "--output-dir", "-o",
        default="./ttab_data",
        help="Output directory for downloaded files (default: ./ttab_data)"
    )
    
    parser.add_argument(
        "--api-key", "-k",
        help="USPTO Open Data Portal API key (or set USPTO_API_KEY environment variable)"
    )
    
    parser.add_argument(
        "--year", "-y",
        type=int,
        help="Specific year to download (only applies to daily dataset, must be current year)"
    )
    
    parser.add_argument(
        "--recent", "-r",
        type=int,
        metavar="DAYS",
        help="Download daily files from the last N days (default: 7)"
    )
    
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Download all available files from daily dataset"
    )
    
    parser.add_argument(
        "--annual",
        action="store_true",
        help="Download annual/historical dataset (1951-2024)"
    )
    
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force redownload of existing files"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create downloader instance
    downloader = TTABDownloader(output_dir=args.output_dir, api_key=args.api_key)
    
    # Check if API key is available
    if not downloader.api_key:
        logger.error("USPTO_API_KEY not found!")
        logger.error("Please set the USPTO_API_KEY environment variable or use --api-key option")
        logger.error("Visit https://data.uspto.gov/myodp to obtain an API key")
        sys.exit(1)
    
    try:
        if args.annual:
            # Download annual dataset
            count = downloader.download_annual(force_redownload=args.force)
        elif args.all:
            # Download all daily files
            count = downloader.download_all_daily(
                year=args.year,
                force_redownload=args.force
            )
        elif args.recent is not None:
            # Download recent files
            count = downloader.download_recent_daily(
                days=args.recent,
                force_redownload=args.force
            )
        elif args.year:
            # Download specific year from daily dataset
            count = downloader.download_all_daily(
                year=args.year,
                force_redownload=args.force
            )
        else:
            # Default: download recent 7 days
            count = downloader.download_recent_daily(
                days=7,
                force_redownload=args.force
            )
        
        logger.info(f"Download completed successfully: {count} files")
        
    except KeyboardInterrupt:
        logger.info("Download interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Download failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
