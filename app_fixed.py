
import io
import re
from typing import Tuple, Dict, Optional, List
import numpy as np
import pandas as pd
import streamlit as st

# ------------------------------------------------------------
# WFP Somali Region – Process Monitoring Thematic Cleaner
# Improved: robust MoDA header detection + debug
# ------------------------------------------------------------

# ------------------------------
# Helper functions
# ------------------------------

def infer_activity_and_type(sheet_name: str) -> Tuple[str, str, str]:
    """Infer activity code/name and monitoring type from sheet name."""
    s = sheet_name.lower()
    act_code = "OTHER"
    act_name = "Other / Unclassified"
    mtype = "General Monitoring"

    if "activity 1" in s or "(rel-" in s:
        act_code = "ACT1"
        act_name = "Relief / General Food Assistance"
    elif "activity 2" in s or "(nut-" in s:
        act_code = "ACT2"
        act_name = "Nutrition (MAM/BSFP/TSFP)"
    elif "activity 3" in s or "(ref-" in s or "refugee" in s:
        act_code = "ACT3"
        act_name = "Refugees"
    elif "activity 5" in s or "social protec" in s:
        act_code = "ACT5"
        act_name = "Social Protection / Resilience"
    elif "market and mills" in s or "market" in s:
        act_code = "X-MARKET"
        act_name = "Market & Mills Monitoring"

    if "beneficiary" in s:
        mtype = "Beneficiary Interview"
    elif "observe distrib" in s:
        mtype = "Distribution Observation"
    elif "food basket" in s:
        mtype = "Food Basket Monitoring"
    elif "warehouse" in s:
        mtype = "Warehouse Monitoring"
    elif "partner monitor" in s:
        mtype = "Partner Monitoring"
    elif "refugee opera" in s:
        mtype = "Refugee Operations Monitoring"
    elif "nutrition ass" in s:
        mtype = "Nutrition Assistance Monitoring"
    elif "social protec" in s:
        mtype = "Social Protection / SBC Monitoring"
    elif "market and mills" in s or "market" in s:
        mtype = "Market & Mills Monitoring"

    return act_code, act_name, mtype

META_KEYWORDS = [
    "starttime", "endtime", "deviceid", "_id", "_uuid", "_submission", "meta/instanceid",
    "_index", "_parent_index", "_version", "_duration", "_submitted_by",
    "geographic coordinates", "latitude", "longitude", "altitude", "precision",
    "region", "zone", "wfp sub office", "sub office", "wereda", "woreda",
    "fdp name", "fdp", "kebele", "village",
    "monitoring year", "monitoring month", "information collected by",
    "name of wfp staff", "field monitoring", "tpm field monitoring",
    "today"
]

EXPECTED_HEADER_TOKENS = {
    "starttime", "endtime", "instanceid", "_uuid", "_submission_time", "region", "woreda",
    "fdp", "monitoring month", "monitoring year"
}


def is_metadata_column(col: str) -> bool:
    c = str(col).lower()
    for k in META_KEYWORDS:
        if k in c:
            return True
    return False


def detect_header_row(raw_df: pd.DataFrame, max_scan: int = 50) -> Optional[int]:
    """Detect the header row by scanning the first max_scan rows for expected MoDA tokens."""
    # Work on string-converted copy
    sample = raw_df.iloc[:max_scan].astype(str)
    for idx in sample.index:
        row_vals = {str(v).strip().lower() for v in sample.loc[idx].values}
        hits = len(row_vals & EXPECTED_HEADER_TOKENS)
        # Heuristic: header row contains multiple expected tokens
        if hits >= 2:
            return idx
    return None


def read_moda_sheet(excel_io: io.BytesIO, sheet: str) -> Optional[pd.DataFrame]:
    """Read a MoDA sheet with robust header detection. Returns cleaned DataFrame or None."""
    try:
        raw = pd.read_excel(excel_io, sheet_name=sheet, header=None, engine="openpyxl")
    except Exception:
        return None
    if raw.empty:
        return None
    hidx = detect_header_row(raw)
    if hidx is None:
        # Fallback: try first non-empty row as header
        non_empty_rows = raw.dropna(how='all')
        if non_empty_rows.empty:
            return None
        hidx = int(non_empty_rows.index[0])
    # Set header and slice data
    header = raw.iloc[hidx].astype(str)
    df = raw.iloc[hidx + 1:].copy()
    df.columns = header
    # Drop completely empty columns and rows
    df = df.dropna(axis=1, how='all').dropna(how='all')
    if df.empty:
        return None
    return df


