#!/usr/bin/env python3
"""
View Healthcare Database - Complete Database Viewer
Shows schema, data, and extracted healthcare rules
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import json
from datetime import datetime

load_dotenv()

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(
        host=os.getenv('POSTGRES_HOST'),
        port=os.getenv('POSTGRES_PORT'),
        user=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASSWORD'),
        database=os.getenv('POSTGRES_DB'),
        cursor_factory=RealDictCursor
    )

def show_database_schema():
    """Show complete database schema"""
    print("📋 DATABASE SCHEMA")
    print("=" * 50)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get all tables
    cur.execute("""
        SELECT table_name, table_type
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """)
    tables = cur.fetchall()
    
    print(f"📊 Found {len(tables)} tables:")
    for table in tables:
        print(f"   • {table['table_name']} ({table['table_type']})")
    
    print("\n🔗 TABLE RELATIONSHIPS:")
    
    # Show foreign keys
    cur.execute("""
        SELECT 
            tc.table_name, 
            kcu.column_name, 
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name 
        FROM information_schema.table_constraints AS tc 
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
        WHERE constraint_type = 'FOREIGN KEY'
        ORDER BY tc.table_name;
    """)
    
    foreign_keys = cur.fetchall()
    for fk in foreign_keys:
        print(f"   {fk['table_name']}.{fk['column_name']} → {fk['foreign_table_name']}.{fk['foreign_column_name']}")
    
    cur.close()
    conn.close()

def show_table_structure(table_name):
    """Show detailed structure of a specific table"""
    print(f"\n📋 TABLE STRUCTURE: {table_name.upper()}")
    print("=" * 50)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get column information
    cur.execute("""
        SELECT 
            column_name,
            data_type,
            character_maximum_length,
            is_nullable,
            column_default
        FROM information_schema.columns 
        WHERE table_name = %s
        ORDER BY ordinal_position;
    """, (table_name,))
    
    columns = cur.fetchall()
    
    for col in columns:
        nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
        max_len = f"({col['character_maximum_length']})" if col['character_maximum_length'] else ""
        default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
        
        print(f"   {col['column_name']:<25} {col['data_type']}{max_len:<10} {nullable}{default}")
    
    cur.close()
    conn.close()

def show_healthcare_rules():
    """Show all extracted healthcare rules"""
    print("\n🏥 HEALTHCARE RULES EXTRACTED")
    print("=" * 50)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get all rules with document info
    cur.execute("""
        SELECT 
            hr.rule_id,
            hr.rule_type,
            hr.rule_title,
            hr.rule_content,
            hr.page_number,
            hr.confidence_score,
            d.filename,
            p.name as payer_name
        FROM healthcare_rules hr
        JOIN documents d ON hr.document_id = d.document_id
        JOIN payers p ON d.payer_id = p.payer_id
        ORDER BY hr.rule_type, hr.rule_id;
    """)
    
    rules = cur.fetchall()
    
    if not rules:
        print("❌ No healthcare rules found in database")
        return
    
    # Group by rule type
    rule_types = {}
    for rule in rules:
        rule_type = rule['rule_type']
        if rule_type not in rule_types:
            rule_types[rule_type] = []
        rule_types[rule_type].append(rule)
    
    for rule_type, type_rules in rule_types.items():
        print(f"\n📜 {rule_type.upper().replace('_', ' ')} RULES ({len(type_rules)} found):")
        print("-" * 40)
        
        for rule in type_rules:
            print(f"   Rule ID: {rule['rule_id']}")
            print(f"   Title: {rule['rule_title']}")
            print(f"   Source: {rule['payer_name']} - {rule['filename']}")
            print(f"   Page: {rule['page_number']}")
            print(f"   Confidence: {rule['confidence_score']}")
            print(f"   Content: {rule['rule_content'][:200]}...")
            print()
    
    cur.close()
    conn.close()

def show_documents_processed():
    """Show all processed documents"""
    print("\n📄 PROCESSED DOCUMENTS")
    print("=" * 50)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get documents with processing results
    cur.execute("""
        SELECT 
            d.document_id,
            d.filename,
            d.document_type,
            d.file_size_bytes,
            p.name as payer_name,
            dir.azure_model_used,
            dir.page_count,
            dir.processing_time_seconds,
            COUNT(hr.rule_id) as rules_extracted
        FROM documents d
        JOIN payers p ON d.payer_id = p.payer_id
        LEFT JOIN document_intelligence_results dir ON d.document_id = dir.document_id
        LEFT JOIN healthcare_rules hr ON d.document_id = hr.document_id
        GROUP BY d.document_id, d.filename, d.document_type, d.file_size_bytes, 
                 p.name, dir.azure_model_used, dir.page_count, dir.processing_time_seconds
        ORDER BY d.document_id;
    """)
    
    documents = cur.fetchall()
    
    for doc in documents:
        print(f"📋 Document ID: {doc['document_id']}")
        print(f"   File: {doc['filename']}")
        print(f"   Payer: {doc['payer_name']}")
        print(f"   Type: {doc['document_type']}")
        print(f"   Size: {doc['file_size_bytes']:,} bytes")
        print(f"   Processing: {doc['azure_model_used']} ({doc['page_count']} pages)")
        print(f"   Rules Extracted: {doc['rules_extracted']}")
        print()
    
    cur.close()
    conn.close()

def show_payers():
    """Show all payers in database"""
    print("\n🏢 HEALTHCARE PAYERS")
    print("=" * 50)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT 
            p.*,
            COUNT(d.document_id) as document_count,
            COUNT(hr.rule_id) as total_rules
        FROM payers p
        LEFT JOIN documents d ON p.payer_id = d.payer_id
        LEFT JOIN healthcare_rules hr ON d.document_id = hr.document_id
        GROUP BY p.payer_id, p.name, p.domain, p.provider_portal_url, 
                 p.market_share, p.priority, p.created_at, p.updated_at
        ORDER BY p.name;
    """)
    
    payers = cur.fetchall()
    
    for payer in payers:
        print(f"🏢 {payer['name']}")
        print(f"   Domain: {payer['domain']}")
        print(f"   Priority: {payer['priority']}")
        print(f"   Portal: {payer['provider_portal_url']}")
        print(f"   Documents: {payer['document_count']}")
        print(f"   Rules: {payer['total_rules']}")
        print()
    
    cur.close()
    conn.close()

