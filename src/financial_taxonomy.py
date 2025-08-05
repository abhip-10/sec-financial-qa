import re
import json
from typing import Dict, List
from pathlib import Path

class FinancialTaxonomy:
    """Financial keyword mapping for SEC filings analysis"""
    
    def __init__(self):
        self.taxonomy = {
            "revenue_performance": {
                "keywords": ["revenue", "sales", "income", "earnings", "profit", "performance", "top line", "net sales", "total revenue", "operating revenue", "growth", "decline"],
                "sec_sections": ["Item 1 - Business", "Item 7 - Management's Discussion", "Item 8 - Financial Statements", "Consolidated Statements of Operations"],
                "filing_types": ["10-K", "10-Q", "8-K"], "xbrl_tags": ["Revenues", "SalesRevenueNet"]
            },
            "risk_factors": {
                "keywords": ["risk", "risks", "risk factors", "uncertainties", "challenges", "threats", "vulnerabilities", "material adverse", "cyber", "cybersecurity", "regulatory risk", "market risk"],
                "sec_sections": ["Item 1A - Risk Factors", "Item 7A - Quantitative and Qualitative Disclosures About Market Risk"],
                "filing_types": ["10-K", "10-Q", "8-K"], "xbrl_tags": ["RiskFactors", "MarketRiskDisclosures"]
            },
            "research_development": {
                "keywords": ["research and development", "r&d", "innovation", "technology", "patents", "intellectual property", "development costs", "research expenses", "innovation investment"],
                "sec_sections": ["Item 1 - Business", "Item 7 - Management's Discussion", "Item 8 - Financial Statements"],
                "filing_types": ["10-K", "10-Q"], "xbrl_tags": ["ResearchAndDevelopmentExpense"]
            },
            "working_capital": {
                "keywords": ["working capital", "current assets", "current liabilities", "accounts receivable", "inventory", "accounts payable", "cash conversion", "liquidity"],
                "sec_sections": ["Item 7 - Management's Discussion", "Item 8 - Financial Statements", "Consolidated Balance Sheets"],
                "filing_types": ["10-K", "10-Q"], "xbrl_tags": ["WorkingCapital", "AssetsCurrent", "LiabilitiesCurrent"]
            },
            "executive_compensation": {
                "keywords": ["executive compensation", "ceo pay", "executive pay", "compensation committee", "salary", "bonus", "stock options", "equity compensation"],
                "sec_sections": ["Compensation Discussion and Analysis", "Executive Compensation Tables"],
                "filing_types": ["DEF 14A"], "xbrl_tags": ["CompensationCosts", "ShareBasedCompensation"]
            },
            "insider_trading": {
                "keywords": ["insider trading", "insider transactions", "form 3", "form 4", "form 5", "beneficial ownership", "director transactions", "stock purchases", "stock sales"],
                "sec_sections": ["Security Ownership of Certain Beneficial Owners"],
                "filing_types": ["3", "4", "5", "DEF 14A"], "xbrl_tags": ["SecurityOwned", "TransactionShares"]
            },
            "climate_esg": {
                "keywords": ["climate", "climate change", "environmental", "sustainability", "esg", "carbon", "emissions", "renewable energy", "climate risk"],
                "sec_sections": ["Item 1A - Risk Factors", "Item 1 - Business", "Item 7 - Management's Discussion"],
                "filing_types": ["10-K", "10-Q", "8-K"], "xbrl_tags": ["EnvironmentalCompliance"]
            },
            "mergers_acquisitions": {
                "keywords": ["merger", "acquisition", "m&a", "business combination", "purchase", "divestiture", "joint venture", "strategic alliance"],
                "sec_sections": ["Item 2 - Management's Discussion of Financial Condition", "Item 8 - Financial Statements", "Business Combinations"],
                "filing_types": ["8-K", "10-K", "10-Q"], "xbrl_tags": ["BusinessCombinations", "Goodwill"]
            },
            "competitive_advantage": {
                "keywords": ["competitive advantage", "moat", "differentiation", "market position", "barriers to entry", "competitive strengths", "market leadership", "brand strength"],
                "sec_sections": ["Item 1 - Business", "Item 1A - Risk Factors", "Item 7 - Management's Discussion"],
                "filing_types": ["10-K"], "xbrl_tags": ["BusinessDescription"]
            },
            "ai_automation": {
                "keywords": ["artificial intelligence", "ai", "machine learning", "automation", "robotics", "digital transformation", "technology adoption", "algorithmic"],
                "sec_sections": ["Item 1 - Business", "Item 1A - Risk Factors", "Item 7 - Management's Discussion"],
                "filing_types": ["10-K", "10-Q", "8-K"], "xbrl_tags": ["TechnologyInvestments"]
            }
        }
        
        self.temporal_patterns = {
            "year_patterns": r"\b(19|20)\d{2}\b",
            "quarter_patterns": r"\b(Q[1-4]|first|second|third|fourth)\s+(quarter|Q)\b",
            "period_patterns": {
                "annual": r"\b(annual|yearly|year-over-year|YoY)\b",
                "quarterly": r"\b(quarterly|quarter|QoQ)\b",
                "recent": r"\b(recent|latest|current|last|past)\b",
                "historical": r"\b(historical|over\s+time|trend|evolution)\b"
            }
        }
    
    def parse_query(self, query: str) -> Dict:
        """Parse query to extract concepts, tickers, time periods"""
        query_lower = query.lower()
        
        return {
            "original_query": query,
            "tickers": self._extract_tickers(query),
            "temporal_info": self._extract_temporal_info(query),
            "financial_concepts": self._map_financial_concepts(query_lower),
            "relevant_sections": self._get_relevant_sections(self._map_financial_concepts(query_lower)),
            "filing_types": self._get_filing_types(self._map_financial_concepts(query_lower), self._extract_temporal_info(query)),
            "search_strategy": self._determine_search_strategy(self._map_financial_concepts(query_lower), self._extract_temporal_info(query))
        }
    
    def _extract_tickers(self, query: str) -> List[str]:
        """Extract ticker symbols from query"""
        from config.config import COMPANIES
        tickers = []
        query_upper = query.upper()
        
        for ticker in COMPANIES.keys():
            if ticker in query_upper:
                tickers.append(ticker)
        for ticker, company_name in COMPANIES.items():
            if company_name.lower() in query.lower():
                tickers.append(ticker)
        return list(set(tickers))
    
    def _extract_temporal_info(self, query: str) -> Dict:
        """Extract temporal information from query"""
        temporal_info = {"years": [], "quarters": [], "period_type": None}
        
        years = re.findall(self.temporal_patterns["year_patterns"], query)
        temporal_info["years"] = [int(year) for year in years]
        
        quarter_matches = re.findall(self.temporal_patterns["quarter_patterns"], query.lower())
        temporal_info["quarters"] = quarter_matches
        
        for period_type, pattern in self.temporal_patterns["period_patterns"].items():
            if re.search(pattern, query.lower()):
                temporal_info["period_type"] = period_type
                break
        return temporal_info
    
    def _map_financial_concepts(self, query_lower: str) -> List[str]:
        """Map query to financial concepts"""
        matched_concepts = []
        for concept, details in self.taxonomy.items():
            for keyword in details["keywords"]:
                if keyword.lower() in query_lower:
                    matched_concepts.append(concept)
                    break
        return matched_concepts
    
    def _get_relevant_sections(self, financial_concepts: List[str]) -> List[str]:
        """Get relevant SEC sections for financial concepts"""
        relevant_sections = set()
        for concept in financial_concepts:
            if concept in self.taxonomy:
                relevant_sections.update(self.taxonomy[concept]["sec_sections"])
        return list(relevant_sections)
    
    def _get_filing_types(self, financial_concepts: List[str], temporal_info: Dict) -> List[str]:
        """Determine relevant filing types"""
        filing_types = set()
        for concept in financial_concepts:
            if concept in self.taxonomy:
                filing_types.update(self.taxonomy[concept]["filing_types"])
        
        if temporal_info.get("period_type") == "annual":
            filing_types.add("10-K")
        elif temporal_info.get("period_type") == "quarterly":
            filing_types.add("10-Q")
        return list(filing_types)
    
    def _determine_search_strategy(self, financial_concepts: List[str], temporal_info: Dict) -> Dict:
        """Determine optimal search strategy"""
        strategy = {"search_type": "semantic", "filters": {}, "ranking_factors": ["semantic_similarity", "section_relevance", "temporal_relevance"]}
        
        if len(financial_concepts) == 1 and financial_concepts[0] in ["revenue_performance", "risk_factors"]:
            strategy["search_type"] = "semantic"
        elif temporal_info.get("years") or temporal_info.get("quarters"):
            strategy["search_type"] = "hybrid"
        
        if temporal_info.get("years"):
            strategy["filters"]["years"] = temporal_info["years"]
        return strategy
    
    def get_section_keywords(self, section_name: str) -> List[str]:
        """Get keywords associated with a specific SEC section"""
        section_keywords = []
        for concept, details in self.taxonomy.items():
            if section_name in details["sec_sections"]:
                section_keywords.extend(details["keywords"])
        return list(set(section_keywords))
    
    def save_taxonomy(self, filepath: str):
        """Save taxonomy to JSON file"""
        with open(filepath, 'w') as f:
            json.dump(self.taxonomy, f, indent=2)
    
    def load_taxonomy(self, filepath: str):
        """Load taxonomy from JSON file"""
        with open(filepath, 'r') as f:
            self.taxonomy = json.load(f)


if __name__ == "__main__":
    import sys, os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    taxonomy = FinancialTaxonomy()
    
    test_queries = [
        "What are the primary revenue drivers for major technology companies, and how have they evolved?",
        "Compare R&D spending trends across companies. What insights about innovation investment strategies?",
        "Identify significant working capital changes for financial services companies and driving factors.",
        "What are the most commonly cited risk factors across industries?",
        "How do companies describe climate-related risks? Notable industry differences?",
        "Apple's risk factors in 2022",
        "Compare Apple and Microsoft revenues",
        "Tesla's 2022 10-K risk factors"
    ]
    
    print("Financial Taxonomy Query Parsing Results:")
    print("=" * 60)
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        result = taxonomy.parse_query(query)
        
        print(f"Tickers: {result['tickers']}")
        print(f"Financial Concepts: {result['financial_concepts']}")
        print(f"Filing Types: {result['filing_types']}")
        print(f"Relevant Sections: {result['relevant_sections'][:2]}...")
        print(f"Search Strategy: {result['search_strategy']['search_type']}")
        print("-" * 40)