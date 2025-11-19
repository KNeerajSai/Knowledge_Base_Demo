#!/usr/bin/env python3
"""
Healthcare Data Pipeline
Complete pipeline: Web Scraping → Azure Document Intelligence → PostgreSQL

Integrates existing scrapers with Azure Document Intelligence and PostgreSQL storage
"""

import asyncio
import os
import json
import glob
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

# Import existing components
from payer_portal_crawler import PayerPortalCrawler
from azure_document_intelligence_processor import (
    HealthcarePDFProcessor, 
    AzureConfig, 
    PostgreSQLConfig
)

class HealthcareDataPipeline:
    """
    Complete healthcare payer data pipeline
    Orchestrates scraping, AI processing, and database storage
    """
    
    def __init__(self, 
                 azure_config: Optional[AzureConfig] = None,
                 pg_config: Optional[PostgreSQLConfig] = None):
        
        # Use default configs if not provided
        self.azure_config = azure_config or AzureConfig()
        self.pg_config = pg_config or PostgreSQLConfig()
        
        # Initialize components
        self.pdf_processor = HealthcarePDFProcessor(self.azure_config, self.pg_config)
        self.results_summary = []
        
        print("🏥 Healthcare Data Pipeline Initialized")
        print("="*50)
        self._print_config_status()
    
    def _print_config_status(self):
        """Print configuration status"""
        azure_configured = bool(self.azure_config.endpoint and self.azure_config.api_key)
        pg_configured = bool(self.pdf_processor.pg_engine)
        
        print(f"📊 Azure Document Intelligence: {'✅ Configured' if azure_configured else '❌ Not configured (using mock)'}")
        print(f"🗄️  PostgreSQL Database: {'✅ Connected' if pg_configured else '❌ Not connected'}")
        print()
    
    async def process_existing_pdfs(self, pdf_directory: str = ".") -> Dict[str, Any]:
        """
        Process all existing PDFs found in the directory structure
        
        Args:
            pdf_directory: Root directory to search for PDFs
            
        Returns:
            Summary of processing results
        """
        print(f"🔍 SCANNING FOR EXISTING PDFs in {pdf_directory}")
        print("-" * 50)
        
        # Find all PDF files
        pdf_files = self._find_all_pdfs(pdf_directory)
        
        if not pdf_files:
            print("❌ No PDF files found")
            return {"error": "No PDFs found"}
        
        print(f"📄 Found {len(pdf_files)} PDF files:")
        for pdf in pdf_files:
            size = os.path.getsize(pdf) / 1024  # KB
            print(f"   • {pdf} ({size:.1f} KB)")
        
        # Process each PDF
        processing_results = []
        for i, pdf_path in enumerate(pdf_files, 1):
            print(f"\n[{i}/{len(pdf_files)}] Processing: {os.path.basename(pdf_path)}")
            
            # Determine payer name and document type from path
            payer_name, doc_type = self._extract_metadata_from_path(pdf_path)
            
            # Process with Azure DI
            result = await self.pdf_processor.process_pdf_with_azure_di(
                pdf_path, payer_name, doc_type
            )
            
            if result:
                # Store in PostgreSQL
                document_id = await self.pdf_processor.store_in_postgres(result)
                
                processing_results.append({
                    "pdf_path": pdf_path,
                    "payer_name": payer_name,
                    "document_type": doc_type,
                    "document_id": document_id,
                    "success": document_id is not None,
                    "rules_extracted": len(result["structured_data"].get("healthcare_rules", [])),
                    "pages_processed": result["structured_data"]["processing_metadata"].get("page_count", 0)
                })
                
                print(f"   ✅ Success: Document ID {document_id}")
                print(f"      Rules extracted: {len(result['structured_data'].get('healthcare_rules', []))}")
                print(f"      Pages: {result['structured_data']['processing_metadata'].get('page_count', 0)}")
            else:
                processing_results.append({
                    "pdf_path": pdf_path,
                    "payer_name": payer_name,
                    "document_type": doc_type,
                    "success": False,
                    "error": "Processing failed"
                })
                print(f"   ❌ Failed to process")
        
        # Generate summary
        summary = self._generate_processing_summary(processing_results)
        
        # Save results
        self._save_pipeline_results(processing_results, summary)
        
        return summary
    
    async def run_full_pipeline(self, payer_keys: List[str] = None) -> Dict[str, Any]:
        """
        Run complete pipeline: Scrape → Process → Store
        
        Args:
            payer_keys: List of payer keys to crawl (default: ['countycare'])
            
        Returns:
            Complete pipeline results
        """
        if payer_keys is None:
            payer_keys = ['countycare']  # Default to CountyCare
        
        print(f"🚀 RUNNING FULL HEALTHCARE DATA PIPELINE")
        print("="*60)
        print(f"📋 Target payers: {', '.join(payer_keys)}")
        
        all_results = []
        
        for payer_key in payer_keys:
            print(f"\n🏥 Processing payer: {payer_key.upper()}")
            print("-" * 40)
            
            # Step 1: Scrape new data
            crawler_results = await self._scrape_payer_data(payer_key)
            
            if not crawler_results:
                print(f"❌ Scraping failed for {payer_key}")
                continue
            
            # Step 2: Process PDFs with Azure DI
            pdf_results = await self._process_scraped_pdfs(crawler_results, payer_key)
            
            # Step 3: Store in database
            storage_results = await self._store_results(pdf_results)
            
            all_results.append({
                "payer_key": payer_key,
                "scraping_results": crawler_results,
                "processing_results": pdf_results,
                "storage_results": storage_results
            })
        
        # Generate final summary
        final_summary = self._generate_pipeline_summary(all_results)
        
        print(f"\n🎉 PIPELINE COMPLETED")
        print("="*30)
        print(f"✅ Successful payers: {final_summary['successful_payers']}")
        print(f"📄 Total PDFs processed: {final_summary['total_pdfs_processed']}")
        print(f"📋 Total rules extracted: {final_summary['total_rules_extracted']}")
        print(f"🗄️  Documents stored: {final_summary['documents_stored']}")
        
        return final_summary
    
    async def _scrape_payer_data(self, payer_key: str) -> Optional[Dict[str, Any]]:
        """Scrape data for a specific payer"""
        try:
            crawler = PayerPortalCrawler(headless=True, timeout=90)
            results = crawler.crawl_payer(payer_key)
            crawler.close()
            
            if 'error' not in results:
                pdf_count = len(results.get('pdf_documents', []))
                print(f"   ✅ Scraped {pdf_count} PDFs")
                return results
            else:
                print(f"   ❌ Scraping error: {results['error']}")
                return None
                
        except Exception as e:
            print(f"   ❌ Scraping exception: {e}")
            return None
    
    async def _process_scraped_pdfs(self, crawler_results: Dict[str, Any], payer_key: str) -> List[Dict[str, Any]]:
        """Process PDFs from scraping results"""
        pdf_documents = crawler_results.get('pdf_documents', [])
        processing_results = []
        
        for pdf_doc in pdf_documents:
            # Extract PDF info
            filename = pdf_doc.get('filename', 'unknown.pdf')
            file_path = pdf_doc.get('file_path', '')
            
            if os.path.exists(file_path):
                print(f"      Processing: {filename}")
                
                # Process with Azure DI
                result = await self.pdf_processor.process_pdf_with_azure_di(
                    file_path, 
                    crawler_results.get('payer', payer_key),
                    'provider_document'
                )
                
                processing_results.append({
                    "filename": filename,
                    "file_path": file_path,
                    "processing_result": result,
                    "success": result is not None
                })
                
                if result:
                    rules_count = len(result["structured_data"].get("healthcare_rules", []))
                    print(f"         ✅ {rules_count} rules extracted")
                else:
                    print(f"         ❌ Processing failed")
            else:
                print(f"      ❌ File not found: {file_path}")
        
        return processing_results
    
    async def _store_results(self, pdf_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Store processing results in PostgreSQL"""
        storage_results = []
        
        for pdf_result in pdf_results:
            if pdf_result["success"] and pdf_result["processing_result"]:
                document_id = await self.pdf_processor.store_in_postgres(
                    pdf_result["processing_result"]
                )
                
                storage_results.append({
                    "filename": pdf_result["filename"],
                    "document_id": document_id,
                    "success": document_id is not None
                })
                
                if document_id:
                    print(f"         💾 Stored as document_id: {document_id}")
                else:
                    print(f"         ❌ Storage failed")
        
        return storage_results
    
    def _find_all_pdfs(self, directory: str) -> List[str]:
        """Find all PDF files in directory structure"""
        pdf_patterns = [
            f"{directory}/**/*.pdf",
            f"{directory}/*.pdf"
        ]
        
        all_pdfs = []
        for pattern in pdf_patterns:
            all_pdfs.extend(glob.glob(pattern, recursive=True))
        
        return sorted(list(set(all_pdfs)))  # Remove duplicates and sort
    
    def _extract_metadata_from_path(self, pdf_path: str) -> tuple:
        """Extract payer name and document type from file path"""
        path_parts = pdf_path.split('/')
        
        # Try to identify payer from path
        payer_name = "Unknown Payer"
        doc_type = "provider_document"
        
        for part in path_parts:
            part_lower = part.lower()
            if 'countycare' in part_lower:
                payer_name = "CountyCare Health Plan"
            elif 'unitedhealthcare' in part_lower or 'uhc' in part_lower:
                payer_name = "United Healthcare"
            elif 'anthem' in part_lower:
                payer_name = "Anthem/Elevance Health"
            elif 'aetna' in part_lower:
                payer_name = "Aetna/CVS Health"
            elif 'cigna' in part_lower:
                payer_name = "Cigna Healthcare"
            
            # Document type detection
            if 'manual' in part_lower:
                doc_type = "provider_manual"
            elif 'prior' in part_lower and 'auth' in part_lower:
                doc_type = "prior_authorization"
            elif 'newsletter' in part_lower:
                doc_type = "newsletter"
            elif 'form' in part_lower:
                doc_type = "form"
        
        return payer_name, doc_type
    
    def _generate_processing_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary of processing results"""
        successful = [r for r in results if r.get('success', False)]
        failed = [r for r in results if not r.get('success', False)]
        
        total_rules = sum(r.get('rules_extracted', 0) for r in successful)
        total_pages = sum(r.get('pages_processed', 0) for r in successful)
        
        # Group by payer
        payers = {}
        for result in successful:
            payer = result.get('payer_name', 'Unknown')
            if payer not in payers:
                payers[payer] = {'documents': 0, 'rules': 0}
            payers[payer]['documents'] += 1
            payers[payer]['rules'] += result.get('rules_extracted', 0)
        
        return {
            "total_pdfs_found": len(results),
            "successful_processing": len(successful),
            "failed_processing": len(failed),
            "total_rules_extracted": total_rules,
            "total_pages_processed": total_pages,
            "payers_processed": payers,
            "processing_timestamp": datetime.now().isoformat()
        }
    
    def _generate_pipeline_summary(self, all_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary of complete pipeline"""
        successful_payers = 0
        total_pdfs = 0
        total_rules = 0
        documents_stored = 0
        
        for payer_result in all_results:
            if payer_result.get('storage_results'):
                successful_payers += 1
                
                # Count PDFs and rules
                processing_results = payer_result.get('processing_results', [])
                total_pdfs += len(processing_results)
                
                for proc_result in processing_results:
                    if proc_result.get('processing_result'):
                        rules = proc_result['processing_result']['structured_data'].get('healthcare_rules', [])
                        total_rules += len(rules)
                
                # Count stored documents
                storage_results = payer_result.get('storage_results', [])
                documents_stored += len([s for s in storage_results if s.get('success')])
        
        return {
            "successful_payers": successful_payers,
            "total_payers_attempted": len(all_results),
            "total_pdfs_processed": total_pdfs,
            "total_rules_extracted": total_rules,
            "documents_stored": documents_stored,
            "pipeline_completed_at": datetime.now().isoformat()
        }
    
    def _save_pipeline_results(self, results: List[Dict[str, Any]], summary: Dict[str, Any]):
        """Save pipeline results to JSON files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save detailed results
        results_file = f"pipeline_results_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump({
                "summary": summary,
                "detailed_results": results
            }, f, indent=2)
        
        print(f"\n💾 Pipeline results saved to: {results_file}")

async def main():
    """Main function to demonstrate the pipeline"""
    print("🏥 Healthcare Data Pipeline Demo")
    print("="*40)
    
    # Initialize pipeline
    pipeline = HealthcareDataPipeline()
    
    print("\n📋 Available operations:")
    print("1. Process existing PDFs")
    print("2. Run full pipeline (scrape + process + store)")
    print("3. Process CountyCare data only")
    
    # For demo, let's process existing PDFs
    print("\n🔄 Processing existing PDFs...")
    summary = await pipeline.process_existing_pdfs()
    
    print(f"\n📊 FINAL SUMMARY:")
    print(f"   PDFs found: {summary.get('total_pdfs_found', 0)}")
    print(f"   Successfully processed: {summary.get('successful_processing', 0)}")
    print(f"   Rules extracted: {summary.get('total_rules_extracted', 0)}")
    print(f"   Payers: {len(summary.get('payers_processed', {}))}")

if __name__ == "__main__":
    asyncio.run(main())