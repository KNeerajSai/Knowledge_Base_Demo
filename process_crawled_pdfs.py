#!/usr/bin/env python3
"""
Process Crawled PDFs - Healthcare Rule Extraction
Processes all downloaded PDFs and extracts healthcare rules
"""

import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
import PyPDF2
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class HealthcareRuleExtractor:
    def __init__(self):
        self.processed_files = []
        self.total_rules = 0
        
    def get_db_connection(self):
        """Get database connection"""
        return psycopg2.connect(
            host=os.getenv('POSTGRES_HOST'),
            port=os.getenv('POSTGRES_PORT'),
            user=os.getenv('POSTGRES_USER'),
            password=os.getenv('POSTGRES_PASSWORD'),
            database=os.getenv('POSTGRES_DB'),
            cursor_factory=RealDictCursor
        )
    
    def extract_pdf_text(self, pdf_path):
        """Extract text from PDF"""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                pages_text = []
                
                for page_num, page in enumerate(pdf_reader.pages, 1):
                    text = page.extract_text()
                    if text.strip():
                        pages_text.append({
                            'page': page_num,
                            'text': text.strip()
                        })
                
                return pages_text
                
        except Exception as e:
            print(f"❌ Error extracting PDF {pdf_path}: {e}")
            return None
    
    def extract_healthcare_rules(self, pages_text, company_name, filename):
        """Extract healthcare rules from PDF text"""
        rules = []
        
        # Healthcare rule patterns
        rule_patterns = {
            'prior_authorization': [
                'prior authorization', 'preauthorization', 'pre-authorization', 
                'prior auth', 'medical necessity', 'authorization required',
                'coverage determination', 'auth criteria', 'authorization list'
            ],
            'timely_filing': [
                'timely filing', 'claim submission deadline', 'filing requirement',
                'submission timeline', 'claim deadline', 'billing deadline',
                'filing limit', 'submission requirement'
            ],
            'appeals': [
                'appeal', 'grievance', 'dispute resolution', 'claim dispute',
                'appeal process', 'complaint process', 'member complaint',
                'appeal procedure', 'dispute procedure'
            ],
            'claims': [
                'claim submission', 'billing guideline', 'claims processing',
                'reimbursement', 'payment', 'billing procedure', 'claim procedure'
            ]
        }
        
        for page_data in pages_text:
            page_num = page_data['page']
            text = page_data['text'].lower()
            
            for rule_type, patterns in rule_patterns.items():
                for pattern in patterns:
                    if pattern in text:
                        # Extract context around the pattern
                        start_idx = text.find(pattern)
                        context_start = max(0, start_idx - 200)
                        context_end = min(len(text), start_idx + 300)
                        context = text[context_start:context_end]
                        
                        # Create rule
                        rule = {
                            'type': rule_type,
                            'title': f'{company_name} {rule_type.replace("_", " ").title()} Policy',
                            'content': context,
                            'page': page_num,
                            'confidence': 0.8,
                            'pattern_found': pattern,
                            'source_file': filename
                        }
                        
                        rules.append(rule)
                        break  # Only one rule per pattern per page
        
        return rules
    
    def store_in_database(self, pdf_path, company_name, pages_text, rules):
        """Store PDF data and rules in database"""
        try:
            conn = self.get_db_connection()
            cur = conn.cursor()
            
            # Get or ensure payer exists
            cur.execute("SELECT payer_id FROM payers WHERE name = %s", (company_name,))
            result = cur.fetchone()
            
            if not result:
                # Create payer
                cur.execute("""
                    INSERT INTO payers (name, domain, priority) 
                    VALUES (%s, %s, %s) 
                    RETURNING payer_id
                """, (company_name, f"{company_name.lower().replace(' ', '')}.com", "medium"))
                payer_id = cur.fetchone()['payer_id']
                print(f"✅ Created new payer: {company_name}")
            else:
                payer_id = result['payer_id']
            
            # Store document
            filename = os.path.basename(pdf_path)
            file_size = os.path.getsize(pdf_path)
            
            cur.execute("""
                INSERT INTO documents (payer_id, filename, file_path, file_size_bytes, 
                                     document_type, downloaded_at) 
                VALUES (%s, %s, %s, %s, %s, %s) 
                RETURNING document_id
            """, (payer_id, filename, pdf_path, file_size, "provider_manual", datetime.now()))
            
            document_id = cur.fetchone()['document_id']
            
            # Store Azure DI result (mock)
            structured_data = {
                "total_pages": len(pages_text),
                "extraction_method": "PyPDF2_Healthcare",
                "rules_extracted": len(rules),
                "processing_timestamp": datetime.now().isoformat(),
                "source_company": company_name
            }
            
            cur.execute("""
                INSERT INTO document_intelligence_results 
                (document_id, azure_model_used, page_count, processing_time_seconds,
                 raw_response, structured_data) 
                VALUES (%s, %s, %s, %s, %s, %s) 
                RETURNING result_id
            """, (document_id, "healthcare_pdf_extractor", len(pages_text), 5.0,
                  json.dumps({"method": "PyPDF2_Healthcare"}), json.dumps(structured_data)))
            
            result_id = cur.fetchone()['result_id']
            
            # Store healthcare rules
            rules_stored = 0
            for rule in rules:
                cur.execute("""
                    INSERT INTO healthcare_rules 
                    (document_id, rule_type, rule_title, rule_content, page_number, 
                     confidence_score, extracted_entities)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (document_id, rule['type'], rule['title'], rule['content'],
                      rule['page'], rule['confidence'], 
                      json.dumps({"pattern": rule['pattern_found'], "file": rule['source_file']})))
                rules_stored += 1
            
            conn.commit()
            
            print(f"✅ Stored {filename} in database:")
            print(f"   Document ID: {document_id}")
            print(f"   Pages: {len(pages_text)}")
            print(f"   Rules: {rules_stored}")
            
            cur.close()
            conn.close()
            
            return {
                'document_id': document_id,
                'pages': len(pages_text),
                'rules': rules_stored,
                'company': company_name,
                'filename': filename
            }
            
        except Exception as e:
            print(f"❌ Database error for {pdf_path}: {e}")
            return None
    
    def process_all_pdfs(self):
        """Process all downloaded PDFs"""
        print("🏥 Processing All Downloaded PDFs")
        print("=" * 40)
        
        # Map company directories to names
        company_mapping = {
            'united_healthcare': 'United Healthcare',
            'countycare': 'CountyCare Health Plan',
            'anthem': 'Anthem/Elevance Health',
            'aetna': 'Aetna'
        }
        
        for company_dir, company_name in company_mapping.items():
            pdf_dir = f"payer_pdfs/{company_dir}"
            
            if not os.path.exists(pdf_dir):
                continue
                
            print(f"\n📋 Processing {company_name}...")
            
            pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith('.pdf')]
            
            for pdf_file in pdf_files:
                pdf_path = os.path.join(pdf_dir, pdf_file)
                print(f"   📄 Processing: {pdf_file}")
                
                # Extract text
                pages_text = self.extract_pdf_text(pdf_path)
                if not pages_text:
                    continue
                
                # Extract rules
                rules = self.extract_healthcare_rules(pages_text, company_name, pdf_file)
                
                # Store in database
                result = self.store_in_database(pdf_path, company_name, pages_text, rules)
                
                if result:
                    self.processed_files.append(result)
                    self.total_rules += result['rules']
        
        return self.processed_files
    
    def generate_summary_report(self):
        """Generate processing summary"""
        print(f"\n📊 PROCESSING SUMMARY")
        print("=" * 30)
        print(f"Files Processed: {len(self.processed_files)}")
        print(f"Total Rules Extracted: {self.total_rules}")
        
        print(f"\n📋 Detailed Results:")
        for file_info in self.processed_files:
            print(f"   • {file_info['company']}: {file_info['filename']}")
            print(f"     Pages: {file_info['pages']}, Rules: {file_info['rules']}")
        
        return {
            'files_processed': len(self.processed_files),
            'total_rules': self.total_rules,
            'files': self.processed_files
        }

def main():
    """Main processing function"""
    print("🏥 Healthcare PDF Processing Pipeline")
    print("=" * 45)
    
    extractor = HealthcareRuleExtractor()
    
    # Process all PDFs
    processed_files = extractor.process_all_pdfs()
    
    # Generate summary
    summary = extractor.generate_summary_report()
    
    # Save processing log
    with open('pdf_processing_log.json', 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    
    print(f"\n✅ Processing completed!")
    print(f"📄 Log saved to: pdf_processing_log.json")
    
    return summary

if __name__ == "__main__":
    main()