#!/usr/bin/env python3
"""
Regional Enhanced Crawler
Specifically designed to discover state and region-specific healthcare payer content

Key Features:
1. Geographic-aware crawling patterns
2. State-specific portal discovery
3. Regional variation detection
4. Medicaid/Medicare state-specific searches
5. Coverage gap identification and targeted discovery

Author: Neeraj Kondaveeti
Date: October 2025
"""

import re
import time
import logging
from collections import deque, defaultdict
from urllib.parse import urljoin, urlparse
from typing import Dict, List, Set, Tuple
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

class RegionalEnhancedCrawler:
    """BFS crawler enhanced for comprehensive regional coverage discovery"""
    
    def __init__(self, headless=True, max_depth=3):
        self.headless = headless
        self.max_depth = max_depth
        self.setup_logging()
        self.setup_webdriver()
        
        # US States mapping
        self.us_states = {
            'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California',
            'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware', 'FL': 'Florida', 'GA': 'Georgia',
            'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa',
            'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
            'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri',
            'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey',
            'NM': 'New Mexico', 'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio',
            'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
            'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont',
            'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming',
            'DC': 'District of Columbia'
        }
        
        # Regional search patterns to prioritize
        self.regional_keywords = [
            'state specific', 'state-specific', 'by state', 'regional',
            'medicaid', 'medicare', 'state plan', 'local coverage',
            'geographic', 'territory', 'area', 'zone'
        ]
        
        # URL patterns that indicate regional content
        self.regional_url_indicators = [
            r'/state[s]?/',
            r'/region[s]?/',
            r'/area[s]?/',
            r'/local/',
            r'/geographic/',
            r'/[a-z]{2}/',  # State codes
            r'/[A-Z]{2}[_-]',  # State codes with separators
            r'medicaid',
            r'medicare',
            r'state[_-]specific'
        ]
        
        # Results tracking
        self.regional_discoveries = defaultdict(list)
        self.visited_urls = set()
        self.state_coverage_map = defaultdict(list)
    
    def setup_logging(self):
        """Setup logging for regional crawler"""
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
        """Clean up resources"""
        if self.driver:
            self.driver.quit()
    
    def detect_regional_indicators(self, url: str, text: str) -> Set[str]:
        """Detect regional/state indicators in URL and content"""
        indicators = set()
        
        # URL-based detection
        url_lower = url.lower()
        for pattern in self.regional_url_indicators:
            if re.search(pattern, url_lower):
                indicators.add('regional_url_pattern')
        
        # State code detection in URL
        for state_code in self.us_states.keys():
            if f'/{state_code.lower()}/' in url_lower or f'{state_code}_' in url_lower:
                indicators.add(f'state_{state_code}')
        
        # Content-based detection
        text_lower = text.lower()
        for keyword in self.regional_keywords:
            if keyword in text_lower:
                indicators.add(f'keyword_{keyword.replace(" ", "_")}')
        
        # State name detection in content
        for state_code, state_name in self.us_states.items():
            if state_name.lower() in text_lower:
                indicators.add(f'state_{state_code}')
        
        return indicators
    
    def score_regional_relevance(self, url: str, text: str) -> int:
        """Score how relevant a page is for regional content discovery"""
        score = 0
        url_lower = url.lower()
        text_lower = text.lower()
        
        # URL-based scoring
        if any(re.search(pattern, url_lower) for pattern in self.regional_url_indicators):
            score += 5
        
        # Content-based scoring
        for keyword in self.regional_keywords:
            if keyword in text_lower:
                score += 2
        
        # State-specific content
        state_mentions = sum(1 for state_name in self.us_states.values() if state_name.lower() in text_lower)
        score += min(state_mentions, 10)  # Cap at 10 points
        
        # High-value regional terms
        high_value_terms = ['provider portal', 'state portal', 'select your state', 'choose state', 'by location']
        for term in high_value_terms:
            if term in text_lower:
                score += 3
        
        return score
    
    def generate_state_specific_urls(self, base_url: str, base_domain: str) -> List[str]:
        """Generate potential state-specific URLs to explore"""
        candidate_urls = []
        
        # Common state-specific URL patterns
        patterns = [
            f"https://www.{base_domain}/providers/{{state}}/",
            f"https://provider.{base_domain}/{{state}}/",
            f"https://providers.{base_domain}/{{state}}/",
            f"https://www.{base_domain}/state/{{state}}/",
            f"https://www.{base_domain}/regional/{{state}}/",
            f"https://www.{base_domain}/{{state}}/providers/",
            f"https://www.{base_domain}/medicaid/{{state}}/",
            f"https://www.{base_domain}/medicare/{{state}}/"
        ]
        
        # Test a sample of states (focus on high-population states first)
        priority_states = ['CA', 'TX', 'FL', 'NY', 'PA', 'IL', 'OH', 'GA', 'NC', 'MI']
        
        for state_code in priority_states:
            state_name = self.us_states[state_code]
            
            for pattern in patterns:
                # Try with state code
                url_with_code = pattern.format(state=state_code.lower())
                candidate_urls.append(url_with_code)
                
                # Try with state name
                url_with_name = pattern.format(state=state_name.lower().replace(' ', '-'))
                candidate_urls.append(url_with_name)
        
        return candidate_urls
    
    def discover_regional_content_bfs(self, starting_urls: List[str], allowed_domains: List[str], 
                                     company_name: str, max_time_minutes: int = 5) -> Dict:
        """
        Enhanced BFS discovery focused on regional content
        
        Args:
            starting_urls: Initial URLs to start crawling
            allowed_domains: Domains to restrict crawling to
            company_name: Name of the healthcare company
            max_time_minutes: Maximum time to spend crawling
            
        Returns:
            Dictionary with regional discovery results
        """
        start_time = time.time()
        max_time_seconds = max_time_minutes * 60
        
        # Initialize BFS queue with (url, depth, regional_score)
        queue = deque([(url, 0, 0) for url in starting_urls])
        
        regional_pdfs = defaultdict(list)  # state -> [pdf_urls]
        all_pdfs = []
        relevant_pages = []
        state_coverage = set()
        
        self.logger.info(f"Starting regional BFS for {company_name}")
        self.logger.info(f"Time limit: {max_time_minutes} minutes")
        
        # Add state-specific candidate URLs to queue
        if starting_urls:
            base_domain = urlparse(starting_urls[0]).netloc.replace('www.', '').replace('provider.', '').replace('providers.', '')
            state_urls = self.generate_state_specific_urls(starting_urls[0], base_domain)
            
            # Add high-priority state URLs to queue
            for url in state_urls[:20]:  # Limit to prevent queue explosion
                queue.append((url, 1, 5))  # Give them higher initial score
        
        urls_processed = 0
        max_urls = 50  # Limit to prevent excessive crawling
        
        while queue and urls_processed < max_urls and time.time() - start_time < max_time_seconds:
            current_url, depth, regional_score = queue.popleft()
            
            if current_url in self.visited_urls or depth > self.max_depth:
                continue
            
            self.visited_urls.add(current_url)
            urls_processed += 1
            
            # Check domain restrictions
            parsed = urlparse(current_url)
            if not any(domain in parsed.netloc for domain in allowed_domains):
                continue
            
            self.logger.info(f"[{depth}] Exploring: {current_url}")
            
            try:
                self.driver.get(current_url)
                time.sleep(1)  # Be respectful
                
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                page_text = soup.get_text()
                
                # Detect regional indicators
                regional_indicators = self.detect_regional_indicators(current_url, page_text)
                page_regional_score = self.score_regional_relevance(current_url, page_text)
                
                # Extract state coverage from page
                for state_code in self.us_states:
                    if f'state_{state_code}' in regional_indicators:
                        state_coverage.add(state_code)
                
                # Process links on this page
                links = soup.find_all('a', href=True)
                
                for link in links:
                    href = link['href']
                    link_text = link.get_text(strip=True).lower()
                    absolute_url = urljoin(current_url, href)
                    
                    # Skip if not in allowed domains
                    link_parsed = urlparse(absolute_url)
                    if not any(domain in link_parsed.netloc for domain in allowed_domains):
                        continue
                    
                    # Check for PDFs
                    if absolute_url.lower().endswith('.pdf') or '.pdf' in absolute_url.lower():
                        all_pdfs.append(absolute_url)
                        
                        # Categorize PDF by state if detected
                        pdf_indicators = self.detect_regional_indicators(absolute_url, link_text)
                        for indicator in pdf_indicators:
                            if indicator.startswith('state_'):
                                state_code = indicator.split('_')[1]
                                if state_code in self.us_states:
                                    regional_pdfs[state_code].append(absolute_url)
                        
                        self.logger.info(f"  📄 PDF found: {absolute_url}")
                        continue
                    
                    # Score link for regional relevance
                    link_regional_score = self.score_regional_relevance(absolute_url, link_text)
                    
                    # Add high-scoring regional links to queue
                    if (link_regional_score >= 3 and 
                        depth < self.max_depth and 
                        absolute_url not in self.visited_urls):
                        
                        queue.append((absolute_url, depth + 1, link_regional_score))
                
                # Track relevant pages
                if page_regional_score >= 5:
                    relevant_pages.append({
                        'url': current_url,
                        'score': page_regional_score,
                        'indicators': list(regional_indicators),
                        'depth': depth
                    })
                
            except Exception as e:
                self.logger.warning(f"Error processing {current_url}: {e}")
                continue
        
        elapsed_time = time.time() - start_time
        
        # Compile results
        results = {
            'company_name': company_name,
            'elapsed_time_minutes': elapsed_time / 60,
            'urls_processed': urls_processed,
            'total_pdfs_found': len(all_pdfs),
            'regional_pdfs': dict(regional_pdfs),
            'state_coverage': list(state_coverage),
            'states_covered_count': len(state_coverage),
            'relevant_pages': relevant_pages,
            'all_pdfs': all_pdfs,
            'regional_completeness': len(state_coverage) / 50 if state_coverage else 0
        }
        
        self.logger.info(f"Regional discovery completed for {company_name}")
        self.logger.info(f"States covered: {len(state_coverage)} ({len(state_coverage)/50:.1%})")
        self.logger.info(f"Total PDFs: {len(all_pdfs)}")
        self.logger.info(f"Regional PDFs: {sum(len(pdfs) for pdfs in regional_pdfs.values())}")
        
        return results

