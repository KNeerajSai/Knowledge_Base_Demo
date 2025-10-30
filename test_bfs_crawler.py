#!/usr/bin/env python3
"""
Test BFS Crawler - Enhanced PDF Discovery
Simple test to see if BFS can find more PDFs than direct URLs
"""

import time
import logging
from collections import deque
from urllib.parse import urljoin, urlparse
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

class SimpleBFSCrawler:
    """Simple BFS crawler to test PDF discovery"""
    
    def __init__(self, headless=True, max_depth=2):
        self.headless = headless
        self.max_depth = max_depth
        self.visited_urls = set()
        self.discovered_pdfs = set()
        self.setup_webdriver()
        
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def setup_webdriver(self):
        """Setup Chrome WebDriver"""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.set_page_load_timeout(30)
    
    def close(self):
        if self.driver:
            self.driver.quit()
    
    def is_pdf_url(self, url):
        """Check if URL points to a PDF"""
        return url.lower().endswith('.pdf') or '.pdf' in url.lower()
    
    def is_relevant_link(self, text, href):
        """Check if link is relevant for healthcare provider content"""
        text_lower = text.lower()
        href_lower = href.lower()
        
        relevant_keywords = [
            'provider', 'manual', 'guide', 'policy', 'procedure',
            'prior auth', 'authorization', 'timely filing', 'appeals',
            'claims', 'billing', 'coverage', 'benefits', 'forms'
        ]
        
        combined = f"{text_lower} {href_lower}"
        return any(keyword in combined for keyword in relevant_keywords)
    
    def discover_pdfs_bfs(self, start_urls, allowed_domains):
        """Discover PDFs using BFS traversal"""
        # Initialize queue with (url, depth)
        queue = deque([(url, 0) for url in start_urls])
        
        all_links_found = []
        pdfs_found = set()
        
        while queue and len(self.visited_urls) < 50:  # Limit to prevent excessive crawling
            current_url, depth = queue.popleft()
            
            # Skip if already visited or max depth reached
            if current_url in self.visited_urls or depth > self.max_depth:
                continue
            
            self.visited_urls.add(current_url)
            self.logger.info(f"Exploring (depth {depth}): {current_url}")
            
            try:
                # Navigate to URL
                self.driver.get(current_url)
                time.sleep(2)  # Be respectful
                
                # Wait for page to load
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # Parse page
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                
                # Find all links
                links = soup.find_all('a', href=True)
                self.logger.info(f"Found {len(links)} links on page")
                
                for link in links:
                    href = link['href']
                    text = link.get_text(strip=True)
                    
                    # Convert to absolute URL
                    absolute_url = urljoin(current_url, href)
                    
                    # Check if it's within allowed domains
                    parsed = urlparse(absolute_url)
                    if not any(domain in parsed.netloc for domain in allowed_domains):
                        continue
                    
                    # Record all relevant links
                    if self.is_relevant_link(text, href):
                        all_links_found.append({
                            'url': absolute_url,
                            'text': text,
                            'depth': depth,
                            'parent': current_url
                        })
                    
                    # Check if it's a PDF
                    if self.is_pdf_url(absolute_url):
                        pdfs_found.add(absolute_url)
                        self.logger.info(f"Found PDF: {absolute_url}")
                    
                    # Add to queue for further exploration if relevant and within depth
                    elif (self.is_relevant_link(text, href) and 
                          depth < self.max_depth and 
                          absolute_url not in self.visited_urls):
                        queue.append((absolute_url, depth + 1))
                
            except Exception as e:
                self.logger.warning(f"Error processing {current_url}: {e}")
                continue
        
        return {
            'all_links': all_links_found,
            'pdfs_discovered': list(pdfs_found),
            'urls_visited': list(self.visited_urls),
            'total_links_found': len(all_links_found),
            'total_pdfs_found': len(pdfs_found),
            'total_urls_visited': len(self.visited_urls)
        }