def infer_thematic_area(col: str, act_code: str, monitoring_type: str) -> str:
    """Assign a thematic area based on column name and context."""
    c = str(col).lower()

    if is_metadata_column(col):
        return "Demographics & Metadata"

    demo_kw = ["sex", "gender", "age", "marital", "education", "literacy",
               "disability", "pregnant", "lactating", "household size", "hh size",
               "children under", "head of household", "hh head"]
    if any(k in c for k in demo_kw):
        return "Demographics & Metadata"

    cfm_kw = ["complain", "complaint", "feedback", "hotline", "toll free", "toll-free",
              "cfm", "suggestion box", "helpline", "grievance"]
    if any(k in c for k in cfm_kw):
        return "Accountability to Affected Populations (CFM & Information)"

    prot_kw = ["protection", "safe", "safety", "harassment", "violence", "abuse",
               "threat", "security", "unsafe"]
    if any(k in c for k in prot_kw):
        return "Protection, Safety & Accessibility"

    targ_kw = ["registration", "registered", "beneficiary category", "id number", "ration card",
               "id card", "on the list", "hh id", "household id", "name of beneficiary",
               "deduplication", "psnp", "displaced_person", "displaced person"]
    if any(k in c for k in targ_kw):
        return "Targeting & Registration"

    dist_kw = ["queue", "orderly", "crowd", "distribution process",
               "procedure", "token", "ticket", "priority", "served first",
               "distribution site", "entry point", "exit"]
    if any(k in c for k in dist_kw):
        return "Distribution Process & Procedures"

    time_kw = ["waiting time", "how long", "time did", "minutes", "delay", "delayed"]
    if any(k in c for k in time_kw):
        return "Timeliness & Waiting Time"

    ent_kw = ["full ration", "ration", "entitlement", "enough", "sufficient",
              "adequate", "receive all", "missing item", "partial ration",
              "food basket", "cereal", "pulse", "oil", "csb", "sugar", "salt",
              "kg", "litre", "gram", "ml"]
    if any(k in c for k in ent_kw):
        return "Entitlement Adequacy & Commodity Basket"

    util_kw = ["use of assistance", "spent on", "selling", "sold", "barter", "swap",
               "consumption", "used for"]
    if any(k in c for k in util_kw):
        return "Utilization of Assistance"

    wh_kw = ["warehouse", "storage", "stack card", "bin card", "pallet",
             "fumigation", "rodent", "insect", "weevil", "leakage", "roof",
             "hygiene", "cleanliness", "ventilation", "lighting", "fire extinguisher",
             "bag condition", "damaged bag"]
    if any(k in c for k in wh_kw):
        return "Warehouse & Storage Monitoring"

    cp_kw = ["implementing partner", "cooperating partner", "cp ", "partner staff",
             "partner name"]
    if any(k in c for k in cp_kw):
        return "Partner Performance & Compliance"

    market_kw = ["market", "shop", "milling", "mill ", "trader", "vendor",
                 "price", "retail", "wholesale", "purchase"]
    if any(k in c for k in market_kw):
        return "Market & Mills Monitoring"

    if monitoring_type == "Warehouse Monitoring":
        return "Warehouse & Storage Monitoring"
    if monitoring_type == "Food Basket Monitoring":
        return "Entitlement Adequacy & Commodity Basket"
    if monitoring_type == "Market & Mills Monitoring":
        return "Market & Mills Monitoring"
    if monitoring_type == "Partner Monitoring":
        return "Partner Performance & Compliance"

    return ""


def clean_indicator_name(col: str) -> str:
    c = str(col).strip().lower()
    c = re.sub(r'[^a-z0-9]+', '_', c)
    c = re.sub(r'_+', '_', c).strip('_')
    return c[:60]


