# Revenue Integrity Audit Pipeline

A Python-based reconciliation tool designed to identify revenue leakage between internal lead generation logs and external buyer reports. This was built specifically to audit Voice AI performance and API delivery consistency.

## Overview
The script automates the daily "handshake" audit between the internal records and buyer-side dispositions. It identifies two primary types of revenue risk:
1. **Technical Gaps (Ghost Leads):** Leads successfully generated but never recorded by the buyer API.
2. **Quality Gaps (Voice AI RCA):** Leads returned by the buyer due to short call durations (<30s), indicating a need for script optimization.

## Tech Stack
* **Language:** Python 3.x
* **Data:** Pandas for relational joins and financial calculations
* **Storage:** Google Sheets API (via `gspread`)
* **Environment:** Google Colab with encrypted Secrets for GCP credentials

## Logic Flow
1. **Ingestion:** Pulls raw data from `Internal Leads` and `Buyer Report` tabs.
2. **Left Join:** Matches records on `lead_id` to isolate discrepancies.
3. **Risk Quantification:** Calculates total "At Risk" revenue (Missing Leads + Credits Issued).
4. **Historical Logging:** Appends a summary row to the `Audit Result` tab to track leakage trends over time.

## Setup
1. Store your Google Service Account JSON in a Colab Secret named `GCP_JSON`.
2. Share your target Google Sheet with the `client_email` found in your service account credentials.
3. Update the `SHEET_URL` variable in the script.

## Monitoring
The output is synced to the **Audit Result** worksheet, providing a historical trail of:
* Total Leakage Amount ($)
* Leakage Percentage (%)
* Specific Lead IDs for Engineering/Product review.

* ## Google Sheet Url
The sheet used for this project containing `Internal Leads`, `Buyer Report` and `Audit Result` tabs 
https://docs.google.com/spreadsheets/d/1Xq2WX0NSDJJnpIBl4mo71ioKu9Gm0MnYIEx7HgdY67w/edit?gid=0#gid=0