def test_bfs_vs_direct():
    """Test BFS discovery vs direct URLs for Anthem"""
    
    print("🔍 Testing BFS PDF Discovery vs Direct URLs")
    print("=" * 60)
    
    # Known direct PDFs from basic crawler (8 PDFs)
    direct_pdfs = [
        "https://files.providernews.anthem.com/1661/2022-Provider-Manual-pages-44-113.pdf",
        "https://providers.anthem.com/docs/gpp/OH_CAID_ProviderManual.pdf",
        "https://providers.anthem.com/docs/gpp/CA_CAID_ProviderManual.pdf",
        "https://providers.anthem.com/docs/gpp/NY_ABC_CAID_ProviderManual.pdf",
        "https://providers.anthem.com/docs/gpp/VA_CAID_ProviderManual.pdf",
        "https://providers.anthem.com/docs/gpp/WI_CAID_Provider_Manual.pdf",
        "https://providers.anthem.com/docs/gpp/NV_CAID_PriorAuthreq006648-22.pdf",
        "https://providers.anthem.com/docs/gpp/OH_CAID_ClaimsEscalation.pdf"
    ]
    
    print(f"📋 Direct PDFs (baseline): {len(direct_pdfs)} PDFs")
    
    # BFS starting points for Anthem
    starting_urls = [
        "https://providers.anthem.com/",
        "https://providers.anthem.com/docs/",
        "https://providers.anthem.com/provider-support/"
    ]
    
    allowed_domains = ["anthem.com", "providers.anthem.com", "files.providernews.anthem.com"]
    
    # Initialize BFS crawler
    crawler = SimpleBFSCrawler(headless=True, max_depth=2)
    
    try:
        print(f"🚀 Starting BFS crawl from {len(starting_urls)} URLs...")
        print(f"📏 Max depth: {crawler.max_depth}")
        
        results = crawler.discover_pdfs_bfs(starting_urls, allowed_domains)
        
        print(f"\\n📊 BFS Results:")
        print(f"   URLs visited: {results['total_urls_visited']}")
        print(f"   Relevant links found: {results['total_links_found']}")
        print(f"   PDFs discovered: {results['total_pdfs_found']}")
        
        # Compare with direct PDFs
        bfs_pdfs = set(results['pdfs_discovered'])
        direct_pdfs_set = set(direct_pdfs)
        
        # Find additional PDFs discovered by BFS
        additional_pdfs = bfs_pdfs - direct_pdfs_set
        missing_pdfs = direct_pdfs_set - bfs_pdfs
        common_pdfs = bfs_pdfs & direct_pdfs_set
        
        print(f"\\n🔍 Comparison Analysis:")
        print(f"   PDFs found by both methods: {len(common_pdfs)}")
        print(f"   Additional PDFs found by BFS: {len(additional_pdfs)}")
        print(f"   Direct PDFs missed by BFS: {len(missing_pdfs)}")
        
        if additional_pdfs:
            print(f"\\n🎉 BFS found {len(additional_pdfs)} NEW PDFs:")
            for i, pdf in enumerate(additional_pdfs, 1):
                print(f"   {i}. {pdf}")
        
        if missing_pdfs:
            print(f"\\n⚠️ BFS missed {len(missing_pdfs)} direct PDFs:")
            for i, pdf in enumerate(missing_pdfs, 1):
                print(f"   {i}. {pdf}")
        
        # Show some relevant links found
        relevant_links = [link for link in results['all_links'] if not crawler.is_pdf_url(link['url'])]
        if relevant_links:
            print(f"\\n🔗 Sample relevant pages discovered:")
            for i, link in enumerate(relevant_links[:5], 1):
                print(f"   {i}. {link['text'][:50]}... ({link['depth']} levels deep)")
                print(f"      URL: {link['url']}")
        
        print(f"\\n🎯 Conclusion:")
        if len(additional_pdfs) > 0:
            print(f"✅ BFS is MORE comprehensive - found {len(additional_pdfs)} additional PDFs!")
        elif len(bfs_pdfs) == len(direct_pdfs_set):
            print(f"📊 BFS and direct methods found similar results")
        else:
            print(f"📋 Direct method was more comprehensive for this case")
        
    except Exception as e:
        print(f"❌ BFS test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        crawler.close()

if __name__ == "__main__":
    test_bfs_vs_direct()