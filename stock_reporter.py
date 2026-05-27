import pandas as pd
import yagmail

def fetch_broker_recommendations():
    # Simulated current cross-broker picks for testing
    moneycontrol_list = ['Torrent Pharma', 'J K Cements', 'HDFC Bank', 'Persistent Systems']
    icici_direct_list = ['Torrent Pharma', 'J K Cements', 'Va Tech Wabag', 'HDFC Bank']
    axis_direct_list = ['Torrent Pharma', 'J K Cements', 'Va Tech Wabag', 'HDFC Bank', 'Eicher Motors']
    
    # Finds only the stocks present in ALL three lists
    common_buys = list(set(moneycontrol_list) & set(icici_direct_list) & set(axis_direct_list))
    return common_buys

def send_email(common_stocks):
    # CRITICAL: Replace these with your real details
    sender_email = "shamwazsam@gmail.com" 
    app_password = "ofobgycmjsqrvpbz" # No spaces
    receiver = "shamwazsam@gmail.com" 
    
    subject = "Weekly Consensus Stock Report"
    
    html_content = f"""
    <h3>Weekly Automated Broker Consensus Report</h3>
    <p>The following shares have matching <b>BUY</b> recommendations across Moneycontrol, Axis Direct, and ICICI Direct:</p>
    <table border="1" cellpadding="5" style="border-collapse:collapse; font-family:Arial;">
        <tr style="background-color:#f2f2f2;">
            <th>Stock Name</th>
            <th>Signal</th>
        </tr>
        {"".join([f"<tr><td><b>{stock}</b></td><td style='color:green;'>Consensus Buy</td></tr>" for stock in common_stocks])}
    </table>
    """
    
    try:
        yag = yagmail.SMTP(sender_email, app_password)
        yag.send(to=receiver, subject=subject, contents=html_content)
        print("Success: Test email sent!")
    except Exception as e:
        print(f"Error sending email: {e}")

if __name__ == "__main__":
    stocks = fetch_broker_recommendations()
    send_email(stocks)
