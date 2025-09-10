@echo off
REM ArXiv Paper Crawler - Windows Batch Script
REM This script provides easy access to common crawler functions on Windows

setlocal enabledelayedexpansion

:menu
cls
echo.
echo ===============================================
echo         ArXiv Academic Paper Crawler
echo ===============================================
echo.
echo 1. Search papers by keyword
echo 2. Search papers by author
echo 3. Search papers by category
echo 4. Download papers (interactive)
echo 5. View database statistics
echo 6. Search local database
echo 7. View available categories
echo 8. Update database
echo 9. Run custom command
echo 0. Exit
echo.
set /p choice="Select an option (0-9): "

if "%choice%"=="1" goto search_keyword
if "%choice%"=="2" goto search_author
if "%choice%"=="3" goto search_category
if "%choice%"=="4" goto download_papers
if "%choice%"=="5" goto show_stats
if "%choice%"=="6" goto search_local
if "%choice%"=="7" goto show_categories
if "%choice%"=="8" goto update_db
if "%choice%"=="9" goto custom_command
if "%choice%"=="0" goto exit
goto menu

:search_keyword
echo.
set /p query="Enter search keywords: "
set /p max_results="Maximum results (default 20): "
if "%max_results%"=="" set max_results=20

python main.py search --query "%query%" --max-results %max_results%
echo.
pause
goto menu

:search_author
echo.
set /p author="Enter author name: "
set /p max_results="Maximum results (default 20): "
if "%max_results%"=="" set max_results=20

python main.py search --author "%author%" --max-results %max_results%
echo.
pause
goto menu

:search_category
echo.
echo Available categories (showing top categories):
echo cs.AI - Artificial Intelligence
echo cs.CV - Computer Vision and Pattern Recognition
echo cs.LG - Machine Learning
echo cs.CL - Computation and Language
echo cs.RO - Robotics
echo.
echo For full list, choose option 7 from main menu
echo.
set /p category="Enter category code (e.g., cs.AI): "
set /p max_results="Maximum results (default 20): "
if "%max_results%"=="" set max_results=20

python main.py search --category "%category%" --max-results %max_results%
echo.
pause
goto menu

:download_papers
echo.
echo Download options:
echo 1. Search and download
echo 2. Download from JSON file
set /p download_choice="Choose option (1-2): "

if "%download_choice%"=="1" (
    set /p query="Enter search query: "
    set /p max_results="Maximum papers to download (default 10): "
    if "!max_results!"=="" set max_results=10
    
    python main.py download --query "!query!" --max-results !max_results! --interactive
) else if "%download_choice%"=="2" (
    set /p json_file="Enter JSON file path: "
    python main.py download --input "!json_file!" --interactive
)
echo.
pause
goto menu

:show_stats
echo.
python main.py stats
echo.
pause
goto menu

:search_local
echo.
set /p query="Enter search query for local database: "
set /p fields="Search fields (default: title,abstract,authors): "
if "%fields%"=="" set fields=title,abstract,authors

python main.py search-local --query "%query%" --fields "%fields%"
echo.
pause
goto menu

:show_categories
echo.
python main.py categories
echo.
pause
goto menu

:update_db
echo.
set /p category="Enter category to update (leave empty for all): "
set /p days="Days to look back (default 7): "
if "%days%"=="" set days=7

if "%category%"=="" (
    python main.py update --days %days%
) else (
    python main.py update --category "%category%" --days %days%
)
echo.
pause
goto menu

:custom_command
echo.
echo Enter a custom command (without 'python main.py')
echo Examples:
echo   search --query "deep learning" --export results.json
echo   download --query "computer vision" --threads 8
echo   cleanup --backup
echo.
set /p custom_cmd="Command: "
if not "%custom_cmd%"=="" (
    python main.py %custom_cmd%
)
echo.
pause
goto menu

:exit
echo.
echo Thank you for using ArXiv Paper Crawler!
echo.
pause
exit /b 0