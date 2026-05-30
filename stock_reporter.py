import os
import re
import yagmail
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

def clean_stock_name(text):
    """
    Cleans structural metadata out of scraped stock text fields 
    (e.g., converting 'BUY HDFC Bank | Target 1800' to just 'HDFC BANK')
    """
    if not text:
        return ""
    text = text.upper()
    # Remove common advisory directional keywords
    text = re.sub(r'\b(BUY|SELL|HOLD|ACCUMULATE|REDUCE|TARGET|PRICE)\b', '', text)
    # Strip away trailing target figures, pipeline brackets, or special characters
    text = re.sub(r'[\d|:,\.\-\(\)\/]', '', text)
    return " ".join(text.split()).strip()

def extract_profit_target(text):
    """
    Extracts target price from recommendation text
    (e.g., 'BUY HDFC Bank | Target 1800' -> 1800)
    """
    if not text:
        return None
    numbers = re.findall(r'\b\d+(?:\.\d+)?\b', text)
    if numbers:
        try:
            return float(numbers[-1])
        except:
            return None
    return None

def extract_current_price(text):
    """
    Extracts current price from text
    """
    if not text:
        return None
    numbers = re.findall(r'\b\d+(?:\.\d+)?\b', text)
    if numbers:
        try:
            return float(numbers[0])
        except:
            return None
    return None

def calculate_gain_percentage(current_price, target_price):
    """
    Calculates percentage gain from current to target price
    """
    if not current_price or not target_price or current_price <= 0:
        return None
    return round(((target_price - current_price) / current_price) * 100, 2)

def fetch_moneycontrol_buys():
    """
    Dynamically pulls all BUY recommendations with profit targets from Moneycontrol
    Returns dict with {stock_name: {'target': price, 'current': price, 'gain': %, 'source': 'Moneycontrol'}}
    """
    stocks = {}
    url = "https://www.moneycontrol.com/markets/recommendations/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        print("Fetching Moneycontrol recommendations...")
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            # Look for recommendation rows in tables
            tables = soup.find_all("table")
            for table in tables:
                rows = table.find_all("tr")
                for row in rows:
                    cells = row.find_all("td")
                    if len(cells) >= 4:
                        try:
                            stock_name = cells[0].text.strip()
                            recommendation = cells[1].text.strip().upper()
                            current_text = cells[2].text.strip()
                            target_text = cells[3].text.strip()
                            
                            if "BUY" in recommendation or "ACCUMULATE" in recommendation:
                                cleaned = clean_stock_name(stock_name)
                                if cleaned:
                                    current = extract_current_price(current_text)
                                    target = extract_profit_target(target_text)
                                    gain = calculate_gain_percentage(current, target)
                                    if current and target and gain:
                                        stocks[cleaned] = {
                                            'target': target,
                                            'current': current,
                                            'gain': gain,
                                            'source': 'Moneycontrol'
                                        }
                        except:
                            pass
        print(f"✓ Successfully scraped {len(stocks)} BUY recommendations from Moneycontrol")
    except Exception as e:
        print(f"✗ Error fetching Moneycontrol: {e}")
    return stocks

def fetch_icici_direct_buys():
    """
    Dynamically pulls all BUY recommendations from ICICI Direct
    Returns dict with {stock_name: {'target': price, 'current': price, 'gain': %, 'source': 'ICICI Direct'}}
    """
    stocks = {}
    url = "https://www.icicidirect.com/research/equity"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        print("Fetching ICICI Direct recommendations...")
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            # Look for recommendation data in tables
            tables = soup.find_all("table")
            for table in tables:
                rows = table.find_all("tr")
                for row in rows:
                    cells = row.find_all("td")
                    if len(cells) >= 5:
                        try:
                            stock_name = cells[0].text.strip()
                            rating = cells[1].text.strip().upper() if len(cells) > 1 else ""
                            current_text = cells[2].text.strip() if len(cells) > 2 else ""
                            target_text = cells[3].text.strip() if len(cells) > 3 else ""
                            
                            if "BUY" in rating:
                                cleaned = clean_stock_name(stock_name)
                                if cleaned:
                                    current = extract_current_price(current_text)
                                    target = extract_profit_target(target_text)
                                    gain = calculate_gain_percentage(current, target)
                                    if current and target and gain:
                                        stocks[cleaned] = {
                                            'target': target,
                                            'current': current,
                                            'gain': gain,
                                            'source': 'ICICI Direct'
                                        }
                        except:
                            pass
        print(f"✓ Successfully scraped {len(stocks)} BUY recommendations from ICICI Direct")
    except Exception as e:
        print(f"✗ Error fetching ICICI Direct: {e}")
    return stocks

