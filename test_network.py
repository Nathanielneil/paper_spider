#!/usr/bin/env python3
"""
Network connectivity test tool for ArXiv Paper Crawler.
Use this to diagnose network issues and find the best configuration.
"""

import sys
import requests
import urllib3
from network_utils import test_arxiv_connectivity, test_url_with_different_methods, fix_ssl_issues


def main():
    print("=" * 60)
    print("ArXiv Paper Crawler - Network Connectivity Test")
    print("=" * 60)
    
    # Test 1: Basic connectivity
    print("\n1. Testing basic connectivity to ArXiv...")
    connectivity_results = test_arxiv_connectivity()
    
    for service, result in connectivity_results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"   {service}: {status}")
    
    # Test 2: Different SSL configurations
    print("\n2. Testing different SSL configurations...")
    test_url = "http://export.arxiv.org/api/query"
    ssl_results = test_url_with_different_methods(test_url)
    
    for config, result in ssl_results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"   {config}: {status}")
    
    # Test 3: Simple ArXiv API call
    print("\n3. Testing ArXiv API call...")
    
    test_configs = [
        {"verify": True, "name": "With SSL verification"},
        {"verify": False, "name": "Without SSL verification"}
    ]
    
    for config in test_configs:
        try:
            url = "http://export.arxiv.org/api/query"
            params = {
                'search_query': 'all:test',
                'start': 0,
                'max_results': 1
            }
            
            response = requests.get(
                url, 
                params=params,
                timeout=15,
                verify=config["verify"],
                headers={'User-Agent': 'ArxivCrawler/1.0 Test'}
            )
            
            if response.status_code == 200:
                print(f"   {config['name']}: ✓ PASS (Status: {response.status_code})")
            else:
                print(f"   {config['name']}: ✗ FAIL (Status: {response.status_code})")
                
        except Exception as e:
            print(f"   {config['name']}: ✗ FAIL (Error: {e})")
    
    # Recommendations
    print("\n" + "=" * 60)
    print("RECOMMENDATIONS:")
    print("=" * 60)
    
    if any(ssl_results.values()):
        working_configs = [k for k, v in ssl_results.items() if v]
        print(f"✓ Working configurations found: {', '.join(working_configs)}")
        
        if 'no_ssl_verify' in working_configs:
            print("✓ Recommend disabling SSL verification (verify_ssl: false in config)")
        if 'no_proxy' in str(working_configs):
            print("✓ Recommend disabling proxy usage")
    else:
        print("✗ No working configurations found")
        print("  Try the following:")
        print("  1. Check your internet connection")
        print("  2. Disable firewall/antivirus temporarily")
        print("  3. Try using a VPN")
        print("  4. Check if your network requires proxy settings")
    
    print("\nIf SSL issues persist, run this command to apply SSL fixes:")
    print("python -c \"from network_utils import fix_ssl_issues; fix_ssl_issues()\"")
    
    print("\nThen try running the crawler with:")
    print("python main.py search --query 'test' --max-results 1")


if __name__ == "__main__":
    main()