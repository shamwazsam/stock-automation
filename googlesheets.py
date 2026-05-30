import os
import json
import yagmail
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

# --- CONFIGURATION ---
# Replace with your actual Google Sheet ID (found in the Sheet's URL)
SPREADSHEET_ID = "15-HLXriIL-25NVjDZDa81Ht_qHUowdAOvaZ59ieXNJk"
# Replace with the exact name of the tab/sheet (e.g., "Sheet1" or "Recommendations")
RANGE_NAME = "Zerodha!A1:Z100" 
RECEIVER_EMAIL = "shamwazsam@gmail.com"

def get_sheet_data():
    """Fetches data from Google Sheets using a Service Account."""
    # Define the scope required to read Google Sheets
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    
    # Load credentials from the environment variable (configured in GitHub Secrets)
    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not creds_json:
        raise ValueError("Missing GOOGLE_SERVICE_ACCOUNT_JSON secret.")
        
    # Authenticate using the service account key
    creds = service_account.Credentials.from_service_account_info(
        json.loads(creds_json), scopes=SCOPES
    )
    
    # Build the Google Sheets API client
    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets()
    
    # Request data from the sheet
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    rows = result.get('values', [])
    
    if not rows:
        print("No data found in the spreadsheet.")
        return None
        
    # Convert the raw rows into a clean Pandas DataFrame
    df = pd.DataFrame(rows[1:], columns=rows[0])
    return df

def send_email(dataframe):
    """Sends the DataFrame styled as an HTML table via email."""
    sender = os.environ.get("SENDER_EMAIL")
    password = os.environ.get("APP_PASSWORD")
    
    if not sender or not password:
        raise ValueError("Missing SENDER_EMAIL or APP_PASSWORD environment variables.")
    
    # Convert DataFrame to a clean, styled HTML table
    html_table = dataframe.to_html(index=False, classes='table table-striped')
    
    # Add simple CSS styling to make the email look professional
    email_body = f"""
    <html>
      <head>
        <style>
          table {{ border-collapse: collapse; width: 100%; font-family: Arial, sans-serif; }}
          th {{ background-color: #0073e6; color: white; padding: 8px; text-align: left; }}
          td {{ border: 1px solid #ddd; padding: 8px; }}
          tr:nth-child(even) {{ background-color: #f2f2f2; }}
        </style>
      </head>
      <body>
        <h2>Daily Broker Stock Report</h2>
        <p>Here is the latest stock data extracted from your Google Sheet:</p>
        {html_table}
        <br>
        <p><i>Automated via GitHub Actions</i></p>
      </body>
    </html>
    """
    
    # Initialize yagmail and dispatch the message
    yag = yagmail.SMTP(sender, password)
    yag.send(
        to=RECEIVER_EMAIL,
        subject="Daily Weekday Broker Stock Report",
        contents=email_body
    )
    print("Email dispatched successfully!")

if __name__ == "__main__":
    df_data = get_sheet_data()
    if df_data is not None:
        send_email(df_data)
