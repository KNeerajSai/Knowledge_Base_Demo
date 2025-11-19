#!/usr/bin/env python3
"""
Healthcare Payer Knowledge Base - PDF Processor and Database Loader
Data processor to parse downloaded PDFs and load their content into PostgreSQL database.

This script processes the downloaded PDFs, extracts text, chunks it into manageable pieces,
and loads the structured data into a PostgreSQL database for retrieval and analysis.

Author: Development Team
Date: November 2025
"""

import os
import fitz  # PyMuPDF
import psycopg2
from psycopg2 import sql
import logging
from datetime import datetime

# --- Configuration ---
# Configure logging.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Database connection parameters.
# IMPORTANT: Replace with your actual PostgreSQL credentials.
DB_CONFIG = {
    "dbname": "healthcare_knowledge_base",
    "user": "postgres",
    "password": "your_password",
    "host": "localhost",
    "port": "5432"
}

# Directory where the scraper downloads PDF files.
PDF_SOURCE_DIR = 'payer_manuals'

# --- Database Functions ---
def get_db_connection():
    """Establishes and returns a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        logging.info("Database connection established successfully.")
        return conn
    except psycopg2.OperationalError as e:
        logging.error(f"Could not connect to the database: {e}")
        logging.error("Please ensure PostgreSQL is running and the credentials in DB_CONFIG are correct.")
        return None

def setup_database_schema(conn):
    """
    Creates the required tables in the database if they don't already exist.
    This schema supports structured healthcare payer knowledge storage.
    """
    schema_queries = [
        """
        CREATE TABLE IF NOT EXISTS Source (
            source_id SERIAL PRIMARY KEY,
            name VARCHAR(255) UNIQUE NOT NULL,
            search_url TEXT,
            crawl_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS Document (
            document_id SERIAL PRIMARY KEY,
            source_id INTEGER REFERENCES Source(source_id),
            file_path VARCHAR(1024) UNIQUE NOT NULL,
            title VARCHAR(512),
            file_size BIGINT,
            page_count INTEGER,
            last_processed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processing_status VARCHAR(50) DEFAULT 'pending'
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS Chunk (
            chunk_id SERIAL PRIMARY KEY,
            document_id INTEGER REFERENCES Document(document_id),
            page_number INTEGER,
            chunk_index INTEGER,
            chunk_text TEXT NOT NULL,
            token_count INTEGER,
            content_type VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            -- The 'embedding_vector' would be added here for vector search.
            -- Example for pgVector: embedding_vector VECTOR(384)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS Rule_Category (
            category_id SERIAL PRIMARY KEY,
            category_name VARCHAR(255) UNIQUE NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS Extracted_Rule (
            rule_id SERIAL PRIMARY KEY,
            chunk_id INTEGER REFERENCES Chunk(chunk_id),
            category_id INTEGER REFERENCES Rule_Category(category_id),
            rule_text TEXT NOT NULL,
            rule_type VARCHAR(100),
            confidence_score DECIMAL(3,2),
            extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_chunk_document ON Chunk(document_id);
        CREATE INDEX IF NOT EXISTS idx_chunk_content_type ON Chunk(content_type);
        CREATE INDEX IF NOT EXISTS idx_rule_category ON Extracted_Rule(category_id);
        CREATE INDEX IF NOT EXISTS idx_document_source ON Document(source_id);
        """
    ]
    
    with conn.cursor() as cursor:
        logging.info("Setting up database schema...")
        for query in schema_queries:
            cursor.execute(query)
    conn.commit()
    logging.info("Database schema is ready.")

def insert_initial_categories(conn):
    """Insert initial rule categories if they don't exist."""
    categories = [
        ('Prior Authorization', 'Rules and requirements for prior authorization'),
        ('Timely Filing', 'Claim submission deadlines and requirements'),
        ('Appeals Process', 'Appeal procedures and timelines'),
        ('Claims Processing', 'General claims processing guidelines'),
        ('Provider Network', 'Provider credentialing and network requirements'),
        ('Coverage Guidelines', 'Medical coverage determination criteria'),
        ('Billing Requirements', 'Billing and coding requirements'),
        ('Member Benefits', 'Member benefit descriptions and limitations')
    ]
    
    with conn.cursor() as cursor:
        for name, description in categories:
            cursor.execute(
                "INSERT INTO Rule_Category (category_name, description) VALUES (%s, %s) ON CONFLICT (category_name) DO NOTHING;",
                (name, description)
            )
    conn.commit()
    logging.info("Rule categories initialized.")

def insert_data(conn, query, params):
    """
    Executes an INSERT query and returns the ID of the new row.

    Args:
        conn: The database connection object.
        query (str): The SQL INSERT statement.
        params (tuple): The parameters to substitute into the query.

    Returns:
        int: The primary key ID of the newly inserted record, or None on failure.
    """
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            conn.commit()
            return cursor.fetchone()[0]
    except (Exception, psycopg2.Error) as error:
        logging.error(f"Error inserting data: {error}")
        conn.rollback()
        return None

# --- PDF Processing Functions ---
def extract_text_from_pdf(file_path):
    """
    Extracts text from each page of a PDF file.

    Args:
        file_path (str): The path to the PDF file.

    Yields:
        tuple: A tuple containing the page number and the extracted text for that page.
    """
    try:
        doc = fitz.open(file_path)
        for page_num, page in enumerate(doc):
            yield (page_num + 1, page.get_text())
        doc.close()
    except Exception as e:
        logging.error(f"Could not process PDF {file_path}: {e}")

def get_pdf_metadata(file_path):
    """Extract metadata from PDF file."""
    try:
        doc = fitz.open(file_path)
        metadata = {
            'page_count': doc.page_count,
            'file_size': os.path.getsize(file_path)
        }
        doc.close()
        return metadata
    except Exception as e:
        logging.error(f"Could not extract metadata from PDF {file_path}: {e}")
        return {'page_count': 0, 'file_size': 0}

def chunk_text(text, chunk_size=500, overlap=50):
    """
    Splits text into smaller, overlapping chunks.

    Args:
        text (str): The text to be chunked.
        chunk_size (int): The target size of each chunk (in words).
        overlap (int): The number of words to overlap between chunks.

    Returns:
        list: A list of text chunks.
    """
    words = text.split()
    if not words:
        return []
    
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunks.append(" ".join(words[start:end]))
        start += chunk_size - overlap
    return chunks

def classify_content_type(text):
    """
    Basic content classification based on keywords.
    
    Args:
        text (str): Text to classify
        
    Returns:
        str: Content type classification
    """
    text_lower = text.lower()
    
    # Healthcare-specific content classification
    if any(keyword in text_lower for keyword in ['prior authorization', 'preauthorization', 'pre-auth']):
        return 'prior_authorization'
    elif any(keyword in text_lower for keyword in ['timely filing', 'filing deadline', 'submission deadline']):
        return 'timely_filing'
    elif any(keyword in text_lower for keyword in ['appeal', 'dispute', 'grievance']):
        return 'appeals'
    elif any(keyword in text_lower for keyword in ['billing', 'claim submission', 'coding']):
        return 'billing'
    elif any(keyword in text_lower for keyword in ['coverage', 'benefit', 'covered service']):
        return 'coverage'
    elif any(keyword in text_lower for keyword in ['provider', 'network', 'credentialing']):
        return 'provider_network'
    else:
        return 'general'

# --- Main Processing Logic ---
def process_payer_documents(conn, payer_name, payer_path):
    """Process all PDFs for a specific payer."""
    logging.info(f"--- Processing documents for {payer_name} ---")
    
    # 1. Insert or get the Source ID for the current payer.
    source_id = insert_data(
        conn,
        "INSERT INTO Source (name) VALUES (%s) ON CONFLICT (name) DO UPDATE SET last_updated=CURRENT_TIMESTAMP RETURNING source_id;",
        (payer_name,)
    )
    if not source_id:
        logging.error(f"Failed to insert/get source for {payer_name}")
        return
    
    pdf_count = 0
    # Iterate through each PDF in the payer's directory.
    for pdf_filename in os.listdir(payer_path):
        if pdf_filename.endswith('.pdf'):
            file_path = os.path.join(payer_path, pdf_filename)
            pdf_count += 1
            
            # Get PDF metadata
            metadata = get_pdf_metadata(file_path)
            
            # 2. Insert or get the Document ID for the current PDF.
            document_id = insert_data(
                conn,
                """INSERT INTO Document (source_id, file_path, title, file_size, page_count, processing_status) 
                   VALUES (%s, %s, %s, %s, %s, 'processing') 
                   ON CONFLICT (file_path) DO UPDATE SET 
                   last_processed=CURRENT_TIMESTAMP, processing_status='processing' 
                   RETURNING document_id;""",
                (source_id, file_path, pdf_filename.replace('.pdf', ''), 
                 metadata['file_size'], metadata['page_count'])
            )
            if not document_id:
                logging.error(f"Failed to insert document for {pdf_filename}")
                continue
            
            # 3. Process the PDF, chunk it, and insert chunks.
            logging.info(f"Processing and chunking: {pdf_filename}")
            chunk_count = 0
            
            try:
                for page_number, page_text in extract_text_from_pdf(file_path):
                    if page_text.strip():  # Only process pages with content
                        text_chunks = chunk_text(page_text)
                        
                        for chunk_index, chunk in enumerate(text_chunks):
                            if chunk.strip():  # Only insert non-empty chunks
                                token_count = len(chunk.split())
                                content_type = classify_content_type(chunk)
                                
                                insert_data(
                                    conn,
                                    """INSERT INTO Chunk (document_id, page_number, chunk_index, chunk_text, token_count, content_type) 
                                       VALUES (%s, %s, %s, %s, %s, %s) RETURNING chunk_id;""",
                                    (document_id, page_number, chunk_index, chunk, token_count, content_type)
                                )
                                chunk_count += 1
                
                # Update document status to completed
                with conn.cursor() as cursor:
                    cursor.execute(
                        "UPDATE Document SET processing_status='completed' WHERE document_id=%s;",
                        (document_id,)
                    )
                conn.commit()
                
                logging.info(f"Finished processing {pdf_filename}: {chunk_count} chunks inserted")
                
            except Exception as e:
                logging.error(f"Error processing {pdf_filename}: {e}")
                # Update document status to failed
                with conn.cursor() as cursor:
                    cursor.execute(
                        "UPDATE Document SET processing_status='failed' WHERE document_id=%s;",
                        (document_id,)
                    )
                conn.commit()
    
    logging.info(f"Completed processing {pdf_count} PDFs for {payer_name}")

def main():
    """Main function to process downloaded PDFs and load them into the database."""
    logging.info("Healthcare Payer Knowledge Base - PDF Processor")
    logging.info("=" * 60)
    
    conn = get_db_connection()
    if not conn:
        return

    setup_database_schema(conn)
    insert_initial_categories(conn)

    if not os.path.exists(PDF_SOURCE_DIR):
        logging.error(f"PDF source directory '{PDF_SOURCE_DIR}' does not exist. Please run scraper.py first.")
        conn.close()
        return

    # Iterate through each payer directory created by the scraper.
    total_payers = 0
    for payer_name in os.listdir(PDF_SOURCE_DIR):
        payer_path = os.path.join(PDF_SOURCE_DIR, payer_name)
        if os.path.isdir(payer_path):
            total_payers += 1
            process_payer_documents(conn, payer_name, payer_path)

    # Generate summary report
    with conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM Source;")
        source_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM Document WHERE processing_status='completed';")
        doc_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM Chunk;")
        chunk_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT content_type, COUNT(*) FROM Chunk GROUP BY content_type ORDER BY COUNT(*) DESC;")
        content_distribution = cursor.fetchall()

    logging.info("=" * 60)
    logging.info("DATABASE PROCESSING SUMMARY")
    logging.info("=" * 60)
    logging.info(f"Total payers processed: {source_count}")
    logging.info(f"Total documents processed: {doc_count}")
    logging.info(f"Total chunks created: {chunk_count}")
    logging.info("\nContent type distribution:")
    for content_type, count in content_distribution:
        logging.info(f"  {content_type}: {count} chunks")
    
    conn.close()
    logging.info("Database processing complete.")

if __name__ == "__main__":
    main()