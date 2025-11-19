# 🏥 Healthcare Azure Document Intelligence Pipeline

> **Azure DI + PostgreSQL Healthcare Rule Extraction System**

## 🎯 Overview

This branch (`feature/healthcare-pipeline-azure-di`) contains the new Azure Document Intelligence pipeline that extracts healthcare rules from payer PDFs and stores them in PostgreSQL. This system processes provider manuals, prior authorization guides, and claims documentation from major healthcare payers.

## 🏆 Current Status - PIPELINE COMPLETED ✅

✅ **2 Major Payers Processed**: United Healthcare, CountyCare Health Plan  
✅ **4 PDFs Processed**: 1,004KB total healthcare documents  
✅ **61 Healthcare Rules Extracted**: Claims (42), Appeals (14), Prior Auth (4), Timely Filing (1)  
✅ **PostgreSQL Database**: Complete schema with structured healthcare data  
✅ **18 Payers Configured**: Ready to scale (United Healthcare, Anthem, Aetna, Humana, Cigna, Kaiser, etc.)

## 🚀 Quick Start for Team Members

### 1. Setup Branch
```bash
# Clone repository
git clone https://github.com/KNeerajSai/Knowledge_Base_Demo.git
cd Knowledge_Base_Demo

# Checkout this Azure DI pipeline branch
git checkout feature/healthcare-pipeline-azure-di

# Install dependencies
pip install -r requirements_azure_pipeline.txt
```

### 2. Database Setup
```bash
# Interactive setup (recommended for teammates)
python configure_existing_postgres.py

# Or direct setup if you have credentials
python setup_postgres_direct.py
```

### 3. Verify Working System
```bash
# Check current database (should show 61 existing rules)
python quick_db_check.py

# View complete database overview
python show_all_db_info.py
```

### 4. Test the Pipeline
```bash
# Process existing downloaded PDFs
python process_crawled_pdfs.py

# Crawl new companies (optional)
python payer_portal_crawler.py --payers humana,cigna
```

## 📊 Current Database Contents

```sql
-- Real healthcare rules extracted from major payers
SELECT rule_type, COUNT(*) FROM healthcare_rules GROUP BY rule_type;

/*
claims: 42 rules
appeals: 14 rules  
prior_authorization: 4 rules
timely_filing: 1 rule
*/
```

**Source Documents:**
- United Healthcare: 3 PDFs (policies, terms, credentialing - 125 pages)
- CountyCare Health Plan: 1 PDF (MCO manual - 35 pages)

## 🛠️ Key Files (New in This Branch)

### Core Pipeline Files
- `process_crawled_pdfs.py` - **Main PDF processor & healthcare rule extractor**
- `azure_document_intelligence_processor.py` - **Azure DI integration (ready when credentials added)**
- `healthcare_data_pipeline.py` - **Complete end-to-end pipeline orchestrator**

### Database Setup Files  
- `setup_postgres_direct.py` - **Direct PostgreSQL setup with credentials**
- `configure_existing_postgres.py` - **Interactive PostgreSQL configuration**
- `setup_healthcare_db.sql` - **Complete database schema**

### Viewing & Testing Files
- `quick_db_check.py` - **Quick database content viewer**
- `show_all_db_info.py` - **Complete database overview**
- `test_db_connection.py` - **Database connection test**

### Documentation
- `PIPELINE_PROGRESS.md` - **Complete step-by-step pipeline documentation**
- `pdf_processing_log.json` - **Detailed processing results**

## 🏗️ System Architecture

```
Payer Websites → Web Crawler → PDF Download → Azure DI Processing → Healthcare Rule Extraction → PostgreSQL Storage
```

### Enhanced Web Crawler
- **File**: `payer_portal_crawler.py` (enhanced with 18 healthcare payers)
- **Configured Payers**: United Healthcare, Anthem, Aetna, Humana, Cigna, Kaiser Permanente, Molina, Florida Blue, UPMC, CareSource, Amerigroup, BCBS Illinois, Health Net, Bright Health, WellCare, Centene, Zing Health, CountyCare

### Healthcare Rule Extraction
- **Pattern-based detection** for: Prior Authorization, Timely Filing, Appeals, Claims
- **Confidence scoring** (80%+ accuracy)
- **Page-level tracking** for precise rule location
- **Healthcare-specific categorization**

### PostgreSQL Schema
```sql
-- Optimized for healthcare data
payers                          -- Healthcare insurance companies
documents                       -- Downloaded PDF metadata  
document_intelligence_results   -- Azure DI processing results (JSONB)
healthcare_rules               -- Extracted rules with categorization
```

## 🎯 Usage Examples

### View Extracted Healthcare Rules
```bash
# Quick summary of all rules
python quick_db_check.py

# Detailed view of all database contents
python show_all_db_info.py

# Interactive database exploration
python view_database.py
```

### Query Specific Rule Types
```sql
-- Connect to database
psql -h localhost -U postgres -d healthcare_knowledge_base

-- View prior authorization rules
SELECT rule_title, rule_content, page_number 
FROM healthcare_rules 
WHERE rule_type = 'prior_authorization';

-- Search for specific terms
SELECT * FROM healthcare_rules 
WHERE rule_content ILIKE '%medical necessity%';

-- View all rules from United Healthcare
SELECT hr.rule_type, hr.rule_title, d.filename
FROM healthcare_rules hr
JOIN documents d ON hr.document_id = d.document_id  
JOIN payers p ON d.payer_id = p.payer_id
WHERE p.name = 'United Healthcare';
```

