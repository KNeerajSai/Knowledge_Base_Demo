#!/usr/bin/env python3
"""
Test PDF Processing Pipeline
Process CountyCare PDF and store in database
"""

import os
import psycopg2
from dotenv import load_dotenv
import PyPDF2
from datetime import datetime
import json

load_dotenv()

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(
        host=os.getenv('POSTGRES_HOST'),
        port=os.getenv('POSTGRES_PORT'),
        user=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASSWORD'),
        database=os.getenv('POSTGRES_DB')
    )

def extract_pdf_text(pdf_path):
    """Extract text from PDF using PyPDF2"""
    text_content = []
    
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            for page_num, page in enumerate(pdf_reader.pages, 1):
                text = page.extract_text()
                if text.strip():
                    text_content.append({
                        'page': page_num,
                        'text': text.strip()
                    })
    
    except Exception as e:
        print(f"❌ Error extracting PDF: {e}")
        return None
    
    return text_content

def store_in_database(pdf_path, text_content):
    """Store PDF data in database"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Get or create payer
        cur.execute("SELECT payer_id FROM payers WHERE name = %s", ("CountyCare Health Plan",))
        result = cur.fetchone()
        if result:
            payer_id = result[0]
        else:
            print("❌ CountyCare payer not found in database")
            return False
        
        # Get file info
        file_size = os.path.getsize(pdf_path)
        filename = os.path.basename(pdf_path)
        
        # Insert document
        cur.execute("""
            INSERT INTO documents (payer_id, filename, file_path, file_size_bytes, 
                                 document_type, downloaded_at) 
            VALUES (%s, %s, %s, %s, %s, %s) 
            RETURNING document_id
        """, (payer_id, filename, pdf_path, file_size, "provider_manual", datetime.now()))
        
        document_id = cur.fetchone()[0]
        
        # Create basic structured data
        structured_data = {
            "total_pages": len(text_content),
            "extracted_text_pages": text_content[:3],  # Store first 3 pages as sample
            "extraction_method": "PyPDF2",
            "processing_timestamp": datetime.now().isoformat()
        }
        
        # Store processing result (mock Azure DI result)
        cur.execute("""
            INSERT INTO document_intelligence_results 
            (document_id, azure_model_used, page_count, processing_time_seconds,
             raw_response, structured_data) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (document_id, "basic_pdf_extraction", len(text_content), 2.5, 
              json.dumps({"method": "PyPDF2"}), json.dumps(structured_data)))
        
        # Extract sample healthcare rules (basic keyword search)
        rules_found = 0
        for page_data in text_content:
            text = page_data['text'].lower()
            
            # Look for prior authorization mentions
            if 'prior authorization' in text or 'pre-authorization' in text:
                cur.execute("""
                    INSERT INTO healthcare_rules 
                    (document_id, rule_type, rule_title, rule_content, page_number, confidence_score)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (document_id, "prior_authorization", "Prior Authorization Requirement",
                      text[:500] + "...", page_data['page'], 0.8))
                rules_found += 1
            
            # Look for timely filing mentions  
            if 'timely filing' in text or 'filing deadline' in text:
                cur.execute("""
                    INSERT INTO healthcare_rules 
                    (document_id, rule_type, rule_title, rule_content, page_number, confidence_score)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (document_id, "timely_filing", "Timely Filing Requirement",
                      text[:500] + "...", page_data['page'], 0.8))
                rules_found += 1
        
        conn.commit()
        
        print(f"✅ Stored document in database:")
        print(f"   Document ID: {document_id}")
        print(f"   Pages processed: {len(text_content)}")
        print(f"   Healthcare rules found: {rules_found}")
        
        return True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        conn.rollback()
        return False
    
    finally:
        cur.close()
        conn.close()

def test_pipeline():
    """Test the complete pipeline"""
    print("🏥 Testing Healthcare PDF Processing Pipeline")
    print("=" * 50)
    
    pdf_path = "./payer_pdfs/countycare/mcomanual.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF not found: {pdf_path}")
        return
    
    print(f"📄 Processing: {pdf_path}")
    
    # Extract text
    text_content = extract_pdf_text(pdf_path)
    if not text_content:
        return
    
    print(f"✅ Extracted text from {len(text_content)} pages")
    
    # Store in database
    if store_in_database(pdf_path, text_content):
        print("✅ Pipeline test successful!")
    else:
        print("❌ Pipeline test failed!")

if __name__ == "__main__":
    test_pipeline()