import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from google.colab import userdata
import json
import datetime

# --- Setup Connection ---
secret_json = userdata.get('GCP_JSON')
info = json.loads(secret_json)
creds = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
client = gspread.authorize(creds)

# Update this ID if the sheet changes
SHEET_URL = "https://docs.google.com/spreadsheets/d/1Xq2WX0NSDJJnpIBl4mo71ioKu9Gm0MnYIEx7HgdY67w/edit"
wb = client.open_by_url(SHEET_URL)

# --- Load Data ---
# Note: Ensure tab names match exactly (Internal Leads / Buyer Report)
internal_df = pd.DataFrame(wb.worksheet("Internal Leads").get_all_records())
buyer_df = pd.DataFrame(wb.worksheet("Buyer Report").get_all_records())

# --- Audit Logic ---
# Merge datasets to find where the buyer report is missing our internal leads
audit_master = pd.merge(internal_df, buyer_df, on='lead_id', how='left')

# 1. Ghost Leads: we have them, they don't
missing_leads = audit_master[audit_master['disposition'].isna()].copy()

# 2. Returns: Buyer marked as returned
returned_leads = audit_master[audit_master['disposition'] == 'Returned'].copy()

# 3. Voice AI RCA: Returns where call was too short (< 30s)
voice_fails = returned_leads[returned_leads['call_duration_sec'] < 30].copy()

# --- Calculations ---
total_expected = internal_df['revenue_expected'].sum()
risk_amt = missing_leads['revenue_expected'].sum() + returned_leads['credit_issued'].sum()
leakage_pct = (risk_amt / total_expected) * 100 if total_expected > 0 else 0

# Grab a few IDs for the logs
tech_ids = missing_leads['lead_id'].head(3).tolist()
voice_ids = voice_fails['lead_id'].head(3).tolist()

print(f"Audit Complete. Risk: ${risk_amt:,.2f} ({leakage_pct:.2f}%)")

# --- Export to Historical Log ---
results_tab = wb.worksheet("Audit Result")

# Check if we need headers (if sheet is new/empty)
if not results_tab.acell('A1').value:
    cols = ["Timestamp", "At Risk $", "Leakage %", "Missing Leads", "Short Calls", "Sample IDs"]
    results_tab.update('A1', [cols])

# Create the new row
timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
row_to_add = [
    timestamp, 
    f"${risk_amt:,.2f}", 
    f"{leakage_pct:.2f}%", 
    len(missing_leads), 
    len(voice_fails), 
    f"Tech: {tech_ids} | Voice: {voice_ids}"
]

results_tab.append_row(row_to_add)
print("Row appended to Audit Result tab.")
