#!/usr/bin/env python3
"""
Comprehensive PDF Discovery Test
CSV + BFS Combined Approach
Measures total PDF discovery potential across all healthcare payers

This script combines:
1. CSV-driven payer discovery
2. BFS (Breadth-First Search) web crawling
3. Comprehensive PDF detection and counting

Author: Neeraj Kondaveeti
Date: October 2025
"""

import time
import logging
import json
from datetime import datetime
from collections import deque
from urllib.parse import urljoin, urlparse
from pathlib import Path
import pandas as pd
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

class ComprehensivePDFDiscovery:
    """
    Advanced crawler that combines CSV-driven payer discovery with BFS crawling
    to measure total PDF discovery potential across healthcare payers
    """
    
    def __init__(self, csv_file="payer_companies.csv", headless=True, max_depth=2, max_urls_per_payer=30):
        self.csv_file = Path(csv_file)
        self.headless = headless
        self.max_depth = max_depth
        self.max_urls_per_payer = max_urls_per_payer
        
        # Discovery tracking
        self.total_pdfs_discovered = 0
        self.total_urls_visited = 0
        self.payer_results = {}
        
        # Setup
        self.setup_logging()
        self.setup_webdriver()
        self.load_payer_csv()
        
        # Portal discovery patterns
        self.portal_patterns = [
            "provider", "providers", "health-care-professionals",
            "healthcare-professionals", "provider-portal", "provider-resources",
            "provider-support", "professional", "professionals", "practitioner",
            "physician", "doctor", "medical-professionals"
        ]
        
        self.portal_subdomains = [
            "provider", "providers", "professional", "portal", "prov"
        ]
    
    def setup_logging(self):
        """Setup comprehensive logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('pdf_discovery_test.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def setup_webdriver(self):
        """Setup Chrome WebDriver with optimized settings"""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-images')  # Speed optimization
        chrome_options.add_argument('--disable-javascript')  # Speed optimization for some pages
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.set_page_load_timeout(20)
    
    def load_payer_csv(self):
        """Load payer information from CSV"""
        try:
            self.payer_df = pd.read_csv(self.csv_file)
            self.logger.info(f"Loaded {len(self.payer_df)} payers from CSV")
        except Exception as e:
            self.logger.error(f"Failed to load CSV: {e}")
            raise
    
    def close(self):
        """Clean up resources"""
        if hasattr(self, 'driver') and self.driver:
            self.driver.quit()
    
    def discover_provider_portals(self, company_name, base_domain, known_portal=None):
        """Discover provider portal URLs for a company"""
        discovered_urls = []
        
        # Use known portal if available
        if known_portal and pd.notna(known_portal):
            discovered_urls.append(known_portal)
        
        # Auto-discovery strategies
        base_url = f"https://www.{base_domain}" if not base_domain.startswith('http') else base_domain
        
        # Strategy 1: Common portal patterns
        for pattern in self.portal_patterns[:5]:  # Limit for speed
            candidate_urls = [
                f"{base_url}/{pattern}/",
                f"https://provider.{base_domain}/",
                f"https://providers.{base_domain}/"
            ]
            
            for url in candidate_urls:
                if self.check_url_validity(url) and url not in discovered_urls:
                    discovered_urls.append(url)
                    if len(discovered_urls) >= 3:  # Limit discovery for speed
                        break
            
            if len(discovered_urls) >= 3:
                break
        
        self.logger.info(f"{company_name}: Discovered {len(discovered_urls)} portal URLs")
        return discovered_urls
    
    def check_url_validity(self, url):
        """Quick URL validity check"""
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.head(url, headers=headers, timeout=5, allow_redirects=True)
            return 200 <= response.status_code < 400
        except:
            return False
    
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
            'claims', 'billing', 'coverage', 'benefits', 'forms',
            'documents', 'resources', 'tools', 'materials'
        ]
        
        combined = f"{text_lower} {href_lower}"
        return any(keyword in combined for keyword in relevant_keywords)
    
    def discover_pdfs_bfs(self, starting_urls, allowed_domains, company_name):
        """Discover PDFs using BFS traversal"""
        visited_urls = set()
        pdfs_discovered = set()
        queue = deque([(url, 0) for url in starting_urls])
        
        while queue and len(visited_urls) < self.max_urls_per_payer:
            current_url, depth = queue.popleft()
            
            if current_url in visited_urls or depth > self.max_depth:
                continue
            
            visited_urls.add(current_url)
            self.logger.info(f"{company_name} (depth {depth}): Exploring {current_url}")
            
            try:
                self.driver.get(current_url)
                time.sleep(1)  # Respectful crawling
                
                # Wait for body to load
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                links = soup.find_all('a', href=True)
                
                for link in links:
                    href = link['href']
                    text = link.get_text(strip=True)
                    absolute_url = urljoin(current_url, href)
                    
                    # Check domain restrictions
                    parsed = urlparse(absolute_url)
                    if not any(domain in parsed.netloc for domain in allowed_domains):
                        continue
                    
                    # Check for PDFs
                    if self.is_pdf_url(absolute_url):
                        pdfs_discovered.add(absolute_url)
                        self.logger.info(f"{company_name}: Found PDF - {absolute_url}")
                    
                    # Add relevant links to queue for further exploration
                    elif (self.is_relevant_link(text, href) and 
                          depth < self.max_depth and 
                          absolute_url not in visited_urls):
                        queue.append((absolute_url, depth + 1))
                
            except Exception as e:
                self.logger.warning(f"{company_name}: Error processing {current_url}: {e}")
                continue
        
        return {
            'pdfs_discovered': list(pdfs_discovered),
            'urls_visited': list(visited_urls),
            'total_pdfs': len(pdfs_discovered),
            'total_urls_visited': len(visited_urls)
        }
    
    def test_single_payer(self, company_name, base_domain, known_portal=None, time_limit_minutes=3):
        """Test PDF discovery for a single payer with time limit"""
        start_time = time.time()
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"Testing: {company_name}")
        self.logger.info(f"Domain: {base_domain}")
        self.logger.info(f"Time limit: {time_limit_minutes} minutes")
        self.logger.info(f"{'='*60}")
        
        try:
            # Discover portal URLs
            portal_urls = self.discover_provider_portals(company_name, base_domain, known_portal)
            
            if not portal_urls:
                self.logger.warning(f"{company_name}: No portal URLs discovered")
                return {'error': 'No portal URLs found'}
            
            # Define allowed domains
            allowed_domains = [base_domain]
            if not base_domain.startswith('www.'):
                allowed_domains.append(f"www.{base_domain}")
            for subdomain in self.portal_subdomains:
                allowed_domains.append(f"{subdomain}.{base_domain}")
            
            # Run BFS discovery with time limit
            results = self.discover_pdfs_bfs(portal_urls, allowed_domains, company_name)
            
            elapsed_time = time.time() - start_time
            results['elapsed_time_minutes'] = elapsed_time / 60
            results['portal_urls_used'] = portal_urls
            results['allowed_domains'] = allowed_domains
            
            self.logger.info(f"{company_name}: Found {results['total_pdfs']} PDFs in {elapsed_time/60:.1f} minutes")
            
            return results
            
        except Exception as e:
            self.logger.error(f"{company_name}: Test failed - {e}")
            return {'error': str(e)}
    
    def run_comprehensive_test(self, max_payers=None, time_per_payer_minutes=3):
        """Run comprehensive PDF discovery test across all payers"""
        self.logger.info(f"\n🚀 Starting Comprehensive PDF Discovery Test")
        self.logger.info(f"Total payers in CSV: {len(self.payer_df)}")
        self.logger.info(f"Max payers to test: {max_payers or 'All'}")
        self.logger.info(f"Time per payer: {time_per_payer_minutes} minutes")
        self.logger.info(f"Max depth: {self.max_depth}")
        self.logger.info(f"Max URLs per payer: {self.max_urls_per_payer}")
        
        test_start_time = time.time()
        
        # Select payers to test
        test_payers = self.payer_df.head(max_payers) if max_payers else self.payer_df
        
        for idx, row in test_payers.iterrows():
            company_name = row['company_name']
            base_domain = row['base_domain']
            known_portal = row.get('known_provider_portal')
            
            # Test single payer
            result = self.test_single_payer(company_name, base_domain, known_portal, time_per_payer_minutes)
            
            # Store results
            self.payer_results[company_name] = result
            
            if 'total_pdfs' in result:
                self.total_pdfs_discovered += result['total_pdfs']
                self.total_urls_visited += result['total_urls_visited']
        
        total_elapsed = time.time() - test_start_time
        
        # Generate comprehensive report
        self.generate_comprehensive_report(total_elapsed)
        
        return self.payer_results
    
    def generate_comprehensive_report(self, total_elapsed_seconds):
        """Generate comprehensive test report"""
        print(f"\n🎯 COMPREHENSIVE PDF DISCOVERY REPORT")
        print(f"{'='*70}")
        print(f"Test Duration: {total_elapsed_seconds/60:.1f} minutes")
        print(f"Total Payers Tested: {len(self.payer_results)}")
        print(f"Total PDFs Discovered: {self.total_pdfs_discovered}")
        print(f"Total URLs Visited: {self.total_urls_visited}")
        print(f"Average PDFs per Payer: {self.total_pdfs_discovered/len(self.payer_results):.1f}")
        
        # Success/failure breakdown
        successful_tests = sum(1 for result in self.payer_results.values() if 'total_pdfs' in result)
        failed_tests = len(self.payer_results) - successful_tests
        
        print(f"\n📊 Success Rate:")
        print(f"Successful tests: {successful_tests}")
        print(f"Failed tests: {failed_tests}")
        print(f"Success rate: {successful_tests/len(self.payer_results)*100:.1f}%")
        
        # Top performers
        print(f"\n🏆 Top PDF Discoverers:")
        sorted_results = sorted(
            [(name, result) for name, result in self.payer_results.items() if 'total_pdfs' in result],
            key=lambda x: x[1]['total_pdfs'], reverse=True
        )
        
        for i, (name, result) in enumerate(sorted_results[:5], 1):
            print(f"{i}. {name}: {result['total_pdfs']} PDFs ({result['elapsed_time_minutes']:.1f} min)")
        
        # Projection for all payers
        if successful_tests > 0:
            avg_pdfs_successful = sum(result['total_pdfs'] for result in self.payer_results.values() 
                                    if 'total_pdfs' in result) / successful_tests
            
            total_payers_in_csv = len(self.payer_df)
            projected_total = int(avg_pdfs_successful * total_payers_in_csv)
            
            print(f"\n🔮 Projection for All {total_payers_in_csv} Payers:")
            print(f"Average PDFs per successful payer: {avg_pdfs_successful:.1f}")
            print(f"Projected total PDFs (all payers): {projected_total:,}")
        
        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"comprehensive_pdf_discovery_{timestamp}.json"
        
        report_data = {
            'test_metadata': {
                'timestamp': datetime.now().isoformat(),
                'test_duration_minutes': total_elapsed_seconds / 60,
                'max_depth': self.max_depth,
                'max_urls_per_payer': self.max_urls_per_payer,
                'total_payers_tested': len(self.payer_results)
            },
            'summary': {
                'total_pdfs_discovered': self.total_pdfs_discovered,
                'total_urls_visited': self.total_urls_visited,
                'successful_tests': successful_tests,
                'failed_tests': failed_tests,
                'success_rate_percent': successful_tests/len(self.payer_results)*100
            },
            'payer_results': self.payer_results
        }
        
        with open(results_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"\n💾 Detailed results saved to: {results_file}")

def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Comprehensive PDF Discovery Test')
    parser.add_argument('--max-payers', type=int, help='Maximum number of payers to test')
    parser.add_argument('--time-per-payer', type=int, default=3, help='Time limit per payer (minutes)')
    parser.add_argument('--max-depth', type=int, default=2, help='Maximum BFS depth')
    parser.add_argument('--max-urls', type=int, default=30, help='Maximum URLs per payer')
    parser.add_argument('--visible', action='store_true', help='Run with visible browser')
    
    args = parser.parse_args()
    
    print(f"🔍 Comprehensive PDF Discovery Test")
    print(f"Configuration:")
    print(f"  Max payers: {args.max_payers or 'All'}")
    print(f"  Time per payer: {args.time_per_payer} minutes")
    print(f"  Max depth: {args.max_depth}")
    print(f"  Max URLs per payer: {args.max_urls}")
    print(f"  Browser mode: {'Visible' if args.visible else 'Headless'}")
    
    discovery_test = ComprehensivePDFDiscovery(
        headless=not args.visible,
        max_depth=args.max_depth,
        max_urls_per_payer=args.max_urls
    )
    
    try:
        results = discovery_test.run_comprehensive_test(
            max_payers=args.max_payers,
            time_per_payer_minutes=args.time_per_payer
        )
        
        print(f"\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        discovery_test.close()

if __name__ == "__main__":
    main()