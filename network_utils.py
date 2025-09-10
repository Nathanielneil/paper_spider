"""
Network utilities for handling connection issues and testing connectivity.
"""

import requests
import logging
from typing import Optional, Dict, List
import urllib3


def test_arxiv_connectivity() -> Dict[str, bool]:
    """
    Test connectivity to ArXiv servers.
    
    Returns:
        Dictionary with connectivity test results
    """
    logger = logging.getLogger(__name__)
    
    test_urls = {
        'arxiv_main': 'https://arxiv.org',
        'arxiv_api': 'http://export.arxiv.org/api/query',
        'arxiv_api_https': 'https://export.arxiv.org/api/query'
    }
    
    results = {}
    
    for name, url in test_urls.items():
        try:
            response = requests.get(url, timeout=10, verify=True)
            results[name] = response.status_code == 200
            logger.info(f"Connectivity test {name}: {'PASS' if results[name] else 'FAIL'}")
        except Exception as e:
            results[name] = False
            logger.warning(f"Connectivity test {name}: FAIL - {e}")
    
    return results


def configure_session_for_china() -> requests.Session:
    """
    Configure a requests session optimized for Chinese network environment.
    
    Returns:
        Configured requests session
    """
    session = requests.Session()
    
    # Disable SSL warnings if needed
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # Set headers
    session.headers.update({
        'User-Agent': 'ArxivCrawler/1.0 (Windows; compatible)',
        'Accept': 'application/atom+xml, text/xml, */*',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
        'Connection': 'keep-alive',
        'Cache-Control': 'no-cache'
    })
    
    # Configure timeout
    session.timeout = 30
    
    # Try to use system proxy if available
    session.trust_env = True
    
    return session


def get_arxiv_mirrors() -> List[str]:
    """
    Get list of ArXiv mirror URLs.
    
    Returns:
        List of mirror base URLs
    """
    return [
        'http://export.arxiv.org/api/query',    # Original
        'https://export.arxiv.org/api/query',   # HTTPS version
        'http://arxiv.org/api/query',           # Alternative
    ]


def test_url_with_different_methods(url: str) -> Dict[str, bool]:
    """
    Test URL with different SSL and proxy configurations.
    
    Args:
        url: URL to test
        
    Returns:
        Dictionary with test results for different configurations
    """
    logger = logging.getLogger(__name__)
    results = {}
    
    # Test configurations
    configs = [
        {'verify': True, 'proxies': None, 'name': 'default_ssl_verify'},
        {'verify': False, 'proxies': None, 'name': 'no_ssl_verify'},
        {'verify': True, 'proxies': {}, 'name': 'no_proxy_ssl_verify'},
        {'verify': False, 'proxies': {}, 'name': 'no_proxy_no_ssl_verify'},
    ]
    
    for config in configs:
        try:
            response = requests.get(
                url,
                timeout=10,
                verify=config['verify'],
                proxies=config['proxies']
            )
            results[config['name']] = response.status_code == 200
            logger.info(f"Test {config['name']}: {'PASS' if results[config['name']] else 'FAIL'}")
        except Exception as e:
            results[config['name']] = False
            logger.warning(f"Test {config['name']}: FAIL - {e}")
    
    return results


def fix_ssl_issues():
    """
    Apply common SSL fixes for Chinese network environment.
    """
    import ssl
    import os
    
    # Disable SSL warnings
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # Set environment variables for SSL
    os.environ['PYTHONHTTPSVERIFY'] = '0'
    os.environ['CURL_CA_BUNDLE'] = ''
    os.environ['REQUESTS_CA_BUNDLE'] = ''
    
    # Create unverified SSL context
    ssl._create_default_https_context = ssl._create_unverified_context


def create_robust_session(config: Dict) -> requests.Session:
    """
    Create a robust session that handles various network issues.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Configured requests session
    """
    session = requests.Session()
    
    # Configure retry strategy
    from urllib3.util.retry import Retry
    from requests.adapters import HTTPAdapter
    
    retry_strategy = Retry(
        total=5,
        status_forcelist=[429, 500, 502, 503, 504, 520, 521, 522, 523, 524],
        allowed_methods=["HEAD", "GET", "OPTIONS"],
        backoff_factor=2
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Set headers
    session.headers.update({
        'User-Agent': config.get('user_agent', 'ArxivCrawler/1.0'),
        'Accept': 'application/atom+xml, text/xml, */*',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'close'  # Prevent connection reuse issues
    })
    
    # Configure SSL - disable verification if issues persist
    session.verify = config.get('verify_ssl', False)
    
    # Clear proxies if not explicitly set
    import os
    if not any(os.getenv(var) for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']):
        session.proxies = {}
    
    return session