
import io
import re
from typing import Tuple, Dict, Optional, List
import numpy as np
import pandas as pd
import streamlit as st

# ------------------------------------------------------------
# WFP Somali Region – Process Monitoring Thematic Cleaner
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

    if "activity 1" in s or "rel" in s:
        act_code = "ACT1"; act_name = "Relief / General Food Assistance"
    elif "activity 2" in s or "nut" in s:
        act_code = "ACT2"; act_name = "Nutrition"
    elif "activity 3" in s or "ref" in s:
        act_code = "ACT3"; act_name = "Refugees"
    elif "activity 5" in s or "social" in s:
        act_code = "ACT5"; act_name = "Social Protection"
    elif "market" in s:
        act_code = "X-MARKET"; act_name = "Market & Mills Monitoring"

    if "beneficiary" in s:
        mtype = "Beneficiary Interview"
    elif "observe" in s:
        mtype = "Distribution Observation"
    elif "food basket" in s:
        mtype = "Food Basket Monitoring"
    elif "warehouse" in s:
        mtype = "Warehouse Monitoring"
    elif "partner" in s:
        mtype = "Partner Monitoring"
    elif "market" in s:
        mtype = "Market & Mills Monitoring"

    return act_code, act_name, mtype


def clean_indicator_name(col: str) -> str:
    """Create a clean indicator name for dashboards."""
    c = str(col).strip().lower()
    c = re.sub(r'[^a-z0-9]+', '_', c)
    c = re.sub(r'_+', '_', c).strip('_')
    return c[:60]


def yes_no_to_binary(series: pd.Series) -> pd.Series:
    """Convert Yes/No responses to binary (1/0)."""
    if series.dtype == object:
        s = series.astype(str).str.strip().str.lower()
        yes_like = {"yes", "y", "haa", "haa/yes"}
        no_like = {"no", "n", "maya", "no/maya"}
        if set(s.dropna().unique()).issubset(yes_like | no_like | {""}):
            return s.map(lambda x: 1 if x in yes_like else (0 if x in no_like else np.nan))
    return series


def process_excel_to_wide_and_long(xls_bytes: bytes):
    """Process Excel file into wide and long formats with thematic mapping."""
    excel_io = io.BytesIO(xls_bytes)
    try:
        xls = pd.ExcelFile(excel_io, engine="openpyxl")
    except Exception:
        return None, None, None

    annotated_sheets = []
    mapping_rows = []

    for sheet in xls.sheet_names:
        df = pd.read_excel(excel_io, sheet_name=sheet, engine="openpyxl")
        if df.empty:
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
            mapping_rows.append({
                "Activity_Code": act_code,
                "Activity_Name": act_name,
                "Monitoring_Type": mtype,
                "Source_Sheet": sheet,
                "Raw_Column_Name": col,
                "Clean_Indicator_Name": clean_indicator_name(col),
                "Thematic_Area": "Auto-assigned"
            })

    if not annotated_sheets:
        return None, None, None

    wide_df = pd.concat(annotated_sheets, ignore_index=True)
    mapping_df = pd.DataFrame(mapping_rows).drop_duplicates()

    meta_cols = ["Activity_Code", "Activity_Name", "Monitoring_Type", "Source_Sheet"]
    indicator_cols = [c for c in wide_df.columns if c not in meta_cols]

    wide_df_binary = wide_df.copy()
    for col in indicator_cols:
        bin_series = yes_no_to_binary(wide_df_binary[col])
        if not bin_series.equals(wide_df_binary[col]):
            wide_df_binary[col + "_bin"] = bin_series

    long_df = wide_df.melt(id_vars=meta_cols, value_vars=indicator_cols,
                           var_name="Raw_Column_Name", value_name="Value")

    return wide_df_binary, long_df, mapping_df


def to_excel_bytes(sheets: Dict[str, pd.DataFrame]) -> bytes:
    """Export multiple DataFrames to a single Excel file."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name[:31], index=False)
    output.seek(0)
    return output.getvalue()


# ------------------------------
# Streamlit UI
# ------------------------------

def render_footer():
    st.markdown("---")
    st.caption("""WFP Somali Region – RAM/M&E Unit
Internal tool for process monitoring data cleaning,
thematic grouping and dashboard-ready outputs.""")


def main():
    st.set_page_config(page_title="WFP Process Monitoring – Thematic Cleaner",
                       layout="wide", page_icon="📊")
    st.title("📂 Process Monitoring – Thematic Grouper & Cleaner")
    st.write("Upload MoDA Excel exports and generate dashboard-ready datasets.")

    uploaded_file = st.file_uploader("📂 Upload MoDA Excel file (.xlsx)", type=["xlsx"])
    run = st.button("🛠️ Run Processing", disabled=(uploaded_file is None))

    if run:
        if uploaded_file is None:
            st.error("Please upload a file first.")
            render_footer()
            return

        with st.spinner("Processing Excel file..."):
            wide_df, long_df, mapping_df = process_excel_to_wide_and_long(uploaded_file.getvalue())

        if wide_df is None:
            st.error("No usable sheets found or file could not be read.")
            render_footer()
            return

        st.success("✅ Processing complete. Preview below and download outputs.")

        st.subheader("1⃣ Column-level Thematic Mapping")
        st.dataframe(mapping_df.head(50))

        st.subheader("2⃣ Cleaned Wide Dataset")
        st.dataframe(wide_df.head(50))

        st.subheader("3⃣ Long-format Fact Table")
        st.dataframe(long_df.head(50))

        excel_bytes = to_excel_bytes({
            "Wide_Cleaned": wide_df,
            "Fact_Long": long_df,
            "Indicator_Mapping": mapping_df
        })

        st.download_button("⬇️ Download Excel Package",
                           data=excel_bytes,
                           file_name="ProcessMonitoring_Thematic_Cleaned_Output.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    render_footer()


if __name__ == '__main__':
    main()