def search_rules(search_term):
    """Search for specific terms in healthcare rules"""
    print(f"\n🔍 SEARCHING RULES FOR: '{search_term}'")
    print("=" * 50)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT 
            hr.rule_id,
            hr.rule_type,
            hr.rule_title,
            hr.rule_content,
            hr.page_number,
            d.filename,
            p.name as payer_name
        FROM healthcare_rules hr
        JOIN documents d ON hr.document_id = d.document_id
        JOIN payers p ON d.payer_id = p.payer_id
        WHERE hr.rule_content ILIKE %s 
           OR hr.rule_title ILIKE %s
           OR hr.rule_type ILIKE %s
        ORDER BY hr.confidence_score DESC;
    """, (f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"))
    
    results = cur.fetchall()
    
    if not results:
        print(f"❌ No rules found containing '{search_term}'")
        return
    
    print(f"✅ Found {len(results)} matching rules:")
    
    for result in results:
        print(f"\n📜 Rule ID: {result['rule_id']}")
        print(f"   Type: {result['rule_type']}")
        print(f"   Title: {result['rule_title']}")
        print(f"   Source: {result['payer_name']} - {result['filename']} (p. {result['page_number']})")
        print(f"   Content: {result['rule_content'][:300]}...")
    
    cur.close()
    conn.close()

def main():
    """Main menu"""
    print("🏥 Healthcare Database Viewer")
    print("=" * 35)
    
    while True:
        print("\nChoose an option:")
        print("1. View database schema")
        print("2. View table structure")
        print("3. Show healthcare rules")
        print("4. Show processed documents")
        print("5. Show payers")
        print("6. Search rules")
        print("7. Show everything")
        print("0. Exit")
        
        choice = input("\nEnter choice (0-7): ").strip()
        
        if choice == "0":
            break
        elif choice == "1":
            show_database_schema()
        elif choice == "2":
            table = input("Enter table name: ").strip()
            show_table_structure(table)
        elif choice == "3":
            show_healthcare_rules()
        elif choice == "4":
            show_documents_processed()
        elif choice == "5":
            show_payers()
        elif choice == "6":
            term = input("Enter search term: ").strip()
            search_rules(term)
        elif choice == "7":
            show_database_schema()
            show_payers()
            show_documents_processed()
            show_healthcare_rules()
        else:
            print("Invalid choice!")

if __name__ == "__main__":
    main()