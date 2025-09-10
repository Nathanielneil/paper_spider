"""
Data processing and storage module for ArXiv papers.
Handles data deduplication, export to various formats, and database operations.
"""

import json
import sqlite3
import csv
import os
import logging
from typing import Dict, List, Optional, Set, Union
from datetime import datetime
from pathlib import Path
import hashlib

import pandas as pd


class DataProcessor:
    """
    Handles data processing, storage, and export for ArXiv papers.
    
    Provides functionality for deduplication, database operations,
    and exporting data to various formats (JSON, CSV, SQLite).
    """
    
    def __init__(self, config: Dict):
        """
        Initialize the data processor.
        
        Args:
            config: Configuration dictionary containing storage settings
        """
        self.config = config
        self.db_path = config.get('database_path', './arxiv_papers.db')
        self.export_formats = config.get('export_formats', ['json', 'csv'])
        self.auto_backup = config.get('auto_backup', True)
        
        self.logger = logging.getLogger(__name__)
        self._papers_cache: List[Dict] = []
        self._seen_ids: Set[str] = set()
        
        # Ensure database directory exists
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        
        # Initialize database
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize SQLite database with required tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create papers table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS papers (
                        arxiv_id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        authors TEXT,
                        abstract TEXT,
                        published TEXT,
                        updated TEXT,
                        primary_category TEXT,
                        categories TEXT,
                        pdf_url TEXT,
                        abs_url TEXT,
                        doi TEXT,
                        comment TEXT,
                        downloaded BOOLEAN DEFAULT 0,
                        download_path TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create search_history table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS search_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        query_params TEXT,
                        query_hash TEXT UNIQUE,
                        results_count INTEGER,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create indexes for better performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_primary_category ON papers(primary_category)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_published ON papers(published)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_downloaded ON papers(downloaded)')
                
                conn.commit()
                self.logger.info("Database initialized successfully")
                
        except sqlite3.Error as e:
            self.logger.error(f"Database initialization failed: {e}")
            raise
    
    def add_papers(self, papers: List[Dict]) -> int:
        """
        Add papers to the collection with deduplication.
        
        Args:
            papers: List of paper dictionaries
            
        Returns:
            Number of new papers added
        """
        if not papers:
            return 0
        
        new_papers = []
        duplicate_count = 0
        
        for paper in papers:
            arxiv_id = paper.get('arxiv_id', '')
            
            if not arxiv_id:
                self.logger.warning("Paper without ArXiv ID, skipping")
                continue
            
            if arxiv_id in self._seen_ids:
                duplicate_count += 1
                continue
            
            # Add to cache and tracking set
            self._papers_cache.append(paper)
            self._seen_ids.add(arxiv_id)
            new_papers.append(paper)
        
        if new_papers:
            self._save_to_database(new_papers)
            self.logger.info(f"Added {len(new_papers)} new papers, skipped {duplicate_count} duplicates")
        
        return len(new_papers)
    
    def _save_to_database(self, papers: List[Dict]) -> None:
        """Save papers to SQLite database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for paper in papers:
                    # Convert lists to JSON strings for storage
                    authors_json = json.dumps(paper.get('authors', []))
                    categories_json = json.dumps(paper.get('categories', []))
                    
                    cursor.execute('''
                        INSERT OR REPLACE INTO papers (
                            arxiv_id, title, authors, abstract, published, updated,
                            primary_category, categories, pdf_url, abs_url, doi, comment,
                            updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ''', (
                        paper.get('arxiv_id', ''),
                        paper.get('title', ''),
                        authors_json,
                        paper.get('abstract', ''),
                        paper.get('published', ''),
                        paper.get('updated', ''),
                        paper.get('primary_category', ''),
                        categories_json,
                        paper.get('pdf_url', ''),
                        paper.get('abs_url', ''),
                        paper.get('doi', ''),
                        paper.get('comment', '')
                    ))
                
                conn.commit()
                
        except sqlite3.Error as e:
            self.logger.error(f"Failed to save papers to database: {e}")
            raise
    
    def get_papers(self, 
                   category: Optional[str] = None,
                   date_from: Optional[str] = None,
                   date_to: Optional[str] = None,
                   downloaded_only: bool = False) -> List[Dict]:
        """
        Retrieve papers from database with optional filtering.
        
        Args:
            category: Filter by primary category
            date_from: Filter papers published from this date (YYYY-MM-DD)
            date_to: Filter papers published until this date (YYYY-MM-DD)
            downloaded_only: Return only downloaded papers
            
        Returns:
            List of paper dictionaries
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                query = "SELECT * FROM papers WHERE 1=1"
                params = []
                
                if category:
                    query += " AND primary_category = ?"
                    params.append(category)
                
                if date_from:
                    query += " AND published >= ?"
                    params.append(date_from)
                
                if date_to:
                    query += " AND published <= ?"
                    params.append(date_to)
                
                if downloaded_only:
                    query += " AND downloaded = 1"
                
                query += " ORDER BY published DESC"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                papers = []
                for row in rows:
                    paper = dict(row)
                    # Convert JSON strings back to lists
                    paper['authors'] = json.loads(paper['authors']) if paper['authors'] else []
                    paper['categories'] = json.loads(paper['categories']) if paper['categories'] else []
                    papers.append(paper)
                
                return papers
                
        except sqlite3.Error as e:
            self.logger.error(f"Failed to retrieve papers: {e}")
            return []
    
    def update_download_status(self, arxiv_id: str, downloaded: bool, file_path: Optional[str] = None) -> bool:
        """
        Update download status for a paper.
        
        Args:
            arxiv_id: ArXiv paper ID
            downloaded: Download status
            file_path: Path to downloaded file
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE papers 
                    SET downloaded = ?, download_path = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE arxiv_id = ?
                ''', (downloaded, file_path, arxiv_id))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except sqlite3.Error as e:
            self.logger.error(f"Failed to update download status for {arxiv_id}: {e}")
            return False
    
    def export_to_json(self, output_path: str, papers: Optional[List[Dict]] = None) -> bool:
        """
        Export papers to JSON format.
        
        Args:
            output_path: Output file path
            papers: List of papers to export (defaults to all cached papers)
            
        Returns:
            True if export successful, False otherwise
        """
        try:
            if papers is None:
                papers = self._papers_cache
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            
            export_data = {
                'exported_at': datetime.now().isoformat(),
                'total_papers': len(papers),
                'papers': papers
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Exported {len(papers)} papers to {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export to JSON: {e}")
            return False
    
    def export_to_csv(self, output_path: str, papers: Optional[List[Dict]] = None) -> bool:
        """
        Export papers to CSV format.
        
        Args:
            output_path: Output file path
            papers: List of papers to export (defaults to all cached papers)
            
        Returns:
            True if export successful, False otherwise
        """
        try:
            if papers is None:
                papers = self._papers_cache
            
            if not papers:
                self.logger.warning("No papers to export")
                return False
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            
            # Flatten data for CSV export
            flattened_papers = []
            for paper in papers:
                flat_paper = paper.copy()
                # Convert lists to comma-separated strings
                flat_paper['authors'] = '; '.join(paper.get('authors', []))
                flat_paper['categories'] = '; '.join(paper.get('categories', []))
                flattened_papers.append(flat_paper)
            
            # Create DataFrame and export
            df = pd.DataFrame(flattened_papers)
            df.to_csv(output_path, index=False, encoding='utf-8')
            
            self.logger.info(f"Exported {len(papers)} papers to {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export to CSV: {e}")
            return False
    
    def load_from_json(self, input_path: str) -> List[Dict]:
        """
        Load papers from JSON file.
        
        Args:
            input_path: Path to JSON file
            
        Returns:
            List of loaded papers
        """
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            papers = data.get('papers', []) if isinstance(data, dict) else data
            self.logger.info(f"Loaded {len(papers)} papers from {input_path}")
            return papers
            
        except Exception as e:
            self.logger.error(f"Failed to load from JSON: {e}")
            return []
    
    def get_statistics(self) -> Dict:
        """
        Get statistics about the paper collection.
        
        Returns:
            Dictionary containing various statistics
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Total papers
                cursor.execute("SELECT COUNT(*) FROM papers")
                total_papers = cursor.fetchone()[0]
                
                # Downloaded papers
                cursor.execute("SELECT COUNT(*) FROM papers WHERE downloaded = 1")
                downloaded_papers = cursor.fetchone()[0]
                
                # Papers by category
                cursor.execute('''
                    SELECT primary_category, COUNT(*) 
                    FROM papers 
                    WHERE primary_category != '' 
                    GROUP BY primary_category 
                    ORDER BY COUNT(*) DESC 
                    LIMIT 10
                ''')
                top_categories = dict(cursor.fetchall())
                
                # Papers by year
                cursor.execute('''
                    SELECT substr(published, 1, 4) as year, COUNT(*) 
                    FROM papers 
                    WHERE published != '' 
                    GROUP BY year 
                    ORDER BY year DESC 
                    LIMIT 10
                ''')
                papers_by_year = dict(cursor.fetchall())
                
                # Recent papers (last 30 days)
                cursor.execute('''
                    SELECT COUNT(*) FROM papers 
                    WHERE created_at >= datetime('now', '-30 days')
                ''')
                recent_papers = cursor.fetchone()[0]
                
                return {
                    'total_papers': total_papers,
                    'downloaded_papers': downloaded_papers,
                    'download_rate': downloaded_papers / max(total_papers, 1) * 100,
                    'recent_papers': recent_papers,
                    'top_categories': top_categories,
                    'papers_by_year': papers_by_year
                }
                
        except sqlite3.Error as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {}
    
    def cleanup_database(self) -> bool:
        """
        Clean up database by removing duplicate entries and optimizing.
        
        Returns:
            True if cleanup successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Remove exact duplicates (keeping the most recent)
                cursor.execute('''
                    DELETE FROM papers 
                    WHERE rowid NOT IN (
                        SELECT MIN(rowid) 
                        FROM papers 
                        GROUP BY arxiv_id
                    )
                ''')
                
                removed_duplicates = cursor.rowcount
                
                # Vacuum database to reclaim space
                cursor.execute("VACUUM")
                
                conn.commit()
                
                self.logger.info(f"Database cleanup completed. Removed {removed_duplicates} duplicates")
                return True
                
        except sqlite3.Error as e:
            self.logger.error(f"Database cleanup failed: {e}")
            return False
    
    def backup_database(self, backup_path: Optional[str] = None) -> bool:
        """
        Create a backup of the database.
        
        Args:
            backup_path: Path for backup file (defaults to timestamped backup)
            
        Returns:
            True if backup successful, False otherwise
        """
        try:
            if not backup_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"{self.db_path}.backup_{timestamp}"
            
            # Ensure backup directory exists
            os.makedirs(os.path.dirname(os.path.abspath(backup_path)), exist_ok=True)
            
            with sqlite3.connect(self.db_path) as source:
                with sqlite3.connect(backup_path) as backup:
                    source.backup(backup)
            
            self.logger.info(f"Database backed up to {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Database backup failed: {e}")
            return False
    
    def search_papers(self, 
                     query: str, 
                     fields: Optional[List[str]] = None) -> List[Dict]:
        """
        Search papers in local database using text search.
        
        Args:
            query: Search query
            fields: Fields to search in (defaults to title, abstract, authors)
            
        Returns:
            List of matching papers
        """
        if not fields:
            fields = ['title', 'abstract', 'authors']
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Build search query
                conditions = []
                params = []
                
                for field in fields:
                    if field in ['title', 'abstract']:
                        conditions.append(f"{field} LIKE ?")
                        params.append(f"%{query}%")
                    elif field == 'authors':
                        conditions.append("authors LIKE ?")
                        params.append(f"%{query}%")
                
                if not conditions:
                    return []
                
                sql_query = f"SELECT * FROM papers WHERE ({' OR '.join(conditions)}) ORDER BY published DESC"
                
                cursor.execute(sql_query, params)
                rows = cursor.fetchall()
                
                papers = []
                for row in rows:
                    paper = dict(row)
                    paper['authors'] = json.loads(paper['authors']) if paper['authors'] else []
                    paper['categories'] = json.loads(paper['categories']) if paper['categories'] else []
                    papers.append(paper)
                
                return papers
                
        except sqlite3.Error as e:
            self.logger.error(f"Database search failed: {e}")
            return []
    
    def clear_cache(self) -> None:
        """Clear the in-memory papers cache."""
        self._papers_cache.clear()
        self._seen_ids.clear()
        self.logger.info("Papers cache cleared")
    
    def get_cache_size(self) -> int:
        """Get the current cache size."""
        return len(self._papers_cache)