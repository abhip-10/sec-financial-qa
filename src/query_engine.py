
import json
import time
import requests
import sys
import os
from typing import Dict, List
from dataclasses import dataclass
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import FIREWORKS_API_KEY, COMPANIES
from financial_taxonomy import FinancialTaxonomy
from embedding_engine import EmbeddingEngine, SearchResult

@dataclass
class QAResult:
    question: str
    answer: str
    sources: List[Dict]
    confidence: float
    time: float
    companies: List[str]

class SECFinancialQA:
    def __init__(self):
        print("Initializing SEC QA System...")
        self.taxonomy = FinancialTaxonomy()
        self.engine = EmbeddingEngine()
        self.engine.initialize()
        
        self.api_key = FIREWORKS_API_KEY
        self.model = "accounts/fireworks/models/llama-v3p1-70b-instruct"
        self.api_url = "https://api.fireworks.ai/inference/v1/chat/completions"
        print("System ready")

    def call_llm(self, prompt: str) -> str:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a financial analyst expert. Provide accurate answers based only on SEC filing context. Always cite sources [Source X]."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 1500,
            "temperature": 0.1
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Error: {e}"

    def create_prompt(self, question: str, results: List[SearchResult]) -> str:
        context = [f"Question: {question}\n\nSEC Filing Context:"]
        
        for i, result in enumerate(results[:8], 1):
            company = COMPANIES.get(result.ticker, result.ticker)
            context.append(f"[Source {i}] {company} ({result.ticker}) - {result.filing_type} - {result.section}")
            context.append(f"{result.content[:600]}...")
            context.append("")
        
        context.extend([
            "Instructions:",
            "1. Answer based only on the SEC filing content above",
            "2. Reference sources using [Source X] notation", 
            "3. Compare companies when multiple are mentioned",
            "4. Be specific about metrics, dates, filing types",
            "5. Acknowledge limitations if information is insufficient",
            "\nAnswer:"
        ])
        
        return "\n".join(context)

    def calculate_confidence(self, results: List[SearchResult], query_info: Dict) -> float:
        if not results:
            return 0.0
        
        # Base score from search results
        base_score = sum(r.final_score for r in results) / len(results)
        
        # Boost for ticker matches
        ticker_boost = 0.1
        if query_info.get('tickers'):
            matches = sum(1 for r in results if r.ticker in query_info['tickers'])
            ticker_boost = (matches / len(results)) * 0.2
        
        # Boost for concept matches
        concept_boost = 0
        for result in results:
            if any(c in result.financial_concepts for c in query_info.get('financial_concepts', [])):
                concept_boost += 0.02
        
        # Boost for company diversity
        diversity = len(set(r.ticker for r in results)) * 0.03
        
        return min(base_score + ticker_boost + concept_boost + diversity, 1.0)

    def answer(self, question: str) -> QAResult:
        start_time = time.time()
        
        # Parse and search
        query_info = self.taxonomy.parse_query(question)
        results = self.engine.search(question, top_k=12)
        
        if not results:
            return QAResult(question, "No relevant SEC filing information found.", [], 0.0, time.time() - start_time, [])
        
        # Generate answer
        prompt = self.create_prompt(question, results)
        answer = self.call_llm(prompt)
        
        # Extract metadata
        sources = []
        for i, r in enumerate(results, 1):
            sources.append({
                "id": i,
                "company": f"{COMPANIES.get(r.ticker, r.ticker)} ({r.ticker})",
                "filing": r.filing_type,
                "section": r.section,
                "score": round(r.final_score, 3)
            })
        
        confidence = self.calculate_confidence(results, query_info)
        companies = list(set(r.ticker for r in results))
        processing_time = time.time() - start_time
        
        return QAResult(question, answer, sources, confidence, processing_time, companies)

    def evaluate(self, questions: List[str]) -> List[QAResult]:
        print(f"Evaluating {len(questions)} questions...")
        results = []
        
        for i, q in enumerate(questions, 1):
            print(f"[{i}/{len(questions)}] {q[:50]}...")
            result = self.answer(q)
            results.append(result)
            print(f"  Confidence: {result.confidence:.3f}, Time: {result.time:.1f}s")
        
        return results

    def print_result(self, result: QAResult):
        print("=" * 60)
        print(f"Q: {result.question}")
        print(f"\nA: {result.answer}")
        print(f"\nMetadata: Confidence {result.confidence:.3f}, {result.time:.1f}s, {len(result.companies)} companies")
        print(f"Sources: {', '.join([f'{s["company"]}-{s["filing"]}' for s in result.sources[:3]])}")


def main():
    qa = SECFinancialQA()
    
    # Diverse evaluation questions targeting different filing types
    questions = [
        # 10-K: Annual comprehensive business overview
        "What are the primary revenue drivers and business segments for major technology companies like Apple and Microsoft?",
        
        # 10-Q: Quarterly financial performance analysis
        "Compare Apple and Microsoft's quarterly revenue performance trends and identify key growth drivers from recent quarters",
        
        # 8-K: Current events and material changes
        "What significant corporate events, acquisitions, or strategic changes have been reported by companies recently?",
        
        # DEF 14A: Executive compensation and governance
        "Analyze executive compensation structures and governance practices across technology versus traditional industry companies",
        
        # Form 4: Insider trading patterns
        "Identify patterns in insider trading activity across companies and analyze the timing of these transactions",
        
        # 10-Q Risk Factors: Industry-specific risks
        "How do companies describe climate-related risks and what industry differences exist in risk disclosure approaches?",
        
        # 10-K Business Description: Competitive landscape
        "How do companies describe their competitive advantages and market positioning strategies across different industries?",
        
        # 10-Q Financial Statements: Working capital analysis
        "Compare working capital management strategies between retail companies like Walmart and financial services firms",
        
        # 10-K/10-Q R&D Disclosures: Innovation investment
        "Analyze research and development spending efficiency across sectors: R&D investment per revenue dollar trends",
        
        # 10-Q Risk Factors: Regulatory compliance
        "Compare regulatory compliance costs and legal risk factors between financial services and healthcare companies"
    ]
    
    print("SEC FINANCIAL QA EVALUATION")
    print("=" * 60)
    print(f"Testing {len(questions)} diverse questions across filing types")
    print(f"Data: {len(COMPANIES)} companies, 7 years SEC filings")
    print("Filing types: 10-K, 10-Q, 8-K, DEF 14A, Form 4\n")
    
    # Run evaluation
    results = qa.evaluate(questions)
    
    # Print results
    for result in results:
        qa.print_result(result)
        print()
    
    # Summary
    avg_conf = sum(r.confidence for r in results) / len(results)
    avg_time = sum(r.time for r in results) / len(results)
    high_conf = sum(1 for r in results if r.confidence > 0.6)
    
    print("=" * 60)
    print("SUMMARY")
    print(f"Average Confidence: {avg_conf:.3f}")
    print(f"Average Time: {avg_time:.1f}s")
    print(f"High Confidence (>0.6): {high_conf}/{len(results)}")
    
    # Save results
    output = Path("qa_results.json")
    with open(output, 'w') as f:
        data = [{"q": r.question, "a": r.answer, "conf": float(r.confidence), "time": float(r.time)} for r in results]
        json.dump(data, f, indent=2)
    
    print(f"Results saved: {output}")
    print("Evaluation complete!")


if __name__ == '__main__':
    main()
