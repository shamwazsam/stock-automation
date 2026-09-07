#!/usr/bin/env python3
import time
import re
import pandas as pd
import requests
from bs4 import BeautifulSoup
import yfinance as yf
import gspread
from google.oauth2.service_account import Credentials
import json
import os
from tabulate import tabulate

# Google Sheets Configuration
SHEET_ID = "15-HLXriIL-25NVjDZDa81Ht_qHUowdAOvaZ59ieXNJk"
SHEET_NAME = "Sheet1"  # Update if your sheet tab has a different name

# Set up browser headers
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}

def authenticate_google_sheets():
    """Authenticate with Google Sheets API using service account from environment variable."""
    try:
        # Get the service account JSON from environment variable (GitHub secret)
        service_account_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
        
        if not service_account_json:
            print("⚠️ GOOGLE_SERVICE_ACCOUNT_JSON environment variable not found")
            return None
        
        # Parse the JSON string
        service_account_info = json.loads(service_account_json)
        
        # Authenticate with Google Sheets
        credentials = Credentials.from_service_account_info(
            service_account_info,
            scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
        )
        client = gspread.authorize(credentials)
        print("✅ Successfully authenticated with Google Sheets API")
        return client
    except Exception as e:
        print(f"❌ Google Sheets authentication failed: {e}")
        return None

def fetch_data_from_google_sheet(client):
    """Fetch stock recommendations from Google Sheet."""
    print("📊 Fetching data from Google Sheet...")
    scraped_data = []
    
    try:
        sheet = client.open_by_key(SHEET_ID)
        worksheet = sheet.worksheet(SHEET_NAME)
        
        # Get all records (assumes headers in first row)
        records = worksheet.get_all_records()
        print(f"📋 Found {len(records)} records in Google Sheet")
        
        for record in records:
            # Adjust column names based on your sheet structure
            # Common column names: Broker, Stock, Company, Target Price, Target, Duration
            broker = record.get('Broker', record.get('broker', 'N/A'))
            stock_name = record.get('Stock', record.get('Company', record.get('stock', '')))
            target_price_str = record.get('Target Price', record.get('Target', record.get('target', 0)))
            duration = record.get('Duration', record.get('duration', '12 Months'))
            
            if stock_name and target_price_str:
                try:
                    # Clean and convert target price
                    target_price = float(str(target_price_str).replace(',', '').replace('₹', '').strip())
                    scraped_data.append({
                        "broker": str(broker),
                        "search_query": str(stock_name).strip(),
                        "target": target_price,
                        "duration": str(duration)
                    })
                except (ValueError, AttributeError) as e:
                    print(f"⚠️ Skipping row - could not parse: {record}")
                    continue
        
        print(f"✅ Successfully loaded {len(scraped_data)} valid recommendations from Google Sheet.")
    except Exception as e:
        print(f"❌ Failed to fetch Google Sheet data: {e}")
    
    return scraped_data

def fetch_live_broker_calls():
    """
    Fallback: Scrapes broker recommendations from Moneycontrol if needed.
    """
    print("🌐 Connecting to live broker recommendation feeds...")
    url = "https://moneycontrol.com"
    
    scraped_data = []
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            print(f"⚠️ Link connection returned status code: {response.status_code}")
            return scraped_data
            
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Target the main news/brokerage list container
        stories = soup.find_all("li", class_="clearfix")
        
        for story in stories:
            title_element = story.find("h2")
            if not title_element:
                continue
                
            title_text = title_element.get_text(strip=True)
            
            # Filter text to isolate explicit "Buy" recommendations
            if "Buy" in title_text or "Accumulate" in title_text:
                match = re.search(r'(?:Buy|Accumulate)\s+([^;:]+)(?:;|:)\s*target\s+of\s+(?:Rs\.?\s*)?(\d+[\d,]*)\s*(?::|by)?\s*([A-Za-z\s]+)?', title_text, re.IGNORECASE)
                
                if match:
                    stock_raw = match.group(1).strip()
                    target_raw = match.group(2).strip()
                    broker_raw = match.group(3).strip() if match.group(3) else "Institutional Call"
                    
                    try:
                        target_price = float(target_raw.replace(',', ''))
                        scraped_data.append({
                            "broker": broker_raw,
                            "search_query": stock_raw,
                            "target": target_price,
                            "duration": "12 Months"
                        })
                    except ValueError:
                        continue
                        
        print(f"✅ Successfully scraped {len(scraped_data)} active calls from web.")
    except Exception as e:
        print(f"❌ Web Scraping failed: {e}")
        
    return scraped_data

def match_ticker_and_get_price(query_name):
    """
    Queries yfinance to match stock name to NSE ticker and fetch live price.
    """
    overrides = {
        "m&m": "M&M.NS", 
        "tata motors": "TATAMOTORS.NS", 
        "reliance": "RELIANCE.NS",
        "hdfc bank": "HDFCBANK.NS", 
        "icici bank": "ICICIBANK.NS", 
        "sbi": "SBIN.NS",
        "tcs": "TCS.NS",
        "infosys": "INFY.NS",
        "wipro": "WIPRO.NS",
        "axis bank": "AXISBANK.NS",
        "maruti": "MARUTI.NS",
        "bajaj auto": "BAJAJJ.NS"
    }
    
    clean_query = query_name.lower().strip()
    if clean_query in overrides:
        ticker_symbol = overrides[clean_query]
    else:
        ticker_symbol = f"{query_name.upper().replace(' ', '')}.NS"

    try:
        ticker_obj = yf.Ticker(ticker_symbol)
        hist = ticker_obj.history(period="1d")
        if not hist.empty:
            cmp = hist['Close'].iloc[-1]
            official_name = ticker_obj.info.get('shortName', query_name)
            return ticker_symbol, cmp, official_name
    except Exception as e:
        pass
        
    return None, None, query_name

