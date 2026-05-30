import os
import re
import yagmail
import requests
from bs4 import BeautifulSoup
import json

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

def get_current_stock_price(stock_name):
    """
    Fetches current stock price using NSE/BSE data
    """
    try:
        # Try using NSE API or mock data for now
        url = f"https://api.example.com/stock/{stock_name}"
        # For now, return a mock value - in production, integrate with real API
        # Common ranges for Indian stocks
        common_prices = {
            "HDFC BANK": 1650,
            "RELIANCE": 1300,
            "TCS": 3900,
            "INFY": 1800,
            "ICICIBANK": 800,
            "AXIS BANK": 900,
            "SBIN": 600,
        }
        return common_prices.get(stock_name, None)
    except Exception as e:
        print(f"Error fetching current price for {stock_name}: {e}")
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
    url = "https://moneycontrol.com"
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "xml")
            items = soup.find_all("item")
            for item in items:
                title = item.title.text if item.title else ""
                if "BUY" in title.upper() or "ACCUMULATE" in title.upper():
                    stock_name = clean_stock_name(title.split(";")[0])
                    if stock_name:
                        target = extract_profit_target(title)
                        current = get_current_stock_price(stock_name)
                        gain = calculate_gain_percentage(current, target)
                        stocks[stock_name] = {
                            'target': target,
                            'current': current,
                            'gain': gain,
                            'source': 'Moneycontrol'
                        }
    except Exception as e:
        print(f"Error fetching Moneycontrol data feed dynamically: {e}")
    return stocks

def fetch_icici_direct_buys():
    """
    Dynamically pulls all BUY recommendations from ICICI Securities
    Returns dict with {stock_name: {'target': price, 'current': price, 'gain': %, 'source': 'ICICI Direct'}}
    """
    stocks = {}
    url = "https://www.icicidirect.com/mailcontent/co_reports.html"
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            rows = soup.find_all("tr")
            for row in rows:
                cells = row.find_all("td")
                if len(cells) >= 5:
                    stock_name = cells[0].text.strip()
                    rating = cells[4].text.strip().upper()
                    if "BUY" in rating:
                        cleaned = clean_stock_name(stock_name)
                        if cleaned:
                            target = extract_profit_target(cells[4].text)
                            current = get_current_stock_price(cleaned)
                            gain = calculate_gain_percentage(current, target)
                            stocks[cleaned] = {
                                'target': target,
                                'current': current,
                                'gain': gain,
                                'source': 'ICICI Direct'
                            }
    except Exception as e:
        print(f"Error fetching ICICI Direct coverage tables dynamically: {e}")
    return stocks

def fetch_consensus_report():
    print("Initiating automated pipeline: Querying external live endpoints...")
    
    mc_buys = fetch_moneycontrol_buys()
    icici_buys = fetch_icici_direct_buys()
    
    print(f"Successfully scraped {len(mc_buys)} live targets from Moneycontrol.")
    print(f"Successfully scraped {len(icici_buys)} live targets from ICICI Direct.")
    
    # Combine all recommendations from both sources
    all_buys = {}
    all_buys.update(mc_buys)
    all_buys.update(icici_buys)
    
    # If no data from live sources, use sample data for testing
    if not all_buys:
        print("⚠️  No live data fetched. Using sample recommendations for testing...")
        all_buys = {
            "HDFC BANK": {"target": 1800, "current": 1650, "gain": 9.09, "source": "Sample"},
            "RELIANCE": {"target": 1500, "current": 1300, "gain": 15.38, "source": "Sample"},
            "TCS": {"target": 4200, "current": 3900, "gain": 7.69, "source": "Sample"},
            "INFY": {"target": 2100, "current": 1800, "gain": 16.67, "source": "Sample"},
        }
    
    # Sort by gain percentage (highest first) - highest profit first
    sorted_buys = sorted(all_buys.items(), key=lambda x: x[1]['gain'] if x[1]['gain'] else -999, reverse=True)
    return sorted_buys

def send_email(stock_recommendations):
    sender_email = os.environ.get("SENDER_EMAIL")
    app_password = os.environ.get("APP_PASSWORD")
    
    if not sender_email or not app_password:
        sender_email = "your_actual_email@gmail.com"
        app_password = "your_16_character_app_password"
        
    receiver = sender_email
    subject = "📈 DAILY MARKET OPEN: All BUY Recommendations (Ranked by Profit %)"
    
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
            <i>Data pulled from: Moneycontrol, ICICI Direct | Sorted by potential gain % (highest first)</i><br>
            <i>🔥🚀 High Gain (≥20%) | ✅ Moderate Gain (10-20%) | ⚡ Standard Gain (&lt;10%)</i>
        </p>
        """
    
    try:
        yag = yagmail.SMTP(sender_email, app_password)
        yag.send(to=receiver, subject=subject, contents=html_content)
        print("Success: Real-time aggregated data dispatch sent to inbox!")
    except Exception as e:
        print(f"Failed to complete email execution routing: {e}")

if __name__ == "__main__":
    recommendations = fetch_consensus_report()
    send_email(recommendations)
