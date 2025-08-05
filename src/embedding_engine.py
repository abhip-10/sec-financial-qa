
import json
import pickle
import numpy as np
import faiss
import sys
import os
from pathlib import Path
from typing import Dict, List
from sentence_transformers import SentenceTransformer
from dataclasses import dataclass

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import PROCESSED_DATA_DIR, COMPANIES
from financial_taxonomy import FinancialTaxonomy

@dataclass
class SearchResult:
    content: str
    ticker: str
    filing_type: str
    section: str
    chunk_id: str
    financial_concepts: List[str]
    similarity_score: float
    final_score: float

class EmbeddingEngine:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.processed_data_dir = PROCESSED_DATA_DIR
        self.taxonomy = FinancialTaxonomy()
        
        print(f"Loading model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.dim = self.model.get_sentence_embedding_dimension()
        
        self.chunks_data = []
        self.index = None
        
        self.index_dir = self.processed_data_dir / "embeddings"
        self.index_dir.mkdir(exist_ok=True)
        self.embeddings_file = self.index_dir / "embeddings.npy"
        self.index_file = self.index_dir / "index.bin"
        self.metadata_file = self.index_dir / "metadata.pkl"
        
        print(f"Engine ready - Dimension: {self.dim}")

    def load_chunks(self) -> List[Dict]:
        all_chunks = []
        print("Loading chunks...")
        
        for ticker in COMPANIES.keys():
            file_path = self.processed_data_dir / f"{ticker}_processed.json"
            if file_path.exists():
                with open(file_path, 'r') as f:
                    chunks = json.load(f)
                    all_chunks.extend(chunks)
                    print(f"  {ticker}: {len(chunks)} chunks")
        
        print(f"Total: {len(all_chunks)} chunks")
        return all_chunks

    def create_embeddings(self, chunks: List[Dict]) -> np.ndarray:
        print("Generating embeddings...")
        
        texts = []
        for chunk in chunks:
            concepts = " ".join(chunk.get('financial_concepts', []))
            section = chunk.get('section', '')
            text = f"{concepts} {section} {chunk['content']}"[:512]
            texts.append(text)
        
        embeddings = self.model.encode(texts, batch_size=64, show_progress_bar=True, convert_to_numpy=True)
        return embeddings

    def build_index(self, embeddings: np.ndarray) -> faiss.Index:
        print("Building FAISS index...")
        index = faiss.IndexFlatIP(self.dim)
        faiss.normalize_L2(embeddings)
        index.add(embeddings.astype('float32'))
        print(f"Index built: {index.ntotal} vectors")
        return index

    def save_index(self, embeddings: np.ndarray, chunks: List[Dict]):
        np.save(self.embeddings_file, embeddings)
        faiss.write_index(self.index, str(self.index_file))
        with open(self.metadata_file, 'wb') as f:
            pickle.dump(chunks, f)
        print(f"Index saved to {self.index_dir}")

    def load_index(self) -> bool:
        if not all([self.embeddings_file.exists(), self.index_file.exists(), self.metadata_file.exists()]):
            return False
        
        print("Loading existing index...")
        self.index = faiss.read_index(str(self.index_file))
        with open(self.metadata_file, 'rb') as f:
            self.chunks_data = pickle.load(f)
        print(f"Loaded: {len(self.chunks_data)} chunks")
        return True

    def score_metadata(self, chunk: Dict, query_info: Dict) -> float:
        score = 0.1
        
        if query_info.get('tickers') and chunk['ticker'] in query_info['tickers']:
            score += 0.3
        if query_info.get('filing_types') and chunk['filing_type'] in query_info['filing_types']:
            score += 0.2
        if query_info.get('relevant_sections'):
            for section in query_info['relevant_sections']:
                if section.lower() in chunk['section'].lower():
                    score += 0.2
                    break
        if query_info.get('financial_concepts'):
            overlap = set(chunk.get('financial_concepts', [])) & set(query_info['financial_concepts'])
            score += len(overlap) * 0.1
        
        return min(score, 1.0)

    def search(self, query: str, top_k: int = 10) -> List[SearchResult]:
        if not self.index:
            raise ValueError("Index not loaded")
        
        query_info = self.taxonomy.parse_query(query)
        query_embedding = self.model.encode([query], convert_to_numpy=True)
        faiss.normalize_L2(query_embedding)
        
        search_k = min(top_k * 5, len(self.chunks_data))
        similarities, indices = self.index.search(query_embedding.astype('float32'), search_k)
        
        results = []
        for similarity, idx in zip(similarities[0], indices[0]):
            if similarity < 0.1:
                continue
                
            chunk = self.chunks_data[idx]
            metadata_score = self.score_metadata(chunk, query_info)
            final_score = 0.7 * similarity + 0.3 * metadata_score
            
            result = SearchResult(
                content=chunk['content'],
                ticker=chunk['ticker'],  
                filing_type=chunk['filing_type'],
                section=chunk['section'],
                chunk_id=chunk['chunk_id'],
                financial_concepts=chunk.get('financial_concepts', []),
                similarity_score=float(similarity),
                final_score=final_score
            )
            results.append(result)
        
        return sorted(results, key=lambda x: x.final_score, reverse=True)[:top_k]

    def initialize(self, force_rebuild: bool = False):
        if not force_rebuild and self.load_index():
            return
        
        print("Building new index...")
        chunks = self.load_chunks()
        if not chunks:
            raise ValueError("No chunks found!")
        
        embeddings = self.create_embeddings(chunks)
        self.index = self.build_index(embeddings)
        self.chunks_data = chunks
        self.save_index(embeddings, chunks)
        print("Index ready!")

    def stats(self) -> Dict:
        if not self.chunks_data:
            return {"status": "not_initialized"}
        
        filing_types = {}
        sections = {}
        concepts = {}
        
        for chunk in self.chunks_data:
            filing_types[chunk['filing_type']] = filing_types.get(chunk['filing_type'], 0) + 1
            sections[chunk['section']] = sections.get(chunk['section'], 0) + 1
            for concept in chunk.get('financial_concepts', []):
                concepts[concept] = concepts.get(concept, 0) + 1
        
        return {
            "total_chunks": len(self.chunks_data),
            "companies": len(set(chunk['ticker'] for chunk in self.chunks_data)),
            "filing_types": dict(sorted(filing_types.items(), key=lambda x: x[1], reverse=True)[:5]),
            "sections": dict(sorted(sections.items(), key=lambda x: x[1], reverse=True)[:3]),
            "concepts": dict(sorted(concepts.items(), key=lambda x: x[1], reverse=True)[:5])
        }


if __name__ == '__main__':
    engine = EmbeddingEngine()
    
    try:
        print("Initializing embedding engine...")
        engine.initialize()
        
        test_queries = [
            "Apple's revenue growth trends",
            "R&D spending across tech companies", 
            "Financial services risk factors",
            "Energy companies climate risks",
            "Executive compensation changes"
        ]
        
        print("\n" + "="*50)
        print("TESTING EMBEDDING ENGINE")
        print("="*50)
        
        for query in test_queries:
            print(f"\nQuery: {query}")
            print("-" * 30)
            
            results = engine.search(query, top_k=3)
            print(f"Found {len(results)} results")
            
            for i, result in enumerate(results, 1):
                print(f"{i}. {result.ticker} {result.filing_type} - {result.section}")
                print(f"   Score: {result.final_score:.3f} (sim: {result.similarity_score:.3f})")
                print(f"   Content: {result.content[:80]}...")
                print()
        
        stats = engine.stats()
        print("\n" + "="*50)
        print("ENGINE STATS")
        print("="*50)
        print(f"Chunks: {stats['total_chunks']:,}")  
        print(f"Companies: {stats['companies']}")
        print(f"Filing types: {stats['filing_types']}")
        print(f"Sections: {stats['sections']}")
        print(f"Concepts: {stats['concepts']}")
        print("\nEmbedding engine test complete!")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
