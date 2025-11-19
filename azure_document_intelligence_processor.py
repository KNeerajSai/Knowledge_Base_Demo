#!/usr/bin/env python3
"""
Azure Document Intelligence Processor
Convert scraped PDFs to structured JSON using Azure Document Intelligence
Replace basic PDF processors with AI-powered extraction
"""

import os
import json
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import logging

# Azure Document Intelligence
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from azure.core.credentials import AzureKeyCredential

# Database
import psycopg2
from psycopg2.extras import RealDictCursor, Json
import sqlalchemy
from sqlalchemy import create_engine, text

# Configuration
from dataclasses import dataclass

@dataclass
class AzureConfig:
    """Azure Document Intelligence Configuration"""
    endpoint: str = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT", "")
    api_key: str = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY", "")
    model_id: str = "prebuilt-document"  # or "prebuilt-layout" for more structure

@dataclass 
class PostgreSQLConfig:
    """PostgreSQL Database Configuration"""
    host: str = os.getenv("POSTGRES_HOST", "localhost")
    port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    database: str = os.getenv("POSTGRES_DB", "healthcare_knowledge_base")
    username: str = os.getenv("POSTGRES_USER", "postgres")
    password: str = os.getenv("POSTGRES_PASSWORD", "password")

class HealthcarePDFProcessor:
    """
    Azure Document Intelligence processor for healthcare payer documents
    Extracts structured data from PDFs and stores in PostgreSQL
    """
    
    def __init__(self, azure_config: AzureConfig, pg_config: PostgreSQLConfig):
        self.azure_config = azure_config
        self.pg_config = pg_config
        self.logger = self._setup_logging()
        
        # Initialize Azure Document Intelligence client
        if azure_config.endpoint and azure_config.api_key:
            self.doc_client = DocumentIntelligenceClient(
                endpoint=azure_config.endpoint,
                credential=AzureKeyCredential(azure_config.api_key)
            )
        else:
            self.doc_client = None
            self.logger.warning("Azure credentials not provided - running in demo mode")
        
        # Initialize PostgreSQL connection
        self.pg_engine = None
        self._setup_database()
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)
    
    def _setup_database(self):
        """Setup PostgreSQL database connection and schema"""
        try:
            connection_string = (
                f"postgresql://{self.pg_config.username}:{self.pg_config.password}@"
                f"{self.pg_config.host}:{self.pg_config.port}/{self.pg_config.database}"
            )
            self.pg_engine = create_engine(connection_string)
            
            # Test connection
            with self.pg_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            self.logger.info("PostgreSQL connection established")
            self._create_schema()
            
        except Exception as e:
            self.logger.error(f"Database connection failed: {e}")
            self.pg_engine = None
    
    def _create_schema(self):
        """Create database schema for healthcare payer data"""
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
        """
        
        try:
            with self.pg_engine.connect() as conn:
                conn.execute(text(schema_sql))
                conn.commit()
            self.logger.info("Database schema created/updated successfully")
        except Exception as e:
            self.logger.error(f"Schema creation failed: {e}")
    
    async def process_pdf_with_azure_di(self, pdf_path: str, payer_name: str, document_type: str = "provider_manual") -> Optional[Dict[str, Any]]:
        """
        Process PDF with Azure Document Intelligence
        
        Args:
            pdf_path: Path to PDF file
            payer_name: Name of healthcare payer
            document_type: Type of document (provider_manual, prior_auth, etc.)
            
        Returns:
            Structured data dictionary or None if failed
        """
        if not self.doc_client:
            self.logger.warning("Azure Document Intelligence not configured - using mock data")
            return self._create_mock_response(pdf_path, payer_name, document_type)
        
        try:
            self.logger.info(f"Processing {pdf_path} with Azure Document Intelligence")
            start_time = datetime.now()
            
            # Read PDF file
            with open(pdf_path, "rb") as pdf_file:
                pdf_content = pdf_file.read()
            
            # Analyze document with Azure DI
            poller = self.doc_client.begin_analyze_document(
                model_id=self.azure_config.model_id,
                analyze_request=AnalyzeDocumentRequest(bytes_source=pdf_content)
            )
            
            result = poller.result()
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Extract structured data
            structured_data = self._extract_healthcare_data(result, payer_name, document_type)
            structured_data["processing_metadata"] = {
                "processing_time_seconds": processing_time,
                "azure_model": self.azure_config.model_id,
                "page_count": len(result.pages) if result.pages else 0,
                "confidence_score": self._calculate_confidence_score(result)
            }
            
            self.logger.info(f"Successfully processed {pdf_path} in {processing_time:.2f} seconds")
            return {
                "structured_data": structured_data,
                "raw_azure_response": self._serialize_azure_response(result),
                "metadata": {
                    "file_path": pdf_path,
                    "payer_name": payer_name,
                    "document_type": document_type,
                    "processing_time": processing_time
                }
            }
            
        except Exception as e:
            self.logger.error(f"Azure DI processing failed for {pdf_path}: {e}")
            return None
    
    def _extract_healthcare_data(self, azure_result: Any, payer_name: str, document_type: str) -> Dict[str, Any]:
        """
        Extract healthcare-specific structured data from Azure DI results
        """
        structured_data = {
            "payer_name": payer_name,
            "document_type": document_type,
            "extracted_at": datetime.now().isoformat(),
            "sections": [],
            "healthcare_rules": [],
            "key_value_pairs": [],
            "tables": [],
            "entities": []
        }
        
        # Extract text content by pages
        if azure_result.pages:
            for page_num, page in enumerate(azure_result.pages, 1):
                page_data = {
                    "page_number": page_num,
                    "content": "",
                    "tables": [],
                    "key_values": []
                }
                
                # Extract lines and words
                if page.lines:
                    page_content = "\n".join([line.content for line in page.lines])
                    page_data["content"] = page_content
                    
                    # Look for healthcare-specific patterns
                    healthcare_rules = self._extract_healthcare_rules_from_text(page_content, page_num)
                    structured_data["healthcare_rules"].extend(healthcare_rules)
                
                # Extract tables
                if hasattr(page, 'tables') and page.tables:
                    for table in page.tables:
                        table_data = self._extract_table_data(table, page_num)
                        page_data["tables"].append(table_data)
                
                structured_data["sections"].append(page_data)
        
        # Extract key-value pairs
        if hasattr(azure_result, 'key_value_pairs') and azure_result.key_value_pairs:
            for kv_pair in azure_result.key_value_pairs:
                structured_data["key_value_pairs"].append({
                    "key": kv_pair.key.content if kv_pair.key else "",
                    "value": kv_pair.value.content if kv_pair.value else "",
                    "confidence": kv_pair.confidence if hasattr(kv_pair, 'confidence') else 0.0
                })
        
        # Extract entities (if available)
        if hasattr(azure_result, 'entities') and azure_result.entities:
            for entity in azure_result.entities:
                structured_data["entities"].append({
                    "type": entity.category if hasattr(entity, 'category') else "unknown",
                    "content": entity.content,
                    "confidence": entity.confidence if hasattr(entity, 'confidence') else 0.0
                })
        
        return structured_data
    
    def _extract_healthcare_rules_from_text(self, text: str, page_number: int) -> List[Dict[str, Any]]:
        """
        Extract healthcare-specific rules from text using pattern matching
        """
        rules = []
        text_lower = text.lower()
        
        # Healthcare rule patterns
        patterns = {
            "prior_authorization": [
                r"prior authorization.*?(?=\n\n|\n[A-Z]|\.|$)",
                r"preauthorization.*?(?=\n\n|\n[A-Z]|\.|$)",
                r"authorization.*?required.*?(?=\n\n|\n[A-Z]|\.|$)"
            ],
            "timely_filing": [
                r"timely filing.*?(?=\n\n|\n[A-Z]|\.|$)",
                r"filing.*?deadline.*?(?=\n\n|\n[A-Z]|\.|$)",
                r"submit.*?within.*?days.*?(?=\n\n|\n[A-Z]|\.|$)"
            ],
            "appeals": [
                r"appeal.*?process.*?(?=\n\n|\n[A-Z]|\.|$)",
                r"grievance.*?(?=\n\n|\n[A-Z]|\.|$)",
                r"dispute.*?resolution.*?(?=\n\n|\n[A-Z]|\.|$)"
            ],
            "claims": [
                r"claim.*?submission.*?(?=\n\n|\n[A-Z]|\.|$)",
                r"billing.*?requirements.*?(?=\n\n|\n[A-Z]|\.|$)",
                r"reimbursement.*?(?=\n\n|\n[A-Z]|\.|$)"
            ]
        }
        
        import re
        for rule_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    rule_content = match.group().strip()
                    if len(rule_content) > 20:  # Filter out very short matches
                        rules.append({
                            "type": rule_type,
                            "content": rule_content,
                            "page_number": page_number,
                            "confidence_score": min(len(rule_content) / 200, 1.0)  # Simple confidence based on length
                        })
        
        return rules
    
    def _extract_table_data(self, table: Any, page_number: int) -> Dict[str, Any]:
        """Extract table data from Azure DI table object"""
        table_data = {
            "page_number": page_number,
            "row_count": table.row_count if hasattr(table, 'row_count') else 0,
            "column_count": table.column_count if hasattr(table, 'column_count') else 0,
            "cells": []
        }
        
        if hasattr(table, 'cells') and table.cells:
            for cell in table.cells:
                table_data["cells"].append({
                    "row_index": cell.row_index if hasattr(cell, 'row_index') else 0,
                    "column_index": cell.column_index if hasattr(cell, 'column_index') else 0,
                    "content": cell.content,
                    "is_header": getattr(cell, 'is_header', False)
                })
        
        return table_data
    
    def _calculate_confidence_score(self, azure_result: Any) -> float:
        """Calculate overall confidence score from Azure DI results"""
        # Simple confidence calculation based on available data
        confidence_scores = []
        
        if hasattr(azure_result, 'pages') and azure_result.pages:
            for page in azure_result.pages:
                if hasattr(page, 'lines') and page.lines:
                    for line in page.lines:
                        if hasattr(line, 'confidence'):
                            confidence_scores.append(line.confidence)
        
        return sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.8
    
    def _serialize_azure_response(self, azure_result: Any) -> Dict[str, Any]:
        """Convert Azure DI response to JSON-serializable format"""
        # Simplified serialization - in production you'd want more complete serialization
        return {
            "model_id": getattr(azure_result, 'model_id', 'unknown'),
            "api_version": getattr(azure_result, 'api_version', 'unknown'),
            "page_count": len(azure_result.pages) if azure_result.pages else 0,
            "timestamp": datetime.now().isoformat()
        }
    
    def _create_mock_response(self, pdf_path: str, payer_name: str, document_type: str) -> Dict[str, Any]:
        """Create mock response when Azure DI is not available"""
        return {
            "structured_data": {
                "payer_name": payer_name,
                "document_type": document_type,
                "extracted_at": datetime.now().isoformat(),
                "sections": [{"page_number": 1, "content": f"Mock data for {pdf_path}"}],
                "healthcare_rules": [
                    {
                        "type": "prior_authorization",
                        "content": "Mock prior authorization rule",
                        "page_number": 1,
                        "confidence_score": 0.9
                    }
                ],
                "processing_metadata": {
                    "processing_time_seconds": 1.0,
                    "azure_model": "mock",
                    "page_count": 1,
                    "confidence_score": 0.9
                }
            },
            "raw_azure_response": {"mock": True},
            "metadata": {
                "file_path": pdf_path,
                "payer_name": payer_name,
                "document_type": document_type,
                "processing_time": 1.0
            }
        }
    
    async def store_in_postgres(self, processed_data: Dict[str, Any]) -> Optional[int]:
        """
        Store processed document data in PostgreSQL
        
        Returns:
            document_id if successful, None if failed
        """
        if not self.pg_engine:
            self.logger.error("PostgreSQL not available")
            return None
        
        try:
            with self.pg_engine.connect() as conn:
                # Insert/get payer
                payer_id = self._insert_or_get_payer(conn, processed_data["metadata"]["payer_name"])
                
                # Insert document
                document_id = self._insert_document(conn, payer_id, processed_data)
                
                # Insert Azure DI results
                self._insert_di_results(conn, document_id, processed_data)
                
                # Insert healthcare rules
                self._insert_healthcare_rules(conn, document_id, processed_data)
                
                conn.commit()
                self.logger.info(f"Successfully stored data for document_id: {document_id}")
                return document_id
                
        except Exception as e:
            self.logger.error(f"Failed to store data in PostgreSQL: {e}")
            return None
    
    def _insert_or_get_payer(self, conn, payer_name: str) -> int:
        """Insert or get existing payer ID"""
        # Try to get existing payer
        result = conn.execute(
            text("SELECT payer_id FROM payers WHERE name = :name"),
            {"name": payer_name}
        ).fetchone()
        
        if result:
            return result[0]
        
        # Insert new payer
        result = conn.execute(
            text("""
                INSERT INTO payers (name, created_at) 
                VALUES (:name, CURRENT_TIMESTAMP) 
                RETURNING payer_id
            """),
            {"name": payer_name}
        ).fetchone()
        
        return result[0]
    
    def _insert_document(self, conn, payer_id: int, processed_data: Dict[str, Any]) -> int:
        """Insert document record"""
        metadata = processed_data["metadata"]
        file_path = metadata["file_path"]
        filename = os.path.basename(file_path)
        
        result = conn.execute(
            text("""
                INSERT INTO documents (
                    payer_id, filename, file_path, document_type,
                    processed_at, created_at
                ) VALUES (
                    :payer_id, :filename, :file_path, :document_type,
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                ) RETURNING document_id
            """),
            {
                "payer_id": payer_id,
                "filename": filename,
                "file_path": file_path,
                "document_type": metadata["document_type"]
            }
        ).fetchone()
        
        return result[0]
    
    def _insert_di_results(self, conn, document_id: int, processed_data: Dict[str, Any]):
        """Insert Azure Document Intelligence results"""
        structured_data = processed_data["structured_data"]
        metadata = structured_data.get("processing_metadata", {})
        
        conn.execute(
            text("""
                INSERT INTO document_intelligence_results (
                    document_id, azure_model_used, confidence_score,
                    page_count, processing_time_seconds, raw_response,
                    structured_data, extraction_timestamp
                ) VALUES (
                    :document_id, :azure_model, :confidence,
                    :page_count, :processing_time, :raw_response,
                    :structured_data, CURRENT_TIMESTAMP
                )
            """),
            {
                "document_id": document_id,
                "azure_model": metadata.get("azure_model", "unknown"),
                "confidence": metadata.get("confidence_score", 0.0),
                "page_count": metadata.get("page_count", 0),
                "processing_time": metadata.get("processing_time_seconds", 0.0),
                "raw_response": Json(processed_data["raw_azure_response"]),
                "structured_data": Json(structured_data)
            }
        )
    
    def _insert_healthcare_rules(self, conn, document_id: int, processed_data: Dict[str, Any]):
        """Insert extracted healthcare rules"""
        rules = processed_data["structured_data"].get("healthcare_rules", [])
        
        for rule in rules:
            conn.execute(
                text("""
                    INSERT INTO healthcare_rules (
                        document_id, rule_type, rule_content,
                        page_number, confidence_score, created_at
                    ) VALUES (
                        :document_id, :rule_type, :rule_content,
                        :page_number, :confidence_score, CURRENT_TIMESTAMP
                    )
                """),
                {
                    "document_id": document_id,
                    "rule_type": rule.get("type", "unknown"),
                    "rule_content": rule.get("content", ""),
                    "page_number": rule.get("page_number", 1),
                    "confidence_score": rule.get("confidence_score", 0.0)
                }
            )

# Usage example and configuration
if __name__ == "__main__":
    print("🏥 Azure Document Intelligence + PostgreSQL Processor")
    print("=" * 60)
    print("📋 Configuration required:")
    print("   • AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
    print("   • AZURE_DOCUMENT_INTELLIGENCE_KEY")
    print("   • POSTGRES_HOST, POSTGRES_USER, POSTGRES_PASSWORD")
    print()
    print("💡 This replaces basic PDF processors with Azure AI")
    print("🔄 Pipeline: PDF → Azure DI → Structured JSON → PostgreSQL")