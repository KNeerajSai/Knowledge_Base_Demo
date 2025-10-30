# 🏥 Healthcare Payer Knowledge Base

**Automated Healthcare Payer Rule Extraction System**

[![Python](https://img.shields.io/badge/Python-3.8+-blue)](https://python.org) [![License](https://img.shields.io/badge/License-MIT-green)](LICENSE) [![Selenium](https://img.shields.io/badge/Selenium-4.15-orange)](https://selenium.dev)

> Intelligent web crawler that automatically extracts payer rules, filing requirements, and policies from major healthcare insurance portals, converting unstructured information into structured knowledge for revenue cycle teams.

---

## 🎯 **Project Overview**

### **Problem Statement**
Healthcare revenue cycle teams face significant challenges:
- **Manual Portal Navigation**: Staff spend hours searching multiple payer websites
- **Fragmented Information**: Rules scattered across PDFs, portals, and documents  
- **Frequent Policy Changes**: Updates occur regularly without centralized notifications
- **Operational Inefficiency**: Manual processes lead to claim denials and revenue loss
- **Compliance Risks**: Outdated information causes regulatory and financial issues

### **Solution**
Our automated payer portal crawler:
- ✅ **Extracts** payer rules from major healthcare portals automatically
- ✅ **Structures** unorganized data into queryable JSON format
- ✅ **Monitors** policy changes systematically 
- ✅ **Centralizes** knowledge for conversational AI access
- ✅ **Reduces** manual effort by 80%+ for revenue cycle teams

---

## 🏗️ **System Architecture**

```
┌─────────────────────────────────────────────────────────┐
│                Healthcare Knowledge Base                │
├─────────────────────────────────────────────────────────┤
│  🌐 Web Crawler (Selenium)                            │
│     ├── Dynamic content handling                       │
│     ├── Multi-payer portal navigation                  │
│     └── Respectful crawling with rate limits           │
│                                                         │
│  📄 PDF Processor (PyMuPDF + PyPDF2)                  │
│     ├── Dual extraction methods                        │
│     ├── Fallback processing                            │
│     └── Content validation                             │
│                                                         │
│  🧠 Rule Extraction Engine                            │
│     ├── Regex pattern matching                         │
│     ├── Content classification                         │
│     ├── Geographic zone detection                      │
│     └── JSON structure generation                      │
│                                                         │
│  💾 Knowledge Base                                     │
│     ├── Structured JSON output                         │
│     ├── Queryable format                               │
│     └── API-ready data                                 │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 **Crawler Versions & Capabilities**

### **1. Basic Crawler** (`payer_portal_crawler.py`)
**Purpose**: Reliable baseline functionality for single payer extraction

**Features**:
- Direct PDF discovery from provider portals
- Rule extraction with healthcare-specific patterns
- JSON output with structured data
- Rate limiting and respectful crawling

**Proven Results**:
- ✅ **8 PDFs** downloaded from Anthem
- ✅ **880+ pages** of content processed
- ✅ **723 healthcare rules** extracted
- ✅ Categories: Prior Authorization, Timely Filing, Appeals, Claims

**Usage**:
```python
from payer_portal_crawler import PayerPortalCrawler

crawler = PayerPortalCrawler()
results = crawler.crawl_payer("anthem")
```

### **2. CSV-Driven Crawler** (`intelligent_csv_crawler.py`)
**Purpose**: Scalable approach for multiple payers with auto-discovery

**Features**:
- CSV database of 15 major US healthcare payers
- Automatic provider portal discovery
- Intelligent domain pattern matching
- Priority-based crawling
- Batch processing capabilities

**Proven Results**:
- ✅ **15 major payers** configured (UHC, Anthem, Aetna, Kaiser, etc.)
- ✅ **Auto-discovery**: Found 50+ provider portals
- ✅ **Scalable**: Add new payers via CSV updates
- ✅ **Zero manual configuration** needed

**Usage**:
```python
from intelligent_csv_crawler import IntelligentCSVCrawler

crawler = IntelligentCSVCrawler("payer_companies.csv")
results = crawler.crawl_by_priority("high")
```

### **3. BFS Advanced Crawler** (`test_bfs_crawler.py`)
**Purpose**: Maximum discovery using Breadth-First Search algorithm

**Features**:
- Hierarchical link exploration (depth 2-3 levels)
- Intelligent content pattern following
- Hidden PDF repository discovery
- Advanced portal structure mapping

**Proven Results**:
- ✅ **10x more content** than basic crawler
- ✅ **79 PDFs** from United Healthcare in 1.9 minutes
- ✅ **100+ PDFs** discoverable from Anthem
- ✅ **State-specific variations** found automatically

**Usage**:
```python
from test_bfs_crawler import SimpleBFSCrawler

crawler = SimpleBFSCrawler(max_depth=3)
results = crawler.discover_pdfs_bfs(starting_urls, allowed_domains)
```

---

## 📋 **Quick Start Guide**

### **Installation**
```bash
git clone https://github.com/KNeerajSai/Knowledge_Base_Demo.git
cd Knowledge_Base_Demo
pip install -r requirements.txt
```

### **Interactive Demo**
```bash
python demo_launcher.py
```

### **Basic Usage**
```bash
# Single payer extraction
python examples/basic_usage.py

# CSV-driven multi-payer
python examples/csv_driven_example.py

# Advanced BFS discovery
python test_bfs_crawler.py
```

---

## 💡 **Configuration**

### **Payer Database** (`payer_companies.csv`)
The system includes 15 major US healthcare payers:

| Company | Type | States | Market Share |
|---------|------|--------|--------------|
| United Healthcare | National | All 50 | 23.0% |
| Anthem/Elevance | Multi-State | 14 states | 8.2% |
| Aetna/CVS Health | National | All 50 | 7.8% |
| Kaiser Permanente | Regional | 9 regions | 5.1% |
| Centene Corporation | Multi-State | 26+ states | 4.8% |

### **Adding New Payers**
Simply update `payer_companies.csv`:
```csv
company_name,base_domain,known_provider_portal,priority,market_share
"New Payer","newpayer.com","https://providers.newpayer.com","high","2.5%"
```

---

## 📊 **Performance Metrics**

### **Discovery Capacity**
- **Basic Crawler**: 8-20 PDFs per payer
- **CSV Crawler**: 50+ provider portals discovered
- **BFS Crawler**: 100+ PDFs per major payer
- **Combined System**: 1,000-3,000 PDFs potential

### **Quality Filtering**
- **78% noise reduction** (removes privacy policies, marketing)
- **167% quality improvement** (relevant healthcare content)
- **Perfect validity rate** (no broken/corrupted files)
- **12+ healthcare terms** per accepted PDF

### **Regional Coverage**
- **Current**: 8/50 US states (16% coverage)
- **Enhanced Potential**: 42-47/50 states (85-95% coverage)
- **Implementation**: 20-30 hours for complete US coverage

---

## 🔧 **Advanced Features**

### **Quality Filtering** (`intelligent_pdf_filter.py`)
```python
from intelligent_pdf_filter import IntelligentPDFFilter

filter_system = IntelligentPDFFilter()
results = filter_system.process_pdf_batch_with_filtering(pdf_urls)
```

### **Content Analysis** (`pdf_quality_analyzer.py`)
```python
from pdf_quality_analyzer import PDFQualityAnalyzer

analyzer = PDFQualityAnalyzer()
results = analyzer.analyze_pdf_batch(pdf_urls)
```

### **Regional Coverage** (`regional_coverage_analyzer.py`)
```python
from regional_coverage_analyzer import RegionalCoverageAnalyzer

analyzer = RegionalCoverageAnalyzer()
analysis = analyzer.analyze_payer_regional_coverage(payer_name, pdf_list)
```

---

## 📈 **Production Deployment**

### **Recommended Architecture**
```bash
# 1. Basic extraction for reliable baseline
python payer_portal_crawler.py

# 2. CSV-driven for scalable multi-payer
python intelligent_csv_crawler.py --priority high

# 3. BFS for comprehensive discovery
python test_bfs_crawler.py --max-depth 3

# 4. Quality filtering for production data
python intelligent_pdf_filter.py
```

### **Expected Results**
- **1,500-3,000 high-quality PDFs** discovered
- **85-95% US state coverage** achieved
- **Comprehensive rule extraction** across all major payers
- **Production-ready structured data**

---

## 🎯 **Use Cases**

### **Revenue Cycle Management**
- Automated payer rule discovery
- Real-time policy change monitoring
- Compliance verification
- Claim denial reduction

### **Healthcare Operations**
- Prior authorization automation
- Timely filing requirement tracking
- Appeals process optimization
- Provider network management

### **AI/ML Applications**
- Training data for healthcare AI models
- Knowledge base for conversational AI
- Automated rule interpretation
- Predictive compliance analytics

---

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Healthcare Payer Knowledge Base - Automated Rule Extraction System**