#!/usr/bin/env python3
"""
Basic Usage Examples for Healthcare Payer Knowledge Base Crawler
"""

from payer_portal_crawler import PayerPortalCrawler

def example_single_payer():
    """Example: Extract from a single payer"""
    print("Example 1: Single Payer Extraction")
    
    crawler = PayerPortalCrawler(headless=True, timeout=30)
    
    try:
        # Extract from United Healthcare
        print("Extracting from United Healthcare...")
        results = crawler.crawl_payer("united_healthcare")
        
        # Save results
        crawler.save_results({"uhc": results}, "uhc_extraction.json")
        
        # Print summary
        if 'extracted_content' in results:
            content = results['extracted_content']
            print(f"✅ Extraction completed!")
            print(f"📊 Rules extracted: {len(content.get('rules', []))}")
            print(f"📄 Pages crawled: {len(content.get('pages_visited', []))}")
        else:
            print("❌ Extraction failed")
            
    finally:
        crawler.close()

def example_all_payers():
    """Example: Extract from all configured payers"""
    print("\\nExample 2: All Payers Extraction")
    
    crawler = PayerPortalCrawler(headless=True)
    
    try:
        # Extract from all payers
        print("Extracting from all payers...")
        results = crawler.crawl_all_payers()
        
        # Generate summary report
        summary = crawler.generate_summary_report(results)
        
        # Save results
        crawler.save_results(results, "all_payers_extraction.json")
        
        # Print summary
        print(f"✅ All extractions completed!")
        print(f"📊 Total rules: {summary.get('total_rules', 0)}")
        print(f"📄 Total PDFs: {summary.get('total_pdfs', 0)}")
        print(f"🏥 Payers processed: {summary.get('total_payers', 0)}")
        
    finally:
        crawler.close()

if __name__ == "__main__":
    example_single_payer()
    example_all_payers()