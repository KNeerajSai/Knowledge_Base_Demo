#!/usr/bin/env python3
"""
PostgreSQL Setup - No Password Authentication
Try connecting without password (peer authentication)
"""

import os
import sys
import subprocess

# PostgreSQL settings for local development (no password)
POSTGRES_CREDENTIALS = {
    'host': 'localhost',  # Try localhost first
    'port': '5432',
    'username': 'deepthikondaveeti',  # Your system user
    'database': 'healthcare_knowledge_base'
    # No password - will try peer authentication
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

def test_connection_methods():
    """Try different connection methods"""
    print("🔌 Testing PostgreSQL connection methods...")
    
    try:
        import psycopg2
    except ImportError:
        print("❌ psycopg2 not installed")
        return None
    
    # Method 1: No password, localhost
    print("\n   Method 1: No password, localhost")
    try:
        conn = psycopg2.connect(
            host=POSTGRES_CREDENTIALS['host'],
            port=POSTGRES_CREDENTIALS['port'],
            user=POSTGRES_CREDENTIALS['username'],
            database='postgres'
        )
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        print(f"   ✅ Success! Version: {version.split(',')[0]}")
        cur.close()
        conn.close()
        return 'localhost_no_password'
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    # Method 2: Unix socket (no host)
    print("\n   Method 2: Unix socket (no host)")
    try:
        conn = psycopg2.connect(
            user=POSTGRES_CREDENTIALS['username'],
            database='postgres'
        )
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        print(f"   ✅ Success! Version: {version.split(',')[0]}")
        cur.close()
        conn.close()
        POSTGRES_CREDENTIALS['connection_method'] = 'unix_socket'
        return 'unix_socket'
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    # Method 3: Try default postgres user with no password
    print("\n   Method 3: postgres user, no password")
    try:
        conn = psycopg2.connect(
            host=POSTGRES_CREDENTIALS['host'],
            port=POSTGRES_CREDENTIALS['port'],
            user='postgres',
            database='postgres'
        )
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        print(f"   ✅ Success! Version: {version.split(',')[0]}")
        cur.close()
        conn.close()
        POSTGRES_CREDENTIALS['username'] = 'postgres'
        return 'postgres_no_password'
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    print("\n❌ All connection methods failed")
    return None

def get_connection_params(method):
    """Get connection parameters based on working method"""
    if method == 'unix_socket':
        return {
            'user': POSTGRES_CREDENTIALS['username'],
            'database': POSTGRES_CREDENTIALS['database']
        }
    else:
        return {
            'host': POSTGRES_CREDENTIALS['host'],
            'port': POSTGRES_CREDENTIALS['port'],
            'user': POSTGRES_CREDENTIALS['username'],
            'database': POSTGRES_CREDENTIALS['database']
        }

def create_database_and_schema(connection_method):
    """Create healthcare database and schema"""
    print("🏗️  Creating healthcare database and schema...")
    
    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
        
        # Connect to postgres to create database
        if connection_method == 'unix_socket':
            conn = psycopg2.connect(
                user=POSTGRES_CREDENTIALS['username'],
                database='postgres'
            )
        else:
            conn = psycopg2.connect(
                host=POSTGRES_CREDENTIALS['host'],
                port=POSTGRES_CREDENTIALS['port'],
                user=POSTGRES_CREDENTIALS['username'],
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
        
        # Connect to healthcare database and create schema
        if connection_method == 'unix_socket':
            conn = psycopg2.connect(
                user=POSTGRES_CREDENTIALS['username'],
                database=POSTGRES_CREDENTIALS['database']
            )
        else:
            conn = psycopg2.connect(
                host=POSTGRES_CREDENTIALS['host'],
                port=POSTGRES_CREDENTIALS['port'],
                user=POSTGRES_CREDENTIALS['username'],
                database=POSTGRES_CREDENTIALS['database']
            )
        
        cur = conn.cursor()
        
        # Create healthcare schema
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

def create_env_file(connection_method):
    """Create .env file based on connection method"""
    print("📝 Creating .env file...")
    
    if connection_method == 'unix_socket':
        # For Unix socket connections, we don't specify host/port
        env_content = f'''# Healthcare Data Pipeline Environment Configuration

# PostgreSQL Database Configuration (Unix socket)
POSTGRES_DB={POSTGRES_CREDENTIALS['database']}
POSTGRES_USER={POSTGRES_CREDENTIALS['username']}
# No password needed for Unix socket connection

# Azure Document Intelligence Configuration (add your credentials)
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://your-region.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_KEY=your-api-key-here

# Optional: Azure Model Configuration
AZURE_DI_MODEL=prebuilt-document
'''
    else:
        env_content = f'''# Healthcare Data Pipeline Environment Configuration

# PostgreSQL Database Configuration (localhost)
POSTGRES_HOST={POSTGRES_CREDENTIALS['host']}
POSTGRES_PORT={POSTGRES_CREDENTIALS['port']}
POSTGRES_DB={POSTGRES_CREDENTIALS['database']}
POSTGRES_USER={POSTGRES_CREDENTIALS['username']}
# No password needed for peer authentication

# Azure Document Intelligence Configuration (add your credentials)
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://your-region.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_KEY=your-api-key-here

# Optional: Azure Model Configuration
AZURE_DI_MODEL=prebuilt-document
'''
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("✅ .env file created (no password authentication)")

def test_healthcare_database(connection_method):
    """Test healthcare database"""
    print("🧪 Testing healthcare database...")
    
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        if connection_method == 'unix_socket':
            conn = psycopg2.connect(
                user=POSTGRES_CREDENTIALS['username'],
                database=POSTGRES_CREDENTIALS['database']
            )
        else:
            conn = psycopg2.connect(
                host=POSTGRES_CREDENTIALS['host'],
                port=POSTGRES_CREDENTIALS['port'],
                user=POSTGRES_CREDENTIALS['username'],
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
    print("🏥 PostgreSQL Setup - No Password Authentication")
    print("=" * 55)
    print("💡 Trying peer authentication (no password required)")
    
    # Step 1: Install dependencies
    install_dependencies()
    
    # Step 2: Test connection methods
    connection_method = test_connection_methods()
    if not connection_method:
        print("\n❌ Could not establish PostgreSQL connection")
        print("💡 Possible solutions:")
        print("   1. Check if PostgreSQL is running: brew services start postgresql@15")
        print("   2. Try setting a password for your user")
        print("   3. Check PostgreSQL authentication config (pg_hba.conf)")
        return
    
    print(f"\n✅ Using connection method: {connection_method}")
    
    # Step 3: Create database and schema
    if not create_database_and_schema(connection_method):
        return
    
    # Step 4: Create .env file
    create_env_file(connection_method)
    
    # Step 5: Test healthcare database
    if not test_healthcare_database(connection_method):
        return
    
    print(f"\n🎉 PostgreSQL Setup Complete!")
    print("=" * 35)
    print("✅ PostgreSQL connected (no password)")
    print("✅ Healthcare database created")
    print("✅ Schema initialized")
    print("✅ .env file configured")
    
    print(f"\n🚀 Ready for Healthcare Data Pipeline!")
    print(f"📋 Connection details:")
    print(f"   • Method: {connection_method}")
    print(f"   • Database: {POSTGRES_CREDENTIALS['database']}")
    print(f"   • User: {POSTGRES_CREDENTIALS['username']}")
    
    print(f"\n📁 Next: python healthcare_data_pipeline.py")

if __name__ == "__main__":
    main()