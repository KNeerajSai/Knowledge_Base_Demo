#!/usr/bin/env python3
"""
Quick Database Check - Show healthcare rules immediately
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

def quick_rules_check():
    """Quick check of healthcare rules"""
    try:
        conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST'),
            port=os.getenv('POSTGRES_PORT'),
            user=os.getenv('POSTGRES_USER'),
            password=os.getenv('POSTGRES_PASSWORD'),
            database=os.getenv('POSTGRES_DB'),
            cursor_factory=RealDictCursor
        )
        
        cur = conn.cursor()
        
        print("🏥 HEALTHCARE RULES IN DATABASE")
        print("=" * 40)
        
        # Get rule summary
        cur.execute("""
            SELECT 
                rule_type,
                COUNT(*) as count,
                AVG(confidence_score) as avg_confidence
            FROM healthcare_rules 
            GROUP BY rule_type
            ORDER BY count DESC;
        """)
        
        summary = cur.fetchall()
        print(f"📊 SUMMARY: {sum([s['count'] for s in summary])} total rules")
        for s in summary:
            print(f"   • {s['rule_type']}: {s['count']} rules (confidence: {s['avg_confidence']:.2f})")
        
        print("\n📜 DETAILED RULES:")
        print("-" * 40)
        
        # Get all rules
        cur.execute("""
            SELECT 
                rule_id, rule_type, rule_title, 
                LEFT(rule_content, 150) as content_preview,
                page_number, confidence_score
            FROM healthcare_rules 
            ORDER BY rule_type, rule_id;
        """)
        
        rules = cur.fetchall()
        
        for rule in rules:
            print(f"\n🔹 Rule #{rule['rule_id']} ({rule['rule_type']})")
            print(f"   Title: {rule['rule_title']}")
            print(f"   Page: {rule['page_number']} | Confidence: {rule['confidence_score']}")
            print(f"   Preview: {rule['content_preview']}...")
        
        # Show document info
        print("\n📄 DOCUMENTS PROCESSED:")
        print("-" * 25)
        
        cur.execute("""
            SELECT d.filename, p.name as payer, COUNT(hr.rule_id) as rules
            FROM documents d
            JOIN payers p ON d.payer_id = p.payer_id
            LEFT JOIN healthcare_rules hr ON d.document_id = hr.document_id
            GROUP BY d.filename, p.name;
        """)
        
        docs = cur.fetchall()
        for doc in docs:
            print(f"   📋 {doc['filename']} ({doc['payer']}) - {doc['rules']} rules")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Database error: {e}")

if __name__ == "__main__":
    quick_rules_check()