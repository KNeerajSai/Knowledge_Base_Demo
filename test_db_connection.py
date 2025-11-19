#!/usr/bin/env python3
"""
Test PostgreSQL connection with correct credentials
"""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def test_connection():
    """Test database connection"""
    try:
        conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST'),
            port=os.getenv('POSTGRES_PORT'),
            user=os.getenv('POSTGRES_USER'),
            password=os.getenv('POSTGRES_PASSWORD'),
            database=os.getenv('POSTGRES_DB')
        )
        
        cur = conn.cursor()
        
        # Test tables exist
        cur.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        tables = [row[0] for row in cur.fetchall()]
        
        print("✅ Connected to healthcare_knowledge_base")
        print(f"📋 Tables: {', '.join(tables)}")
        
        # Test sample data
        cur.execute("SELECT name, priority FROM payers;")
        payers = cur.fetchall()
        
        print("📊 Sample payers:")
        for name, priority in payers:
            print(f"   • {name} ({priority})")
        
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing PostgreSQL Healthcare Database")
    print("=" * 45)
    test_connection()