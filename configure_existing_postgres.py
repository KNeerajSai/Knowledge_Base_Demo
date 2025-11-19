#!/usr/bin/env python3
"""
Configure Existing PostgreSQL for Healthcare Pipeline
Works with your existing PostgreSQL installation on port 5432
"""

import os
import sys
import getpass
import subprocess
from pathlib import Path

def get_postgres_credentials():
    """Get PostgreSQL credentials from user"""
    print("🔐 PostgreSQL Connection Setup")
    print("=" * 35)
    
    print("Using your existing PostgreSQL on localhost:5432")
    
    # Get credentials
    username = input(f"PostgreSQL username [{getpass.getuser()}]: ").strip()
    if not username:
        username = getpass.getuser()
    
    password = getpass.getpass(f"PostgreSQL password for {username}: ")
    
    # Database name for healthcare data
    db_name = input("Database name [healthcare_knowledge_base]: ").strip()
    if not db_name:
        db_name = "healthcare_knowledge_base"
    
    return {
        'host': 'localhost',
        'port': '5432',
        'username': username,
        'password': password,
        'database': db_name
    }

def test_postgres_connection(credentials):
    """Test PostgreSQL connection"""
    print(f"\n🔌 Testing PostgreSQL connection...")
    
    try:
        import psycopg2
    except ImportError:
        print("📦 Installing psycopg2-binary...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'psycopg2-binary'], check=True)
        import psycopg2
    
    try:
        # Test connection to postgres database first
        conn = psycopg2.connect(
            host=credentials['host'],
            port=credentials['port'],
            user=credentials['username'],
            password=credentials['password'],
            database='postgres'  # Connect to default database first
        )
        
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        
        print("✅ Connection successful!")
        print(f"   PostgreSQL version: {version.split(',')[0]}")
        
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\n💡 Please verify:")
        print(f"   • PostgreSQL is running on {credentials['host']}:{credentials['port']}")
        print(f"   • Username '{credentials['username']}' exists")
        print(f"   • Password is correct")
        return False

def create_healthcare_database(credentials):
    """Create healthcare database and schema"""
    print(f"\n🏥 Creating healthcare database...")
    
    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
        
        # Connect to postgres database to create new database
        conn = psycopg2.connect(
            host=credentials['host'],
            port=credentials['port'],
            user=credentials['username'],
            password=credentials['password'],
            database='postgres'
        )
        
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        # Create healthcare database
        try:
            cur.execute(f"CREATE DATABASE {credentials['database']};")
            print(f"✅ Database '{credentials['database']}' created")
        except psycopg2.errors.DuplicateDatabase:
            print(f"ℹ️  Database '{credentials['database']}' already exists")
        
        cur.close()
        conn.close()
        
        # Now connect to healthcare database and create schema
        return create_healthcare_schema(credentials)
        
    except Exception as e:
        print(f"❌ Database creation failed: {e}")
        return False

def create_healthcare_schema(credentials):
    """Create healthcare database schema"""
    print(f"🏗️  Creating healthcare database schema...")
    
    schema_sql = """
    -- Healthcare Payers table
    CREATE TABLE IF NOT EXISTS payers (
        payer_id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL UNIQUE,
        domain VARCHAR(255),
        provider_portal_url TEXT,
        market_share DECIMAL(5,2),
        priority VARCHAR(20),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Documents table
    CREATE TABLE IF NOT EXISTS documents (
        document_id SERIAL PRIMARY KEY,
        payer_id INTEGER REFERENCES payers(payer_id),
        filename VARCHAR(255) NOT NULL,
        file_path TEXT,
        file_size_bytes INTEGER,
        document_type VARCHAR(100), -- provider_manual, prior_auth, claims_guide
        original_url TEXT,
        downloaded_at TIMESTAMP,
        processed_at TIMESTAMP,
        azure_document_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Azure Document Intelligence Results
    CREATE TABLE IF NOT EXISTS document_intelligence_results (
        result_id SERIAL PRIMARY KEY,
        document_id INTEGER REFERENCES documents(document_id),
        azure_model_used VARCHAR(100),
        confidence_score DECIMAL(5,4),
        page_count INTEGER,
        processing_time_seconds DECIMAL(8,2),
        raw_response JSONB, -- Full Azure DI response
        structured_data JSONB, -- Our processed structure
        extraction_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Healthcare Rules extracted from documents
    CREATE TABLE IF NOT EXISTS healthcare_rules (
        rule_id SERIAL PRIMARY KEY,
        document_id INTEGER REFERENCES documents(document_id),
        rule_type VARCHAR(50), -- prior_authorization, timely_filing, appeals
        rule_title VARCHAR(500),
        rule_content TEXT,
        page_number INTEGER,
        confidence_score DECIMAL(5,4),
        geographic_scope VARCHAR(100), -- state, national, regional
        effective_date DATE,
        expiration_date DATE,
        extracted_entities JSONB, -- Named entities, dates, etc.
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Create indexes for performance
    CREATE INDEX IF NOT EXISTS idx_documents_payer_id ON documents(payer_id);
    CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(document_type);
    CREATE INDEX IF NOT EXISTS idx_rules_document_id ON healthcare_rules(document_id);
    CREATE INDEX IF NOT EXISTS idx_rules_type ON healthcare_rules(rule_type);
    CREATE INDEX IF NOT EXISTS idx_di_results_document_id ON document_intelligence_results(document_id);
    
    -- JSONB indexes for fast querying
    CREATE INDEX IF NOT EXISTS idx_di_structured_data_gin ON document_intelligence_results USING GIN (structured_data);
    CREATE INDEX IF NOT EXISTS idx_rules_entities_gin ON healthcare_rules USING GIN (extracted_entities);
    
    -- Insert sample payer data
    INSERT INTO payers (name, domain, provider_portal_url, priority) VALUES
    ('CountyCare Health Plan', 'countycare.com', 'https://countycare.com/providers/', 'medium'),
    ('United Healthcare', 'uhc.com', 'https://www.uhcprovider.com/', 'high'),
    ('Anthem/Elevance Health', 'anthem.com', 'https://providers.anthem.com/', 'high')
    ON CONFLICT (name) DO NOTHING;
    """
    
    try:
        import psycopg2
        
        conn = psycopg2.connect(
            host=credentials['host'],
            port=credentials['port'],
            user=credentials['username'],
            password=credentials['password'],
            database=credentials['database']
        )
        
        cur = conn.cursor()
        cur.execute(schema_sql)
        conn.commit()
        
        # Verify tables were created
        cur.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        tables = cur.fetchall()
        
        print("✅ Healthcare schema created successfully!")
        print("📋 Tables created:")
        for table in tables:
            print(f"   • {table[0]}")
        
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Schema creation failed: {e}")
        return False

def create_env_file(credentials):
    """Create .env file with PostgreSQL configuration"""
    print(f"\n📝 Creating environment configuration...")
    
    env_content = f"""# Healthcare Data Pipeline Environment Configuration

# PostgreSQL Database Configuration
POSTGRES_HOST={credentials['host']}
POSTGRES_PORT={credentials['port']}
POSTGRES_DB={credentials['database']}
POSTGRES_USER={credentials['username']}
POSTGRES_PASSWORD={credentials['password']}

# Azure Document Intelligence Configuration (add your credentials)
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://your-region.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_KEY=your-api-key-here

# Optional: Azure Model Configuration
AZURE_DI_MODEL=prebuilt-document
"""
    
    env_path = Path(".env")
    
    # Backup existing .env
    if env_path.exists():
        backup_path = Path(".env.backup")
        env_path.rename(backup_path)
        print(f"📋 Existing .env backed up to {backup_path}")
    
    with open(env_path, 'w') as f:
        f.write(env_content)
    
    print(f"✅ Environment file created: {env_path}")
    print(f"⚠️  Remember to add your Azure Document Intelligence credentials")

def test_full_connection(credentials):
    """Test complete connection to healthcare database"""
    print(f"\n🧪 Testing healthcare database connection...")
    
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(
            host=credentials['host'],
            port=credentials['port'],
            user=credentials['username'],
            password=credentials['password'],
            database=credentials['database']
        )
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Test data query
        cur.execute("SELECT name, priority FROM payers ORDER BY name;")
        payers = cur.fetchall()
        
        print("✅ Healthcare database test successful!")
        print(f"📊 Sample data found:")
        for payer in payers:
            print(f"   • {payer['name']} ({payer['priority']} priority)")
        
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Healthcare database test failed: {e}")
        return False

def install_dependencies():
    """Install required Python packages"""
    print(f"\n📦 Installing Python dependencies...")
    
    packages = [
        'psycopg2-binary',
        'sqlalchemy', 
        'python-dotenv'
    ]
    
    for package in packages:
        try:
            print(f"   Installing {package}...")
            subprocess.run([
                sys.executable, '-m', 'pip', 'install', package
            ], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            print(f"   ⚠️  Failed to install {package}")
    
    print("✅ Dependencies installation completed")

def main():
    """Main configuration function"""
    print("🏥 Configure Existing PostgreSQL for Healthcare Pipeline")
    print("=" * 60)
    
    # Step 1: Install dependencies
    install_dependencies()
    
    # Step 2: Get credentials
    credentials = get_postgres_credentials()
    
    # Step 3: Test connection
    if not test_postgres_connection(credentials):
        print("❌ Cannot proceed without working PostgreSQL connection")
        return
    
    # Step 4: Create healthcare database and schema
    if not create_healthcare_database(credentials):
        print("❌ Database setup failed")
        return
    
    # Step 5: Create environment file
    create_env_file(credentials)
    
    # Step 6: Final test
    if not test_full_connection(credentials):
        print("❌ Final test failed")
        return
    
    # Success!
    print(f"\n🎉 PostgreSQL Configuration Complete!")
    print("=" * 45)
    print("✅ Connected to existing PostgreSQL")
    print("✅ Healthcare database created")
    print("✅ Database schema initialized")
    print("✅ Sample data inserted")
    print("✅ Environment file configured")
    
    print(f"\n🚀 Ready for Healthcare Data Pipeline!")
    print(f"📋 Connection details:")
    print(f"   • Host: {credentials['host']}:{credentials['port']}")
    print(f"   • Database: {credentials['database']}")
    print(f"   • User: {credentials['username']}")
    
    print(f"\n📁 Next steps:")
    print(f"   1. Add Azure Document Intelligence credentials to .env")
    print(f"   2. Test the pipeline: python healthcare_data_pipeline.py")
    print(f"   3. Process existing PDFs with the full pipeline")

if __name__ == "__main__":
    main()