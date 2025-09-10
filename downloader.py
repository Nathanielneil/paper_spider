"""
Multi-threaded PDF download manager for ArXiv papers.
Handles concurrent downloads, resume functionality, and progress tracking.
"""

import os
import re
import time
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Callable, Tuple
from urllib.parse import urlparse
import hashlib

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm


class DownloadException(Exception):
    """Custom exception for download-related errors."""
    pass


class DownloadResult:
    """Represents the result of a download operation."""
    
    def __init__(self, arxiv_id: str, success: bool, file_path: Optional[str] = None, 
                 error: Optional[str] = None, size: int = 0):
        self.arxiv_id = arxiv_id
        self.success = success
        self.file_path = file_path
        self.error = error
        self.size = size
        self.timestamp = time.time()


class DownloadManager:
    """
    Manages concurrent PDF downloads from ArXiv.
    
    Features:
    - Multi-threaded concurrent downloads
    - Resume functionality for interrupted downloads
    - Progress tracking and reporting
    - Automatic retry on failures
    - File naming and organization
    """
    
    def __init__(self, config: Dict):
        """
        Initialize the download manager.
        
        Args:
            config: Configuration dictionary containing download settings
        """
        self.config = config
        self.output_dir = Path(config.get('output_directory', './downloaded_papers'))
        self.max_workers = config.get('max_concurrent_downloads', 5)
        self.retry_attempts = config.get('retry_attempts', 3)
        self.timeout = config.get('timeout', 60)
        self.filename_pattern = config.get('filename_pattern', '{year}_{first_author}_{title}')
        self.create_category_folders = config.get('create_category_folders', True)
        
        self.logger = logging.getLogger(__name__)
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Download statistics
        self._stats = {
            'total': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'bytes_downloaded': 0
        }
        
        # Thread-safe lock for statistics
        self._stats_lock = threading.Lock()
        
        # Setup HTTP session with retry strategy
        self._setup_session()
    
    def _setup_session(self) -> None:
        """Setup HTTP session with retry strategy and headers."""
        self.session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.retry_attempts,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
            backoff_factor=1
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set headers
        self.session.headers.update({
            'User-Agent': 'ArxivCrawler/1.0 (https://github.com/user/arxiv-crawler)'
        })
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename to be safe across different operating systems.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename safe for Windows and Unix systems
        """
        # Remove or replace problematic characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filename)  # Remove control characters
        filename = filename.strip()
        
        # Limit filename length (Windows has 260 char limit for full path)
        if len(filename) > 150:
            filename = filename[:150]
        
        # Ensure filename doesn't end with space or dot (Windows issue)
        filename = filename.rstrip('. ')
        
        return filename if filename else 'untitled'
    
    def _generate_filename(self, paper: Dict) -> str:
        """
        Generate filename based on pattern and paper metadata.
        
        Args:
            paper: Paper dictionary containing metadata
            
        Returns:
            Generated filename
        """
        try:
            # Extract year from published date
            published = paper.get('published', '')
            year = published[:4] if published else 'unknown'
            
            # Get first author
            authors = paper.get('authors', [])
            first_author = authors[0] if authors else 'unknown'
            # Clean author name (keep only letters and spaces)
            first_author = re.sub(r'[^a-zA-Z\s]', '', first_author).strip()
            first_author = first_author.replace(' ', '_') if first_author else 'unknown'
            
            # Clean title
            title = paper.get('title', 'untitled')
            title = re.sub(r'[^\w\s-]', '', title).strip()
            title = re.sub(r'\s+', '_', title)
            
            # Apply pattern
            filename = self.filename_pattern.format(
                year=year,
                first_author=first_author,
                title=title,
                arxiv_id=paper.get('arxiv_id', 'unknown')
            )
            
            # Sanitize the result
            filename = self._sanitize_filename(filename)
            
            return f"{filename}.pdf"
            
        except Exception as e:
            self.logger.warning(f"Failed to generate filename for {paper.get('arxiv_id', 'unknown')}: {e}")
            return f"{paper.get('arxiv_id', 'unknown')}.pdf"
    
    def _get_output_path(self, paper: Dict) -> Path:
        """
        Get the full output path for a paper.
        
        Args:
            paper: Paper dictionary
            
        Returns:
            Path object for the output file
        """
        filename = self._generate_filename(paper)
        
        if self.create_category_folders:
            category = paper.get('primary_category', 'unknown')
            category_dir = self.output_dir / self._sanitize_filename(category)
            category_dir.mkdir(parents=True, exist_ok=True)
            return category_dir / filename
        else:
            return self.output_dir / filename
    
    def _handle_filename_conflict(self, file_path: Path) -> Path:
        """
        Handle filename conflicts by adding a numeric suffix.
        
        Args:
            file_path: Original file path
            
        Returns:
            Non-conflicting file path
        """
        if not file_path.exists():
            return file_path
        
        stem = file_path.stem
        suffix = file_path.suffix
        parent = file_path.parent
        
        counter = 1
        while True:
            new_path = parent / f"{stem}_{counter}{suffix}"
            if not new_path.exists():
                return new_path
            counter += 1
    
    def _download_single_paper(self, paper: Dict, progress_callback: Optional[Callable] = None) -> DownloadResult:
        """
        Download a single paper PDF.
        
        Args:
            paper: Paper dictionary containing metadata
            progress_callback: Optional callback for progress updates
            
        Returns:
            DownloadResult object
        """
        arxiv_id = paper.get('arxiv_id', '')
        pdf_url = paper.get('pdf_url', '')
        
        if not pdf_url:
            return DownloadResult(arxiv_id, False, error="No PDF URL available")
        
        try:
            # Get output path
            output_path = self._get_output_path(paper)
            output_path = self._handle_filename_conflict(output_path)
            
            # Check if file already exists and is valid
            if output_path.exists():
                file_size = output_path.stat().st_size
                if file_size > 1024:  # File exists and is larger than 1KB
                    self.logger.info(f"File already exists: {output_path}")
                    with self._stats_lock:
                        self._stats['skipped'] += 1
                    return DownloadResult(arxiv_id, True, str(output_path), size=file_size)
            
            # Start download
            self.logger.info(f"Downloading {arxiv_id} from {pdf_url}")
            
            response = self.session.get(pdf_url, stream=True, timeout=self.timeout)
            response.raise_for_status()
            
            # Get file size from headers
            total_size = int(response.headers.get('content-length', 0))
            
            # Download with progress tracking
            downloaded_size = 0
            chunk_size = 8192
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        if progress_callback:
                            progress_callback(downloaded_size, total_size)
            
            # Verify download
            if downloaded_size == 0:
                output_path.unlink(missing_ok=True)
                return DownloadResult(arxiv_id, False, error="Downloaded file is empty")
            
            self.logger.info(f"Successfully downloaded {arxiv_id} ({downloaded_size} bytes)")
            
            # Update statistics
            with self._stats_lock:
                self._stats['successful'] += 1
                self._stats['bytes_downloaded'] += downloaded_size
            
            return DownloadResult(arxiv_id, True, str(output_path), size=downloaded_size)
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Network error downloading {arxiv_id}: {e}"
            self.logger.error(error_msg)
            return DownloadResult(arxiv_id, False, error=error_msg)
        
        except Exception as e:
            error_msg = f"Unexpected error downloading {arxiv_id}: {e}"
            self.logger.error(error_msg)
            return DownloadResult(arxiv_id, False, error=error_msg)
    
    def download_papers(self, 
                       papers: List[Dict], 
                       progress_callback: Optional[Callable] = None,
                       max_workers: Optional[int] = None) -> List[DownloadResult]:
        """
        Download multiple papers concurrently.
        
        Args:
            papers: List of paper dictionaries
            progress_callback: Optional callback for overall progress updates
            max_workers: Override default number of worker threads
            
        Returns:
            List of DownloadResult objects
        """
        if not papers:
            return []
        
        workers = max_workers or self.max_workers
        results = []
        
        # Reset statistics
        with self._stats_lock:
            self._stats['total'] = len(papers)
            self._stats['successful'] = 0
            self._stats['failed'] = 0
            self._stats['skipped'] = 0
            self._stats['bytes_downloaded'] = 0
        
        self.logger.info(f"Starting download of {len(papers)} papers with {workers} workers")
        
        # Create progress bar
        with tqdm(total=len(papers), desc="Downloading papers", unit="paper") as pbar:
            
            # Use ThreadPoolExecutor for concurrent downloads
            with ThreadPoolExecutor(max_workers=workers) as executor:
                
                # Submit all download tasks
                future_to_paper = {
                    executor.submit(self._download_single_paper, paper): paper
                    for paper in papers
                }
                
                # Process completed downloads
                for future in as_completed(future_to_paper):
                    paper = future_to_paper[future]
                    
                    try:
                        result = future.result()
                        results.append(result)
                        
                        if not result.success:
                            with self._stats_lock:
                                self._stats['failed'] += 1
                        
                        # Update progress
                        pbar.update(1)
                        pbar.set_postfix({
                            'Success': self._stats['successful'],
                            'Failed': self._stats['failed'],
                            'Skipped': self._stats['skipped']
                        })
                        
                        if progress_callback:
                            progress_callback(len(results), len(papers), result)
                            
                    except Exception as e:
                        error_msg = f"Future execution failed for {paper.get('arxiv_id', 'unknown')}: {e}"
                        self.logger.error(error_msg)
                        results.append(DownloadResult(paper.get('arxiv_id', ''), False, error=error_msg))
                        
                        with self._stats_lock:
                            self._stats['failed'] += 1
                        
                        pbar.update(1)
        
        self.logger.info(f"Download completed. Success: {self._stats['successful']}, "
                        f"Failed: {self._stats['failed']}, Skipped: {self._stats['skipped']}")
        
        return results
    
    def download_with_selection(self, 
                               papers: List[Dict],
                               interactive: bool = True) -> List[DownloadResult]:
        """
        Download papers with interactive selection.
        
        Args:
            papers: List of paper dictionaries
            interactive: Whether to prompt user for selection
            
        Returns:
            List of DownloadResult objects
        """
        if not papers:
            self.logger.info("No papers to download")
            return []
        
        if not interactive:
            return self.download_papers(papers)
        
        # Display papers for selection
        print(f"\nFound {len(papers)} papers:")
        print("-" * 80)
        
        for i, paper in enumerate(papers, 1):
            authors = ', '.join(paper.get('authors', [])[:3])
            if len(paper.get('authors', [])) > 3:
                authors += ' et al.'
            
            print(f"{i:3d}. {paper.get('title', 'No title')}")
            print(f"     Authors: {authors}")
            print(f"     Category: {paper.get('primary_category', 'Unknown')}")
            print(f"     Published: {paper.get('published', 'Unknown')[:10]}")
            print(f"     ArXiv ID: {paper.get('arxiv_id', 'Unknown')}")
            print()
        
        # Get user selection
        while True:
            try:
                selection = input("\nSelect papers to download (e.g., 1,3,5-10 or 'all' or 'none'): ").strip()
                
                if selection.lower() == 'none':
                    return []
                elif selection.lower() == 'all':
                    selected_papers = papers
                    break
                else:
                    selected_indices = self._parse_selection(selection, len(papers))
                    selected_papers = [papers[i-1] for i in selected_indices]
                    break
                    
            except ValueError as e:
                print(f"Invalid selection: {e}")
                continue
        
        if not selected_papers:
            self.logger.info("No papers selected for download")
            return []
        
        print(f"\nStarting download of {len(selected_papers)} selected papers...")
        return self.download_papers(selected_papers)
    
    def _parse_selection(self, selection: str, max_index: int) -> List[int]:
        """
        Parse user selection string into list of indices.
        
        Args:
            selection: User selection string (e.g., "1,3,5-10")
            max_index: Maximum valid index
            
        Returns:
            List of selected indices
        """
        indices = set()
        
        for part in selection.split(','):
            part = part.strip()
            
            if '-' in part:
                # Handle range (e.g., "5-10")
                try:
                    start, end = map(int, part.split('-', 1))
                    if start < 1 or end > max_index or start > end:
                        raise ValueError(f"Invalid range: {part}")
                    indices.update(range(start, end + 1))
                except ValueError:
                    raise ValueError(f"Invalid range format: {part}")
            else:
                # Handle single number
                try:
                    index = int(part)
                    if index < 1 or index > max_index:
                        raise ValueError(f"Index {index} out of range (1-{max_index})")
                    indices.add(index)
                except ValueError:
                    raise ValueError(f"Invalid number: {part}")
        
        return sorted(list(indices))
    
    def get_statistics(self) -> Dict:
        """
        Get download statistics.
        
        Returns:
            Dictionary containing download statistics
        """
        with self._stats_lock:
            stats = self._stats.copy()
        
        # Add derived statistics
        if stats['total'] > 0:
            stats['success_rate'] = stats['successful'] / stats['total'] * 100
        else:
            stats['success_rate'] = 0.0
        
        # Format bytes downloaded
        bytes_downloaded = stats['bytes_downloaded']
        if bytes_downloaded >= 1024**3:
            stats['formatted_size'] = f"{bytes_downloaded / 1024**3:.2f} GB"
        elif bytes_downloaded >= 1024**2:
            stats['formatted_size'] = f"{bytes_downloaded / 1024**2:.2f} MB"
        elif bytes_downloaded >= 1024:
            stats['formatted_size'] = f"{bytes_downloaded / 1024:.2f} KB"
        else:
            stats['formatted_size'] = f"{bytes_downloaded} bytes"
        
        return stats
    
    def retry_failed_downloads(self, failed_results: List[DownloadResult], 
                              papers: List[Dict]) -> List[DownloadResult]:
        """
        Retry failed downloads.
        
        Args:
            failed_results: List of failed DownloadResult objects
            papers: Original list of paper dictionaries
            
        Returns:
            List of retry DownloadResult objects
        """
        if not failed_results:
            return []
        
        # Create mapping from arxiv_id to paper
        paper_map = {paper.get('arxiv_id', ''): paper for paper in papers}
        
        # Get papers for retry
        retry_papers = []
        for result in failed_results:
            if result.arxiv_id in paper_map:
                retry_papers.append(paper_map[result.arxiv_id])
        
        if retry_papers:
            self.logger.info(f"Retrying download of {len(retry_papers)} failed papers")
            return self.download_papers(retry_papers)
        
        return []
    
    def cleanup_incomplete_downloads(self) -> int:
        """
        Clean up incomplete or corrupted download files.
        
        Returns:
            Number of files cleaned up
        """
        cleanup_count = 0
        
        try:
            for file_path in self.output_dir.rglob("*.pdf"):
                # Check if file is very small (likely incomplete)
                if file_path.stat().st_size < 1024:
                    self.logger.info(f"Removing incomplete download: {file_path}")
                    file_path.unlink()
                    cleanup_count += 1
            
            self.logger.info(f"Cleaned up {cleanup_count} incomplete downloads")
            
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
        
        return cleanup_count