# Healthcare Payer Knowledge Base - PostgreSQL Version Setup

## 📋 **Project Overview**

This PostgreSQL-integrated version provides a complete solution for scraping healthcare payer documents and loading them into a structured database for analysis and retrieval.

### **Components**

1. **`scraper.py`**: Configurable web scraper to find and download provider manuals
2. **`processor.py`**: Data processor to parse PDFs and load content into PostgreSQL database  
3. **Setup and instruction files**: Complete deployment guide

---

## 🔧 **Prerequisites**

### **1. Python 3.8+**
Ensure you have Python installed on your system.

### **2. PostgreSQL Database**
- Install PostgreSQL server (version 12+ recommended)
- Create a database for this project
- Note your connection credentials

### **3. System Dependencies**
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3-dev libpq-dev

# macOS (with Homebrew)
brew install postgresql libpq

# Windows
# Install PostgreSQL from https://www.postgresql.org/download/windows/
```

---

## ⚡ **Quick Setup**

### **Step 1: Create Database**
```sql
-- Connect to PostgreSQL as superuser
psql -U postgres

-- Create database and user
CREATE DATABASE healthcare_knowledge_base;
CREATE USER healthcare_user WITH PASSWORD 'secure_password_123';
GRANT ALL PRIVILEGES ON DATABASE healthcare_knowledge_base TO healthcare_user;

-- Exit psql
\q
```

### **Step 2: Install Python Dependencies**
```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install required libraries
pip install -r requirements_postgres.txt
```

### **Step 3: Configure Database Connection**
Edit `processor.py` and update the `DB_CONFIG` dictionary:

```python
DB_CONFIG = {
    "dbname": "healthcare_knowledge_base",
    "user": "healthcare_user", 
    "password": "secure_password_123",
    "host": "localhost",
    "port": "5432"
}
```

---

## 🚀 **How to Run**

### **Step 1: Run the Scraper**
Download PDF documents from healthcare payer websites:

```bash
python scraper.py
```

**What it does**:
- Creates `payer_manuals/` directory
- Downloads PDFs from 8 major healthcare payers
- Organizes files by payer name
- Logs progress and errors

**Expected output**:
```
payer_manuals/
├── UnitedHealthcare/
│   ├── provider_manual_2024.pdf
│   └── clinical_guidelines.pdf
├── Anthem/
│   ├── policy_manual.pdf
│   └── auth_guidelines.pdf
└── ...
```

### **Step 2: Run the Processor**
Parse PDFs and load into database:

```bash
python processor.py
```

**What it does**:
- Connects to PostgreSQL database
- Creates database schema (tables and indexes)
- Processes all downloaded PDFs
- Extracts text and creates searchable chunks
- Classifies content by healthcare category
- Generates processing summary

---

## 🗄️ **Database Schema**

The system creates the following tables:

### **Source Table**
Stores information about healthcare payers:
```sql
source_id (PK) | name | search_url | crawl_date | last_updated
```

### **Document Table**  
Tracks individual PDF files:
```sql
document_id (PK) | source_id (FK) | file_path | title | file_size | page_count | processing_status
```

### **Chunk Table**
Stores processed text chunks for search:
```sql
chunk_id (PK) | document_id (FK) | page_number | chunk_text | token_count | content_type
```

### **Rule_Category Table**
Healthcare rule categories:
```sql
category_id (PK) | category_name | description
```

### **Extracted_Rule Table**
Identified healthcare rules:
```sql
rule_id (PK) | chunk_id (FK) | category_id (FK) | rule_text | confidence_score
```

---

## 📊 **Sample Queries**

### **View Processing Summary**
```sql
SELECT 
    s.name as payer_name,
    COUNT(d.document_id) as document_count,
    COUNT(c.chunk_id) as chunk_count
FROM Source s
LEFT JOIN Document d ON s.source_id = d.source_id
LEFT JOIN Chunk c ON d.document_id = c.document_id
GROUP BY s.source_id, s.name
ORDER BY chunk_count DESC;
```

### **Search Content by Type**
```sql
SELECT 
    s.name as payer,
    d.title as document,
    c.page_number,
    c.chunk_text
FROM Chunk c
JOIN Document d ON c.document_id = d.document_id  
JOIN Source s ON d.source_id = s.source_id
WHERE c.content_type = 'prior_authorization'
LIMIT 10;
```

### **Find Prior Authorization Rules**
```sql
SELECT 
    s.name as payer,
    c.chunk_text
FROM Chunk c
JOIN Document d ON c.document_id = d.document_id
JOIN Source s ON d.source_id = s.source_id  
WHERE c.chunk_text ILIKE '%prior authorization%'
   OR c.chunk_text ILIKE '%preauthorization%'
ORDER BY s.name;
```

---

## 🔧 **Customization**

### **Add New Payers**
Edit the `PAYERS` list in `scraper.py`:

```python
PAYERS = [
    {
        'name': 'New_Payer_Name',
        'search_url': 'https://www.newpayer.com/provider-resources'
    },
    # ... existing payers
]
```

### **Adjust Chunking Parameters**
Modify `chunk_text()` function in `processor.py`:

```python
def chunk_text(text, chunk_size=500, overlap=50):
    # chunk_size: Target words per chunk
    # overlap: Overlapping words between chunks
```

### **Configure Content Classification**
Update `classify_content_type()` function to add new categories:

```python
def classify_content_type(text):
    text_lower = text.lower()
    
    if 'your_new_keyword' in text_lower:
        return 'your_new_category'
    # ... existing classifications
```

---

## 🚨 **Troubleshooting**

### **Database Connection Issues**
```bash
# Test PostgreSQL connection
psql -h localhost -U healthcare_user -d healthcare_knowledge_base

# Check if PostgreSQL is running
sudo systemctl status postgresql  # Linux
brew services list | grep postgresql  # macOS
```

### **PDF Processing Errors**
- **"Could not open PDF"**: File may be corrupted or password-protected
- **"No text extracted"**: PDF might be image-based (requires OCR)
- **Memory issues**: Reduce chunk size or process fewer files at once

### **Web Scraping Issues**
- **"No PDF links found"**: Site may use JavaScript (consider Selenium)
- **"Access denied"**: Site may be blocking automated requests
- **Timeout errors**: Increase timeout values in `scraper.py`

---

## 📈 **Next Steps**

### **Vector Search Integration**
Add pgvector extension for semantic search:

```sql
-- Install pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Add embedding column to Chunk table
ALTER TABLE Chunk ADD COLUMN embedding_vector vector(384);
```

### **API Development**
Create REST API using FastAPI:

```python
# api.py
from fastapi import FastAPI
import psycopg2

app = FastAPI()

@app.get("/search/{query}")
def search_content(query: str):
    # Query database and return results
    pass
```

### **Advanced Scraping**
For JavaScript-heavy sites, upgrade to Selenium:

```python
from selenium import webdriver
from selenium.webdriver.common.by import By

# Enhanced scraping with browser automation
```

---

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Healthcare Payer Knowledge Base - PostgreSQL Enterprise Version**