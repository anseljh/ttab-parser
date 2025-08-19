#!/usr/bin/env python3
"""
TTAB Bulk Data Downloader

Downloads TTAB XML bulk data files from the USPTO data source.
Supports both daily and annual XML file formats.
"""

import argparse
import logging
import os
import requests
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse
import time
import re
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TTABDownloader:
    """Downloads TTAB XML files from USPTO bulk data repository."""
    
    BASE_URL = "https://bulkdata.uspto.gov/data/trademark/dailyxml/ttab/"
    
    def __init__(self, output_dir="./ttab_data"):
        """
        Initialize the downloader.
        
        Args:
            output_dir (str): Directory to save downloaded files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'TTAB-Bulk-Data-Downloader/1.0'
        })
    
    def get_available_files(self, year=None):
        """
        Get list of available XML files from USPTO repository.
        
        Args:
            year (int, optional): Specific year to fetch files for
            
        Returns:
            list: List of available file URLs
        """
        try:
            if year:
                url = f"{self.BASE_URL}{year}/"
            else:
                url = self.BASE_URL
                
            logger.info(f"Fetching file list from: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # Parse HTML directory listing to find XML files
            content = response.text
            xml_files = []
            
            # Look for XML file links in the HTML
            xml_pattern = r'href="([^"]*\.xml(?:\.gz)?)"'
            matches = re.findall(xml_pattern, content, re.IGNORECASE)
            
            for match in matches:
                if not match.startswith('http'):
                    file_url = urljoin(url, match)
                else:
                    file_url = match
                xml_files.append(file_url)
            
            logger.info(f"Found {len(xml_files)} XML files")
            return xml_files
            
        except requests.RequestException as e:
            logger.error(f"Error fetching file list: {e}")
            return []
    
    def download_file(self, file_url, force_redownload=False):
        """
        Download a single XML file.
        
        Args:
            file_url (str): URL of the file to download
            force_redownload (bool): Whether to redownload existing files
            
        Returns:
            bool: True if download was successful
        """
        try:
            filename = Path(urlparse(file_url).path).name
            output_path = self.output_dir / filename
            
            # Skip if file already exists and not forcing redownload
            if output_path.exists() and not force_redownload:
                logger.info(f"File already exists, skipping: {filename}")
                return True
            
            logger.info(f"Downloading: {filename}")
            
            # Stream download to handle large files
            response = self.session.get(file_url, stream=True, timeout=120)
            response.raise_for_status()
            
            # Get file size for progress tracking
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # Show progress for large files
                        if total_size > 0:
                            progress = (downloaded_size / total_size) * 100
                            if downloaded_size % (1024 * 1024) == 0:  # Every MB
                                logger.info(f"Progress: {progress:.1f}% ({downloaded_size:,} / {total_size:,} bytes)")
            
            logger.info(f"Successfully downloaded: {filename} ({downloaded_size:,} bytes)")
            return True
            
        except requests.RequestException as e:
            logger.error(f"Error downloading {file_url}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error downloading {file_url}: {e}")
            return False
    
    def download_recent_files(self, days=7, force_redownload=False):
        """
        Download recent files from the last N days.
        
        Args:
            days (int): Number of recent days to download
            force_redownload (bool): Whether to redownload existing files
            
        Returns:
            int: Number of files successfully downloaded
        """
        current_year = datetime.now().year
        files = self.get_available_files(year=current_year)
        
        if not files:
            logger.warning("No files found for current year")
            return 0
        
        # Filter files by date if possible (based on filename patterns)
        recent_cutoff = datetime.now() - timedelta(days=days)
        recent_files = []
        
        for file_url in files:
            filename = Path(urlparse(file_url).path).name
            
            # Try to extract date from filename (common patterns)
            date_match = re.search(r'(\d{4})(\d{2})(\d{2})', filename)
            if date_match:
                try:
                    file_date = datetime(
                        int(date_match.group(1)),
                        int(date_match.group(2)),
                        int(date_match.group(3))
                    )
                    if file_date >= recent_cutoff:
                        recent_files.append(file_url)
                except ValueError:
                    # If date parsing fails, include the file anyway
                    recent_files.append(file_url)
            else:
                # If no date found in filename, include it
                recent_files.append(file_url)
        
        logger.info(f"Found {len(recent_files)} recent files to download")
        
        successful_downloads = 0
        for file_url in recent_files:
            if self.download_file(file_url, force_redownload):
                successful_downloads += 1
            
            # Small delay between downloads to be respectful
            time.sleep(1)
        
        return successful_downloads
    
    def download_all_files(self, year=None, force_redownload=False):
        """
        Download all available files for a specific year or all years.
        
        Args:
            year (int, optional): Specific year to download
            force_redownload (bool): Whether to redownload existing files
            
        Returns:
            int: Number of files successfully downloaded
        """
        files = self.get_available_files(year=year)
        
        if not files:
            logger.warning("No files found")
            return 0
        
        logger.info(f"Starting download of {len(files)} files")
        
        successful_downloads = 0
        for i, file_url in enumerate(files, 1):
            logger.info(f"Processing file {i}/{len(files)}")
            
            if self.download_file(file_url, force_redownload):
                successful_downloads += 1
            
            # Small delay between downloads to be respectful
            time.sleep(1)
        
        logger.info(f"Download complete: {successful_downloads}/{len(files)} files successful")
        return successful_downloads


def main():
    """Main command-line interface."""
    parser = argparse.ArgumentParser(
        description="Download TTAB XML bulk data files from USPTO"
    )
    
    parser.add_argument(
        "--output-dir", "-o",
        default="./ttab_data",
        help="Output directory for downloaded files (default: ./ttab_data)"
    )
    
    parser.add_argument(
        "--year", "-y",
        type=int,
        help="Specific year to download (default: current year)"
    )
    
    parser.add_argument(
        "--recent", "-r",
        type=int,
        metavar="DAYS",
        help="Download files from the last N days (default: 7)"
    )
    
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Download all available files"
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
    downloader = TTABDownloader(output_dir=args.output_dir)
    
    try:
        if args.all:
            # Download all files
            count = downloader.download_all_files(
                year=args.year,
                force_redownload=args.force
            )
        elif args.recent is not None:
            # Download recent files
            count = downloader.download_recent_files(
                days=args.recent,
                force_redownload=args.force
            )
        elif args.year:
            # Download specific year
            count = downloader.download_all_files(
                year=args.year,
                force_redownload=args.force
            )
        else:
            # Default: download recent 7 days
            count = downloader.download_recent_files(
                days=7,
                force_redownload=args.force
            )
        
        logger.info(f"Download completed successfully: {count} files")
        
    except KeyboardInterrupt:
        logger.info("Download interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Download failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
