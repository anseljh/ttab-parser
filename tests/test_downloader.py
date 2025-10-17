"""Unit tests for TTAB downloader."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from src.ttab_downloader import TTABDownloader


class TestTTABDownloader:
    """Tests for TTABDownloader class."""
    
    def test_initialization(self, temp_data_dir):
        """Test downloader initialization."""
        downloader = TTABDownloader(output_dir=str(temp_data_dir))
        assert downloader.output_dir == temp_data_dir
        assert temp_data_dir.exists()
    
    def test_initialization_creates_directory(self, tmp_path):
        """Test initialization creates output directory if it doesn't exist."""
        new_dir = tmp_path / "new_downloads"
        assert not new_dir.exists()
        
        downloader = TTABDownloader(output_dir=str(new_dir))
        assert new_dir.exists()
    
    def test_api_key_from_parameter(self, temp_data_dir):
        """Test API key can be set via parameter."""
        downloader = TTABDownloader(
            output_dir=str(temp_data_dir),
            api_key="test-key-123"
        )
        assert downloader.api_key == "test-key-123"
    
    @patch.dict('os.environ', {'USPTO_API_KEY': 'env-key-456'})
    def test_api_key_from_environment(self, temp_data_dir):
        """Test API key is loaded from environment."""
        downloader = TTABDownloader(output_dir=str(temp_data_dir))
        assert downloader.api_key == "env-key-456"
    
    def test_extraction_threads_initialized(self, temp_data_dir):
        """Test extraction threads list is initialized."""
        downloader = TTABDownloader(output_dir=str(temp_data_dir))
        assert downloader.extraction_threads == []


class TestFileDetection:
    """Tests for file detection and duplicate checking."""
    
    def test_skip_existing_zip_file(self, temp_data_dir):
        """Test skips download if ZIP file already exists."""
        downloader = TTABDownloader(output_dir=str(temp_data_dir))
        
        # Create a fake ZIP file
        zip_file = temp_data_dir / "test.zip"
        zip_file.touch()
        
        file_info = {
            'fileName': 'test.zip',
            'fileDownloadURI': 'http://example.com/test.zip',
            'fileSize': 1000
        }
        
        result = downloader.download_file(file_info, force_redownload=False)
        assert result is True  # Returns success without downloading
    
    def test_skip_if_xml_exists(self, temp_data_dir):
        """Test skips download if extracted XML already exists."""
        downloader = TTABDownloader(output_dir=str(temp_data_dir))
        
        # Create a fake XML file (as if it was already extracted)
        xml_file = temp_data_dir / "test.xml"
        xml_file.touch()
        
        file_info = {
            'fileName': 'test.zip',
            'fileDownloadURI': 'http://example.com/test.zip',
            'fileSize': 1000
        }
        
        result = downloader.download_file(file_info, force_redownload=False)
        assert result is True  # Returns success without downloading
    
    def test_force_redownload_ignores_existing(self, temp_data_dir):
        """Test force_redownload downloads even if file exists."""
        downloader = TTABDownloader(output_dir=str(temp_data_dir))
        
        # Create a fake ZIP file
        zip_file = temp_data_dir / "test.zip"
        zip_file.write_text("fake content")
        
        file_info = {
            'fileName': 'test.zip',
            'fileDownloadURI': 'http://example.com/test.zip',
            'fileSize': 1000
        }
        
        with patch.object(downloader.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.headers.get.return_value = '1000'
            mock_response.iter_content.return_value = [b'new content']
            mock_get.return_value = mock_response
            
            result = downloader.download_file(file_info, force_redownload=True)
            # Should attempt to download (mock will be called)
            mock_get.assert_called_once()


class TestWaitForExtractions:
    """Tests for extraction thread management."""
    
    def test_wait_for_extractions_empty_list(self, temp_data_dir):
        """Test waiting with no extraction threads."""
        downloader = TTABDownloader(output_dir=str(temp_data_dir))
        downloader.wait_for_extractions()  # Should not raise error
        assert downloader.extraction_threads == []
    
    def test_wait_for_extractions_joins_threads(self, temp_data_dir):
        """Test waiting joins all threads."""
        downloader = TTABDownloader(output_dir=str(temp_data_dir))
        
        # Create mock threads
        mock_thread1 = Mock()
        mock_thread2 = Mock()
        downloader.extraction_threads = [mock_thread1, mock_thread2]
        
        downloader.wait_for_extractions()
        
        mock_thread1.join.assert_called_once()
        mock_thread2.join.assert_called_once()
        assert downloader.extraction_threads == []


class TestProductIDs:
    """Tests for product ID constants."""
    
    def test_product_id_constants(self):
        """Test product ID constants are set correctly."""
        assert TTABDownloader.DAILY_PRODUCT_ID == "TTABTDXF"
        assert TTABDownloader.ANNUAL_PRODUCT_ID == "TTABYR"
        assert TTABDownloader.API_BASE_URL == "https://api.uspto.gov/api/v1/datasets/products"
