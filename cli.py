"""
Command-line interface for ArXiv paper crawler.
Provides user-friendly commands for searching, downloading, and managing papers.
"""

import sys
import logging
from typing import Optional, List, Dict
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress
from rich.panel import Panel
from rich.text import Text

from config import ConfigManager
from arxiv_api import ArxivAPI, ArxivAPIException
from data_processor import DataProcessor
from downloader import DownloadManager


console = Console()


class CLIException(Exception):
    """Custom exception for CLI-related errors."""
    pass


def setup_logging(log_level: str, log_file: Optional[str] = None) -> None:
    """Setup logging configuration."""
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Setup console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)
    
    # Setup file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def display_papers_table(papers: List[Dict], max_rows: int = 20) -> None:
    """Display papers in a formatted table."""
    if not papers:
        console.print("[yellow]No papers found.[/yellow]")
        return
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID", style="dim", width=12)
    table.add_column("Title", style="bold", max_width=50)
    table.add_column("First Author", style="cyan", width=20)
    table.add_column("Category", style="green", width=10)
    table.add_column("Published", style="blue", width=10)
    
    displayed_papers = papers[:max_rows]
    
    for paper in displayed_papers:
        arxiv_id = paper.get('arxiv_id', 'Unknown')
        title = paper.get('title', 'No title')
        
        # Truncate title if too long
        if len(title) > 47:
            title = title[:44] + "..."
        
        # Get first author
        authors = paper.get('authors', [])
        first_author = authors[0] if authors else 'Unknown'
        if len(first_author) > 17:
            first_author = first_author[:14] + "..."
        
        category = paper.get('primary_category', 'Unknown')
        published = paper.get('published', 'Unknown')[:10]  # YYYY-MM-DD
        
        table.add_row(arxiv_id, title, first_author, category, published)
    
    console.print(table)
    
    if len(papers) > max_rows:
        console.print(f"[dim]... and {len(papers) - max_rows} more papers[/dim]")


def display_paper_details(paper: Dict) -> None:
    """Display detailed information about a single paper."""
    title = Text(paper.get('title', 'No title'), style="bold blue")
    
    panel_content = []
    panel_content.append(f"ArXiv ID: {paper.get('arxiv_id', 'Unknown')}")
    
    authors = paper.get('authors', [])
    if authors:
        authors_text = ', '.join(authors[:5])
        if len(authors) > 5:
            authors_text += f" (and {len(authors) - 5} more)"
        panel_content.append(f"Authors: {authors_text}")
    
    panel_content.append(f"Primary Category: {paper.get('primary_category', 'Unknown')}")
    panel_content.append(f"Published: {paper.get('published', 'Unknown')[:10]}")
    panel_content.append(f"Updated: {paper.get('updated', 'Unknown')[:10]}")
    
    if paper.get('doi'):
        panel_content.append(f"DOI: {paper.get('doi')}")
    
    abstract = paper.get('abstract', 'No abstract available')
    if len(abstract) > 500:
        abstract = abstract[:497] + "..."
    panel_content.append(f"\nAbstract:\n{abstract}")
    
    if paper.get('comment'):
        panel_content.append(f"\nComment: {paper.get('comment')}")
    
    content = '\n'.join(panel_content)
    panel = Panel(content, title=title, border_style="blue")
    console.print(panel)


@click.group()
@click.option('--config', '-c', default='config.yaml', 
              help='Configuration file path')
@click.option('--log-level', default='INFO',
              type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']),
              help='Logging level')