def test_regional_enhanced_discovery():
    """Test the regional enhanced crawler"""
    
    print("🗺️  REGIONAL ENHANCED DISCOVERY TEST")
    print("=" * 60)
    
    # Test with companies known to have regional variations
    test_cases = [
        {
            'company': 'Anthem/Elevance Health',
            'starting_urls': ['https://providers.anthem.com/', 'https://www.anthem.com/provider/'],
            'allowed_domains': ['anthem.com', 'providers.anthem.com', 'www.anthem.com']
        },
        {
            'company': 'Kaiser Permanente',
            'starting_urls': ['https://providers.kp.org/', 'https://healthy.kaiserpermanente.org/'],
            'allowed_domains': ['kp.org', 'providers.kp.org', 'kaiserpermanente.org', 'healthy.kaiserpermanente.org']
        }
    ]
    
    crawler = RegionalEnhancedCrawler(headless=True, max_depth=2)
    
    try:
        all_results = {}
        
        for test_case in test_cases:
            company = test_case['company']
            print(f"\n🏢 Testing: {company}")
            print("-" * 40)
            
            results = crawler.discover_regional_content_bfs(
                starting_urls=test_case['starting_urls'],
                allowed_domains=test_case['allowed_domains'],
                company_name=company,
                max_time_minutes=3
            )
            
            all_results[company] = results
            
            # Display results
            print(f"Time elapsed: {results['elapsed_time_minutes']:.1f} minutes")
            print(f"URLs processed: {results['urls_processed']}")
            print(f"Total PDFs found: {results['total_pdfs_found']}")
            print(f"States covered: {results['states_covered_count']} ({results['regional_completeness']:.1%})")
            
            if results['state_coverage']:
                print(f"Covered states: {', '.join(results['state_coverage'][:10])}{'...' if len(results['state_coverage']) > 10 else ''}")
            
            if results['regional_pdfs']:
                print(f"State-specific PDFs found:")
                for state, pdfs in list(results['regional_pdfs'].items())[:5]:
                    print(f"  {state}: {len(pdfs)} PDFs")
            
            print(f"Regional pages discovered: {len(results['relevant_pages'])}")
        
        # Overall analysis
        print(f"\n📊 OVERALL REGIONAL DISCOVERY ANALYSIS")
        print("=" * 50)
        
        total_states = set()
        total_pdfs = 0
        total_regional_pdfs = 0
        
        for company, results in all_results.items():
            total_states.update(results['state_coverage'])
            total_pdfs += results['total_pdfs_found']
            total_regional_pdfs += sum(len(pdfs) for pdfs in results['regional_pdfs'].values())
        
        print(f"Combined state coverage: {len(total_states)}/50 ({len(total_states)/50:.1%})")
        print(f"Total PDFs discovered: {total_pdfs}")
        print(f"State-specific PDFs: {total_regional_pdfs}")
        print(f"Regional coverage ratio: {total_regional_pdfs/total_pdfs:.1%}" if total_pdfs > 0 else "Regional coverage ratio: 0%")
        
        # Recommendations
        print(f"\n🎯 REGIONAL COVERAGE RECOMMENDATIONS")
        print("-" * 40)
        
        coverage_percentage = len(total_states) / 50
        
        if coverage_percentage < 0.3:
            print("❌ Poor regional coverage detected")
            print("Recommendations:")
            print("  • Increase crawl depth to 3-4 levels")
            print("  • Focus on state selection pages")
            print("  • Search Medicaid-specific portals")
            print("  • Check for geographic navigation menus")
        elif coverage_percentage < 0.6:
            print("⚠️  Moderate regional coverage")
            print("Recommendations:")
            print("  • Target missing high-population states")
            print("  • Explore regional health plan variations")
            print("  • Check state insurance department links")
        else:
            print("✅ Good regional coverage achieved")
            print("Continue with current strategy")
        
        return all_results
        
    finally:
        crawler.close()

if __name__ == "__main__":
    test_regional_enhanced_discovery()