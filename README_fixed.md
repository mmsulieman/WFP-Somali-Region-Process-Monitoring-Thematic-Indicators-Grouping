# WFP Somali Region – Process Monitoring Thematic Cleaner

A Streamlit application for the **WFP Ethiopia – Somali Region RAM/M&E Unit** that converts raw **MoDA/ODK Excel exports (multi-sheet)** into:

- A **cleaned, annotated wide dataset** (one row per interview / observation),
- A **long-format fact table** (one row per indicator value),
- A **column-level thematic mapping** (Protection, CFM, Entitlement, etc.).

## 1. Features
- Detects **Activity** (Relief, Nutrition, Refugees, Social Protection, Market) from sheet names.
- Detects **Monitoring Type** (Beneficiary Interview, Distribution Observation, Food Basket, Warehouse, Partner, Market).
- Automatically assigns a **Thematic Area** to each column.
- Creates:
  - `Wide_Cleaned` – original data + context columns + extra `_bin` columns (Yes/No → 1/0 where possible);
  - `Fact_Long` – long-format dataset (id columns + Raw_Column_Name + Value + thematic/meta);
  - `Indicator_Mapping` – one row per column with thematic classification and clean indicator names.

## 2. Installation
1. Ensure **Python 3.9+** is installed.
2. (Recommended) Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # on Windows: venv\Scripts\activate
   ```
3. Install required packages:
   ```bash
   pip install -r requirements_fixed.txt
   ```

## 3. Running the app
From the folder containing `app_fixed.py`:
```bash
streamlit run app_fixed.py
```
Streamlit will open the app in your browser (usually at `http://localhost:8501`).

## 4. Using the app
1. **Upload data**
   - Export your **MoDA/ODK** process monitoring data to a single Excel file (`.xlsx`) with multiple sheets.
   - Each sheet should correspond to a specific **Activity** and **Monitoring Type**.
2. **Run processing**
   - Click **"Run Processing"**.
   - The app will detect context, build mapping, and generate outputs.
3. **Review and download**
   - Previews (first 50 rows) are shown for `Indicator_Mapping`, `Wide_Cleaned`, and `Fact_Long`.
   - Click the **download button** to get a single Excel file: `ProcessMonitoring_Thematic_Cleaned_Output.xlsx`.

## 5. Notes
- Includes basic error handling for corrupted/empty sheets.
- Button is disabled until a file is uploaded.
- Adds `xlrd` to support legacy `.xls` files if needed.