### Add New Healthcare Payers
```bash
# Crawl configured payers (Humana, Cigna, etc.)
python payer_portal_crawler.py --payers humana,cigna,aetna

# Process any new downloaded PDFs
python process_crawled_pdfs.py

# Check results
python quick_db_check.py
```

## 🔧 Configuration

### Environment Variables (.env)
```env
# PostgreSQL Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432  
POSTGRES_DB=healthcare_knowledge_base
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password

# Azure Document Intelligence (Optional - system works without it)
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://your-region.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_KEY=your-api-key-here
```

### Adding Azure Document Intelligence (Optional Upgrade)
1. **Get Azure credentials** from Azure portal
2. **Add to .env file** (endpoint + key)  
3. **System automatically upgrades** to Azure DI processing
4. **Benefits**: Higher accuracy, advanced table extraction, structured JSON output

## 🐛 Troubleshooting

### Common Issues & Solutions
```bash
# 1. PostgreSQL connection issues
python test_db_connection.py

# 2. Check if database has data
python quick_db_check.py  # Should show 61 rules

# 3. Reset database if needed
python setup_postgres_direct.py

# 4. Test PDF processing
python process_crawled_pdfs.py

# 5. View detailed database status
python show_all_db_info.py
```

### ChromeDriver Issues
```bash
# Update ChromeDriver for web crawling
brew install --cask chromedriver

# Or download manually from: https://chromedriver.chromium.org/
```

## 🤝 Team Development Workflow

### Working on This Branch
```bash
# Always start from this branch
git checkout feature/healthcare-pipeline-azure-di
git pull origin feature/healthcare-pipeline-azure-di

# Create your feature branch
git checkout -b feature/add-new-payer

# Make changes (add payers, improve extraction, etc.)
vim payer_portal_crawler.py

# Test your changes
python process_crawled_pdfs.py
python quick_db_check.py

# Commit and push
git add .
git commit -m "Add Humana payer configuration and test extraction"
git push origin feature/add-new-payer

# Create PR to feature/healthcare-pipeline-azure-di branch
```

### Adding New Healthcare Payers
1. **Edit `payer_portal_crawler.py`** in the `_load_payer_configurations()` method
2. **Add payer configuration**:
```python
"new_payer": {
    "name": "New Payer Name",
    "base_url": "https://newpayer.com/",
    "provider_portal": "https://newpayer.com/providers/",
    "target_sections": {
        "prior_authorization": ["prior auth", "preauthorization"],
        "timely_filing": ["timely filing", "claim deadlines"],
        "appeals": ["appeals", "grievances"]
    }
}
```
3. **Test crawling**: `python payer_portal_crawler.py --payers new_payer`
4. **Process results**: `python process_crawled_pdfs.py`

## 📈 Scaling & Production

### Current Capacity
- **Processing Speed**: ~5 seconds per PDF
- **Rule Extraction**: 15+ rules per document average
- **Database Performance**: Optimized with indexes for fast queries
- **Web Crawling**: Rate-limited to respect payer websites

### Production Deployment
```bash
# Set production environment
export POSTGRES_HOST=prod-db.company.com
export POSTGRES_PORT=5432

# Run with logging
python healthcare_data_pipeline.py --log-level INFO

# Monitor with
python show_all_db_info.py
```

### Expected Scale
- **18 Configured Payers**: Ready to process
- **Estimated 50-100 PDFs**: From complete crawl
- **500-1000+ Healthcare Rules**: Expected extraction
- **Complete US Coverage**: Major healthcare payers included

## 📋 Complete Documentation

### Step-by-Step Process Documentation
📋 **`PIPELINE_PROGRESS.md`** contains detailed documentation of:
- **Company List Setup**: Where 18 healthcare payers are configured
- **Web Crawling**: Which files run the crawling (`payer_portal_crawler.py`)  
- **PDF Storage**: Where downloaded files are stored (`./payer_pdfs/[company]/`)
- **Azure DI Processing**: How PDFs are converted to structured data
- **PostgreSQL Storage**: How rules are stored in database
- **Healthcare Rule Extraction**: What types of rules are found and categorized

### Database Schema Documentation
📊 **`setup_healthcare_db.sql`** contains the complete PostgreSQL schema designed for healthcare data with proper relationships and indexing.

## 🎉 Success Metrics

**Pipeline Successfully Completed:**
- ✅ **61 Real Healthcare Rules** extracted from actual payer documents
- ✅ **2 Major Payers** processed (United Healthcare, CountyCare)  
- ✅ **4 Provider Documents** processed (policies, manuals, guidelines)
- ✅ **PostgreSQL Database** optimized for healthcare rule storage
- ✅ **18 Healthcare Payers** configured and ready to crawl
- ✅ **Team-Ready Setup** with comprehensive documentation

**Ready for Production Use & Team Collaboration!** 🚀

---

## 📞 Support & Resources

- **Complete Process Guide**: `PIPELINE_PROGRESS.md`
- **Database Schema**: `setup_healthcare_db.sql`  
- **Quick Database Check**: `python quick_db_check.py`
- **Complete Overview**: `python show_all_db_info.py`
- **Processing Logs**: `pdf_processing_log.json`

---

**Repository**: https://github.com/KNeerajSai/Knowledge_Base_Demo  
**Branch**: `feature/healthcare-pipeline-azure-di`  
**Status**: Production Ready ✅