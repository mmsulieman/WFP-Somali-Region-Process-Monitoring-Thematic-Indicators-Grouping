# WFP Somali Region – Process Monitoring Thematic Cleaner

A Streamlit application for the **WFP Ethiopia – Somali Region RAM/M&E Unit** that converts raw **MoDA/ODK Excel exports (multi-sheet)** into:

- A **cleaned, annotated wide dataset** (one row per interview / observation),
- A **long-format fact table** (one row per indicator value),
- A **column-level thematic mapping** (Protection, CFM, Entitlement, etc.).

You can use the outputs directly in **Tableau**, **Power BI**, or Python for FMPI and other analyses.

---

## 1. Features

- Detects **Activity** (Relief, Nutrition, Refugees, Social Protection, Market) from sheet names.
- Detects **Monitoring Type** (Beneficiary Interview, Distribution Observation, Food Basket, Warehouse, Partner, Market).
- Automatically assigns a **Thematic Area** to each column, e.g.:
  - Protection, Safety & Accessibility  
  - Accountability to Affected Populations (CFM & Information)  
  - Entitlement Adequacy & Commodity Basket  
  - Distribution Process & Procedures  
  - Timeliness & Waiting Time  
  - Targeting & Registration  
  - Warehouse & Storage Monitoring  
  - Partner Performance & Compliance  
  - Market & Mills Monitoring  
  - Demographics & Metadata  
- Creates:
  - `Wide_Cleaned` – original data + context columns + extra `_bin` columns (Yes/No → 1/0 where possible);
  - `Fact_Long` – long-format dataset (id columns + Raw_Column_Name + Value + thematic/meta);
  - `Indicator_Mapping` – one row per column with thematic classification and clean indicator names.

---

## 2. Installation

1. Make sure you have **Python 3.9+** installed.

2. Create and activate a virtual environment (recommended):

```bash
python -m venv venv
source venv/bin/activate   # on Windows: venv\Scripts\activate
```

3. Install the required packages:

```bash
pip install -r requirements.txt
```

---

## 3. Running the app

From the folder containing `app.py`:

```bash
streamlit run app.py
```

Streamlit will open the app in your browser (usually at `http://localhost:8501`).

---

## 4. Using the app

1. **Upload data**

   - Export your **MoDA/ODK** process monitoring data to a single Excel file (`.xlsx`) with multiple sheets.
   - Each sheet should correspond to a specific **Activity** and **Monitoring Type**, e.g.:
     - `Activity 1 (Rel-Beneficiary ...)`
     - `Activity 1 (Rel-Observe distrib ...)`
     - `Activity 2 (Nut-Beneficiary ...)`
     - `Activity 3 (Ref-Warehouse Monit ...)`
     - `Market and Mills Monitoring ...`, etc.

2. **Run processing**

   - Click the **"Run Processing"** button.
   - The app will:
     - Detect Activity & Monitoring Type per sheet,
     - Build the column-level thematic mapping,
     - Create the cleaned wide dataset with binary flags,
     - Create the long-format fact table.

3. **Review and download**

   - The app shows previews (first 50 rows) of:
     - `Indicator_Mapping`,
     - `Wide_Cleaned`,
     - `Fact_Long`.
   - Click the **download button** to get a single Excel file:
     - `ProcessMonitoring_Thematic_Cleaned_Output.xlsx`  
       containing all three sheets.

---

## 5. Working with the outputs

### 5.1 Wide_Cleaned

- One row per interview / observation.
- Includes:
  - `Activity_Code`, `Activity_Name`,
  - `Monitoring_Type`,
  - `Source_Sheet`,
  - Original raw columns from MoDA,
  - Extra `_bin` columns where Yes/No answers were converted to 1/0.

Use this sheet if you prefer **record-level analysis** in Python or Excel.

---

### 5.2 Fact_Long

This is the recommended input for **Tableau / Power BI**:

- Each row = one **indicator value**.
- Columns include:
  - Identifiers:
    - `Activity_Code`, `Activity_Name`,
    - `Monitoring_Type`, `Source_Sheet`,
    - All metadata (Region, Zone, Woreda, FDP, etc.)
  - Indicator meta:
    - `Raw_Column_Name`,
    - `Clean_Indicator_Name`,
    - `Thematic_Area`,
    - `KPI_Type`,
    - `Suggested_Aggregation`.

You can aggregate by:

- Activity, Monitoring Type,
- Woreda, FDP, Site,
- Partner, Time,
- Thematic Area, Indicator.

---

### 5.3 Indicator_Mapping

A reference table describing each column:

- Where it came from (sheet),
- Which Activity and Monitoring Type it belongs to,
- Thematic Area,
- Clean indicator name for use in BI tools.

You can also export this as an **Indicator Dictionary** for SOPs/training.

---

## 6. Suggested extensions

You can further extend this app by:

- Adding **FMPI scoring**:
  - Create new calculated fields that aggregate indicators into a Field Monitor Performance Index.
- Adding **quality checks**:
  - Missingness rates,
  - Outlier detection,
  - Consistency checks between BI, Observation, Basket, and Warehouse.
- Adding **export to CSV/hyper** for direct Tableau integration.

---

## 7. Credits

This tool was designed around the process monitoring workflows of the  
**WFP Ethiopia – Somali Region (Jijiga AO) RAM/M&E Unit**, to reduce repetitive manual cleaning and  
enable faster, more consistent reporting and dashboarding.
