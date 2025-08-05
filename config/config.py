import os
from pathlib import Path

# Project directories
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed" 
CACHE_DIR = DATA_DIR / "cache"

# API configuration - requires environment variables
FIREWORKS_API_KEY = os.getenv("FIREWORKS_API_KEY")
if not FIREWORKS_API_KEY:
    raise ValueError("FIREWORKS_API_KEY environment variable is required")

# Processing configuration
MAX_WORKERS = 8
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Company CIKs - selected for sector diversity
COMPANIES = {
    "AAPL": "320193",    # Technology
    "MSFT": "789019",    # Technology
    "NVDA": "1045810",   # Technology
    "JPM": "19617",      # Financial Services
    "TSLA": "1318605",   # Automotive/Technology
    "JNJ": "200406",     # Healthcare
    "PFE": "78003",      # Pharmaceuticals
    "WMT": "104169",     # Retail
    "AMZN": "1018724",   # E-commerce
    "XOM": "34088",      # Energy
    "CAT": "18230"       # Industrial
}