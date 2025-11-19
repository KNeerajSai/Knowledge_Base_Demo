#!/usr/bin/env python3
"""
Direct PostgreSQL Setup
Edit the credentials below and run this script
"""

import os
import sys
import subprocess

# 🔧 EDIT THESE POSTGRESQL CREDENTIALS:
POSTGRES_CREDENTIALS = {
    'host': 'localhost',
    'port': '5432',
    'username': 'deepthikondaveeti',  # ← Your system user
    'password': 'Viral@2110',  # ← CHANGE THIS
    'database': 'healthcare_knowledge_base'
}

def install_dependencies():
    """Install required packages"""
    packages = ['psycopg2-binary', 'sqlalchemy', 'python-dotenv']
    
    for package in packages:
        try:
            print(f"Installing {package}...")
            subprocess.run([sys.executable, '-m', 'pip', 'install', package], 
                         check=True, capture_output=True)
        except:
            print(f"Warning: Could not install {package}")
    
    print("✅ Dependencies installed")

def test_connection():
    """Test PostgreSQL connection"""
    print("🔌 Testing PostgreSQL connection...")
    
    try:
        import psycopg2
        
        # Test connection
        conn = psycopg2.connect(
            host=POSTGRES_CREDENTIALS['host'],
            port=POSTGRES_CREDENTIALS['port'],
            user=POSTGRES_CREDENTIALS['username'],
            password=POSTGRES_CREDENTIALS['password'],
            database='postgres'  # Connect to default database
        )
        
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        
        print(f"✅ Connection successful!")
        print(f"   Version: {version.split(',')[0]}")
        
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print(f"\n💡 Please check:")
        print(f"   • Username: {POSTGRES_CREDENTIALS['username']}")
        print(f"   • Host: {POSTGRES_CREDENTIALS['host']}:{POSTGRES_CREDENTIALS['port']}")
        print(f"   • Password is correct")
        return False