@click.option('--log-file', help='Log file path')
@click.pass_context
def cli(ctx, config, log_level, log_file):
    """ArXiv Academic Paper Crawler - Search and download research papers."""
    ctx.ensure_object(dict)
    
    # Setup logging
    setup_logging(log_level, log_file)
    
    # Load configuration
    try:
        config_manager = ConfigManager(config)
        ctx.obj['config'] = config_manager.get_all()
        ctx.obj['config_manager'] = config_manager
    except Exception as e:
        console.print(f"[red]Error loading configuration: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option('--query', '-q', help='General search query')
@click.option('--author', '-a', help='Author name to search')
@click.option('--title', '-t', help='Title keywords to search')
@click.option('--abstract', help='Abstract keywords to search')
@click.option('--category', '-c', help='ArXiv category (e.g., cs.AI)')
@click.option('--date-from', help='Start date (YYYY-MM-DD)')
@click.option('--date-to', help='End date (YYYY-MM-DD)')
@click.option('--max-results', '-n', default=50, type=int, 
              help='Maximum number of results')
@click.option('--sort-by', default='relevance',
              type=click.Choice(['relevance', 'lastUpdatedDate', 'submittedDate']),
              help='Sort criteria')
@click.option('--sort-order', default='descending',
              type=click.Choice(['ascending', 'descending']),
              help='Sort order')
@click.option('--export', '-e', help='Export results to file (JSON or CSV)')
@click.option('--show-details', is_flag=True, help='Show detailed paper information')
@click.pass_context
def search(ctx, query, author, title, abstract, category, date_from, date_to,
           max_results, sort_by, sort_order, export, show_details):
    """Search ArXiv papers with specified criteria."""
    config = ctx.obj['config']
    
    # Validate inputs
    if not any([query, author, title, abstract, category]):
        console.print("[red]Error: At least one search criteria must be specified.[/red]")
        return
    
    try:
        # Initialize API and data processor
        api = ArxivAPI(config['api'])
        data_processor = DataProcessor(config['storage'])
        
        console.print("[blue]Searching ArXiv papers...[/blue]")
        
        # Perform search
        with console.status("[bold green]Searching...") as status:
            result = api.search(
                query=query,
                author=author,
                title=title,
                abstract=abstract,
                category=category,
                date_from=date_from,
                date_to=date_to,
                max_results=max_results,
                sort_by=sort_by,
                sort_order=sort_order
            )
        
        papers = result.get('papers', [])
        
        if not papers:
            console.print("[yellow]No papers found matching your criteria.[/yellow]")
            return
        
        console.print(f"[green]Found {len(papers)} papers[/green]")
        
        # Add papers to database
        new_count = data_processor.add_papers(papers)
        if new_count > 0:
            console.print(f"[blue]Added {new_count} new papers to database[/blue]")
        
        # Display results
        if show_details:
            for paper in papers:
                display_paper_details(paper)
                console.print("-" * 80)
        else:
            display_papers_table(papers)
        
        # Export results if requested
        if export:
            export_path = Path(export)
            if export_path.suffix.lower() == '.json':
                success = data_processor.export_to_json(export, papers)
            elif export_path.suffix.lower() == '.csv':
                success = data_processor.export_to_csv(export, papers)
            else:
                console.print("[red]Error: Export format must be .json or .csv[/red]")
                return
            
            if success:
                console.print(f"[green]Results exported to {export}[/green]")
            else:
                console.print(f"[red]Failed to export results to {export}[/red]")
    
    except ArxivAPIException as e:
        console.print(f"[red]API Error: {e}[/red]")
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")


@cli.command()
@click.option('--input', '-i', help='Input file (JSON) containing papers')
@click.option('--query', '-q', help='Search query to download results')
@click.option('--category', '-c', help='Download papers from specific category')
@click.option('--max-results', '-n', type=int, help='Maximum papers to download')
@click.option('--threads', '-t', default=5, type=int, help='Number of download threads')
@click.option('--interactive', is_flag=True, help='Interactive paper selection')
@click.option('--output-dir', '-o', help='Output directory for downloads')
@click.pass_context
def download(ctx, input, query, category, max_results, threads, interactive, output_dir):
    """Download PDF files for papers."""
    config = ctx.obj['config']
    
    papers = []
    
    # Load papers from different sources
    if input:
        # Load from JSON file
        try:
            data_processor = DataProcessor(config['storage'])
            papers = data_processor.load_from_json(input)
            console.print(f"[blue]Loaded {len(papers)} papers from {input}[/blue]")
        except Exception as e:
            console.print(f"[red]Error loading papers from file: {e}[/red]")
            return
    
    elif query or category:
        # Search and download
        try:
            api = ArxivAPI(config['api'])
            data_processor = DataProcessor(config['storage'])
            
            console.print("[blue]Searching for papers to download...[/blue]")
            
            result = api.search(
                query=query,
                category=category,
                max_results=max_results or 100
            )
            
            papers = result.get('papers', [])
            
            if papers:
                data_processor.add_papers(papers)
                console.print(f"[green]Found {len(papers)} papers for download[/green]")
            
        except Exception as e:
            console.print(f"[red]Error searching papers: {e}[/red]")
            return
    
    else:
        console.print("[red]Error: Specify --input file or search criteria (--query/--category)[/red]")
        return
    
    if not papers:
        console.print("[yellow]No papers to download.[/yellow]")
        return
    
    try:
        # Setup download manager
        download_config = config['download'].copy()
        if output_dir:
            download_config['output_directory'] = output_dir
        if threads:
            download_config['max_concurrent_downloads'] = threads
        
        downloader = DownloadManager(download_config)
        data_processor = DataProcessor(config['storage'])
        
        # Download papers
        if interactive:
            results = downloader.download_with_selection(papers, interactive=True)
        else:
            console.print(f"[blue]Starting download of {len(papers)} papers with {threads} threads...[/blue]")
            results = downloader.download_papers(papers)
        
        # Update database with download status
        for result in results:
            if result.success:
                data_processor.update_download_status(result.arxiv_id, True, result.file_path)
            else:
                data_processor.update_download_status(result.arxiv_id, False)
        
        # Display statistics
        stats = downloader.get_statistics()
        console.print("\n[bold green]Download Summary:[/bold green]")
        console.print(f"Total papers: {stats['total']}")
        console.print(f"Successful: {stats['successful']}")
        console.print(f"Failed: {stats['failed']}")
        console.print(f"Skipped: {stats['skipped']}")
        console.print(f"Success rate: {stats['success_rate']:.1f}%")
        console.print(f"Total downloaded: {stats['formatted_size']}")
        
        # Show failed downloads
        failed_results = [r for r in results if not r.success]
        if failed_results:
            console.print(f"\n[red]Failed downloads ({len(failed_results)}):[/red]")
            for result in failed_results[:10]:  # Show first 10 failures
                console.print(f"  {result.arxiv_id}: {result.error}")
            
            if len(failed_results) > 10:
                console.print(f"  ... and {len(failed_results) - 10} more")
            
            # Ask if user wants to retry
            if click.confirm("\nRetry failed downloads?"):
                console.print("[blue]Retrying failed downloads...[/blue]")
                retry_results = downloader.retry_failed_downloads(failed_results, papers)
                
                retry_stats = {'successful': 0, 'failed': 0}
                for result in retry_results:
                    if result.success:
                        retry_stats['successful'] += 1
                        data_processor.update_download_status(result.arxiv_id, True, result.file_path)
                    else:
                        retry_stats['failed'] += 1
                
                console.print(f"[green]Retry results: {retry_stats['successful']} successful, {retry_stats['failed']} failed[/green]")
    
    except Exception as e:
        console.print(f"[red]Download error: {e}[/red]")


@cli.command()
@click.option('--category', '-c', help='Update papers from specific category')
@click.option('--days', '-d', default=7, type=int, help='Update papers from last N days')
@click.option('--max-results', '-n', type=int, help='Maximum papers to update')
@click.pass_context
def update(ctx, category, days, max_results):
    """Update database with new papers."""
    config = ctx.obj['config']
    
    try:
        api = ArxivAPI(config['api'])
        data_processor = DataProcessor(config['storage'])
        
        # Calculate date range
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        date_from = start_date.strftime('%Y-%m-%d')
        date_to = end_date.strftime('%Y-%m-%d')
        
        console.print(f"[blue]Updating papers from {date_from} to {date_to}[/blue]")
        if category:
            console.print(f"[blue]Category filter: {category}[/blue]")
        
        # Search for recent papers
        with console.status("[bold green]Searching for updates...") as status:
            result = api.search(
                category=category,
                date_from=date_from,
                date_to=date_to,
                max_results=max_results or 1000
            )
        
        papers = result.get('papers', [])
        
        if not papers:
            console.print("[yellow]No new papers found.[/yellow]")
            return
        
        console.print(f"[green]Found {len(papers)} papers[/green]")
        
        # Add to database
        new_count = data_processor.add_papers(papers)
        console.print(f"[blue]Added {new_count} new papers to database[/blue]")
        
        if new_count == 0:
            console.print("[yellow]No new papers were added (all papers already in database).[/yellow]")
        
    except Exception as e:
        console.print(f"[red]Update error: {e}[/red]")


@cli.command()
@click.option('--category', '-c', help='Show statistics for specific category')
@click.option('--export', '-e', help='Export statistics to file')
@click.pass_context
def stats(ctx, category, export):
    """Show database statistics."""
    config = ctx.obj['config']
    
    try:
        data_processor = DataProcessor(config['storage'])
        statistics = data_processor.get_statistics()
        
        if not statistics:
            console.print("[yellow]No statistics available.[/yellow]")
            return
        
        # Display general statistics
        console.print("[bold blue]Database Statistics:[/bold blue]")
        console.print(f"Total papers: {statistics.get('total_papers', 0):,}")
        console.print(f"Downloaded papers: {statistics.get('downloaded_papers', 0):,}")
        console.print(f"Download rate: {statistics.get('download_rate', 0):.1f}%")
        console.print(f"Papers added in last 30 days: {statistics.get('recent_papers', 0):,}")
        
        # Top categories
        top_categories = statistics.get('top_categories', {})
        if top_categories:
            console.print("\n[bold blue]Top Categories:[/bold blue]")
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Category", style="green")
            table.add_column("Papers", justify="right", style="cyan")
            
            for cat, count in list(top_categories.items())[:10]:
                table.add_row(cat, f"{count:,}")
            
            console.print(table)
        
        # Papers by year
        papers_by_year = statistics.get('papers_by_year', {})
        if papers_by_year:
            console.print("\n[bold blue]Papers by Year:[/bold blue]")
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Year", style="green")
            table.add_column("Papers", justify="right", style="cyan")
            
            for year, count in list(papers_by_year.items())[:10]:
                table.add_row(year, f"{count:,}")
            
            console.print(table)
        
        # Export if requested
        if export:
            import json
            with open(export, 'w') as f:
                json.dump(statistics, f, indent=2)
            console.print(f"[green]Statistics exported to {export}[/green]")
    
    except Exception as e:
        console.print(f"[red]Statistics error: {e}[/red]")


@cli.command()
@click.option('--query', '-q', required=True, help='Search query')
@click.option('--fields', default='title,abstract,authors', 
              help='Fields to search (comma-separated)')
@click.option('--limit', '-l', default=50, type=int, help='Maximum results to show')
@click.pass_context
def search_local(ctx, query, fields, limit):
    """Search papers in local database."""
    config = ctx.obj['config']
    
    try:
        data_processor = DataProcessor(config['storage'])
        
        search_fields = [f.strip() for f in fields.split(',')]
        
        console.print(f"[blue]Searching local database for: '{query}'[/blue]")
        console.print(f"[blue]Fields: {', '.join(search_fields)}[/blue]")
        
        papers = data_processor.search_papers(query, search_fields)
        
        if not papers:
            console.print("[yellow]No papers found matching your query.[/yellow]")
            return
        
        console.print(f"[green]Found {len(papers)} papers[/green]")
        
        # Limit results if requested
        if limit and len(papers) > limit:
            papers = papers[:limit]
            console.print(f"[blue]Showing first {limit} results[/blue]")
        
        display_papers_table(papers)
    
    except Exception as e:
        console.print(f"[red]Search error: {e}[/red]")


@cli.command()
@click.option('--backup', is_flag=True, help='Create backup before cleanup')
@click.pass_context
def cleanup(ctx, backup):
    """Clean up database and downloaded files."""
    config = ctx.obj['config']
    
    try:
        data_processor = DataProcessor(config['storage'])
        downloader = DownloadManager(config['download'])
        
        if backup:
            console.print("[blue]Creating database backup...[/blue]")
            if data_processor.backup_database():
                console.print("[green]Database backup created[/green]")
            else:
                console.print("[red]Failed to create backup[/red]")
                return
        
        console.print("[blue]Cleaning up database...[/blue]")
        if data_processor.cleanup_database():
            console.print("[green]Database cleanup completed[/green]")
        
        console.print("[blue]Cleaning up incomplete downloads...[/blue]")
        cleaned_files = downloader.cleanup_incomplete_downloads()
        console.print(f"[green]Removed {cleaned_files} incomplete download files[/green]")
    
    except Exception as e:
        console.print(f"[red]Cleanup error: {e}[/red]")


@cli.command()
@click.pass_context
def categories(ctx):
    """Show available ArXiv categories."""
    config = ctx.obj['config']
    
    try:
        api = ArxivAPI(config['api'])
        categories = api.get_categories()
        
        console.print("[bold blue]Available ArXiv Categories:[/bold blue]")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Code", style="green", width=15)
        table.add_column("Description", style="cyan")
        
        for code, description in sorted(categories.items()):
            table.add_row(code, description)
        
        console.print(table)
    
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


if __name__ == '__main__':
    cli()