
import sys
import os
import re
import json
import time
import shutil
from datetime import datetime
from pathlib import Path
from sec_edgar_downloader import Downloader

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import RAW_DATA_DIR, COMPANIES

FILING_TYPES = ["10-K", "10-Q", "8-K", "DEF 14A", "3", "4", "5"]

FILING_LIMITS = {
    "10-K": 8, "10-Q": 16, "8-K": 20, 
    "DEF 14A": 6, "3": 8, "4": 20, "5": 6
}

DATE_RANGES = {
    "3": "2020-01-01", 
    "4": "2020-01-01", 
    "5": "2020-01-01",
    "10-K": "2018-01-01", 
    "10-Q": "2018-01-01", 
    "default": "2020-01-01"
}

class SECDownloader:
    def __init__(self, data_dir=None):
        self.base_path = Path(data_dir) if data_dir else RAW_DATA_DIR
        self.temp_path = self.base_path / "temp_download"
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.temp_path.mkdir(parents=True, exist_ok=True)
        
        user_agent = os.getenv("SEC_USER_AGENT", "research@example.com")
        self.downloader = Downloader("SECFinancialQA", user_agent, str(self.temp_path))
        self.accession_pattern = re.compile(r'(\d{10})-(\d{2})-(\d{6})')
        print(f"SEC Downloader initialized. Data: {self.base_path}")

    def extract_metadata(self, file_path, ticker, filing_type):
        match = self.accession_pattern.search(file_path.name)
        if match:
            year_int = int(match.groups()[1])
            filing_year = (1900 if year_int >= 90 else 2000) + year_int
        else:
            filing_year = None
            
        stats = file_path.stat()
        return {
            'ticker': ticker, 
            'company_name': COMPANIES.get(ticker, ticker),
            'filing_type': filing_type, 
            'file_path': str(file_path.relative_to(self.base_path)),
            'accession_number': match.group(0) if match else None, 
            'estimated_year': filing_year,
            'file_size': stats.st_size, 
            'file_extension': file_path.suffix
        }

    def organize_files(self, ticker):
        source_path = self.temp_path / "sec-edgar-filings" / ticker
        target_path = self.base_path / ticker
        
        if not source_path.exists():
            return 0, []
            
        target_path.mkdir(exist_ok=True)
        total_moved, all_metadata = 0, []
        
        for filing_type in source_path.iterdir():
            if not filing_type.is_dir():
                continue
                
            target_filing_path = target_path / filing_type.name
            target_filing_path.mkdir(exist_ok=True)
            
            limit = FILING_LIMITS.get(filing_type.name, 10)
            files_moved = 0
            
            for accession_dir in sorted(filing_type.iterdir(), reverse=True):
                if not accession_dir.is_dir() or files_moved >= limit:
                    continue
                    
                for file_path in accession_dir.iterdir():
                    if (file_path.suffix.lower() in ['.html', '.xml', '.htm'] and 
                        files_moved < limit and file_path.stat().st_size > 500):
                        
                        target_file = target_filing_path / f"{accession_dir.name}_{file_path.name}"
                        try:
                            shutil.move(str(file_path), str(target_file))
                            all_metadata.append(self.extract_metadata(target_file, ticker, filing_type.name))
                            total_moved += 1
                            files_moved += 1
                        except Exception as e:
                            print(f"Error moving {file_path.name}: {e}")
                            
        json.dump(all_metadata, open(target_path / 'filing_metadata.json', 'w'), indent=2, default=str)
        summary = self.create_summary(all_metadata, ticker)
        json.dump(summary, open(target_path / 'filing_summary.json', 'w'), indent=2)
        
        return total_moved, all_metadata

    def create_summary(self, metadata_list, ticker):
        summary = {
            'ticker': ticker, 'company_name': COMPANIES.get(ticker, ticker),
            'total_files': len(metadata_list), 'filing_types': {}, 'years_covered': set(), 'total_size': 0
        }
        
        for meta in metadata_list:
            filing_type = meta['filing_type']
            summary['filing_types'][filing_type] = summary['filing_types'].get(filing_type, 0) + 1
            if meta['estimated_year']:
                summary['years_covered'].add(meta['estimated_year'])
            summary['total_size'] += meta['file_size']
            
        summary['years_covered'] = sorted(list(summary['years_covered']))
        summary['size_mb'] = round(summary['total_size'] / (1024 * 1024), 2)
        return summary

    def download_filings(self, ticker):
        print(f"Downloading {ticker}")
        for filing_type in FILING_TYPES:
            try:
                after_date = DATE_RANGES.get(filing_type, DATE_RANGES["default"])
                limit = FILING_LIMITS.get(filing_type, 10)
                
                self.downloader.get(filing_type, ticker, download_details=True, after=after_date, limit=limit)
                print(f"  {filing_type} (limit: {limit})")
                time.sleep(0.2)
            except Exception as e:
                print(f"  {filing_type}: {e}")
                
        return self.organize_files(ticker)

    def get_stats(self, ticker):
        ticker_path = self.base_path / ticker
        stats = {}
        for filing_type in FILING_TYPES:
            form_path = ticker_path / filing_type
            if form_path.exists():
                files = list(form_path.glob("*.html")) + list(form_path.glob("*.xml"))
                total_size = sum(f.stat().st_size for f in files)
                stats[filing_type] = {'count': len(files), 'size_mb': total_size / (1024 * 1024)}
        return stats

    def run(self, companies=None):
        start_time = datetime.now()
        companies_to_process = companies or list(COMPANIES.keys())
        total_files, all_metadata = 0, []
        
        print(f"Processing {len(companies_to_process)} companies with limits: {FILING_LIMITS}")
        
        for i, ticker in enumerate(companies_to_process, 1):
            print(f"\n[{i}/{len(companies_to_process)}] {ticker} ({COMPANIES.get(ticker, 'Unknown')})")
            try:
                files_moved, metadata = self.download_filings(ticker)
                stats = self.get_stats(ticker)
                
                for filing_type, stat in stats.items():
                    if stat['count'] > 0:
                        print(f"  {filing_type}: {stat['count']} files ({stat['size_mb']:.1f} MB)")
                        
                total_files += files_moved
                all_metadata.extend(metadata)
                print(f"  Total: {files_moved} files")
                
            except Exception as e:
                print(f"   Error: {e}")
            time.sleep(1.0)
            
        json.dump(all_metadata, open(self.base_path / 'master_metadata.json', 'w'), indent=2, default=str)
        if self.temp_path.exists():
            shutil.rmtree(self.temp_path)
            
        duration = datetime.now() - start_time
        print(f"\n{'='*50}")
        print(f"Completed: {total_files} files in {duration}")
        self.print_summary(companies_to_process)
        return total_files

    def print_summary(self, companies):
        print(f"\nFINAL SUMMARY:")
        total_files, total_size, filing_totals = 0, 0, {}
        
        for ticker in companies:
            summary_file = self.base_path / ticker / 'filing_summary.json'
            if summary_file.exists():
                summary = json.load(open(summary_file))
                print(f"{ticker}: {summary['total_files']} files ({summary['size_mb']} MB)")
                total_files += summary['total_files']
                total_size += summary['total_size']
                for k, v in summary['filing_types'].items():
                    filing_totals[k] = filing_totals.get(k, 0) + v
                    
        print(f"Total: {total_files} files, {total_size/(1024*1024):.1f} MB")
        print(f"By type: {filing_totals}")


if __name__ == '__main__':
    downloader = SECDownloader()
    
    print(f"Starting full download for all {len(COMPANIES)} companies:")
    print(f"Companies: {list(COMPANIES.keys())}")
    
    try:
        total = downloader.run()  
        print(f"\n Success: {total} files downloaded for all companies")
    except Exception as e:
        print(f" Error: {e}")
        import traceback
        traceback.print_exc()
