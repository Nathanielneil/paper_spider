#!/bin/bash

# ArXiv Paper Crawler - Linux/macOS Shell Script
# This script provides easy access to common crawler functions

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_color() {
    echo -e "${1}${2}${NC}"
}

# Function to show menu
show_menu() {
    clear
    echo
    print_color $BLUE "==============================================="
    print_color $BLUE "         ArXiv Academic Paper Crawler"
    print_color $BLUE "==============================================="
    echo
    echo "1. Search papers by keyword"
    echo "2. Search papers by author"
    echo "3. Search papers by category"
    echo "4. Download papers (interactive)"
    echo "5. View database statistics"
    echo "6. Search local database"
    echo "7. View available categories"
    echo "8. Update database"
    echo "9. Run custom command"
    echo "0. Exit"
    echo
}

# Function to read user input with prompt
read_input() {
    read -p "$1" input
    echo "$input"
}

# Function to pause and wait for user
pause() {
    echo
    read -p "Press Enter to continue..."
}

# Main menu loop
while true; do
    show_menu
    read -p "Select an option (0-9): " choice
    
    case $choice in
        1)
            echo
            query=$(read_input "Enter search keywords: ")
            max_results=$(read_input "Maximum results (default 20): ")
            max_results=${max_results:-20}
            
            python3 main.py search --query "$query" --max-results $max_results
            pause
            ;;
            
        2)
            echo
            author=$(read_input "Enter author name: ")
            max_results=$(read_input "Maximum results (default 20): ")
            max_results=${max_results:-20}
            
            python3 main.py search --author "$author" --max-results $max_results
            pause
            ;;
            
        3)
            echo
            print_color $YELLOW "Available categories (showing top categories):"
            echo "cs.AI - Artificial Intelligence"
            echo "cs.CV - Computer Vision and Pattern Recognition"
            echo "cs.LG - Machine Learning"
            echo "cs.CL - Computation and Language"
            echo "cs.RO - Robotics"
            echo
            print_color $YELLOW "For full list, choose option 7 from main menu"
            echo
            
            category=$(read_input "Enter category code (e.g., cs.AI): ")
            max_results=$(read_input "Maximum results (default 20): ")
            max_results=${max_results:-20}
            
            python3 main.py search --category "$category" --max-results $max_results
            pause
            ;;
            
        4)
            echo
            echo "Download options:"
            echo "1. Search and download"
            echo "2. Download from JSON file"
            read -p "Choose option (1-2): " download_choice
            
            case $download_choice in
                1)
                    query=$(read_input "Enter search query: ")
                    max_results=$(read_input "Maximum papers to download (default 10): ")
                    max_results=${max_results:-10}
                    
                    python3 main.py download --query "$query" --max-results $max_results --interactive
                    ;;
                2)
                    json_file=$(read_input "Enter JSON file path: ")
                    python3 main.py download --input "$json_file" --interactive
                    ;;
                *)
                    print_color $RED "Invalid option"
                    ;;
            esac
            pause
            ;;
            
        5)
            echo
            python3 main.py stats
            pause
            ;;
            
        6)
            echo
            query=$(read_input "Enter search query for local database: ")
            fields=$(read_input "Search fields (default: title,abstract,authors): ")
            fields=${fields:-"title,abstract,authors"}
            
            python3 main.py search-local --query "$query" --fields "$fields"
            pause
            ;;
            
        7)
            echo
            python3 main.py categories
            pause
            ;;
            
        8)
            echo
            category=$(read_input "Enter category to update (leave empty for all): ")
            days=$(read_input "Days to look back (default 7): ")
            days=${days:-7}
            
            if [[ -z "$category" ]]; then
                python3 main.py update --days $days
            else
                python3 main.py update --category "$category" --days $days
            fi
            pause
            ;;
            
        9)
            echo
            print_color $YELLOW "Enter a custom command (without 'python3 main.py')"
            print_color $YELLOW "Examples:"
            echo "  search --query \"deep learning\" --export results.json"
            echo "  download --query \"computer vision\" --threads 8"
            echo "  cleanup --backup"
            echo
            
            custom_cmd=$(read_input "Command: ")
            if [[ -n "$custom_cmd" ]]; then
                python3 main.py $custom_cmd
            fi
            pause
            ;;
            
        0)
            echo
            print_color $GREEN "Thank you for using ArXiv Paper Crawler!"
            echo
            exit 0
            ;;
            
        *)
            print_color $RED "Invalid option. Please try again."
            sleep 1
            ;;
    esac
done