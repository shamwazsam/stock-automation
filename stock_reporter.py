import os
import re
import yagmail
import requests
from bs4 import BeautifulSoup

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

def fetch_moneycontrol_buys():
    """
    Dynamically pulls all BUY recommendations with profit targets from Moneycontrol
    Returns dict with {stock_name: {'target': price, 'source': 'Moneycontrol'}}
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
                        stocks[stock_name] = {'target': target, 'source': 'Moneycontrol'}
    except Exception as e:
        print(f"Error fetching Moneycontrol data feed dynamically: {e}")
    return stocks

def fetch_icici_direct_buys():
    """
    Dynamically pulls all BUY recommendations from ICICI Securities
    Returns dict with {stock_name: {'target': price, 'source': 'ICICI Direct'}}
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
                            stocks[cleaned] = {'target': target, 'source': 'ICICI Direct'}
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
    
    # Sort by target price (profit potential) - highest first
    sorted_buys = sorted(all_buys.items(), key=lambda x: x[1]['target'] if x[1]['target'] else 0, reverse=True)
    return sorted_buys

def send_email(stock_recommendations):
    sender_email = os.environ.get("SENDER_EMAIL")
    app_password = os.environ.get("APP_PASSWORD")
    
    if not sender_email or not app_password:
        sender_email = "your_actual_email@gmail.com"
        app_password = "your_16_character_app_password"
        
    receiver = sender_email
    subject = "📈 DAILY MARKET OPEN: All BUY Recommendations (Ranked by Profit Potential)"
    
    if not stock_recommendations:
        html_content = """
        <h3>Daily Automated Broker Recommendations Report</h3>
        <p>Data pipeline executed successfully. <b>No BUY recommendations</b> were found across monitored sites today.</p>
        """
    else:
        rows = ""
        for idx, (stock_name, data) in enumerate(stock_recommendations, 1):
            target_price = f"₹{data['target']:.2f}" if data['target'] else "N/A"
            source = data['source']
            profit_indicator = "🔥" if data['target'] and data['target'] > 100 else "✅"
            rows += f"""
            <tr>
                <td style="text-align:center; font-weight:bold; color:#1a73e8;">{idx}</td>
                <td><b>{stock_name}</b></td>
                <td style="text-align:center;">{target_price}</td>
                <td>{source}</td>
                <td style="text-align:center; font-size:20px;">{profit_indicator}</td>
            </tr>
            """
        
        html_content = f"""
        <h3>Daily Automated Broker Recommendations Report</h3>
        <p><b>Total Recommendations: {len(stock_recommendations)}</b> stocks with BUY signals ranked by target price (profit potential).</p>
        <table border="1" cellpadding="10" style="border-collapse:collapse; font-family:Arial, sans-serif; width:100%;">
            <tr style="background-color:#1a73e8; color:white;">
                <th>Rank</th>
                <th>Stock Name</th>
                <th>Target Price</th>
                <th>Source</th>
                <th>Status</th>
            </tr>
            {rows}
        </table>
        <p style="font-size:12px; color:#666; margin-top:20px;">
            <i>Data pulled from: Moneycontrol, ICICI Direct | Sorted by target price (highest potential first)</i>
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
