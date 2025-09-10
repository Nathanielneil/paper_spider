#!/usr/bin/env python3
"""
ArXiv Academic Paper Crawler - Main Entry Point
A comprehensive tool for searching, downloading, and managing ArXiv research papers.

This is the main entry point that provides both CLI interface and programmatic access.
"""

import sys
import os
import logging
from pathlib import Path
from typing import Optional

# Add current directory to Python path to ensure imports work
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from cli import cli
from config import ConfigManager, ConfigException


def setup_logging_from_config(config_manager: ConfigManager) -> None:
    """Setup logging based on configuration."""
    try:
        logging_config = config_manager.get_logging_config()
        
        log_level = logging_config.get('level', 'INFO').upper()
        log_file = logging_config.get('log_file', 'arxiv_crawler.log')
        max_file_size = logging_config.get('max_file_size', '10MB')
        backup_count = logging_config.get('backup_count', 3)
        
        # Parse file size
        if isinstance(max_file_size, str):
            if max_file_size.upper().endswith('MB'):
                max_bytes = int(float(max_file_size[:-2]) * 1024 * 1024)
            elif max_file_size.upper().endswith('KB'):
                max_bytes = int(float(max_file_size[:-2]) * 1024)
            else:
                max_bytes = int(max_file_size)
        else:
            max_bytes = max_file_size
        
        # Setup logging
        from logging.handlers import RotatingFileHandler
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Setup root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level, logging.INFO))
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.WARNING)  # Only warnings and errors to console
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        # File handler (if log file is specified)
        if log_file and log_file.lower() != 'none':
            try:
                # Ensure log directory exists
                log_path = Path(log_file)
                log_path.parent.mkdir(parents=True, exist_ok=True)
                
                file_handler = RotatingFileHandler(
                    log_file,
                    maxBytes=max_bytes,
                    backupCount=backup_count,
                    encoding='utf-8'
                )
                file_handler.setLevel(getattr(logging, log_level, logging.INFO))
                file_handler.setFormatter(formatter)
                root_logger.addHandler(file_handler)
                
            except Exception as e:
                print(f"Warning: Could not setup file logging: {e}")
        
        # Log startup message
        logger = logging.getLogger(__name__)
        logger.info("ArXiv Paper Crawler started")
        logger.info(f"Log level: {log_level}")
        if log_file and log_file.lower() != 'none':
            logger.info(f"Log file: {log_file}")
        
    except Exception as e:
        print(f"Warning: Could not setup logging from config: {e}")
        # Fall back to basic logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )


def check_dependencies() -> bool:
    """
    Check if all required dependencies are available.
    
    Returns:
        True if all dependencies are available, False otherwise
    """
    required_modules = [
        ('requests', 'requests'),
        ('feedparser', 'feedparser'),
        ('pandas', 'pandas'),
        ('tqdm', 'tqdm'),
        ('rich', 'rich'),
        ('click', 'click'),
        ('yaml', 'pyyaml')
    ]
    
    missing_modules = []
    
    for module_name, package_name in required_modules:
        try:
            __import__(module_name)
        except ImportError:
            missing_modules.append(package_name)
    
    if missing_modules:
        print("Error: Missing required dependencies:")
        for module in missing_modules:
            print(f"  - {module}")
        print("\nPlease install missing dependencies:")
        print(f"  pip install {' '.join(missing_modules)}")
        print("\nOr install all dependencies:")
        print("  pip install -r requirements.txt")
        return False
    
    return True


def create_default_files() -> None:
    """Create default configuration and directory structure."""
    try:
        # Create default directories
        default_dirs = [
            'downloaded_papers',
            'logs'
        ]
        
        for dir_name in default_dirs:
            dir_path = Path(dir_name)
            dir_path.mkdir(exist_ok=True)
        
        # Create example config if it doesn't exist
        config_path = Path('config.yaml')
        if not config_path.exists():
            config_manager = ConfigManager(config_path)
            print(f"Created default configuration file: {config_path}")
        
    except Exception as e:
        print(f"Warning: Could not create default files: {e}")


def print_banner() -> None:
    """Print application banner."""
    banner = """
╔═══════════════════════════════════════════════════════════════════════════════╗
║                       ArXiv Academic Paper Crawler                           ║
║                                                                               ║
║  A comprehensive tool for searching, downloading, and managing research       ║
║  papers from ArXiv. Features multi-threaded downloads, database storage,     ║
║  and rich command-line interface.                                            ║
║                                                                               ║
║  Usage: python main.py [COMMAND] [OPTIONS]                                   ║
║  Help:  python main.py --help                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_quick_start() -> None:
    """Print quick start guide."""
    guide = """
Quick Start Guide:
==================

1. Search for papers:
   python main.py search --query "machine learning" --max-results 10

2. Search by author:
   python main.py search --author "Yann LeCun" --category "cs.AI"

3. Download papers:
   python main.py download --query "deep learning" --interactive

4. View available categories:
   python main.py categories

5. Get database statistics:
   python main.py stats

6. Search local database:
   python main.py search-local --query "neural networks"

For detailed help on any command:
   python main.py COMMAND --help