def print_table(data, title):
    """Print data in a formatted table."""
    print(f"\n{'=' * 120}")
    print(f"  {title}")
    print(f"{'=' * 120}")
    
    if not data:
        print("No data available")
        return
    
    # Create DataFrame for better formatting
    df = pd.DataFrame(data)
    
    # Print with tabulate for better formatting
    print(tabulate(df, headers='keys', tablefmt='grid', showindex=False))
    print()

def run_live_pipeline():
    start_time = time.time()
    
    print("\n" + "=" * 120)
    print("  🚀 STOCK AUTOMATION PIPELINE STARTED")
    print("=" * 120)
    
    # Try Google Sheets first, fallback to web scraping
    client = authenticate_google_sheets()
    
    if client:
        raw_calls = fetch_data_from_google_sheet(client)
    else:
        print("⚠️ Google Sheets unavailable, falling back to web scraping...")
        raw_calls = fetch_live_broker_calls()
    
    if not raw_calls:
        print("❌ No recommendations found. Check connection or configuration.")
        return

    pipeline_report = {}
    all_results = []
    
    print(f"\n📊 Matching tickers and checking live stock prices for {len(raw_calls)} stocks...")
    print("-" * 120)
    successful_matches = 0
    failed_matches = 0
    
    for idx, item in enumerate(raw_calls[:20], 1):
        print(f"  [{idx:2d}] {item['search_query']:30s} → ", end="", flush=True)
        ticker, cmp, fine_name = match_ticker_and_get_price(item["search_query"])
        
        if cmp and ticker:
            successful_matches += 1
            broker = item["broker"]
            target = item["target"]
            
            return_pct = ((target - cmp) / cmp) * 100
            
            row_entry = {
                "Stock Name": fine_name,
                "Ticker": ticker,
                "Current Price": f"₹{cmp:,.2f}",
                "Target Price": f"₹{target:,.2f}",
                "Upside %": f"{return_pct:+.2f}%",
                "Duration": item["duration"],
                "Broker": broker
            }
            
            all_results.append(row_entry)
            
            if broker not in pipeline_report:
                pipeline_report[broker] = []
            pipeline_report[broker].append(row_entry)
            print(f"✅ {ticker:15s} CMP: ₹{cmp:>8,.2f} | Target: ₹{target:>8,.2f} | Return: {return_pct:>7.2f}%")
        else:
            failed_matches += 1
            print(f"❌ (Could not fetch price)")

    print("-" * 120)
    
    # Summary section
    print(f"\n{'=' * 120}")
    print(f"  📈 EXECUTION SUMMARY")
    print(f"{'=' * 120}")
    print(f"  Total Stocks Processed: {min(len(raw_calls), 20)}")
    print(f"  ✅ Successful Matches: {successful_matches}")
    print(f"  ❌ Failed Matches: {failed_matches}")
    print(f"  Success Rate: {(successful_matches / min(len(raw_calls), 20) * 100):.1f}%")
    print(f"{'=' * 120}\n")
    
    if not all_results:
        print("⚠️ No stocks with valid prices found.")
        return
    
    # Print overall results table
    print_table(all_results, "📊 ALL STOCK RECOMMENDATIONS (SORTED BY UPSIDE %)")
    
    # Print results grouped by broker
    for broker, rows in sorted(pipeline_report.items()):
        print_table(rows, f"🏢 RECOMMENDATIONS FROM: {broker.upper()}")
    
    # Summary statistics
    all_df = pd.DataFrame(all_results)
    if not all_df.empty:
        print(f"\n{'=' * 120}")
        print(f"  📈 STATISTICS")
        print(f"{'=' * 120}")
        
        # Extract numeric values for statistics
        try:
            upside_values = [float(x.strip().rstrip('%')) for x in all_df['Upside %']]
            current_prices = [float(x.replace('₹', '').replace(',', '')) for x in all_df['Current Price']]
            target_prices = [float(x.replace('₹', '').replace(',', '')) for x in all_df['Target Price']]
            
            print(f"  Average Upside: {sum(upside_values)/len(upside_values):>7.2f}%")
            print(f"  Max Upside: {max(upside_values):>7.2f}%")
            print(f"  Min Upside: {min(upside_values):>7.2f}%")
            print(f"  Average Current Price: ₹{sum(current_prices)/len(current_prices):>8,.2f}")
            print(f"  Average Target Price: ₹{sum(target_prices)/len(target_prices):>8,.2f}")
        except:
            pass
        
        print(f"{'=' * 120}\n")
        
    print(f"✅ Pipeline execution completed in {time.time() - start_time:.2f} seconds.")
    print("=" * 120 + "\n")

if __name__ == "__main__":
    run_live_pipeline()
