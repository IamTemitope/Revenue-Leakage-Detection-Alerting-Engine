import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
import datetime
import os
import re
from dotenv import load_dotenv

# 1. LOAD THE ENV
load_dotenv()

# 2. PARSE THE SECRET
gcp_json = os.getenv('GCP_JSON_ADAPTER')

if not gcp_json:
    raise EnvironmentError("❌ 'GCP_JSON_ADAPTER' is missing from .env file.")

try:
    # Strip accidental surrounding quotes
    gcp_json = gcp_json.strip().strip("'\"")

    # Fix invalid JSON escape sequences (e.g. \m, \e, \i) that appear
    # when base64 key data gets interpreted by the .env parser on Windows.
    # Valid JSON escapes are: \" \\ \/ \b \f \n \r \t \uXXXX
    gcp_json = re.sub(r'\\([^"\\/bfnrtu])', r'\\\\\1', gcp_json)

    info = json.loads(gcp_json)

    # Convert literal '\n' text in private_key into actual newline characters
    if "private_key" in info:
        info["private_key"] = info["private_key"].replace("\\n", "\n")

    creds = Credentials.from_service_account_info(
        info,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    client = gspread.authorize(creds)
    print("✅ Auth Successful.")

except json.JSONDecodeError as e:
    raise ValueError(f"❌ Auth Failed — invalid JSON: {e}\nDEBUG: String starts with: {gcp_json[:30]!r}")

except Exception as e:
    raise RuntimeError(f"❌ Auth Failed: {e}")

# 3. CONNECT & LOAD DATA
SHEET_URL = "https://docs.google.com/spreadsheets/d/1Xq2WX0NSDJJnpIBl4mo71ioKu9Gm0MnYIEx7HgdY67w/edit"
wb = client.open_by_url(SHEET_URL)

internal_df = pd.DataFrame(wb.worksheet("Internal Leads").get_all_records())
buyer_df = pd.DataFrame(wb.worksheet("Buyer Report").get_all_records())

# Validate expected columns exist before proceeding
required_internal = {'lead_id', 'revenue_expected'}
required_buyer = {'lead_id', 'disposition', 'call_duration_sec', 'credit_issued'}

missing_internal = required_internal - set(internal_df.columns)
missing_buyer = required_buyer - set(buyer_df.columns)

if missing_internal:
    raise ValueError(f"❌ 'Internal Leads' sheet is missing columns: {missing_internal}")
if missing_buyer:
    raise ValueError(f"❌ 'Buyer Report' sheet is missing columns: {missing_buyer}")

# 4. AUDIT LOGIC
audit_master = pd.merge(internal_df, buyer_df, on='lead_id', how='left')

# Coerce numeric columns — gspread returns empty cells as empty strings
audit_master['revenue_expected'] = pd.to_numeric(audit_master['revenue_expected'], errors='coerce').fillna(0)
audit_master['credit_issued'] = pd.to_numeric(audit_master['credit_issued'], errors='coerce').fillna(0)
audit_master['call_duration_sec'] = pd.to_numeric(audit_master['call_duration_sec'], errors='coerce')

# Leads with no matching buyer disposition after the merge
missing_leads = audit_master[audit_master['disposition'].isna()].copy()

# Leads explicitly marked as returned
returned_leads = audit_master[audit_master['disposition'] == 'Returned'].copy()

# Returned leads where a real call was never made (exclude NaN durations explicitly)
voice_fails = returned_leads[
    returned_leads['call_duration_sec'].notna() &
    (returned_leads['call_duration_sec'] < 30)
].copy()

# 5. CALCULATIONS
total_expected = pd.to_numeric(
    internal_df['revenue_expected'], errors='coerce'
).fillna(0).sum()

risk_amt = (
    missing_leads['revenue_expected'].fillna(0).sum()
    + returned_leads['credit_issued'].fillna(0).sum()
)

leakage_pct = (risk_amt / total_expected * 100) if total_expected > 0 else 0.0

# 6. APPEND TO GOOGLE SHEET
# Store raw numbers so Sheets can chart/formula them
results_tab = wb.worksheet("Audit Result")
timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

new_row = [
    timestamp,
    round(risk_amt, 2),
    round(leakage_pct, 4),
    len(missing_leads),
    len(voice_fails),
    str(missing_leads['lead_id'].head(3).tolist())
]

results_tab.append_row(new_row)
print(f"🚀 Audit Completed: {timestamp} | Total Risk: ${risk_amt:,.2f} | Leakage: {leakage_pct:.2f}%")
