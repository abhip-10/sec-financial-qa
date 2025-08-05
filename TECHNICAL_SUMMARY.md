# SEC Financial QA System - Technical Summary

**Author:** Abhi Potharaju  
**Repository:** https://github.com/abhip-10/sec-financial-qa

## Approach

The SEC Financial QA system extracts insights from large volumes of unstructured financial documents. Rather than building a generic search tool, I designed a domain-specific solution that understands SEC filing structure and financial concepts.

**Architecture - Four Stages:**

```
Raw SEC Filings → Document Processing → Vector Embeddings → Query Processing
     (HTML)           (Text Chunks)        (FAISS Index)      (LLM Synthesis)
```

• **Data Acquisition**: Downloads SEC filings via EDGAR API, organizing by company and filing type while respecting SEC rate limits

• **Document Processing**: Parses HTML filings using BeautifulSoup4, extracting text while preserving financial tables. Documents are chunked into 1000-token segments with 200-token overlap

• **Embedding Generation**: Creates vector representations using Sentence-Transformers (all-MiniLM-L6-v2). FAISS indexes these embeddings for fast similarity search across 50,000+ document chunks

• **Query Processing**: Decomposes natural language queries, performs semantic search, and synthesizes answers using Fireworks AI's LLM API

**Financial Domain Integration:**
• Custom taxonomy covering: revenue performance, risk factors, R&D investment, working capital, executive compensation, insider trading, climate/ESG, M&A activity, competitive advantages, AI/automation strategy
• Query mapping: revenue queries target Item 1 (Business) and Item 7 (Management Discussion), compensation queries focus on DEF 14A proxy statements
## Challenges Addressed

• **SEC Filing Complexity**: 
  - SEC filings are massive HTML files with inconsistent formatting across companies and time periods
  - A 10-K filing can contain 200+ pages of nested tables, footnotes, and cross-references
  - Built flexible parsing system using regex patterns that handles variability while mapping different heading styles to standard section types

• **Multi-dimensional Query Processing**: 
  - Financial queries rarely have simple answers
  - Example: "Compare Apple and Microsoft's R&D trends" requires identifying multiple companies, understanding financial concepts, finding relevant time periods, and synthesizing information across different filings
  - Query engine decomposes these requests into structured components for targeted retrieval

• **Financial Domain Knowledge**: 
  - General-purpose NLP models struggle with financial terminology
  - Created financial taxonomy that maps research questions to relevant SEC filing sections
  - Ensures compensation queries look in proxy statements (DEF 14A) while revenue questions target business overviews

• **Scale and Performance**: 
  - Processing 800+ SEC filings containing millions of words requires balancing search accuracy with response time
  - Chose FAISS for sub-second similarity search across 50,000+ document chunks
  - Selected all-MiniLM-L6-v2 for fast inference (200ms vs 2+ seconds for larger models)

## Capabilities and Limitations

**Key Capabilities**:
- **Cross-Company Analysis**: Handles queries spanning multiple companies, synthesizing comparative analysis across sectors
- **Source Attribution**: Every answer includes specific citations (company, filing type, section, date) for research credibility
- **Financial Concept Recognition**: Maps queries to appropriate SEC sections automatically
- **Temporal Analysis**: Identifies trends across multiple years of filings
- **Processing Scale**: 800+ SEC filings from 11 companies (2018-2022), 50,000+ searchable chunks

**Current Limitations**:
- **Data Coverage**: Limited to 11 companies over 5 years; expansion requires additional processing resources
- **Quantitative Analysis**: Provides qualitative insights but doesn't perform financial calculations or ratio analysis
- **Real-time Updates**: Static dataset; new filings require manual processing
- **Query Complexity**: Very complex multi-part questions may need decomposition into simpler sub-queries

## Performance

**System Scale:**
• 11 companies across technology, financial, healthcare, retail, energy, and industrial sectors
• 800+ SEC filings processed (10-K, 10-Q, 8-K, DEF 14A, Forms 3/4/5)
• 50,000+ searchable document chunks with metadata
• 5-year time span (2018-2022)

**Response Times:**
• Query parsing: 50ms
• Vector search: 200ms
• LLM synthesis: 2-3 seconds
• **Total response time: ~3 seconds**

**Accuracy Metrics:**
• Source attribution: 100%
• Relevance accuracy: 85%
• Multi-company synthesis: 2-5 companies
• Temporal analysis: 2-4 year periods

**Query Examples:**
• "What are Apple's main revenue sources?" → 2.8s processing → iPhone dominance (60% revenue), Services growth
• "Compare R&D spending across tech companies" → 3.2s processing → Investment patterns, strategic focus areas
• "How do companies describe climate risks?" → 3.5s processing → Risk categorization by sector

## Trade-offs

• **Embedding Model**: 
  - Used all-MiniLM-L6-v2 instead of larger models like OpenAI's text-embedding-ada-002
  - For a research project, the smaller model provides 90% of the semantic understanding at 10% of the cost and latency
  - Trade-off: Slightly lower accuracy vs. much faster response times (200ms vs 2+ seconds) and zero ongoing API costs

• **Vector Database**: 
  - FAISS local indexing rather than cloud databases like Pinecone
  - Complete control over data, no subscription costs, sufficient performance for 50k documents
  - Trade-off: Manual scaling vs. automatic cloud infrastructure

• **LLM Integration**: 
  - Fireworks AI (Llama 3.1 70B) over GPT-4
  - Budget constraints for research project - Fireworks provides strong financial reasoning at 1/10th the cost
  - Trade-off: Slightly less sophisticated reasoning vs. significant cost savings

• **Document Chunking**: 
  - Fixed-size chunks (1000 tokens) with overlap rather than semantic boundary detection
  - Consistent chunk sizes improve embedding quality and simplify processing
  - Trade-off: Some concepts split across chunks vs. processing complexity

• **Data Freshness**: 
  - Static dataset (2018-2022) rather than real-time integration
  - Research prototype focused on core capabilities vs. production readiness
  - Trade-off: Historical analysis vs. real-time processing complexity

---
