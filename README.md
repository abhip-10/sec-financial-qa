# SEC Financial QA System

A question-answering system that analyzes SEC filings to answer complex financial research questions using semantic search and Large Language Models.

## Features

- **Multi-Document Analysis**: Process SEC filings (10-K, 10-Q, 8-K, DEF 14A, Forms 3/4/5) across multiple companies
- **Intelligent Query Processing**: Extract tickers, time periods, and financial concepts from natural language queries
- **Semantic Search**: FAISS-powered vector search with financial taxonomy integration
- **Source Attribution**: Detailed citations with company, filing type, and section references

## Quick Start

### Prerequisites
- Python 3.8+
- 16GB+ RAM recommended
- Fireworks AI API key

### Installation

1. **Clone the repository**
```bash
git clone <https://github.com/abhip-10/sec-financial-qa>
cd sec-financial-qa
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your API keys:
# FIREWORKS_API_KEY=your_actual_api_key
# SEC_USER_AGENT=Your Name your.email@domain.com
```

4. **Run the system**
```bash
python main.py
```

## Usage

The system processes queries about SEC filings and returns detailed answers with source citations.

Example queries:
- "What are Apple's primary revenue drivers?"
- "Compare R&D spending trends across technology companies"
- "How do companies describe climate-related risks?"

## Architecture

- **Data Acquisition**: Downloads SEC filings using sec-edgar-downloader
- **Document Processing**: Parses HTML filings and extracts structured content
- **Financial Taxonomy**: Maps financial concepts to relevant SEC sections
- **Embedding Engine**: Creates vector embeddings using sentence-transformers
- **Query Engine**: Combines semantic search with LLM-powered analysis

## Project Structure

```
sec-financial-qa/
├── src/
│   ├── data_acquisition.py    # SEC filing download
│   ├── preprocessing.py       # Document processing
│   ├── financial_taxonomy.py  # Financial concept mapping
│   ├── embedding_engine.py    # Vector search
│   └── query_engine.py        # QA orchestration
├── config/
│   └── config.py              # Configuration
├── main.py                    # Pipeline runner
└── requirements.txt           # Dependencies
```

## Environment Variables

- `FIREWORKS_API_KEY`: Your Fireworks AI API key for LLM inference
- `SEC_USER_AGENT`: Your name and email for SEC API compliance

## Contributing

This project was developed for a financial research challenge. Feel free to extend and improve the system.

## License

MIT License