def create_database_and_schema():
    """Create healthcare database and schema"""
    print("🏗️  Creating healthcare database and schema...")
    
    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
        
        # Connect to postgres to create database
        conn = psycopg2.connect(
            host=POSTGRES_CREDENTIALS['host'],
            port=POSTGRES_CREDENTIALS['port'],
            user=POSTGRES_CREDENTIALS['username'],
            password=POSTGRES_CREDENTIALS['password'],
            database='postgres'
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        cur = conn.cursor()
        
        # Create database
        try:
            cur.execute(f"CREATE DATABASE {POSTGRES_CREDENTIALS['database']};")
            print(f"✅ Database created: {POSTGRES_CREDENTIALS['database']}")
        except psycopg2.errors.DuplicateDatabase:
            print(f"ℹ️  Database already exists: {POSTGRES_CREDENTIALS['database']}")
        
        cur.close()
        conn.close()
        
        # Now create schema in healthcare database
        conn = psycopg2.connect(
            host=POSTGRES_CREDENTIALS['host'],
            port=POSTGRES_CREDENTIALS['port'],
            user=POSTGRES_CREDENTIALS['username'],
            password=POSTGRES_CREDENTIALS['password'],
            database=POSTGRES_CREDENTIALS['database']
        )
        
        cur = conn.cursor()
        
        # Create tables
        schema_sql = '''
        CREATE TABLE IF NOT EXISTS payers (
            payer_id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL UNIQUE,
            domain VARCHAR(255),
            provider_portal_url TEXT,
            market_share DECIMAL(5,2),
            priority VARCHAR(20),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS documents (
            document_id SERIAL PRIMARY KEY,
            payer_id INTEGER REFERENCES payers(payer_id),
            filename VARCHAR(255) NOT NULL,
            file_path TEXT,
            file_size_bytes INTEGER,
            document_type VARCHAR(100),
            processed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS document_intelligence_results (
            result_id SERIAL PRIMARY KEY,
            document_id INTEGER REFERENCES documents(document_id),
            azure_model_used VARCHAR(100),
            confidence_score DECIMAL(5,4),
            page_count INTEGER,
            processing_time_seconds DECIMAL(8,2),
            raw_response JSONB,
            structured_data JSONB,
            extraction_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS healthcare_rules (
            rule_id SERIAL PRIMARY KEY,
            document_id INTEGER REFERENCES documents(document_id),
            rule_type VARCHAR(50),
            rule_content TEXT,
            page_number INTEGER,
            confidence_score DECIMAL(5,4),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Insert sample payers
        INSERT INTO payers (name, domain, priority) VALUES
        ('CountyCare Health Plan', 'countycare.com', 'medium'),
        ('United Healthcare', 'uhc.com', 'high'),
        ('Anthem/Elevance Health', 'anthem.com', 'high')
        ON CONFLICT (name) DO NOTHING;
        '''
        
        cur.execute(schema_sql)
        conn.commit()
        
        # Verify
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
        tables = [row[0] for row in cur.fetchall()]
        
        print(f"✅ Schema created successfully!")
        print(f"📋 Tables: {', '.join(tables)}")
        
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database/schema creation failed: {e}")
        return False

def create_env_file():
    """Create .env file"""
    print("📝 Creating .env file...")
    
    env_content = f'''# Healthcare Data Pipeline Environment Configuration

# PostgreSQL Database Configuration
POSTGRES_HOST={POSTGRES_CREDENTIALS['host']}
POSTGRES_PORT={POSTGRES_CREDENTIALS['port']}
POSTGRES_DB={POSTGRES_CREDENTIALS['database']}
POSTGRES_USER={POSTGRES_CREDENTIALS['username']}
POSTGRES_PASSWORD={POSTGRES_CREDENTIALS['password']}

# Azure Document Intelligence Configuration (add your credentials)
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://your-region.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_KEY=your-api-key-here

# Optional: Azure Model Configuration
AZURE_DI_MODEL=prebuilt-document
'''
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("✅ .env file created")

def test_healthcare_database():
    """Test healthcare database"""
    print("🧪 Testing healthcare database...")
    
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(
            host=POSTGRES_CREDENTIALS['host'],
            port=POSTGRES_CREDENTIALS['port'],
            user=POSTGRES_CREDENTIALS['username'],
            password=POSTGRES_CREDENTIALS['password'],
            database=POSTGRES_CREDENTIALS['database']
        )
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT name, priority FROM payers;")
        payers = cur.fetchall()
        
        print("✅ Healthcare database test successful!")
        print("📊 Sample payers:")
        for payer in payers:
            print(f"   • {payer['name']} ({payer['priority']})")
        
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Healthcare database test failed: {e}")
        return False

def main():
    """Main function"""
    print("🏥 Direct PostgreSQL Setup for Healthcare Pipeline")
    print("=" * 55)
    
    # Check credentials are set
    if POSTGRES_CREDENTIALS['username'] == 'your_postgres_username':
        print("❌ Please edit POSTGRES_CREDENTIALS in this file first!")
        print("   Set your PostgreSQL username and password")
        return
    
    print(f"📊 Using PostgreSQL credentials:")
    print(f"   Host: {POSTGRES_CREDENTIALS['host']}:{POSTGRES_CREDENTIALS['port']}")
    print(f"   User: {POSTGRES_CREDENTIALS['username']}")
    print(f"   Database: {POSTGRES_CREDENTIALS['database']}")
    
    # Step 1: Install dependencies
    install_dependencies()
    
    # Step 2: Test connection
    if not test_connection():
        return
    
    # Step 3: Create database and schema
    if not create_database_and_schema():
        return
    
    # Step 4: Create .env file
    create_env_file()
    
    # Step 5: Test healthcare database
    if not test_healthcare_database():
        return
    
    print(f"\n🎉 PostgreSQL Setup Complete!")
    print("=" * 35)
    print("✅ PostgreSQL connected")
    print("✅ Healthcare database created")
    print("✅ Schema initialized")
    print("✅ .env file configured")
    
    print(f"\n🚀 Ready for Healthcare Data Pipeline!")
    print(f"   Next: python healthcare_data_pipeline.py")

if __name__ == "__main__":
    main()