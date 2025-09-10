"""
ArXiv API wrapper module for fetching academic papers.
Supports various search methods and query types.
"""

import time
import logging
from typing import Dict, List, Optional, Generator, Union
from datetime import datetime
import xml.etree.ElementTree as ET
from urllib.parse import urlencode, quote

import requests
import feedparser
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class ArxivAPIException(Exception):
    """Custom exception for ArXiv API related errors."""
    pass


class ArxivAPI:
    """
    ArXiv API wrapper for searching and retrieving academic papers.
    
    This class provides methods to search papers by various criteria
    including keywords, authors, categories, and date ranges.
    """
    
    def __init__(self, config: Dict):
        """
        Initialize the ArXiv API wrapper.
        
        Args:
            config: Configuration dictionary containing API settings
        """
        self.base_url = config.get('base_url', 'http://export.arxiv.org/api/query')
        self.max_results = config.get('max_results_per_query', 100)
        self.request_delay = config.get('request_delay', 3.0)
        self.user_agent = config.get('user_agent', 'ArxivCrawler/1.0')
        self.timeout = config.get('timeout', 30)
        
        self.logger = logging.getLogger(__name__)
        self._setup_session()
        
    def _setup_session(self) -> None:
        """Setup HTTP session with retry strategy and timeout."""
        self.session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
            backoff_factor=1
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set headers
        self.session.headers.update({
            'User-Agent': self.user_agent,
            'Accept': 'application/atom+xml'
        })
    
    def _build_query(self, 
                     query: Optional[str] = None,
                     author: Optional[str] = None,
                     title: Optional[str] = None,
                     abstract: Optional[str] = None,
                     category: Optional[str] = None,
                     date_from: Optional[str] = None,
                     date_to: Optional[str] = None) -> str:
        """
        Build search query string for ArXiv API.
        
        Args:
            query: General search query
            author: Author name to search
            title: Title keywords to search
            abstract: Abstract keywords to search  
            category: ArXiv category (e.g., cs.AI, physics.gen-ph)
            date_from: Start date (YYYY-MM-DD format)
            date_to: End date (YYYY-MM-DD format)
            
        Returns:
            Formatted query string for ArXiv API
        """
        query_parts = []
        
        if query:
            query_parts.append(f"all:{quote(query)}")
            
        if author:
            query_parts.append(f"au:{quote(author)}")
            
        if title:
            query_parts.append(f"ti:{quote(title)}")
            
        if abstract:
            query_parts.append(f"abs:{quote(abstract)}")
            
        if category:
            query_parts.append(f"cat:{quote(category)}")
            
        # Handle date range
        if date_from or date_to:
            date_query = self._build_date_query(date_from, date_to)
            if date_query:
                query_parts.append(date_query)
        
        return " AND ".join(query_parts) if query_parts else "all:*"
    
    def _build_date_query(self, date_from: Optional[str], date_to: Optional[str]) -> str:
        """Build date range query for ArXiv submissions."""
        if not date_from and not date_to:
            return ""
            
        # Convert dates to ArXiv format (YYYYMMDD)
        date_format = "%Y-%m-%d"
        arxiv_format = "%Y%m%d"
        
        try:
            if date_from and date_to:
                from_date = datetime.strptime(date_from, date_format).strftime(arxiv_format)
                to_date = datetime.strptime(date_to, date_format).strftime(arxiv_format)
                return f"submittedDate:[{from_date} TO {to_date}]"
            elif date_from:
                from_date = datetime.strptime(date_from, date_format).strftime(arxiv_format)
                return f"submittedDate:[{from_date} TO *]"
            elif date_to:
                to_date = datetime.strptime(date_to, date_format).strftime(arxiv_format)
                return f"submittedDate:[* TO {to_date}]"
        except ValueError as e:
            self.logger.warning(f"Invalid date format: {e}")
            return ""
        
        return ""
    
    def search(self,
               query: Optional[str] = None,
               author: Optional[str] = None,
               title: Optional[str] = None,
               abstract: Optional[str] = None,
               category: Optional[str] = None,
               date_from: Optional[str] = None,
               date_to: Optional[str] = None,
               max_results: Optional[int] = None,
               start: int = 0,
               sort_by: str = "relevance",
               sort_order: str = "descending") -> Dict:
        """
        Search ArXiv papers with specified criteria.
        
        Args:
            query: General search query
            author: Author name to search
            title: Title keywords to search
            abstract: Abstract keywords to search
            category: ArXiv category
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)
            max_results: Maximum number of results to return
            start: Start index for pagination
            sort_by: Sort criteria (relevance, lastUpdatedDate, submittedDate)
            sort_order: Sort order (ascending, descending)
            
        Returns:
            Dictionary containing search results and metadata
        """
        search_query = self._build_query(
            query=query, author=author, title=title, abstract=abstract,
            category=category, date_from=date_from, date_to=date_to
        )
        
        if not max_results:
            max_results = self.max_results
            
        params = {
            'search_query': search_query,
            'start': start,
            'max_results': min(max_results, 2000),  # ArXiv API limit
            'sortBy': sort_by,
            'sortOrder': sort_order
        }
        
        self.logger.info(f"Searching ArXiv with query: {search_query}")
        
        try:
            # Respect rate limiting
            time.sleep(self.request_delay)
            
            response = self.session.get(
                self.base_url,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            return self._parse_response(response.content)
            
        except requests.exceptions.RequestException as e:
            raise ArxivAPIException(f"API request failed: {e}")
        except Exception as e:
            raise ArxivAPIException(f"Unexpected error: {e}")
    
    def _parse_response(self, content: bytes) -> Dict:
        """
        Parse ArXiv API response and extract paper information.
        
        Args:
            content: Raw XML content from API response
            
        Returns:
            Dictionary containing parsed papers and metadata
        """
        try:
            feed = feedparser.parse(content)
            
            if feed.bozo:
                self.logger.warning("Received malformed XML response")
            
            papers = []
            
            for entry in feed.entries:
                paper = self._extract_paper_info(entry)
                papers.append(paper)
            
            return {
                'papers': papers,
                'total_results': len(papers),
                'query_info': {
                    'title': feed.feed.get('title', ''),
                    'updated': feed.feed.get('updated', ''),
                    'total_results': getattr(feed.feed, 'opensearch_totalresults', 0),
                    'start_index': getattr(feed.feed, 'opensearch_startindex', 0),
                    'items_per_page': getattr(feed.feed, 'opensearch_itemsperpage', 0)
                }
            }
            
        except Exception as e:
            raise ArxivAPIException(f"Failed to parse API response: {e}")
    
    def _extract_paper_info(self, entry) -> Dict:
        """
        Extract relevant information from a single paper entry.
        
        Args:
            entry: Paper entry from feedparser
            
        Returns:
            Dictionary containing paper information
        """
        # Extract ArXiv ID and version
        arxiv_id = entry.id.split('/abs/')[-1]
        
        # Extract authors
        authors = []
        if hasattr(entry, 'authors'):
            authors = [author.name for author in entry.authors]
        elif hasattr(entry, 'author'):
            authors = [entry.author]
        
        # Extract categories
        categories = []
        primary_category = ""
        
        if hasattr(entry, 'tags'):
            categories = [tag.term for tag in entry.tags]
            if entry.tags:
                primary_category = entry.tags[0].term
        
        # Extract links
        pdf_url = ""
        abs_url = ""
        doi = ""
        
        if hasattr(entry, 'links'):
            for link in entry.links:
                if link.type == 'application/pdf':
                    pdf_url = link.href
                elif 'abs' in link.href:
                    abs_url = link.href
                elif link.title and 'doi' in link.title.lower():
                    doi = link.href
        
        # Clean and format text
        title = entry.title.replace('\n', ' ').strip()
        abstract = entry.summary.replace('\n', ' ').strip()
        
        return {
            'arxiv_id': arxiv_id,
            'title': title,
            'authors': authors,
            'abstract': abstract,
            'published': entry.get('published', ''),
            'updated': entry.get('updated', ''),
            'primary_category': primary_category,
            'categories': categories,
            'pdf_url': pdf_url,
            'abs_url': abs_url,
            'doi': doi,
            'comment': entry.get('arxiv_comment', '')
        }
    
    def get_paper_by_id(self, arxiv_id: str) -> Optional[Dict]:
        """
        Get a specific paper by ArXiv ID.
        
        Args:
            arxiv_id: ArXiv paper ID (e.g., "2301.12345")
            
        Returns:
            Paper information dictionary or None if not found
        """
        try:
            result = self.search(query=f"id:{arxiv_id}", max_results=1)
            papers = result.get('papers', [])
            return papers[0] if papers else None
        except Exception as e:
            self.logger.error(f"Failed to get paper {arxiv_id}: {e}")
            return None
    
    def search_paginated(self, 
                        max_total_results: int,
                        page_size: Optional[int] = None,
                        **search_kwargs) -> Generator[Dict, None, None]:
        """
        Search with pagination support to handle large result sets.
        
        Args:
            max_total_results: Maximum total results to retrieve
            page_size: Results per page (defaults to API max_results)
            **search_kwargs: Search parameters passed to search() method
            
        Yields:
            Individual paper dictionaries
        """
        if not page_size:
            page_size = self.max_results
            
        start = 0
        total_retrieved = 0
        
        while total_retrieved < max_total_results:
            remaining = min(page_size, max_total_results - total_retrieved)
            
            try:
                result = self.search(
                    start=start,
                    max_results=remaining,
                    **search_kwargs
                )
                
                papers = result.get('papers', [])
                
                if not papers:
                    break
                
                for paper in papers:
                    yield paper
                    total_retrieved += 1
                    
                    if total_retrieved >= max_total_results:
                        break
                
                start += len(papers)
                
                # Check if we've reached the end
                if len(papers) < remaining:
                    break
                    
            except ArxivAPIException as e:
                self.logger.error(f"Error during paginated search: {e}")
                break
    
    def get_categories(self) -> Dict[str, str]:
        """
        Get available ArXiv categories.
        
        Returns:
            Dictionary mapping category codes to descriptions
        """
        # Common ArXiv categories
        categories = {
            # Computer Science
            'cs.AI': 'Artificial Intelligence',
            'cs.CL': 'Computation and Language',
            'cs.CV': 'Computer Vision and Pattern Recognition',
            'cs.LG': 'Machine Learning',
            'cs.NE': 'Neural and Evolutionary Computing',
            'cs.RO': 'Robotics',
            'cs.CR': 'Cryptography and Security',
            'cs.DB': 'Databases',
            'cs.DS': 'Data Structures and Algorithms',
            'cs.HC': 'Human-Computer Interaction',
            'cs.IR': 'Information Retrieval',
            'cs.IT': 'Information Theory',
            'cs.SE': 'Software Engineering',
            'cs.SY': 'Systems and Control',
            
            # Mathematics
            'math.CO': 'Combinatorics',
            'math.IT': 'Information Theory',
            'math.OC': 'Optimization and Control',
            'math.PR': 'Probability',
            'math.ST': 'Statistics Theory',
            
            # Physics
            'physics.comp-ph': 'Computational Physics',
            'physics.data-an': 'Data Analysis, Statistics and Probability',
            
            # Statistics
            'stat.AP': 'Applications',
            'stat.CO': 'Computation',
            'stat.ML': 'Machine Learning',
            'stat.TH': 'Theory',
            
            # Economics
            'econ.EM': 'Econometrics',
            'econ.TH': 'Theoretical Economics',
            
            # Quantitative Biology
            'q-bio.BM': 'Biomolecules',
            'q-bio.GN': 'Genomics',
            'q-bio.QM': 'Quantitative Methods',
            
            # Quantitative Finance
            'q-fin.CP': 'Computational Finance',
            'q-fin.RM': 'Risk Management',
            'q-fin.ST': 'Statistical Finance'
        }
        
        return categories