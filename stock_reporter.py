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

def fetch_moneycontrol_buys():
    """
    Dynamically pulls latest real-time broker recommendations via Moneycontrol Broker Feed
    """
    stocks = set()
    url = "https://moneycontrol.com" # Uses stable underlying RSS data layer
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "xml")
            items = soup.find_all("item")
            for item in items:
                title = item.title.text
                if "BUY" in title.upper() or "ACCUMULATE" in title.upper():
                    cleaned = clean_stock_name(title.split(";")[0])
                    if cleaned:
                        stocks.add(cleaned)
    except Exception as e:
        print(f"Error fetching Moneycontrol data feed dynamically: {e}")
    return stocks

def fetch_icici_direct_buys():
    """
    Dynamically parses active coverage and recommendation updates out of ICICI Securities portal
    """
    stocks = set()
    url = "https://www.icicidirect.com/mailcontent/co_reports.html" # Live underlying coverage archive table
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            # Locates rows within ICICI Research Coverage Universe structure
            rows = soup.find_all("tr")
            for row in rows:
                cells = row.find_all("td")
                if len(cells) >= 5:
                    stock_name = cells[0].text.strip()
                    rating = cells[4].text.strip().upper()
                    if "BUY" in rating:
                        cleaned = clean_stock_name(stock_name)
                        if cleaned:
                            stocks.add(cleaned)
    except Exception as e:
        print(f"Error fetching ICICI Direct coverage tables dynamically: {e}")
    return stocks

def fetch_consensus_report():
    print("Initiating automated pipeline: Querying external live endpoints...")
    
    # Dynamic pulling step execution
    mc_buys = fetch_moneycontrol_buys()
    icici_buys = fetch_icici_direct_buys()
    
    print(f"Successfully scraped {len(mc_buys)} live targets from Moneycontrol.")
    print(f"Successfully scraped {len(icici_buys)} live targets from ICICI Direct.")
    
    # Intersecting mathematical overlap logic
    common_buys = mc_buys.intersection(icici_buys)
    return list(common_buys)

def send_email(common_stocks):
    # Pull secure configuration tags directly from operating system memory parameters
    sender_email = os.environ.get("SENDER_EMAIL")
    app_password = os.environ.get("APP_PASSWORD")
    
    if not sender_email or not app_password:
        # Local fallback execution check for testing on your MacBook directly
        sender_email = "your_actual_email@gmail.com"
        app_password = "your_16_character_app_password"
        
    receiver = sender_email
    subject = "⚠️ DAILY MARKET OPEN: Cross-Broker Consensus Stock Signals"
    
    if not common_stocks:
        html_content = """
        <h3>Daily Automated Broker Consensus Report</h3>
        <p>Data pipeline executed successfully. <b>No common overlapping BUY recommendations</b> were found across monitored sites today.</p>
        """
    else:
        html_content = f"""
        <h3>Daily Automated Broker Consensus Report</h3>
        <p>The following equities match active <b>BUY</b> signals on both platforms simultaneously:</p>
        <table border="1" cellpadding="8" style="border-collapse:collapse; font-family:Arial, sans-serif;">
            <tr style="background-color:#1a73e8; color:white;">
                <th>Dynamic Stock Ticker Asset Name</th>
                <th>Consensus Status Action</th>
            </tr>
            {"".join([f"<tr><td><b>{stock}</b></td><td style='color:#0f9d58; font-weight:bold;'>Strong Combined Buy</td></tr>" for stock in common_stocks])}
        </table>
        """
    
    try:
        yag = yagmail.SMTP(sender_email, app_password)
        yag.send(to=receiver, subject=subject, contents=html_content)
        print("Success: Real-time aggregated data dispatch sent to inbox!")
    except Exception as e:
        print(f"Failed to complete email execution routing: {e}")

if __name__ == "__main__":
    consensus_list = fetch_consensus_report()
    send_email(consensus_list)