Configuration:
   Edit 'config.yaml' to customize settings
   Environment variables can override config (see documentation)
    """
    print(guide)


def handle_first_run() -> None:
    """Handle first-time application setup."""
    print("Welcome to ArXiv Paper Crawler!")
    print("This appears to be your first run. Setting up default configuration...")
    
    create_default_files()
    
    print("\nSetup complete! Here's how to get started:\n")
    print_quick_start()
    
    # Ask if user wants to see categories
    try:
        show_categories = input("\nWould you like to see available ArXiv categories? (y/N): ")
        if show_categories.lower().startswith('y'):
            from arxiv_api import ArxivAPI
            from config import get_config_manager
            
            config_manager = get_config_manager()
            api = ArxivAPI(config_manager.get_api_config())
            
            print("\nAvailable ArXiv Categories:")
            print("=" * 50)
            
            categories = api.get_categories()
            for code, description in sorted(categories.items()):
                print(f"{code:15} - {description}")
    
    except (KeyboardInterrupt, EOFError):
        print("\n\nSkipped category listing.")
    
    print("\nYou can now use the application. Try:")
    print("  python main.py search --query 'your topic' --max-results 5")


def main() -> None:
    """Main application entry point."""
    try:
        # Check if this is a first run (no config file and no command line args)
        config_exists = Path('config.yaml').exists()
        has_args = len(sys.argv) > 1
        
        if not config_exists and not has_args:
            print_banner()
            handle_first_run()
            return
        
        # Check dependencies
        if not check_dependencies():
            sys.exit(1)
        
        # Load configuration
        try:
            config_manager = ConfigManager()
            setup_logging_from_config(config_manager)
            
            # Validate paths
            config_manager.validate_paths()
            
        except ConfigException as e:
            print(f"Configuration error: {e}")
            print("Please check your configuration file or create a new one.")
            sys.exit(1)
        
        # If no arguments, show help
        if not has_args:
            print_banner()
            print_quick_start()
            return
        
        # Run CLI
        cli()
        
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(130)  # Standard exit code for Ctrl+C
    
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.exception("Unexpected error in main application")
        print(f"\nUnexpected error: {e}")
        print("Please check the log file for more details.")
        sys.exit(1)


def run_interactive_mode() -> None:
    """Run in interactive mode with menu-driven interface."""
    from rich.console import Console
    from rich.prompt import Prompt, Confirm
    from rich.panel import Panel
    
    console = Console()
    
    while True:
        console.clear()
        
        # Display menu
        menu_text = """
[bold blue]ArXiv Paper Crawler - Interactive Mode[/bold blue]

[cyan]1.[/cyan] Search papers by keyword
[cyan]2.[/cyan] Search papers by author  
[cyan]3.[/cyan] Search papers by category
[cyan]4.[/cyan] Download papers
[cyan]5.[/cyan] View database statistics
[cyan]6.[/cyan] Search local database
[cyan]7.[/cyan] View available categories
[cyan]8.[/cyan] Configuration settings
[cyan]9.[/cyan] Exit

        """
        
        console.print(Panel(menu_text, border_style="blue"))
        
        try:
            choice = Prompt.ask("Select an option", choices=["1", "2", "3", "4", "5", "6", "7", "8", "9"])
            
            if choice == "1":
                # Search by keyword
                query = Prompt.ask("Enter search keywords")
                max_results = Prompt.ask("Maximum results", default="20")
                
                os.system(f'python main.py search --query "{query}" --max-results {max_results}')
                input("\nPress Enter to continue...")
                
            elif choice == "2":
                # Search by author
                author = Prompt.ask("Enter author name")
                max_results = Prompt.ask("Maximum results", default="20")
                
                os.system(f'python main.py search --author "{author}" --max-results {max_results}')
                input("\nPress Enter to continue...")
                
            elif choice == "3":
                # Search by category
                console.print("\n[blue]First, let's see available categories:[/blue]")
                os.system('python main.py categories')
                
                category = Prompt.ask("\nEnter category code (e.g., cs.AI)")
                max_results = Prompt.ask("Maximum results", default="20")
                
                os.system(f'python main.py search --category "{category}" --max-results {max_results}')
                input("\nPress Enter to continue...")
                
            elif choice == "4":
                # Download papers
                download_type = Prompt.ask(
                    "Download from",
                    choices=["search", "file"],
                    default="search"
                )
                
                if download_type == "search":
                    query = Prompt.ask("Enter search query for download")
                    max_results = Prompt.ask("Maximum papers to download", default="10")
                    interactive = Confirm.ask("Interactive selection?", default=True)
                    
                    interactive_flag = "--interactive" if interactive else ""
                    os.system(f'python main.py download --query "{query}" --max-results {max_results} {interactive_flag}')
                else:
                    file_path = Prompt.ask("Enter JSON file path")
                    os.system(f'python main.py download --input "{file_path}" --interactive')
                
                input("\nPress Enter to continue...")
                
            elif choice == "5":
                # Statistics
                os.system('python main.py stats')
                input("\nPress Enter to continue...")
                
            elif choice == "6":
                # Local search
                query = Prompt.ask("Enter search query")
                fields = Prompt.ask("Search fields (comma-separated)", default="title,abstract,authors")
                
                os.system(f'python main.py search-local --query "{query}" --fields "{fields}"')
                input("\nPress Enter to continue...")
                
            elif choice == "7":
                # Categories
                os.system('python main.py categories')
                input("\nPress Enter to continue...")
                
            elif choice == "8":
                # Configuration
                console.print("\n[blue]Current configuration file: config.yaml[/blue]")
                console.print("Edit the file manually or use environment variables.")
                console.print("See documentation for all available options.")
                input("\nPress Enter to continue...")
                
            elif choice == "9":
                # Exit
                console.print("[green]Thank you for using ArXiv Paper Crawler![/green]")
                break
        
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Goodbye![/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            input("\nPress Enter to continue...")


if __name__ == '__main__':
    # Check for interactive mode
    if len(sys.argv) > 1 and sys.argv[1] == '--interactive':
        run_interactive_mode()
    else:
        main()