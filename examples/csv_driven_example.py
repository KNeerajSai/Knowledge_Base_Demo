#!/usr/bin/env python3
"""
CSV-Driven Crawler Examples
"""

from intelligent_csv_crawler import IntelligentCSVCrawler

def example_auto_discovery():
    """Example: Auto-discover payer configurations from CSV"""
    print("Example 1: Auto-Discovery from CSV")
    
    crawler = IntelligentCSVCrawler(
        csv_file="payer_companies.csv",
        headless=True
    )
    
    try:
        # Auto-discover configurations
        print("Running auto-discovery...")
        configs = crawler.auto_discover_all_payers()
        
        # Save configurations
        crawler.save_discovered_configs()
        
        print(f"✅ Auto-discovery completed!")
        print(f"🔍 Discovered configs for {len(configs)} payers")
        
        # Print sample configuration
        if configs:
            sample_key = list(configs.keys())[0]
            sample_config = configs[sample_key]
            print(f"\\n📋 Sample configuration for {sample_config['name']}:")
            print(f"   Starting URLs: {len(sample_config['starting_urls'])}")
            print(f"   Allowed domains: {sample_config['allowed_domains']}")
        
    finally:
        crawler.close()

def example_priority_crawling():
    """Example: Crawl only high-priority payers"""
    print("\\nExample 2: Priority-Based Crawling")
    
    crawler = IntelligentCSVCrawler(
        csv_file="payer_companies.csv",
        headless=True,
        max_depth=2  # Faster crawling
    )
    
    try:
        # Crawl only high-priority payers
        print("Crawling high-priority payers...")
        results = crawler.crawl_by_priority(priority_filter="high")
        
        # Save results
        crawler.save_results(results, "high_priority_crawl.json")
        
        # Generate CSV report
        report_df = crawler.generate_csv_crawl_report(results)
        report_df.to_csv("high_priority_report.csv", index=False)
        
        print(f"✅ High-priority crawling completed!")
        
        # Print summary
        summary = results.get('crawl_summary', {})
        print(f"📊 Successful crawls: {summary.get('successful_crawls', 0)}")
        print(f"📄 Total PDFs downloaded: {summary.get('total_pdfs_downloaded', 0)}")
        print(f"📋 Total rules extracted: {summary.get('total_rules_extracted', 0)}")
        
    finally:
        crawler.close()

def example_custom_csv():
    """Example: Use custom CSV with different payers"""
    print("\\nExample 3: Custom CSV File")
    
    # Create custom CSV
    import pandas as pd
    
    custom_payers = pd.DataFrame([
        {
            'company_name': 'Blue Cross Blue Shield of Texas',
            'base_domain': 'bcbstx.com',
            'priority': 'high',
            'known_provider_portal': 'https://www.bcbstx.com/provider/'
        },
        {
            'company_name': 'Kaiser Permanente',
            'base_domain': 'kp.org', 
            'priority': 'medium',
            'known_provider_portal': None  # Will auto-discover
        }
    ])
    
    custom_payers.to_csv("custom_payers.csv", index=False)
    print("Created custom CSV with 2 payers")
    
    # Use custom CSV
    crawler = IntelligentCSVCrawler(
        csv_file="custom_payers.csv",
        headless=True
    )
    
    try:
        # Auto-discover and crawl
        results = crawler.crawl_by_priority()
        print(f"✅ Custom CSV crawling completed!")
        
    finally:
        crawler.close()

if __name__ == "__main__":
    example_auto_discovery()
    example_priority_crawling()
    example_custom_csv()