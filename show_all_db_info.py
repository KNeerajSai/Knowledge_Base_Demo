#!/usr/bin/env python3
"""
Show All Database Information
Complete overview of healthcare database
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

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

def show_everything():
    """Show complete database overview"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    print("🏥 HEALTHCARE DATABASE COMPLETE OVERVIEW")
    print("=" * 60)
    
    # 1. Database Schema
    print("\n📋 DATABASE SCHEMA")
    print("=" * 25)
    
    cur.execute("""
        SELECT table_name, table_type
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """)
    tables = cur.fetchall()
    
    print(f"📊 Found {len(tables)} tables:")
    for table in tables:
        print(f"   • {table['table_name']:<30} ({table['table_type']})")
    
    # 2. Healthcare Tables Structure
    print("\n🏗️ HEALTHCARE TABLES STRUCTURE")
    print("=" * 40)
    
    healthcare_tables = ['payers', 'documents', 'document_intelligence_results', 'healthcare_rules']
    
    for table_name in healthcare_tables:
        print(f"\n📋 {table_name.upper()}:")
        
        cur.execute(f"SELECT COUNT(*) as count FROM {table_name};")
        count = cur.fetchone()['count']
        
        cur.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = %s
            ORDER BY ordinal_position;
        """, (table_name,))
        
        columns = cur.fetchall()
        print(f"   Rows: {count}")
        print(f"   Columns: {', '.join([col['column_name'] for col in columns[:5]])}...")
    
    # 3. Payers
    print("\n🏢 HEALTHCARE PAYERS")
    print("=" * 25)
    
    cur.execute("""
        SELECT 
            p.*,
            COUNT(d.document_id) as document_count,
            COUNT(hr.rule_id) as total_rules
        FROM payers p
        LEFT JOIN documents d ON p.payer_id = d.payer_id
        LEFT JOIN healthcare_rules hr ON d.document_id = hr.document_id
        GROUP BY p.payer_id
        ORDER BY p.name;
    """)
    
    payers = cur.fetchall()
    
    for payer in payers:
        print(f"\n🏢 {payer['name']}")
        print(f"   Domain: {payer['domain']}")
        print(f"   Priority: {payer['priority']}")
        print(f"   Documents: {payer['document_count']}")
        print(f"   Rules: {payer['total_rules']}")
    
    # 4. Documents
    print("\n📄 PROCESSED DOCUMENTS")
    print("=" * 30)
    
    cur.execute("""
        SELECT 
            d.document_id,
            d.filename,
            d.document_type,
            d.file_size_bytes,
            p.name as payer_name,
            dir.azure_model_used,
            dir.page_count,
            COUNT(hr.rule_id) as rules_extracted,
            d.created_at
        FROM documents d
        JOIN payers p ON d.payer_id = p.payer_id
        LEFT JOIN document_intelligence_results dir ON d.document_id = dir.document_id
        LEFT JOIN healthcare_rules hr ON d.document_id = hr.document_id
        GROUP BY d.document_id, d.filename, d.document_type, d.file_size_bytes, 
                 p.name, dir.azure_model_used, dir.page_count, d.created_at
        ORDER BY d.document_id;
    """)
    
    documents = cur.fetchall()
    
    for doc in documents:
        print(f"\n📋 Document #{doc['document_id']}: {doc['filename']}")
        print(f"   Payer: {doc['payer_name']}")
        print(f"   Type: {doc['document_type']}")
        print(f"   Size: {doc['file_size_bytes']:,} bytes")
        print(f"   Pages: {doc['page_count']}")
        print(f"   Processing: {doc['azure_model_used']}")
        print(f"   Rules Extracted: {doc['rules_extracted']}")
        print(f"   Added: {doc['created_at'].strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 5. Healthcare Rules (Detailed)
    print("\n🏥 HEALTHCARE RULES (DETAILED)")
    print("=" * 45)
    
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
    
    # Group by rule type
    rule_types = {}
    for rule in rules:
        rule_type = rule['rule_type']
        if rule_type not in rule_types:
            rule_types[rule_type] = []
        rule_types[rule_type].append(rule)
    
    for rule_type, type_rules in rule_types.items():
        print(f"\n📜 {rule_type.upper().replace('_', ' ')} RULES ({len(type_rules)} found):")
        print("-" * 50)
        
        for rule in type_rules:
            print(f"\n   🔹 Rule #{rule['rule_id']}")
            print(f"      Title: {rule['rule_title']}")
            print(f"      Source: {rule['payer_name']} - {rule['filename']}")
            print(f"      Page: {rule['page_number']} | Confidence: {rule['confidence_score']}")
            print(f"      Content: {rule['rule_content'][:200]}...")
    
    # 6. Database Statistics
    print("\n📊 DATABASE STATISTICS")
    print("=" * 30)
    
    # Get table sizes
    for table in healthcare_tables:
        cur.execute(f"SELECT COUNT(*) as count FROM {table};")
        count = cur.fetchone()['count']
        print(f"   {table:<30}: {count:>5} rows")
    
    # Get processing stats
    cur.execute("""
        SELECT 
            SUM(dir.page_count) as total_pages,
            AVG(dir.processing_time_seconds) as avg_processing_time,
            SUM(d.file_size_bytes) as total_file_size
        FROM documents d
        LEFT JOIN document_intelligence_results dir ON d.document_id = dir.document_id;
    """)
    
    stats = cur.fetchone()
    if stats['total_pages']:
        print(f"\n📈 Processing Statistics:")
        print(f"   Total Pages Processed: {stats['total_pages']}")
        print(f"   Average Processing Time: {stats['avg_processing_time']:.1f} seconds")
        print(f"   Total File Size: {stats['total_file_size']:,} bytes")
    
    # 7. Recent Activity
    print(f"\n⏰ RECENT ACTIVITY")
    print("=" * 20)
    
    cur.execute("""
        SELECT 
            'Document Added' as activity,
            d.filename as item,
            d.created_at as timestamp
        FROM documents d
        UNION ALL
        SELECT 
            'Rule Extracted' as activity,
            hr.rule_title as item,
            hr.created_at as timestamp
        FROM healthcare_rules hr
        ORDER BY timestamp DESC
        LIMIT 10;
    """)
    
    activities = cur.fetchall()
    
    for activity in activities:
        timestamp = activity['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        print(f"   {timestamp} - {activity['activity']}: {activity['item'][:50]}...")
    
    cur.close()
    conn.close()
    
    print(f"\n✅ Database overview complete!")

if __name__ == "__main__":
    show_everything()