def fetch_trendlyne_buys():
    """
    Dynamically pulls all BUY recommendations from Trendlyne
    Returns dict with {stock_name: {'target': price, 'current': price, 'gain': %, 'source': 'Trendlyne'}}
    """
    stocks = {}
    url = "https://trendlyne.com/research-reports/buy/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        print("Fetching Trendlyne recommendations...")
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            # Look for research report rows
            tables = soup.find_all("table")
            for table in tables:
                rows = table.find_all("tr")
                for row in rows:
                    cells = row.find_all("td")
                    if len(cells) >= 4:
                        try:
                            stock_name = cells[0].text.strip()
                            rating = cells[1].text.strip().upper() if len(cells) > 1 else ""
                            current_text = cells[2].text.strip() if len(cells) > 2 else ""
                            target_text = cells[3].text.strip() if len(cells) > 3 else ""
                            
                            if "BUY" in rating or "ACCUMULATE" in rating:
                                cleaned = clean_stock_name(stock_name)
                                if cleaned:
                                    current = extract_current_price(current_text)
                                    target = extract_profit_target(target_text)
                                    gain = calculate_gain_percentage(current, target)
                                    if current and target and gain:
                                        stocks[cleaned] = {
                                            'target': target,
                                            'current': current,
                                            'gain': gain,
                                            'source': 'Trendlyne'
                                        }
                        except:
                            pass
        print(f"✓ Successfully scraped {len(stocks)} BUY recommendations from Trendlyne")
    except Exception as e:
        print(f"✗ Error fetching Trendlyne: {e}")
    return stocks

def fetch_axis_direct_buys():
    """
    Dynamically pulls all investment ideas from Axis Direct SimpleHAI
    Returns dict with {stock_name: {'target': price, 'current': price, 'gain': %, 'source': 'Axis Direct'}}
    """
    stocks = {}
    url = "https://simplehai.axisdirect.in/research/research-ideas/investment-ideas"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        print("Fetching Axis Direct recommendations...")
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            # Look for investment ideas in tables
            tables = soup.find_all("table")
            for table in tables:
                rows = table.find_all("tr")
                for row in rows:
                    cells = row.find_all("td")
                    if len(cells) >= 4:
                        try:
                            stock_name = cells[0].text.strip()
                            rating = cells[1].text.strip().upper() if len(cells) > 1 else ""
                            current_text = cells[2].text.strip() if len(cells) > 2 else ""
                            target_text = cells[3].text.strip() if len(cells) > 3 else ""
                            
                            if "BUY" in rating or "ACCUMULATE" in rating:
                                cleaned = clean_stock_name(stock_name)
                                if cleaned:
                                    current = extract_current_price(current_text)
                                    target = extract_profit_target(target_text)
                                    gain = calculate_gain_percentage(current, target)
                                    if current and target and gain:
                                        stocks[cleaned] = {
                                            'target': target,
                                            'current': current,
                                            'gain': gain,
                                            'source': 'Axis Direct'
                                        }
                        except:
                            pass
        print(f"✓ Successfully scraped {len(stocks)} BUY recommendations from Axis Direct")
    except Exception as e:
        print(f"✗ Error fetching Axis Direct: {e}")
    return stocks

def fetch_consensus_report():
    print("\n" + "="*80)
    print("Initiating automated pipeline: Querying external live endpoints...")
    print("="*80 + "\n")
    
    mc_buys = fetch_moneycontrol_buys()
    icici_buys = fetch_icici_direct_buys()
    trendlyne_buys = fetch_trendlyne_buys()
    axis_buys = fetch_axis_direct_buys()
    
    # Combine all recommendations from all sources
    all_buys = {}
    all_buys.update(mc_buys)
    all_buys.update(icici_buys)
    all_buys.update(trendlyne_buys)
    all_buys.update(axis_buys)
    
    # Sort by gain percentage (highest first) - highest profit first
    sorted_buys = sorted(all_buys.items(), key=lambda x: x[1]['gain'] if x[1]['gain'] else -999, reverse=True)
    
    print(f"\n{'='*80}")
    print(f"Total BUY recommendations found: {len(sorted_buys)} stocks")
    print(f"{'='*80}\n")
    
    return sorted_buys

