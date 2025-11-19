#!/usr/bin/env python3
"""
Payer Portal Crawler - Dynamic Knowledge Base
Healthcare Knowledge Base System

This module crawls healthcare payer portals to extract:
- Prior authorization requirements
- Timely filing rules  
- Claim submission guidelines
- Appeals processes

Target Payers (Phase 1):
1. United Healthcare
2. Anthem/Elevance Health (BCBS)
3. Aetna

Author: Development Team
Date: October 2025
"""

import time
import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

# Selenium imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains

# BeautifulSoup for HTML parsing
from bs4 import BeautifulSoup
import requests

# PDF processing
import PyPDF2
import fitz  # PyMuPDF for better PDF extraction

# Data processing
import re
import os
from urllib.parse import urljoin, urlparse


class PayerPortalCrawler:
    """
    Comprehensive crawler for healthcare payer portals
    Handles dynamic content, login requirements, and structured data extraction
    """
    
    def __init__(self, headless: bool = True, timeout: int = 30):
        """
        Initialize the crawler with Chrome WebDriver
        
        Args:
            headless: Run browser in headless mode
            timeout: Default timeout for web elements
        """
        self.timeout = timeout
        self.setup_logging()
        
        # Create downloads directory
        self.downloads_dir = Path("payer_pdfs")
        self.downloads_dir.mkdir(exist_ok=True)
        
        self.setup_webdriver(headless)
        self.results = {}
        
        # Define target payers and their portal configurations
        self.payer_configs = self._load_payer_configurations()
        
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('payer_crawler.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_webdriver(self, headless: bool):
        """Configure Chrome WebDriver with optimal settings"""
        chrome_options = Options()
        
        if headless:
            chrome_options.add_argument('--headless')
            
        # Performance and security options
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        # Configure download settings (only if downloads_dir is available)
        prefs = {
            "profile.managed_default_content_settings.images": 2,
            "profile.default_content_setting_values.notifications": 2,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True
        }
        
        # Add download directory if it exists
        if hasattr(self, 'downloads_dir'):
            prefs["download.default_directory"] = str(self.downloads_dir.absolute())
            
        chrome_options.add_experimental_option("prefs", prefs)
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(self.timeout)
            self.logger.info("WebDriver initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize WebDriver: {e}")
            raise
            
    def _load_payer_configurations(self) -> Dict:
        """Load payer portal configurations"""
        return {
            "united_healthcare": {
                "name": "United Healthcare",
                "base_url": "https://www.uhcprovider.com/",
                "provider_portal": "https://www.uhcprovider.com/en/resource-library.html",
                "additional_pages": [
                    "https://www.uhcprovider.com/en/policies-protocols.html",
                    "https://www.uhcprovider.com/en/prior-authorization.html",
                    "https://www.uhcprovider.com/en/claims-payments.html"
                ],
                "target_sections": {
                    "prior_authorization": [
                        "prior authorization", "preauthorization", "pre-auth",
                        "authorization requirements", "auth criteria"
                    ],
                    "timely_filing": [
                        "timely filing", "claim submission deadlines", 
                        "filing requirements", "submission timelines"
                    ],
                    "appeals": [
                        "appeals process", "claim appeals", "dispute resolution",
                        "appeal procedures", "grievances"
                    ]
                },
                "login_required": False,  # Start with public areas
                "rate_limit": 2  # seconds between requests
            },
            
            "countycare": {
                "name": "CountyCare Health Plan",
                "base_url": "https://countycare.com/",
                "provider_portal": "https://countycare.com/providers/",
                "additional_pages": [
                    "https://countycare.com/member-resources/",
                    "https://countycare.com/about-us/",
                    "https://countycare.com/"
                ],
                "target_sections": {
                    "prior_authorization": [
                        "prior authorization", "preauthorization", "pre-auth",
                        "authorization requirements", "auth criteria"
                    ],
                    "timely_filing": [
                        "timely filing", "claim submission deadlines", 
                        "filing requirements", "submission timelines"
                    ],
                    "appeals": [
                        "appeals process", "claim appeals", "dispute resolution",
                        "appeal procedures", "grievances"
                    ]
                },
                "login_required": False,
                "rate_limit": 2
            },
            
            "anthem": {
                "name": "Anthem/Elevance Health",
                "base_url": "https://providers.anthem.com/",
                "provider_portal": "https://providers.anthem.com/docs/gpp/",
                "direct_pdf_urls": [
                    "https://files.providernews.anthem.com/1661/2022-Provider-Manual-pages-44-113.pdf",
                    "https://providers.anthem.com/docs/gpp/OH_CAID_ProviderManual.pdf?v=202210032112",
                    "https://providers.anthem.com/docs/gpp/NY_ABC_CAID_ProviderManual.pdf?v=202501161732",
                    "https://providers.anthem.com/docs/gpp/OH_CAID_ClaimsEscalation.pdf",
                    "https://providers.anthem.com/docs/gpp/NV_CAID_PriorAuthreq006648-22.pdf",
                    "https://providers.anthem.com/docs/gpp/VA_CAID_ProviderManual.pdf?v=202105212022",
                    "https://providers.anthem.com/docs/gpp/california-provider/CA_CAID_ProviderManual.pdf",
                    "https://providers.anthem.com/docs/gpp/WI_CAID_Provider_Manual.pdf?v=202504111439"
                ],
                "additional_pages": [
                    "https://www.anthem.com/provider/forms/",
                    "https://www.anthem.com/provider/individual-commercial/prior-authorization/"
                ],
                "target_sections": {
                    "prior_authorization": [
                        "prior authorization", "preauthorization", "medical necessity",
                        "authorization lists", "pre-auth requirements"
                    ],
                    "timely_filing": [
                        "timely filing", "claim deadlines", "filing limits",
                        "submission requirements", "billing deadlines"
                    ],
                    "appeals": [
                        "appeals", "claim disputes", "grievance procedures",
                        "appeal guidelines", "dispute resolution"
                    ]
                },
                "login_required": False,
                "rate_limit": 2
            },
            
            "aetna": {
                "name": "Aetna",
                "base_url": "https://www.aetna.com/",
                "provider_portal": "https://www.aetna.com/health-care-professionals.html",
                "additional_pages": [
                    "https://www.aetna.com/health-care-professionals/provider-education-center.html",
                    "https://www.aetna.com/health-care-professionals/clinical-policy-bulletins.html",
                    "https://www.aetna.com/health-care-professionals/claims-payment.html"
                ],
                "target_sections": {
                    "prior_authorization": [
                        "prior authorization", "preauthorization", "pre-auth",
                        "authorization requirements", "medical review"
                    ],
                    "timely_filing": [
                        "timely filing", "claim submission", "filing deadlines",
                        "billing requirements", "submission timelines"
                    ],
                    "appeals": [
                        "appeals process", "claim appeals", "disputes",
                        "appeal procedures", "grievance process"
                    ]
                },
                "login_required": False,
                "rate_limit": 2
            }
        }
    
    def crawl_payer(self, payer_key: str) -> Dict:
        """
        Crawl a specific payer portal
        
        Args:
            payer_key: Key for payer configuration
            
        Returns:
            Dictionary containing extracted data
        """
        if payer_key not in self.payer_configs:
            raise ValueError(f"Unknown payer: {payer_key}")
            
        config = self.payer_configs[payer_key]
        self.logger.info(f"Starting crawl for {config['name']}")
        
        try:
            # Navigate to provider portal
            self.driver.get(config['provider_portal'])
            self.wait_for_page_load()
            
            # Extract page content
            page_data = self._extract_page_content(config)
            
            # Find relevant sections
            extracted_data = self._find_target_sections(page_data, config)
            
            # Follow relevant links for deeper extraction
            detailed_data = self._crawl_detailed_sections(extracted_data, config)
            
            # Download and extract PDFs
            self.logger.info(f"Starting PDF download for {config['name']}")
            pdf_data = self.download_pdfs(payer_key)
            
            result = {
                'payer': config['name'],
                'crawl_timestamp': datetime.now().isoformat(),
                'base_url': config['base_url'],
                'extracted_content': detailed_data,
                'pdf_documents': pdf_data,
                'metadata': {
                    'total_pages_crawled': len(detailed_data.get('pages_visited', [])),
                    'total_pdfs_downloaded': len(pdf_data),
                    'content_types_found': list(detailed_data.get('content_summary', {}).keys())
                }
            }
            
            self.results[payer_key] = result
            self.logger.info(f"Successfully crawled {config['name']}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error crawling {config['name']}: {e}")
            return {'error': str(e), 'payer': config['name']}
    
    def _extract_page_content(self, config: Dict) -> Dict:
        """Extract content from current page"""
        try:
            # Get page source
            html_content = self.driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract structured data
            page_data = {
                'title': soup.title.string if soup.title else '',
                'url': self.driver.current_url,
                'text_content': soup.get_text(),
                'links': self._extract_links(soup, config['base_url']),
                'sections': self._extract_sections(soup),
                'download_links': self._extract_download_links(soup)
            }
            
            return page_data
            
        except Exception as e:
            self.logger.error(f"Error extracting page content: {e}")
            return {}
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Extract relevant links from the page"""
        links = []
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text(strip=True)
            
            if not text:
                continue
                
            # Convert relative URLs to absolute
            full_url = urljoin(base_url, href)
            
            # Filter for relevant links
            if self._is_relevant_link(text, href):
                links.append({
                    'text': text,
                    'url': full_url,
                    'type': self._classify_link_type(text, href)
                })
        
        return links
    
    def _is_relevant_link(self, text: str, href: str) -> bool:
        """Determine if a link is relevant for our crawling"""
        text_lower = text.lower()
        href_lower = href.lower()
        
        relevant_keywords = [
            'prior auth', 'authorization', 'timely filing', 'appeals',
            'provider', 'manual', 'guideline', 'policy', 'procedure',
            'claim', 'billing', 'reimbursement', 'coverage'
        ]
        
        return any(keyword in text_lower or keyword in href_lower 
                  for keyword in relevant_keywords)
    
    def _classify_link_type(self, text: str, href: str) -> str:
        """Classify the type of link"""
        text_lower = text.lower()
        href_lower = href.lower()
        
        if any(ext in href_lower for ext in ['.pdf', '.doc', '.docx']):
            return 'document'
        elif 'prior auth' in text_lower or 'authorization' in text_lower:
            return 'prior_authorization'
        elif 'timely filing' in text_lower or 'deadline' in text_lower:
            return 'timely_filing'
        elif 'appeal' in text_lower or 'dispute' in text_lower:
            return 'appeals'
        elif 'manual' in text_lower or 'guide' in text_lower:
            return 'manual'
        else:
            return 'general'
    
    def _extract_sections(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract main content sections from the page"""
        sections = []
        
        # Look for common section headers
        for header in soup.find_all(['h1', 'h2', 'h3', 'h4']):
            header_text = header.get_text(strip=True)
            
            if not header_text:
                continue
                
            # Find content following this header
            content_elements = []
            for sibling in header.find_next_siblings():
                if sibling.name in ['h1', 'h2', 'h3', 'h4']:
                    break
                if sibling.get_text(strip=True):
                    content_elements.append(sibling.get_text(strip=True))
            
            sections.append({
                'header': header_text,
                'content': ' '.join(content_elements),
                'relevance_score': self._calculate_relevance_score(header_text + ' ' + ' '.join(content_elements))
            })
        
        return sorted(sections, key=lambda x: x['relevance_score'], reverse=True)
    
    def _calculate_relevance_score(self, text: str) -> float:
        """Calculate relevance score for content"""
        text_lower = text.lower()
        
        high_value_keywords = [
            'prior authorization', 'timely filing', 'appeals process',
            'claim submission', 'billing guidelines', 'coverage determination'
        ]
        
        medium_value_keywords = [
            'provider', 'healthcare', 'insurance', 'medical',
            'policy', 'procedure', 'requirement', 'deadline'
        ]
        
        score = 0
        for keyword in high_value_keywords:
            score += text_lower.count(keyword) * 3
            
        for keyword in medium_value_keywords:
            score += text_lower.count(keyword) * 1
            
        return score
    
    def _extract_download_links(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract downloadable documents"""
        downloads = []
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text(strip=True)
            
            # Check for document extensions
            if any(ext in href.lower() for ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx']):
                downloads.append({
                    'text': text,
                    'url': href,
                    'type': href.split('.')[-1].lower(),
                    'relevance_score': self._calculate_relevance_score(text)
                })
        
        return sorted(downloads, key=lambda x: x['relevance_score'], reverse=True)
    
    def download_pdfs(self, payer_key: str) -> List[Dict]:
        """Download PDFs from payer websites for different geographic zones"""
        config = self.payer_configs[payer_key]
        downloaded_pdfs = []
        all_pdf_links = []
        
        self.logger.info(f"Starting PDF download for {config['name']}")
        
        # Check if this payer has direct PDF URLs
        if 'direct_pdf_urls' in config:
            self.logger.info(f"Using direct PDF URLs for {config['name']}")
            for pdf_url in config['direct_pdf_urls']:
                filename = os.path.basename(pdf_url.split('?')[0])  # Remove query params
                all_pdf_links.append({
                    'url': pdf_url,
                    'text': filename,
                    'filename': filename,
                    'relevance_score': 5  # High relevance for direct URLs
                })
        else:
            # Standard web crawling approach
            pages_to_search = [config['provider_portal']]
            if 'additional_pages' in config:
                pages_to_search.extend(config['additional_pages'])
            
            try:
                # Search for PDFs across multiple pages
                for page_url in pages_to_search:
                    try:
                        self.logger.info(f"Searching for PDFs on: {page_url}")
                        self.driver.get(page_url)
                        self.wait_for_page_load()
                        
                        # Find PDF links on this page
                        page_pdf_links = self._find_pdf_links()
                        all_pdf_links.extend(page_pdf_links)
                        
                        # Rate limiting between pages
                        time.sleep(config['rate_limit'])
                        
                    except Exception as e:
                        self.logger.warning(f"Failed to search page {page_url}: {e}")
                        continue
                
                # Remove duplicates based on URL
                unique_pdfs = {}
                for pdf_info in all_pdf_links:
                    unique_pdfs[pdf_info['url']] = pdf_info
                all_pdf_links = list(unique_pdfs.values())
                
                # Filter for relevant PDFs (provider manuals, guidelines, etc.)
                all_pdf_links = self._filter_relevant_pdfs(all_pdf_links, config)
                
            except Exception as e:
                self.logger.error(f"Error in PDF search process: {e}")
        
        self.logger.info(f"Found {len(all_pdf_links)} total PDFs to download")
        
        # Download PDFs
        for pdf_info in all_pdf_links[:15]:  # Limit to top 15 most relevant
            try:
                downloaded_file = self._download_pdf(pdf_info, payer_key)
                if downloaded_file:
                    # Extract content from PDF
                    pdf_content = self._extract_pdf_content(downloaded_file)
                    
                    pdf_info.update({
                        'local_file': downloaded_file,
                        'extracted_content': pdf_content,
                        'download_timestamp': datetime.now().isoformat()
                    })
                    downloaded_pdfs.append(pdf_info)
                    
                    self.logger.info(f"Successfully downloaded and extracted: {pdf_info['filename']}")
                    
            except Exception as e:
                self.logger.error(f"Failed to download PDF {pdf_info['url']}: {e}")
                continue
                
        return downloaded_pdfs
    
    def _find_pdf_links(self) -> List[Dict]:
        """Find all PDF links on the current page"""
        pdf_links = []
        
        # Get page source and find PDF links
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text(strip=True)
            
            if href.lower().endswith('.pdf') or '.pdf' in href.lower():
                # Convert relative URLs to absolute
                full_url = urljoin(self.driver.current_url, href)
                
                pdf_links.append({
                    'url': full_url,
                    'text': text,
                    'filename': os.path.basename(urlparse(href).path) or f"document_{len(pdf_links)}.pdf"
                })
        
        return pdf_links
    
    def _filter_relevant_pdfs(self, pdf_links: List[Dict], config: Dict) -> List[Dict]:
        """Filter PDFs based on relevance to our target content"""
        relevant_pdfs = []
        
        # Keywords that indicate relevant content
        relevant_keywords = [
            'provider', 'manual', 'guide', 'policy', 'procedure', 'billing',
            'prior auth', 'authorization', 'timely filing', 'appeals',
            'coverage', 'benefits', 'claim', 'reimbursement', 'network',
            'geographic', 'region', 'state', 'area', 'zone'
        ]
        
        for pdf_info in pdf_links:
            text_to_check = (pdf_info['text'] + ' ' + pdf_info['filename']).lower()
            
            # Calculate relevance score
            relevance_score = sum(1 for keyword in relevant_keywords if keyword in text_to_check)
            
            if relevance_score > 0:
                pdf_info['relevance_score'] = relevance_score
                relevant_pdfs.append(pdf_info)
        
        # Sort by relevance score
        return sorted(relevant_pdfs, key=lambda x: x['relevance_score'], reverse=True)
    
    def _download_pdf(self, pdf_info: Dict, payer_key: str) -> Optional[str]:
        """Download a single PDF file"""
        try:
            # Create payer-specific directory
            payer_dir = self.downloads_dir / payer_key
            payer_dir.mkdir(exist_ok=True)
            
            # Clean filename
            clean_filename = re.sub(r'[^\w\-_\.]', '_', pdf_info['filename'])
            local_file = payer_dir / clean_filename
            
            # Enhanced headers to mimic browser request
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/pdf,application/octet-stream,*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            # Download using requests with enhanced headers
            session = requests.Session()
            response = session.get(pdf_info['url'], headers=headers, timeout=30, stream=True, allow_redirects=True)
            response.raise_for_status()
            
            # Check if response is actually a PDF
            content_type = response.headers.get('content-type', '').lower()
            
            # Download content
            total_size = 0
            with open(local_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        total_size += len(chunk)
            
            # Check file size
            if total_size < 1000:
                self.logger.warning(f"Downloaded file seems too small: {total_size} bytes")
                os.remove(local_file)
                return None
            
            self.logger.info(f"Successfully downloaded PDF: {clean_filename} ({total_size} bytes)")
            return str(local_file)
            
        except Exception as e:
            self.logger.error(f"Failed to download PDF from {pdf_info['url']}: {e}")
            return None
    
    def _extract_pdf_content(self, pdf_file: str) -> Dict:
        """Extract content from a PDF file"""
        content = {
            'text': '',
            'pages': [],
            'extracted_rules': [],
            'geographic_zones': [],
            'extraction_method': 'pymupdf'
        }
        
        try:
            # Use PyMuPDF (fitz) for better text extraction
            doc = fitz.open(pdf_file)
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                page_text = page.get_text()
                
                content['pages'].append({
                    'page_number': page_num + 1,
                    'text': page_text
                })
                content['text'] += page_text + '\n'
            
            doc.close()
            
            # Extract structured information
            content['extracted_rules'] = self._extract_rules_from_text(content['text'])
            content['geographic_zones'] = self._extract_geographic_zones(content['text'])
            
        except Exception as e:
            self.logger.error(f"PyMuPDF extraction failed, trying PyPDF2: {e}")
            
            # Fallback to PyPDF2
            try:
                with open(pdf_file, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    
                    for page_num, page in enumerate(pdf_reader.pages):
                        page_text = page.extract_text()
                        content['pages'].append({
                            'page_number': page_num + 1,
                            'text': page_text
                        })
                        content['text'] += page_text + '\n'
                
                content['extraction_method'] = 'pypdf2'
                content['extracted_rules'] = self._extract_rules_from_text(content['text'])
                content['geographic_zones'] = self._extract_geographic_zones(content['text'])
                
            except Exception as e2:
                self.logger.error(f"PDF extraction failed completely: {e2}")
                content['error'] = str(e2)
        
        return content
    
    def _extract_rules_from_text(self, text: str) -> List[Dict]:
        """Extract payer rules from PDF text"""
        rules = []
        text_lower = text.lower()
        
        # Define rule patterns
        rule_patterns = {
            'prior_authorization': [
                r'prior authorization.*?(?=\n\n|\n[A-Z]|$)',
                r'preauthorization.*?(?=\n\n|\n[A-Z]|$)',
                r'authorization required.*?(?=\n\n|\n[A-Z]|$)'
            ],
            'timely_filing': [
                r'timely filing.*?(?=\n\n|\n[A-Z]|$)',
                r'filing deadline.*?(?=\n\n|\n[A-Z]|$)',
                r'submit.*?within.*?days.*?(?=\n\n|\n[A-Z]|$)'
            ],
            'appeals': [
                r'appeal.*?process.*?(?=\n\n|\n[A-Z]|$)',
                r'grievance.*?procedure.*?(?=\n\n|\n[A-Z]|$)',
                r'dispute.*?resolution.*?(?=\n\n|\n[A-Z]|$)'
            ]
        }
        
        for rule_type, patterns in rule_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    rule_text = match.group().strip()
                    if len(rule_text) > 50:  # Filter out very short matches
                        rules.append({
                            'type': rule_type,
                            'content': rule_text,
                            'confidence': len(rule_text) / 1000  # Simple confidence based on length
                        })
        
        return rules
    
    def _extract_geographic_zones(self, text: str) -> List[Dict]:
        """Extract geographic zone information from PDF text"""
        zones = []
        text_lower = text.lower()
        
        # Common geographic identifiers
        state_patterns = [
            r'(alabama|alaska|arizona|arkansas|california|colorado|connecticut|delaware|florida|georgia|hawaii|idaho|illinois|indiana|iowa|kansas|kentucky|louisiana|maine|maryland|massachusetts|michigan|minnesota|mississippi|missouri|montana|nebraska|nevada|new hampshire|new jersey|new mexico|new york|north carolina|north dakota|ohio|oklahoma|oregon|pennsylvania|rhode island|south carolina|south dakota|tennessee|texas|utah|vermont|virginia|washington|west virginia|wisconsin|wyoming)',
            r'(al|ak|az|ar|ca|co|ct|de|fl|ga|hi|id|il|in|ia|ks|ky|la|me|md|ma|mi|mn|ms|mo|mt|ne|nv|nh|nj|nm|ny|nc|nd|oh|ok|or|pa|ri|sc|sd|tn|tx|ut|vt|va|wa|wv|wi|wy)'
        ]
        
        region_patterns = [
            r'region\s+\d+',
            r'zone\s+[a-z0-9]+',
            r'area\s+[a-z0-9]+',
            r'network\s+[a-z0-9]+',
            r'service\s+area'
        ]
        
        # Extract state mentions
        for pattern in state_patterns:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                zones.append({
                    'type': 'state',
                    'value': match.group().upper(),
                    'context': text[max(0, match.start()-50):match.end()+50]
                })
        
        # Extract region/zone mentions
        for pattern in region_patterns:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                zones.append({
                    'type': 'region',
                    'value': match.group(),
                    'context': text[max(0, match.start()-50):match.end()+50]
                })
        
        return zones
    
    def _find_target_sections(self, page_data: Dict, config: Dict) -> Dict:
        """Find content sections matching our target areas"""
        target_sections = config['target_sections']
        found_content = {}
        
        for section_type, keywords in target_sections.items():
            found_content[section_type] = {
                'sections': [],
                'links': [],
                'documents': []
            }
            
            # Search in page sections
            for section in page_data.get('sections', []):
                if self._matches_keywords(section['header'] + ' ' + section['content'], keywords):
                    found_content[section_type]['sections'].append(section)
            
            # Search in links
            for link in page_data.get('links', []):
                if self._matches_keywords(link['text'], keywords):
                    found_content[section_type]['links'].append(link)
            
            # Search in documents
            for doc in page_data.get('download_links', []):
                if self._matches_keywords(doc['text'], keywords):
                    found_content[section_type]['documents'].append(doc)
        
        return found_content
    
    def _matches_keywords(self, text: str, keywords: List[str]) -> bool:
        """Check if text contains any of the target keywords"""
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in keywords)
    
    def _crawl_detailed_sections(self, extracted_data: Dict, config: Dict) -> Dict:
        """Crawl deeper into relevant links for detailed information"""
        detailed_data = {
            'pages_visited': [],
            'content_summary': {},
            'prior_authorization': {'rules': [], 'documents': []},
            'timely_filing': {'rules': [], 'documents': []},
            'appeals': {'rules': [], 'documents': []}
        }
        
        # Limit the number of pages to crawl to avoid rate limiting
        max_pages_per_section = 3
        
        for section_type, content in extracted_data.items():
            pages_crawled = 0
            
            # Crawl high-relevance links
            for link in content.get('links', [])[:max_pages_per_section]:
                if pages_crawled >= max_pages_per_section:
                    break
                    
                try:
                    self._crawl_individual_page(link['url'], section_type, detailed_data)
                    pages_crawled += 1
                    
                    # Rate limiting
                    time.sleep(config['rate_limit'])
                    
                except Exception as e:
                    self.logger.warning(f"Failed to crawl {link['url']}: {e}")
                    continue
        
        return detailed_data
    
    def _crawl_individual_page(self, url: str, section_type: str, detailed_data: Dict):
        """Crawl an individual page for specific content"""
        try:
            self.driver.get(url)
            self.wait_for_page_load()
            
            # Extract content from this page
            html_content = self.driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract relevant information
            page_info = {
                'url': url,
                'title': soup.title.string if soup.title else '',
                'content_type': section_type,
                'extracted_rules': self._extract_rules_from_page(soup, section_type),
                'crawl_timestamp': datetime.now().isoformat()
            }
            
            detailed_data['pages_visited'].append(page_info)
            
            # Add rules to appropriate section
            if section_type in detailed_data:
                detailed_data[section_type]['rules'].extend(page_info['extracted_rules'])
            
            self.logger.info(f"Successfully crawled page: {url}")
            
        except Exception as e:
            self.logger.error(f"Error crawling individual page {url}: {e}")
            raise
    
    def _extract_rules_from_page(self, soup: BeautifulSoup, section_type: str) -> List[Dict]:
        """Extract specific rules and requirements from a page"""
        rules = []
        
        # Look for structured content like lists, tables, and specific sections
        
        # Extract from lists
        for ul in soup.find_all('ul'):
            list_items = [li.get_text(strip=True) for li in ul.find_all('li')]
            if any(self._is_rule_content(item, section_type) for item in list_items):
                rules.extend([
                    {'type': 'list_item', 'content': item, 'source': 'ul'}
                    for item in list_items if self._is_rule_content(item, section_type)
                ])
        
        # Extract from tables
        for table in soup.find_all('table'):
            table_data = self._extract_table_data(table)
            if table_data and self._is_relevant_table(table_data, section_type):
                rules.append({
                    'type': 'table',
                    'content': table_data,
                    'source': 'table'
                })
        
        # Extract from paragraphs with specific keywords
        for p in soup.find_all('p'):
            text = p.get_text(strip=True)
            if self._is_rule_content(text, section_type):
                rules.append({
                    'type': 'paragraph',
                    'content': text,
                    'source': 'p'
                })
        
        return rules
    
    def _is_rule_content(self, text: str, section_type: str) -> bool:
        """Determine if text contains rule-like content"""
        text_lower = text.lower()
        
        rule_indicators = {
            'prior_authorization': [
                'must obtain', 'requires authorization', 'prior approval',
                'pre-authorization required', 'contact for auth'
            ],
            'timely_filing': [
                'days from', 'within', 'deadline', 'filing limit',
                'submit by', 'time limit'
            ],
            'appeals': [
                'appeal within', 'dispute process', 'grievance procedure',
                'appeal deadline', 'contact to appeal'
            ]
        }
        
        indicators = rule_indicators.get(section_type, [])
        return any(indicator in text_lower for indicator in indicators) and len(text) > 20
    
    def _extract_table_data(self, table) -> List[List[str]]:
        """Extract data from HTML table"""
        rows = []
        for tr in table.find_all('tr'):
            row = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
            if any(cell for cell in row):  # Skip empty rows
                rows.append(row)
        return rows
    
    def _is_relevant_table(self, table_data: List[List[str]], section_type: str) -> bool:
        """Check if table contains relevant information"""
        table_text = ' '.join([' '.join(row) for row in table_data]).lower()
        
        relevant_keywords = {
            'prior_authorization': ['authorization', 'approval', 'required'],
            'timely_filing': ['days', 'deadline', 'filing', 'submission'],
            'appeals': ['appeal', 'dispute', 'grievance', 'review']
        }
        
        keywords = relevant_keywords.get(section_type, [])
        return any(keyword in table_text for keyword in keywords)
    
    def wait_for_page_load(self, timeout: int = None):
        """Wait for page to fully load"""
        timeout = timeout or self.timeout
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            time.sleep(2)  # Additional wait for dynamic content
        except TimeoutException:
            self.logger.warning("Page load timeout - continuing anyway")
    
    def crawl_all_payers(self) -> Dict:
        """Crawl all configured payers"""
        self.logger.info("Starting comprehensive payer portal crawl")
        
        all_results = {}
        
        for payer_key in self.payer_configs.keys():
            try:
                result = self.crawl_payer(payer_key)
                all_results[payer_key] = result
                
                # Save intermediate results
                self.save_results(all_results, f"crawl_results_partial_{payer_key}.json")
                
                # Pause between payers to be respectful
                time.sleep(5)
                
            except Exception as e:
                self.logger.error(f"Failed to crawl {payer_key}: {e}")
                all_results[payer_key] = {'error': str(e)}
        
        # Save final results
        self.save_results(all_results, "crawl_results_final.json")
        
        self.logger.info(f"Completed crawling {len(all_results)} payers")
        return all_results
    
    def save_results(self, results: Dict, filename: str):
        """Save crawling results to JSON file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)
            self.logger.info(f"Results saved to {filename}")
        except Exception as e:
            self.logger.error(f"Failed to save results: {e}")
    
    def generate_summary_report(self, results: Dict) -> Dict:
        """Generate summary report of crawling results"""
        summary = {
            'crawl_timestamp': datetime.now().isoformat(),
            'total_payers': len(results),
            'successful_crawls': len([r for r in results.values() if 'error' not in r]),
            'failed_crawls': len([r for r in results.values() if 'error' in r]),
            'payer_summaries': {}
        }
        
        for payer_key, result in results.items():
            if 'error' not in result:
                payer_summary = {
                    'payer_name': result.get('payer', 'Unknown'),
                    'pages_crawled': len(result.get('extracted_content', {}).get('pages_visited', [])),
                    'prior_auth_rules': len(result.get('extracted_content', {}).get('prior_authorization', {}).get('rules', [])),
                    'timely_filing_rules': len(result.get('extracted_content', {}).get('timely_filing', {}).get('rules', [])),
                    'appeals_rules': len(result.get('extracted_content', {}).get('appeals', {}).get('rules', []))
                }
            else:
                payer_summary = {'error': result['error']}
                
            summary['payer_summaries'][payer_key] = payer_summary
        
        return summary
    
    def close(self):
        """Clean up resources"""
        if hasattr(self, 'driver'):
            self.driver.quit()
            self.logger.info("WebDriver closed")


def main():
    """Main execution function"""
    print("=== Payer Portal Crawler - Healthcare Knowledge Base ===")
    print("Starting crawl of top 3 payers: United Healthcare, Anthem, Aetna")
    
    crawler = None
    try:
        # Initialize crawler
        crawler = PayerPortalCrawler(headless=False)  # Set to False for debugging
        
        # Crawl all payers
        results = crawler.crawl_all_payers()
        
        # Generate summary
        summary = crawler.generate_summary_report(results)
        
        # Save summary
        crawler.save_results(summary, "crawl_summary_report.json")
        
        # Print summary
        print("\n=== CRAWLING SUMMARY ===")
        print(f"Total Payers: {summary['total_payers']}")
        print(f"Successful: {summary['successful_crawls']}")
        print(f"Failed: {summary['failed_crawls']}")
        
        for payer_key, payer_summary in summary['payer_summaries'].items():
            if 'error' not in payer_summary:
                print(f"\n{payer_summary['payer_name']}:")
                print(f"  Pages crawled: {payer_summary['pages_crawled']}")
                print(f"  Prior auth rules: {payer_summary['prior_auth_rules']}")
                print(f"  Timely filing rules: {payer_summary['timely_filing_rules']}")
                print(f"  Appeals rules: {payer_summary['appeals_rules']}")
            else:
                print(f"\n{payer_key}: ERROR - {payer_summary['error']}")
        
        print("\n=== CRAWLING COMPLETED ===")
        
    except Exception as e:
        print(f"Critical error: {e}")
        
    finally:
        if crawler:
            crawler.close()


if __name__ == "__main__":
    main()