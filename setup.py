"""
Setup script for ArXiv Paper Crawler.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = requirements_file.read_text(encoding="utf-8").strip().split('\n')
    requirements = [req.strip() for req in requirements if req.strip() and not req.startswith('#')]

setup(
    name="arxiv-paper-crawler",
    version="1.0.0",
    description="A comprehensive tool for searching, downloading, and managing ArXiv research papers",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="ArXiv Paper Crawler Team",
    author_email="your-email@example.com",
    url="https://github.com/user/arxiv-paper-crawler",
    packages=find_packages(),
    python_requires=">=3.7",
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'arxiv-crawler=main:main',
            'arxiv-spider=main:main',
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    keywords="arxiv papers research academic crawler download pdf",
    project_urls={
        "Bug Reports": "https://github.com/user/arxiv-paper-crawler/issues",
        "Documentation": "https://github.com/user/arxiv-paper-crawler/wiki",
        "Source": "https://github.com/user/arxiv-paper-crawler",
    },
)