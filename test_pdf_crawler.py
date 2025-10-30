#!/usr/bin/env python3
"""
PDF Crawler Test Script
Healthcare Knowledge Base System

Test script for downloading and extracting PDFs from payer websites
"""

import json
import time
from datetime import datetime
from pathlib import Path
from payer_portal_crawler import PayerPortalCrawler


def test_pdf_download_single_payer(payer_key: str = "united_healthcare"):
    """Test PDF download for a single payer"""
    print(f"=== Testing PDF Download for {payer_key.title().replace('_', ' ')} ===")
    
    crawler = None
    try:
        # Initialize crawler
        crawler = PayerPortalCrawler(headless=False, timeout=30)
        
        # Download PDFs
        print("Starting PDF download process...")
        pdf_results = crawler.download_pdfs(payer_key)
        
        # Save results
        results_file = f"pdf_results_{payer_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(pdf_results, f, indent=2, ensure_ascii=False, default=str)
        
        # Print summary
        print(f"\n=== PDF Download Summary for {payer_key} ===")
        print(f"Total PDFs found and downloaded: {len(pdf_results)}")
        
        for i, pdf_info in enumerate(pdf_results, 1):
            print(f"\n{i}. {pdf_info['filename']}")
            print(f"   URL: {pdf_info['url']}")
            print(f"   Local file: {pdf_info.get('local_file', 'Not downloaded')}")
            print(f"   Relevance score: {pdf_info.get('relevance_score', 0)}")
            
            # Show extracted content summary
            if 'extracted_content' in pdf_info:
                content = pdf_info['extracted_content']
                print(f"   Pages extracted: {len(content.get('pages', []))}")
                print(f"   Rules found: {len(content.get('extracted_rules', []))}")
                print(f"   Geographic zones: {len(content.get('geographic_zones', []))}")
                
                # Show first few rules
                rules = content.get('extracted_rules', [])[:3]
                if rules:
                    print("   Sample rules found:")
                    for rule in rules:
                        print(f"     - {rule['type']}: {rule['content'][:100]}...")
        
        print(f"\nResults saved to: {results_file}")
        return pdf_results
        
    except Exception as e:
        print(f"Error during PDF download test: {e}")
        return None
        
    finally:
        if crawler:
            crawler.close()


def test_all_payers_pdf():
    """Test PDF download for all top 3 payers"""
    print("=== Testing PDF Download for All Top 3 Payers ===")
    
    payers = ["united_healthcare", "anthem", "aetna"]
    all_results = {}
    
    for payer in payers:
        print(f"\n--- Starting {payer} ---")
        results = test_pdf_download_single_payer(payer)
        all_results[payer] = results
        
        # Pause between payers to be respectful
        print("Pausing 10 seconds before next payer...")
        time.sleep(10)
    
    # Save combined results
    combined_file = f"all_payers_pdf_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(combined_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n=== Final Summary ===")
    for payer, results in all_results.items():
        if results:
            print(f"{payer}: {len(results)} PDFs downloaded")
        else:
            print(f"{payer}: Failed to download PDFs")
    
    print(f"\nCombined results saved to: {combined_file}")
    return all_results


def analyze_pdf_content(pdf_results_file: str):
    """Analyze the content of downloaded PDFs"""
    print(f"=== Analyzing PDF Content from {pdf_results_file} ===")
    
    try:
        with open(pdf_results_file, 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        total_pdfs = 0
        total_rules = 0
        total_zones = 0
        rule_types = {}
        zone_types = {}
        
        # Analyze each payer's results
        for payer, pdf_list in results.items():
            if not pdf_list:
                continue
                
            print(f"\n--- {payer.title().replace('_', ' ')} Analysis ---")
            payer_pdfs = len(pdf_list)
            payer_rules = 0
            payer_zones = 0
            
            for pdf_info in pdf_list:
                if 'extracted_content' in pdf_info:
                    content = pdf_info['extracted_content']
                    rules = content.get('extracted_rules', [])
                    zones = content.get('geographic_zones', [])
                    
                    payer_rules += len(rules)
                    payer_zones += len(zones)
                    
                    # Count rule types
                    for rule in rules:
                        rule_type = rule.get('type', 'unknown')
                        rule_types[rule_type] = rule_types.get(rule_type, 0) + 1
                    
                    # Count zone types
                    for zone in zones:
                        zone_type = zone.get('type', 'unknown')
                        zone_types[zone_type] = zone_types.get(zone_type, 0) + 1
            
            total_pdfs += payer_pdfs
            total_rules += payer_rules
            total_zones += payer_zones
            
            print(f"  PDFs: {payer_pdfs}")
            print(f"  Rules extracted: {payer_rules}")
            print(f"  Geographic zones: {payer_zones}")
        
        print(f"\n=== Overall Analysis ===")
        print(f"Total PDFs downloaded: {total_pdfs}")
        print(f"Total rules extracted: {total_rules}")
        print(f"Total geographic zones found: {total_zones}")
        
        print(f"\nRule types distribution:")
        for rule_type, count in sorted(rule_types.items()):
            print(f"  {rule_type}: {count}")
        
        print(f"\nZone types distribution:")
        for zone_type, count in sorted(zone_types.items()):
            print(f"  {zone_type}: {count}")
        
    except Exception as e:
        print(f"Error analyzing PDF content: {e}")


def main():
    """Main test execution"""
    print("=== Payer PDF Download and Extraction Test ===")
    print("Choose an option:")
    print("1. Test single payer (United Healthcare)")
    print("2. Test all top 3 payers")
    print("3. Analyze existing PDF results")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        test_pdf_download_single_payer("united_healthcare")
    elif choice == "2":
        test_all_payers_pdf()
    elif choice == "3":
        results_file = input("Enter PDF results file path: ").strip()
        if Path(results_file).exists():
            analyze_pdf_content(results_file)
        else:
            print("File not found!")
    else:
        print("Invalid choice!")


if __name__ == "__main__":
    main()