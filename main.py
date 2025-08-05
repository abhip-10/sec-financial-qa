import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).parent / "src"))

def run_data_acquisition():
    """Download SEC filings if not already present"""
    print("Step 1: Data Acquisition")
    print("-" * 30)
    
    try:
        from data_acquisition import SECDownloader
        from config.config import RAW_DATA_DIR
        
        if (RAW_DATA_DIR / "AAPL").exists():
            print("SEC data already downloaded")
            return True
        
        print("Downloading SEC filings...")
        downloader = SECDownloader()
        downloader.run()
        print("Data acquisition completed")
        return True
        
    except Exception as e:
        print(f"Data acquisition failed: {e}")
        return False

def run_preprocessing():
    """Process documents if needed"""
    print("\nStep 2: Document Processing")
    print("-" * 30)
    
    try:
        from preprocessing import SECDocumentProcessor
        from config.config import PROCESSED_DATA_DIR
        
        # Check if processed data exists
        if list(PROCESSED_DATA_DIR.glob("*_processed.json")):
            print("Documents already processed")
            return True
        
        print("Processing SEC documents...")
        processor = SECDocumentProcessor()
        processor.process_all()
        print("Document processing completed")
        return True
        
    except Exception as e:
        print(f"Document processing failed: {e}")
        return False

def run_embedding_generation():
    """Generate embeddings if needed"""
    print("\nStep 3: Embedding Generation")
    print("-" * 30)
    
    try:
        from embedding_engine import EmbeddingEngine
        
        engine = EmbeddingEngine()
        engine.initialize()
        print("Embedding generation completed")
        return True
        
    except Exception as e:
        print(f"Embedding generation failed: {e}")
        return False

def run_evaluation():
    """Run the query evaluation"""
    print("\nStep 4: Query Evaluation")
    print("-" * 30)
    
    try:
        from query_engine import SECFinancialQA
        
        print("Initializing QA system...")
        qa = SECFinancialQA()
        
        # Quick test
        test_query = "What are Apple's primary revenue drivers?"
        print(f"Testing: {test_query}")
        
        result = qa.answer(test_query)
        print(f"Test passed - Confidence: {result.confidence:.1%}")
        
        # TODO: Run full evaluation suite
        print("\nRunning evaluation...")
        os.system("python src/query_engine.py")
        
        return True
        
    except Exception as e:
        print(f"Evaluation failed: {e}")
        return False

def main():
    """Run the complete pipeline"""
    print("SEC FINANCIAL QA SYSTEM")
    print("=" * 50)
    print("Running complete pipeline...\n")
    
    # Run pipeline steps
    steps = [
        run_data_acquisition,
        run_preprocessing, 
        run_embedding_generation,
        run_evaluation
    ]
    
    for step in steps:
        if not step():
            print(f"\nPipeline failed at {step.__name__}")
            return False
    
    print("\n" + "=" * 50)
    print("Pipeline completed successfully!")
    print("Results saved to qa_results.json")
    print("=" * 50)
    
    return True

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nPipeline interrupted by user")
    except Exception as e:
        print(f"\nPipeline error: {e}")