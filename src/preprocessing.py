#!/usr/bin/env python3
"""SEC Filings Document Processing"""

import re
import json
import time
import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple
from bs4 import BeautifulSoup
from dataclasses import dataclass

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import RAW_DATA_DIR, PROCESSED_DATA_DIR, COMPANIES
from financial_taxonomy import FinancialTaxonomy

@dataclass
class DocumentChunk:
    content: str
    ticker: str
    filing_type: str
    section: str
    estimated_year: int
    chunk_id: str
    financial_concepts: List[str]
    word_count: int

class SECDocumentProcessor:
    def __init__(self, raw_data_dir=None, processed_data_dir=None):
        self.raw_data_dir = Path(raw_data_dir) if raw_data_dir else RAW_DATA_DIR
        self.processed_data_dir = Path(processed_data_dir) if processed_data_dir else PROCESSED_DATA_DIR
        self.processed_data_dir.mkdir(parents=True, exist_ok=True)
        self.taxonomy = FinancialTaxonomy()
        
        self.section_patterns = {
            "Risk Factors": r"(?i)item\s*1a[\.\s]*risk\s*factors",
            "Business": r"(?i)item\s*1[\.\s]*business", 
            "MD&A": r"(?i)item\s*7[\.\s]*management'?s\s*discussion",
            "Financial Statements": r"(?i)item\s*8[\.\s]*financial\s*statements",
            "Compensation": r"(?i)compensation\s*discussion",
            "Executive Compensation": r"(?i)executive\s*compensation"
        }
        
        print(f"Processor initialized: {self.raw_data_dir} → {self.processed_data_dir}")

    def extract_sections(self, content: str, filing_type: str) -> Dict[str, str]:
        sections = {}
        for section_name, pattern in self.section_patterns.items():
            matches = list(re.finditer(pattern, content, re.IGNORECASE))
            if matches:
                start = matches[0].end()
                end = len(content)
                
    
                for other_pattern in self.section_patterns.values():
                    if other_pattern != pattern:
                        next_matches = list(re.finditer(other_pattern, content[start:], re.IGNORECASE))
                        if next_matches:
                            potential_end = start + next_matches[0].start()
                            if start < potential_end < end:
                                end = potential_end
                
                section_content = content[start:end].strip()
                if len(section_content) > 200:
                    sections[section_name] = section_content
        
        
        if not sections and len(content) > 200:
            sections["General Content"] = content
        return sections

    def clean_and_chunk(self, content: str, max_size: int = 1000) -> List[str]:
        content = re.sub(r'<[^>]+>', '', content)  
        content = re.sub(r'\s+', ' ', content).strip() 
        
        
        words = content.split()
        chunks, current_chunk, current_size = [], [], 0
        
        for word in words:
            word_len = len(word) + 1
            if current_size + word_len > max_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk, current_size = [word], len(word)
            else:
                current_chunk.append(word)
                current_size += word_len
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        return chunks

    def tag_concepts(self, content: str) -> List[str]:
        content_lower = content.lower()
        concepts = []
        for concept, details in self.taxonomy.taxonomy.items():
            if any(keyword.lower() in content_lower for keyword in details["keywords"]):
                concepts.append(concept)
        return concepts

    def process_file(self, file_path: Path, ticker: str, filing_type: str) -> List[DocumentChunk]:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            if file_path.suffix.lower() in ['.html', '.htm']:
                content = BeautifulSoup(content, 'html.parser').get_text()
            
            if len(content) < 200:
                return []
            
            sections = self.extract_sections(content, filing_type)
            year_match = re.search(r'(\d{4})', file_path.name)
            estimated_year = int(year_match.group(1)) if year_match else None
            
            chunks = []
            chunk_counter = 0
            
            for section_name, section_content in sections.items():
                section_chunks = self.clean_and_chunk(section_content)
                
                for chunk_content in section_chunks:
                    concepts = self.tag_concepts(chunk_content)
                    
                    chunk = DocumentChunk(
                        content=chunk_content,
                        ticker=ticker,
                        filing_type=filing_type,
                        section=section_name,
                        estimated_year=estimated_year,
                        chunk_id=f"{ticker}_{filing_type}_{estimated_year}_{chunk_counter}",
                        financial_concepts=concepts,
                        word_count=len(chunk_content.split())
                    )
                    chunks.append(chunk)
                    chunk_counter += 1
            
            return chunks
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return []

    def process_company(self, ticker: str) -> List[DocumentChunk]:
        company_dir = self.raw_data_dir / ticker
        if not company_dir.exists():
            return []
        
        all_chunks = []
        print(f"Processing {ticker}")
        
        for filing_type_dir in company_dir.iterdir():
            if not filing_type_dir.is_dir():
                continue
            
            filing_type = filing_type_dir.name
            files = list(filing_type_dir.glob("*.html")) + list(filing_type_dir.glob("*.xml"))
            
            for file_path in files:
                chunks = self.process_file(file_path, ticker, filing_type)
                all_chunks.extend(chunks)
        
        print(f"  Generated {len(all_chunks)} chunks")
        return all_chunks

    def save_data(self, chunks: List[DocumentChunk], ticker: str):
        output_file = self.processed_data_dir / f"{ticker}_processed.json"
        chunks_data = [
            {
                'content': chunk.content, 'ticker': chunk.ticker, 'filing_type': chunk.filing_type,
                'section': chunk.section, 'estimated_year': chunk.estimated_year, 'chunk_id': chunk.chunk_id,
                'financial_concepts': chunk.financial_concepts, 'word_count': chunk.word_count
            } for chunk in chunks
        ]
        
        with open(output_file, 'w') as f:
            json.dump(chunks_data, f, indent=2)

    def create_summary(self, all_chunks: List[DocumentChunk]) -> Dict:
        summary = {
            'total_chunks': len(all_chunks), 'companies': len(set(chunk.ticker for chunk in all_chunks)),
            'filing_types': {}, 'sections': {}, 'financial_concepts': {}, 'years_covered': set(),
            'total_words': sum(chunk.word_count for chunk in all_chunks)
        }
        
        for chunk in all_chunks:
            summary['filing_types'][chunk.filing_type] = summary['filing_types'].get(chunk.filing_type, 0) + 1
            summary['sections'][chunk.section] = summary['sections'].get(chunk.section, 0) + 1
            for concept in chunk.financial_concepts:
                summary['financial_concepts'][concept] = summary['financial_concepts'].get(concept, 0) + 1
            if chunk.estimated_year:
                summary['years_covered'].add(chunk.estimated_year)
        
        summary['years_covered'] = sorted(list(summary['years_covered']))
        return summary

    def run(self, companies=None):
        start_time = time.time()
        companies_to_process = companies or list(COMPANIES.keys())
        all_chunks = []
        
        print(f"Processing {len(companies_to_process)} companies")
        print("=" * 50)
        
        for ticker in companies_to_process:
            chunks = self.process_company(ticker)
            if chunks:
                self.save_data(chunks, ticker)
                all_chunks.extend(chunks)
        
        summary = self.create_summary(all_chunks)
        with open(self.processed_data_dir / 'summary.json', 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        duration = time.time() - start_time
        print("\n" + "=" * 50)
        print("PROCESSING COMPLETE")
        print(f"Total chunks: {summary['total_chunks']:,}")
        print(f"Total words: {summary['total_words']:,}")
        print(f"Companies: {summary['companies']}")  
        print(f"Years: {min(summary['years_covered'])} - {max(summary['years_covered'])}")
        print(f"Filing types: {summary['filing_types']}")
        print(f"Top sections: {dict(sorted(summary['sections'].items(), key=lambda x: x[1], reverse=True)[:3])}")
        print(f"Top concepts: {dict(sorted(summary['financial_concepts'].items(), key=lambda x: x[1], reverse=True)[:3])}")
        print(f"Time: {duration:.1f}s")
        
        return all_chunks


if __name__ == '__main__':
    print("Starting SEC Document Processor...")
    
    try:
        processor = SECDocumentProcessor()
        print("Processing ALL companies in database...")
        
        chunks = processor.run()
        print(f"\nSuccess: Generated {len(chunks)} document chunks")
        
        if chunks:
            sample = chunks[0]
            print(f"\nSample chunk:")
            print(f"Company: {sample.ticker}")
            print(f"Filing: {sample.filing_type} - {sample.section}")
            print(f"Concepts: {sample.financial_concepts[:3]}")
            print(f"Content: {sample.content[:150]}...")
        else:
            print("No chunks generated - checking data availability...")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
