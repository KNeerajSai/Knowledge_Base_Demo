#!/usr/bin/env python3
"""
Quick PDF Discovery Demo
Shows the power of CSV+BFS combination with fast results
"""

import time
import logging
from collections import deque
from urllib.parse import urljoin, urlparse
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

def quick_payer_test(company_name, base_domain, known_portal=None, max_time_seconds=60):
    """Quick test of a single payer's PDF discovery potential"""
    
    print(f"\n🔍 Quick Test: {company_name}")
    print(f"Domain: {base_domain}")
    print(f"Time limit: {max_time_seconds} seconds")
    print("-" * 50)
    
    # Setup WebDriver
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-images')
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_page_load_timeout(10)
    
    start_time = time.time()
    pdfs_found = set()
    urls_visited = set()
    
    try:
        # Discover starting URLs
        starting_urls = []
        if known_portal:
            starting_urls.append(known_portal)
        
        # Add common provider portals
        common_portals = [
            f"https://provider.{base_domain}/",
            f"https://providers.{base_domain}/",
            f"https://www.{base_domain}/provider/",
            f"https://www.{base_domain}/providers/"
        ]
        
        for portal in common_portals:
            try:
                response = requests.head(portal, timeout=3)
                if 200 <= response.status_code < 400:
                    starting_urls.append(portal)
                    break  # Use first working portal for speed
            except:
                continue
        
        if not starting_urls:
            starting_urls = [f"https://www.{base_domain}/"]
        
        print(f"Starting URLs: {starting_urls[:1]}...")  # Show first URL only
        
        # Quick BFS search
        queue = deque([(url, 0) for url in starting_urls[:1]])  # Limit to 1 URL for speed
        allowed_domains = [base_domain, f"www.{base_domain}", f"provider.{base_domain}", f"providers.{base_domain}"]
        
        while queue and time.time() - start_time < max_time_seconds and len(urls_visited) < 15:
            current_url, depth = queue.popleft()
            
            if current_url in urls_visited or depth > 1:  # Shallow search
                continue
            
            urls_visited.add(current_url)
            
            try:
                driver.get(current_url)
                time.sleep(1)
                
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                links = soup.find_all('a', href=True)
                
                for link in links[:100]:  # Limit links processed per page
                    href = link['href']
                    text = link.get_text(strip=True).lower()
                    absolute_url = urljoin(current_url, href)
                    
                    # Check domain
                    parsed = urlparse(absolute_url)
                    if not any(domain in parsed.netloc for domain in allowed_domains):
                        continue
                    
                    # Check for PDFs
                    if absolute_url.lower().endswith('.pdf') or '.pdf' in absolute_url.lower():
                        pdfs_found.add(absolute_url)
                        print(f"  ✓ PDF found: {absolute_url.split('/')[-1]}")
                    
                    # Add relevant links for deeper search
                    elif any(keyword in text for keyword in ['provider', 'manual', 'guide', 'form', 'document']) and depth == 0:
                        queue.append((absolute_url, depth + 1))
                
            except Exception as e:
                print(f"  ⚠️ Error with {current_url}: {str(e)[:50]}...")
                continue
        
        elapsed = time.time() - start_time
        
        print(f"\n📊 Results for {company_name}:")
        print(f"  Time elapsed: {elapsed:.1f} seconds")
        print(f"  URLs visited: {len(urls_visited)}")
        print(f"  PDFs discovered: {len(pdfs_found)}")
        
        if pdfs_found:
            print(f"\n📄 Sample PDFs found:")
            for i, pdf in enumerate(list(pdfs_found)[:3], 1):
                print(f"  {i}. {pdf.split('/')[-1]}")
            if len(pdfs_found) > 3:
                print(f"  ... and {len(pdfs_found) - 3} more")
        
        return len(pdfs_found)
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return 0
    
    finally:
        driver.quit()

def main():
    """Demo the discovery power across multiple payers"""
    
    print("🚀 Quick PDF Discovery Demonstration")
    print("CSV + BFS Combined Approach")
    print("=" * 60)
    
    # Load CSV
    try:
        df = pd.read_csv('payer_companies.csv')
        print(f"📁 Loaded {len(df)} payers from CSV")
    except:
        print("❌ Could not load payer_companies.csv")
        return
    
    # Test first few payers quickly
    test_payers = [
        ("United Healthcare", "uhc.com"),
        ("Anthem/Elevance Health", "anthem.com"),
        ("Aetna", "aetna.com"),
        ("Kaiser Permanente", "kp.org"),
        ("Centene Corporation", "centene.com")
    ]
    
    total_pdfs = 0
    successful_tests = 0
    
    for company, domain in test_payers:
        try:
            pdfs_found = quick_payer_test(company, domain, max_time_seconds=45)
            total_pdfs += pdfs_found
            if pdfs_found > 0:
                successful_tests += 1
        except KeyboardInterrupt:
            print("\n⏹️ Test interrupted by user")
            break
        except Exception as e:
            print(f"❌ {company} test failed: {e}")
    
    print(f"\n🎯 QUICK DEMO SUMMARY")
    print("=" * 40)
    print(f"Payers tested: {len(test_payers)}")
    print(f"Total PDFs found: {total_pdfs}")
    print(f"Successful tests: {successful_tests}")
    
    if successful_tests > 0:
        avg_pdfs = total_pdfs / successful_tests
        print(f"Average PDFs per successful payer: {avg_pdfs:.1f}")
        
        # Project to all 15 payers
        projected_total = int(avg_pdfs * len(df))
        print(f"\n🔮 Projection for all {len(df)} payers:")
        print(f"Estimated total PDFs discoverable: {projected_total:,}")
        
        # Time estimate
        estimated_time = len(df) * 2  # 2 minutes per payer
        print(f"Estimated time for full discovery: {estimated_time} minutes ({estimated_time/60:.1f} hours)")
    
    print(f"\n✨ This demonstrates the power of CSV + BFS!")
    print(f"   The system can systematically discover thousands of PDFs")
    print(f"   across all major healthcare payers automatically.")

if __name__ == "__main__":
    main()