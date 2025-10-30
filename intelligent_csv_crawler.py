#!/usr/bin/env python3
"""
Intelligent CSV-Driven Payer Crawler
Healthcare Knowledge Base System

Features:
- CSV-driven payer configuration
- Automatic provider portal discovery
- Intelligent domain pattern matching
- Priority-based crawling
- Scalable to hundreds of payers
- Auto-detection of common portal URLs

Author: Development Team
Date: October 2025
"""

import pandas as pd
import time
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
import re

# Import the existing basic crawler
from payer_portal_crawler import PayerPortalCrawler


class IntelligentCSVCrawler(PayerPortalCrawler):
    """
    Enhanced crawler that can automatically discover and crawl payers
    from a CSV file with minimal manual configuration
    """
    
    def __init__(self, csv_file: str = "payer_companies.csv", **kwargs):
        """
        Initialize CSV-driven crawler
        
        Args:
            csv_file: Path to CSV file with payer information
            **kwargs: Additional arguments passed to parent class
        """
        super().__init__(**kwargs)
        self.csv_file = Path(csv_file)
        self.payer_df = None
        self.auto_discovered_configs = {}
        
        # Common provider portal patterns
        self.portal_patterns = [
            "provider",
            "providers", 
            "health-care-professionals",
            "healthcare-professionals",
            "provider-portal",
            "provider-resources",
            "provider-support",
            "professional",
            "professionals",
            "practitioner",
            "physician",
            "doctor"
        ]
        
        # Common portal subdomains
        self.portal_subdomains = [
            "provider",
            "providers",
            "professional",
            "portal",
            "prov"
        ]
        
        self.load_payer_csv()
    
    def load_payer_csv(self):
        """Load and validate payer CSV file"""
        try:
            self.payer_df = pd.read_csv(self.csv_file)
            self.logger.info(f"Loaded {len(self.payer_df)} payers from {self.csv_file}")
            
            # Validate required columns
            required_columns = ['company_name', 'base_domain']
            missing_columns = [col for col in required_columns if col not in self.payer_df.columns]
            
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
            
            # Add default values for optional columns
            if 'priority' not in self.payer_df.columns:
                self.payer_df['priority'] = 'medium'
            
            if 'known_provider_portal' not in self.payer_df.columns:
                self.payer_df['known_provider_portal'] = None
            
            self.logger.info(f"CSV validation successful. Ready to process {len(self.payer_df)} payers")
            
        except Exception as e:
            self.logger.error(f"Failed to load CSV file {self.csv_file}: {e}")
            raise
    
    def discover_provider_portal(self, company_name: str, base_domain: str, known_portal: str = None) -> List[str]:
        """
        Intelligently discover provider portal URLs for a company
        
        Args:
            company_name: Name of the healthcare company
            base_domain: Base domain (e.g., 'uhc.com')
            known_portal: Known provider portal URL (optional)
            
        Returns:
            List of discovered portal URLs
        """
        discovered_urls = []
        
        # If we have a known portal, use it first
        if known_portal and pd.notna(known_portal):
            discovered_urls.append(known_portal)
            self.logger.info(f"Using known portal for {company_name}: {known_portal}")
        
        # Auto-discovery strategies
        base_url = f"https://www.{base_domain}" if not base_domain.startswith('http') else base_domain
        
        # Strategy 1: Common provider portal patterns
        for pattern in self.portal_patterns:
            candidate_urls = [
                f"{base_url}/{pattern}/",
                f"{base_url}/{pattern}.html",
                f"{base_url}/en/{pattern}/",
                f"{base_url}/en/{pattern}.html"
            ]
            
            for url in candidate_urls:
                if self.check_url_validity(url):
                    discovered_urls.append(url)
                    self.logger.info(f"Discovered portal for {company_name}: {url}")
        
        # Strategy 2: Common provider subdomains
        for subdomain in self.portal_subdomains:
            subdomain_url = f"https://{subdomain}.{base_domain}/"
            if self.check_url_validity(subdomain_url):
                discovered_urls.append(subdomain_url)
                self.logger.info(f"Discovered subdomain portal for {company_name}: {subdomain_url}")
        
        # Strategy 3: Search main website for provider links
        main_page_portals = self.search_main_page_for_portals(base_url)
        discovered_urls.extend(main_page_portals)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in discovered_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)
        
        self.logger.info(f"Total discovered URLs for {company_name}: {len(unique_urls)}")
        return unique_urls
    
    def check_url_validity(self, url: str) -> bool:
        """
        Check if a URL is valid and accessible
        
        Args:
            url: URL to check
            
        Returns:
            True if URL is valid and accessible
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.head(url, headers=headers, timeout=10, allow_redirects=True)
            
            # Consider 2xx and 3xx status codes as valid
            if 200 <= response.status_code < 400:
                return True
            
            return False
            
        except Exception:
            return False
    
    def search_main_page_for_portals(self, base_url: str) -> List[str]:
        """
        Search the main page for provider portal links
        
        Args:
            base_url: Base URL of the company website
            
        Returns:
            List of discovered provider portal URLs
        """
        portal_urls = []
        
        try:
            self.driver.get(base_url)
            time.sleep(3)  # Allow page to load
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Look for links containing provider-related keywords
            provider_keywords = [
                'provider', 'professional', 'physician', 'doctor',
                'practitioner', 'health care professional', 'medical professional'
            ]
            
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link['href']
                text = link.get_text(strip=True).lower()
                
                # Check if link text contains provider keywords
                if any(keyword in text for keyword in provider_keywords):
                    # Convert relative URL to absolute
                    absolute_url = urljoin(base_url, href)
                    
                    # Validate the URL
                    parsed = urlparse(absolute_url)
                    if parsed.netloc and parsed.scheme in ['http', 'https']:
                        portal_urls.append(absolute_url)
                        self.logger.info(f"Found provider link on main page: {absolute_url}")
            
        except Exception as e:
            self.logger.warning(f"Failed to search main page {base_url}: {e}")
        
        return portal_urls
    
    def generate_auto_config(self, company_name: str, base_domain: str, discovered_urls: List[str]) -> Dict:
        """
        Generate automatic configuration for a payer
        
        Args:
            company_name: Name of the company
            base_domain: Base domain
            discovered_urls: List of discovered portal URLs
            
        Returns:
            Payer configuration dictionary
        """
        # Clean company name for use as key
        payer_key = re.sub(r'[^a-zA-Z0-9]', '_', company_name.lower())
        payer_key = re.sub(r'_+', '_', payer_key).strip('_')
        
        # Determine allowed domains
        allowed_domains = [base_domain]
        
        # Add common variations
        if not base_domain.startswith('www.'):
            allowed_domains.append(f"www.{base_domain}")
        
        # Add subdomain variations
        for subdomain in self.portal_subdomains:
            allowed_domains.append(f"{subdomain}.{base_domain}")
        
        config = {
            "name": company_name,
            "base_url": f"https://www.{base_domain}",
            "starting_urls": discovered_urls[:5],  # Limit to top 5 URLs
            "allowed_domains": allowed_domains,
            "target_sections": {
                "prior_authorization": [
                    "prior authorization", "preauthorization", "pre-auth",
                    "authorization requirements", "auth criteria", "approval"
                ],
                "timely_filing": [
                    "timely filing", "claim submission deadlines", 
                    "filing requirements", "submission timelines", "deadline"
                ],
                "appeals": [
                    "appeals process", "claim appeals", "dispute resolution",
                    "appeal procedures", "grievances", "complaints"
                ]
            },
            "rate_limit": 2,
            "auto_discovered": True,
            "discovery_timestamp": datetime.now().isoformat()
        }
        
        return payer_key, config
    
    def auto_discover_all_payers(self) -> Dict:
        """
        Automatically discover configurations for all payers in CSV
        
        Returns:
            Dictionary of auto-discovered payer configurations
        """
        self.logger.info("Starting auto-discovery for all payers in CSV")
        
        discovered_configs = {}
        
        for idx, row in self.payer_df.iterrows():
            company_name = row['company_name']
            base_domain = row['base_domain']
            known_portal = row.get('known_provider_portal')
            priority = row.get('priority', 'medium')
            
            self.logger.info(f"\\n{'='*60}")
            self.logger.info(f"Auto-discovering: {company_name}")
            self.logger.info(f"Base domain: {base_domain}")
            self.logger.info(f"Priority: {priority}")
            self.logger.info(f"{'='*60}")
            
            try:
                # Discover portal URLs
                discovered_urls = self.discover_provider_portal(
                    company_name, base_domain, known_portal
                )
                
                if discovered_urls:
                    # Generate configuration
                    payer_key, config = self.generate_auto_config(
                        company_name, base_domain, discovered_urls
                    )
                    
                    discovered_configs[payer_key] = config
                    self.logger.info(f"Successfully configured {company_name} with {len(discovered_urls)} URLs")
                else:
                    self.logger.warning(f"No portal URLs discovered for {company_name}")
                
                # Rate limiting between companies
                time.sleep(2)
                
            except Exception as e:
                self.logger.error(f"Failed to auto-discover {company_name}: {e}")
        
        self.auto_discovered_configs = discovered_configs
        self.logger.info(f"\\nAuto-discovery completed: {len(discovered_configs)} payers configured")
        
        return discovered_configs
    
    def crawl_by_priority(self, priority_filter: str = None) -> Dict:
        """
        Crawl payers filtered by priority level
        
        Args:
            priority_filter: Priority level to filter ('high', 'medium', 'low', or None for all)
            
        Returns:
            Crawling results for filtered payers
        """
        if not self.auto_discovered_configs:
            self.logger.info("No auto-discovered configs found. Running auto-discovery first...")
            self.auto_discover_all_payers()
        
        # Filter by priority if specified
        filtered_payers = {}
        
        for idx, row in self.payer_df.iterrows():
            company_name = row['company_name']
            priority = row.get('priority', 'medium')
            
            if priority_filter is None or priority.lower() == priority_filter.lower():
                # Find matching config
                payer_key = re.sub(r'[^a-zA-Z0-9]', '_', company_name.lower())
                payer_key = re.sub(r'_+', '_', payer_key).strip('_')
                
                if payer_key in self.auto_discovered_configs:
                    filtered_payers[payer_key] = self.auto_discovered_configs[payer_key]
        
        self.logger.info(f"Crawling {len(filtered_payers)} payers with priority: {priority_filter or 'all'}")
        
        # Temporarily update payer_configs for crawling
        original_configs = self.payer_configs.copy()
        self.payer_configs = filtered_payers
        
        try:
            # Run BFS crawling
            results = self.crawl_all_payers_bfs()
            return results
        finally:
            # Restore original configs
            self.payer_configs = original_configs
    
    def save_discovered_configs(self, filename: str = "auto_discovered_payer_configs.json"):
        """Save auto-discovered configurations to file"""
        if not self.auto_discovered_configs:
            self.logger.warning("No auto-discovered configs to save")
            return
        
        filepath = self.results_dir / filename
        
        config_data = {
            'discovery_timestamp': datetime.now().isoformat(),
            'total_payers_discovered': len(self.auto_discovered_configs),
            'csv_source': str(self.csv_file),
            'payer_configurations': self.auto_discovered_configs
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Auto-discovered configs saved to: {filepath}")
            
        except Exception as e:
            self.logger.error(f"Failed to save configs to {filepath}: {e}")
    
    def generate_csv_crawl_report(self, results: Dict) -> pd.DataFrame:
        """
        Generate a comprehensive report of crawling results in CSV format
        
        Args:
            results: Crawling results from crawl_by_priority
            
        Returns:
            DataFrame with crawling summary
        """
        report_data = []
        
        payer_results = results.get('payer_results', {})
        
        for idx, row in self.payer_df.iterrows():
            company_name = row['company_name']
            base_domain = row['base_domain']
            priority = row.get('priority', 'medium')
            market_share = row.get('market_share', 'N/A')
            
            # Find matching results
            payer_key = re.sub(r'[^a-zA-Z0-9]', '_', company_name.lower())
            payer_key = re.sub(r'_+', '_', payer_key).strip('_')
            
            payer_result = payer_results.get(payer_key, {})
            
            if 'error' in payer_result:
                status = 'Failed'
                links_discovered = 0
                pdfs_discovered = 0
                pdfs_downloaded = 0
                rules_extracted = 0
                error_message = payer_result.get('error', 'Unknown error')
            else:
                status = 'Success'
                discovery = payer_result.get('discovery_summary', {})
                extracted = payer_result.get('extracted_content', {})
                
                links_discovered = discovery.get('total_links_discovered', 0)
                pdfs_discovered = discovery.get('total_pdfs_discovered', 0)
                pdfs_downloaded = discovery.get('successful_downloads', 0)
                rules_extracted = extracted.get('total_rules_extracted', 0)
                error_message = ''
            
            report_data.append({
                'Company Name': company_name,
                'Base Domain': base_domain,
                'Priority': priority,
                'Market Share (%)': market_share,
                'Crawl Status': status,
                'Links Discovered': links_discovered,
                'PDFs Discovered': pdfs_discovered,
                'PDFs Downloaded': pdfs_downloaded,
                'Rules Extracted': rules_extracted,
                'Error Message': error_message
            })
        
        return pd.DataFrame(report_data)


def main():
    """Main function for CSV-driven crawling"""
    import argparse
    
    parser = argparse.ArgumentParser(description='CSV-Driven Intelligent Payer Crawler')
    parser.add_argument('--csv', type=str, default='payer_companies.csv', help='CSV file with payer information')
    parser.add_argument('--priority', type=str, choices=['high', 'medium', 'low'], help='Filter by priority level')
    parser.add_argument('--discover-only', action='store_true', help='Only run auto-discovery, no crawling')
    parser.add_argument('--max-depth', type=int, default=3, help='Maximum BFS depth')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('--output', type=str, default='csv_crawl_results.json', help='Output filename')
    
    args = parser.parse_args()
    
    # Initialize CSV crawler
    crawler = IntelligentCSVCrawler(
        csv_file=args.csv,
        headless=args.headless,
        max_depth=args.max_depth
    )
    
    try:
        if args.discover_only:
            # Only run auto-discovery
            print(f"Running auto-discovery for payers in {args.csv}...")
            configs = crawler.auto_discover_all_payers()
            crawler.save_discovered_configs()
            print(f"Auto-discovery completed! Found configurations for {len(configs)} payers")
        else:
            # Run full crawling workflow
            print(f"Starting CSV-driven crawling...")
            print(f"CSV file: {args.csv}")
            print(f"Priority filter: {args.priority or 'all'}")
            print(f"Max depth: {args.max_depth}")
            
            # Auto-discover configurations
            crawler.auto_discover_all_payers()
            crawler.save_discovered_configs()
            
            # Run crawling
            results = crawler.crawl_by_priority(args.priority)
            crawler.save_results(results, args.output)
            
            # Generate CSV report
            report_df = crawler.generate_csv_crawl_report(results)
            report_filename = args.output.replace('.json', '_report.csv')
            report_df.to_csv(crawler.results_dir / report_filename, index=False)
            
            print(f"\\nCrawling completed!")
            print(f"Results saved to: {args.output}")
            print(f"CSV report saved to: {report_filename}")
            
            # Print summary
            summary = results.get('crawl_summary', {})
            print(f"\\nSummary:")
            print(f"- Total payers processed: {summary.get('total_payers_crawled', 0)}")
            print(f"- Successful crawls: {summary.get('successful_crawls', 0)}")
            print(f"- Total PDFs downloaded: {summary.get('total_pdfs_downloaded', 0)}")
            print(f"- Total rules extracted: {summary.get('total_rules_extracted', 0)}")
        
    finally:
        crawler.close()


if __name__ == "__main__":
    main()