def detect_kpi_type(series: pd.Series) -> str:
    if pd.api.types.is_numeric_dtype(series):
        return "Numeric"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "Date/Time"
    return "Categorical"


def yes_no_to_binary(series: pd.Series) -> pd.Series:
    """Convert common yes/no variants to 1/0; leave others as-is."""
    if series.dtype == object:
        s = series.astype(str).str.strip().str.lower()
        s = s.str.replace(r'[\.;:,]+$', '', regex=True)
        yes_like = {"yes", "y", "haa", "haa/yes"}
        no_like = {"no", "n", "maya", "no/maya"}
        if set(s.dropna().unique()).issubset(yes_like | no_like | {""}):
            return s.map(lambda x: 1 if x in yes_like else (0 if x in no_like else np.nan))
    return series


def process_excel_to_wide_and_long(xls_bytes: bytes):
    """Read Excel (multi-sheet), header-detect, annotate, and build wide + long datasets."""
    excel_io = io.BytesIO(xls_bytes)
    try:
        xls = pd.ExcelFile(excel_io, engine="openpyxl")
    except Exception:
        return None, None, None, []

    annotated_sheets: List[pd.DataFrame] = []
    meta_rows = []
    debug_log = []

    for sheet in xls.sheet_names:
        df = read_moda_sheet(excel_io, sheet)
        debug_log.append({"sheet": sheet, "status": "ok" if df is not None else "skip", "rows": 0 if df is None else len(df)})
        if df is None:
            continue
        act_code, act_name, mtype = infer_activity_and_type(sheet)
        df["Activity_Code"] = act_code
        df["Activity_Name"] = act_name
        df["Monitoring_Type"] = mtype
        df["Source_Sheet"] = sheet
        annotated_sheets.append(df)
        for col in df.columns:
            if col in ["Activity_Code", "Activity_Name", "Monitoring_Type", "Source_Sheet"]:
                continue
            meta_rows.append({
                "Activity_Code": act_code,
                "Activity_Name": act_name,
                "Monitoring_Type": mtype,
                "Source_Sheet": sheet,
                "Raw_Column_Name": col,
                "Clean_Indicator_Name": clean_indicator_name(col),
                "Thematic_Area": infer_thematic_area(col, act_code, mtype)
            })

    if not annotated_sheets:
        return None, None, None, debug_log

    wide_df = pd.concat(annotated_sheets, ignore_index=True)
    mapping_df = pd.DataFrame(meta_rows).drop_duplicates()

    meta_cols = [c for c in wide_df.columns
                 if c in ["Activity_Code", "Activity_Name", "Monitoring_Type", "Source_Sheet"]
                 or is_metadata_column(c)]
    indicator_cols = [c for c in wide_df.columns if c not in meta_cols]

    wide_df_binary = wide_df.copy()
    for col in indicator_cols:
        series = wide_df_binary[col]
        bin_series = yes_no_to_binary(series)
        if (bin_series is not None) and (not bin_series.equals(series)):
            wide_df_binary[col + "_bin"] = bin_series

    id_cols = list(dict.fromkeys(meta_cols + ["Activity_Code", "Activity_Name", "Monitoring_Type", "Source_Sheet"]))

    try:
        long_df = wide_df.melt(
            id_vars=id_cols,
            value_vars=indicator_cols,
            var_name="Raw_Column_Name",
            value_name="Value"
        )
    except Exception:
        wide_df_uniq = wide_df.copy()
        wide_df_uniq.columns = pd.io.parsers.ParserBase({'names': wide_df.columns})._maybe_dedup_names(wide_df.columns)
        indicator_cols = [c for c in wide_df_uniq.columns if c not in meta_cols]
        long_df = wide_df_uniq.melt(
            id_vars=id_cols,
            value_vars=indicator_cols,
            var_name="Raw_Column_Name",
            value_name="Value"
        )

    long_df["KPI_Type"] = long_df.groupby("Raw_Column_Name")["Value"].transform(lambda s: detect_kpi_type(s))

    def suggest_agg(kpi_type: str) -> str:
        if kpi_type == "Numeric":
            return "Average / Median"
        elif kpi_type == "Date/Time":
            return "Min/Max or distribution"
        else:
            return "% of responses in selected category"

    long_df["Suggested_Aggregation"] = long_df["KPI_Type"].map(suggest_agg)

    return wide_df_binary, long_df, mapping_df, debug_log