def print_console_report(stock_recommendations):
    """
    Prints a formatted table of recommendations to console
    """
    if not stock_recommendations:
        print("No BUY recommendations found today.")
        return
    
    print("\n" + "="*130)
    print(f"{'RANK':<6} {'STOCK NAME':<30} {'CURRENT PRICE':<18} {'TARGET PRICE':<18} {'POTENTIAL GAIN %':<18} {'SOURCE':<30} {'STATUS':<10}")
    print("="*130)
    
    for idx, (stock_name, data) in enumerate(stock_recommendations, 1):
        target_price = f"₹{data['target']:.2f}" if data['target'] else "N/A"
        current_price = f"₹{data['current']:.2f}" if data['current'] else "N/A"
        gain = data['gain']
        gain_str = f"{gain}%" if gain else "N/A"
        source = data['source']
        
        # Status icon based on gain percentage
        if gain and gain >= 20:
            status = "🔥🚀"
        elif gain and gain >= 10:
            status = "✅"
        else:
            status = "⚡"
        
        print(f"{idx:<6} {stock_name:<30} {current_price:<18} {target_price:<18} {gain_str:<18} {source:<30} {status:<10}")
    
    print("="*130)
    print(f"Legend: 🔥🚀 High Gain (≥20%) | ✅ Moderate Gain (10-20%) | ⚡ Standard Gain (<10%)")
    print("="*130 + "\n")

def send_email(stock_recommendations):
    sender_email = os.environ.get("SENDER_EMAIL")
    app_password = os.environ.get("APP_PASSWORD")
    
    if not sender_email or not app_password:
        sender_email = "your_actual_email@gmail.com"
        app_password = "your_16_character_app_password"
        
    receiver = sender_email
    subject = f"📈 DAILY MARKET OPEN: All BUY Recommendations - {datetime.now().strftime('%Y-%m-%d')} (Ranked by Profit %)"
    
    if not stock_recommendations:
        html_content = """
        <h3>Daily Automated Broker Recommendations Report</h3>
        <p>Data pipeline executed successfully. <b>No BUY recommendations</b> were found across monitored sites today.</p>
        """
    else:
        rows = ""
        for idx, (stock_name, data) in enumerate(stock_recommendations, 1):
            target_price = f"₹{data['target']:.2f}" if data['target'] else "N/A"
            current_price = f"₹{data['current']:.2f}" if data['current'] else "N/A"
            gain = data['gain']
            gain_str = f"{gain}%" if gain else "N/A"
            
            # Color code based on gain percentage
            if gain and gain >= 20:
                gain_color = "#0f9d58"  # Green for high gains
                gain_icon = "🔥🚀"
            elif gain and gain >= 10:
                gain_color = "#3366cc"  # Blue for moderate gains
                gain_icon = "✅"
            else:
                gain_color = "#f9ab00"  # Orange for low gains
                gain_icon = "⚡"
            
            source = data['source']
            rows += f"""
            <tr>
                <td style="text-align:center; font-weight:bold; color:#1a73e8;">{idx}</td>
                <td><b>{stock_name}</b></td>
                <td style="text-align:center;">{current_price}</td>
                <td style="text-align:center;">{target_price}</td>
                <td style="text-align:center; font-weight:bold; color:{gain_color};">{gain_str}</td>
                <td>{source}</td>
                <td style="text-align:center; font-size:18px;">{gain_icon}</td>
            </tr>
            """
        
        html_content = f"""
        <h3>Daily Automated Broker Recommendations Report</h3>
        <p><b>Report Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><b>Total Recommendations: {len(stock_recommendations)}</b> stocks with BUY signals ranked by potential gain % (highest first).</p>
        <table border="1" cellpadding="10" style="border-collapse:collapse; font-family:Arial, sans-serif; width:100%;">
            <tr style="background-color:#1a73e8; color:white;">
                <th>Rank</th>
                <th>Stock Name</th>
                <th>Current Price</th>
                <th>Target Price</th>
                <th>Potential Gain %</th>
                <th>Source</th>
                <th>Status</th>
            </tr>
            {rows}
        </table>
        <p style="font-size:12px; color:#666; margin-top:20px;">
            <i>Data pulled from: Moneycontrol, ICICI Direct, Trendlyne, Axis Direct | Sorted by potential gain % (highest first)</i><br>
            <i>🔥🚀 High Gain (≥20%) | ✅ Moderate Gain (10-20%) | ⚡ Standard Gain (&lt;10%)</i><br>
            <i>Disclaimer: These are analyst recommendations. Always do your own research before investing.</i>
        </p>
        """
    
    try:
        yag = yagmail.SMTP(sender_email, app_password)
        yag.send(to=receiver, subject=subject, contents=html_content)
        print("✓ Success: Real-time aggregated data dispatch sent to inbox!")
    except Exception as e:
        print(f"✗ Failed to complete email execution routing: {e}")

if __name__ == "__main__":
    recommendations = fetch_consensus_report()
    print_console_report(recommendations)
    send_email(recommendations)