def to_excel_bytes(sheets: Dict[str, pd.DataFrame]) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        used = set()
        for name, df in sheets.items():
            base = name[:31]
            sname = base
            i = 1
            while sname in used:
                suffix = f"_{i}"
                sname = base[:31 - len(suffix)] + suffix
                i += 1
            used.add(sname)
            df.to_excel(writer, sheet_name=sname, index=False)
    output.seek(0)
    return output.getvalue()

# ------------------------------
# Streamlit UI
# ------------------------------

def render_header():
    st.markdown(
        """
        <div style='padding: .5rem 1rem; border-radius: .5rem; background-color: #0072BC; color: white;'>
          <h3 style='margin-bottom: .2rem;'>World Food Programme (WFP) – Ethiopia</h3>
          <p style='margin: 0;'>Somali Region – RAM / M&E Unit<br/>Process Monitoring Thematic Cleaner</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)


def render_footer():
    st.markdown("---")
    st.caption(
        "WFP Somali Region – RAM/M&E Unit
"
        "Internal tool for process monitoring data cleaning, thematic grouping and dashboard-ready outputs."
    )


def render_sidebar():
    st.sidebar.title("📚 App Guide")
    st.sidebar.markdown("**1. Upload file**")
    st.sidebar.markdown(
        "Upload the MoDA/ODK Excel export (multi-sheet). Each sheet should represent an activity + monitoring type."
    )
    st.sidebar.markdown("**2. Run processing**")
    st.sidebar.markdown(
        "Click **Run Processing**. The app will detect headers, build mapping, and create wide+long outputs."
    )
    st.sidebar.markdown("**3. Download outputs**")
    st.sidebar.markdown(
        "Download the Excel package to feed into Tableau, Power BI or Python for FMPI and other analyses."
    )


def main():
    st.set_page_config(page_title="WFP Process Monitoring – Thematic Cleaner", layout="wide", page_icon="📊")
    render_header()
    render_sidebar()

    st.title("📂 Process Monitoring – Thematic Grouper & Cleaner")
    st.write(
        "Transform raw MoDA/ODK process monitoring exports into a **thematically grouped, dashboard-ready dataset**."
    )

    st.markdown("---")

    uploaded_file = st.file_uploader("📂 Upload MoDA Excel file (.xlsx)", type=["xlsx"])
    run = st.button("🛠️ Run Processing", disabled=(uploaded_file is None))

    if run:
        if uploaded_file is None:
            st.error("Please upload a file first.")
            render_footer()
            return
        with st.spinner("Processing Excel, detecting headers and building thematic mapping..."):
            wide_df, long_df, mapping_df, debug_log = process_excel_to_wide_and_long(uploaded_file.getvalue())
        st.subheader("🔎 Processing Debug Log")
        st.dataframe(pd.DataFrame(debug_log))
        if wide_df is None:
            st.error("No usable sheets found in the file or the file could not be read. Please check the input.")
            render_footer()
            return

        st.success("✅ Processing complete. Scroll down to preview and download outputs.")

        st.subheader("1⃣ Column-level Thematic Mapping")
        st.write("Sample (first 50 rows):")
        st.dataframe(mapping_df.head(50))

        st.subheader("2⃣ Cleaned Wide Dataset (with binary flags where applicable)")
        st.write("Sample (first 50 rows):")
        st.dataframe(wide_df.head(50))

        st.subheader("3⃣ Long-format Fact Table")
        st.write("Sample (first 50 rows):")
        st.dataframe(long_df.head(50))

        excel_bytes = to_excel_bytes({
            "Wide_Cleaned": wide_df,
            "Fact_Long": long_df,
            "Indicator_Mapping": mapping_df
        })
        st.download_button(
            label="⬇️ Download Excel Package (wide + long + mapping)",
            data=excel_bytes,
            file_name="ProcessMonitoring_Thematic_Cleaned_Output.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    render_footer()


if __name__ == '__main__':
    main()
