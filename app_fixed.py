import io
import re
from typing import Tuple, Dict
import numpy as np
import pandas as pd
import streamlit as st

# ------------------------------------------------------------
# WFP Somali Region – Process Monitoring Thematic Cleaner
# RAM / M&E Unit – Internal Tool
# ------------------------------------------------------------

# ------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------

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

def is_metadata_column(col: str) -> bool:
    c = str(col).lower()
    for k in META_KEYWORDS:
        if k in c:
            return True
    return False

def infer_thematic_area(col: str, act_code: str, monitoring_type: str) -> str:
    """Roughly assign a thematic area based on column name and context."""
    c = str(col).lower()

    # Metadata / location
    if is_metadata_column(col):
        return "Demographics & Metadata"

    demo_kw = ["sex", "gender", "age", "marital", "education", "literacy",
               "disability", "pregnant", "lactating", "household size", "hh size",
               "children under", "head of household", "hh head"]
    if any(k in c for k in demo_kw):
        return "Demographics & Metadata"

    cfm_kw = ["complain", "complaint", "feedback", "hotline", "toll free", "toll-free",
              "cfm", "suggestion box", "report any issue", "where do you report",
              "where to report", "where to lodge", "helpline", "grievance"]
    if any(k in c for k in cfm_kw):
        return "Accountability to Affected Populations (CFM & Information)"

    prot_kw = ["protection", "safe", "safety", "harassment", "violence", "abuse",
               "threat", "security", "unsafe", "risk at the distribution", "safety concern"]
    if any(k in c for k in prot_kw):
        return "Protection, Safety & Accessibility"

    targ_kw = ["registration", "registered", "beneficiary category", "id number", "ration card",
               "id card", "on the list", "hh id", "household id", "name of beneficiary",
               "deduplication", "psnp", "displaced_person", "displaced person"]
    if any(k in c for k in targ_kw):
        return "Targeting & Registration"

    dist_kw = ["queue", "que", "line", "orderly", "crowd", "distribution process",
               "procedure", "process", "token", "ticket", "priority", "served first",
               "site arrangement", "space at the distribution", "distribution site", "entry point",
               "exit", "security guard", "distribution conducted by"]
    if any(k in c for k in dist_kw):
        return "Distribution Process & Procedures"

    time_kw = ["waiting time", "how long", "time did you arrive", "time did distribution start",
               "time did distribution end", "time you received", "hours did you wait",
               "minutes did you wait", "delay", "delayed"]
    if any(k in c for k in time_kw):
        return "Timeliness & Waiting Time"

    ent_kw = ["full ration", "ration", "entitlement", "enough food", "sufficient",
              "adequate", "receive all", "received all", "missing item", "partial ration",
              "food basket", "basket", "cereal", "pulse", "oil", "csb", "sugar", "salt",
              "kg", "litre", "gram", "ml"]
    if any(k in c for k in ent_kw):
        return "Entitlement Adequacy & Commodity Basket"

    util_kw = ["how did you use", "use of assistance", "what did you use the cash",
               "spent on", "what did you spend", "did you sell", "selling of", "sold any of",
               "barter", "swap", "consumption", "used for"]
    if any(k in c for k in util_kw):
        return "Utilization of Assistance"

    wh_kw = ["warehouse", "store ", "storage", "stack card", "bin card", "pallet",
             "fumigation", "rodent", "insect", "weevil", "leakage", "roof", "flood",
             "hygiene", "cleanliness", "ventilation", "lighting", "fire extinguisher",
             "safety equipment", "stack", "bag condition", "damaged bag"]
    if any(k in c for k in wh_kw):
        return "Warehouse & Storage Monitoring"

    cp_kw = ["implementing partner", "cooperating partner", "cp ", "partner staff",
             "cp staff", "partner name", "name of implementing partner"]
    if any(k in c for k in cp_kw):
        return "Partner Performance & Compliance"

    market_kw = ["market", "shop", "milling", "mill ", "trader", "vendor",
                 "price", "cost", "retail", "wholesale", "buy", "sell", "selling", "purchase"]
    if any(k in c for k in market_kw):
        return "Market & Mills Monitoring"

    if act_code == "ACT2":
        nutr_kw = ["growth monitoring", "muac", "rutf", "rusf", "bsfp", "tsfp",
                   "screening", "outpatient", "otp", "sfp", "supplementary feeding",
                   "nutrition service", "mother", "child", "anc", "pnc"]
        if any(k in c for k in nutr_kw):
            return "Nutrition Service Quality & Utilization"

    if act_code == "ACT3":
        ref_kw = ["refugee", "camp", "block", "sector", "arrival", "registration centre"]
        if any(k in c for k in ref_kw):
            return "Refugee Operations & Access"

    if act_code == "ACT5":
        sp_kw = ["sbc", "behaviour change", "behavior change", "cooperative", "saving group",
                 "awareness session", "training received", "information session"]
        if any(k in c for k in sp_kw):
            return "Social Behaviour Change & Community Structures"

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
    """Create a stable, Tableau/SQL friendly name."""
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
        # Normalize punctuation
        s = s.str.replace(r'[\.;:,]+$', '', regex=True)
        unique_vals = set(s.dropna().unique())
        yes_like = {"yes", "y", "haa", "haa/yes"}
        no_like = {"no", "n", "maya", "no/maya"}
        if unique_vals.issubset(yes_like.union(no_like).union({""})):
            return s.map(lambda x: 1 if x in yes_like else (0 if x in no_like else np.nan))
    return series

def process_excel_to_wide_and_long(xls_bytes: bytes):
    """Read Excel, annotate, and build wide + long datasets."""
    try:
        excel_io = io.BytesIO(xls_bytes)
        xls = pd.ExcelFile(excel_io)
    except Exception as e:
        return None, None, None

    annotated_sheets = []
    meta_rows = []

    for sheet in xls.sheet_names:
        try:
            df = pd.read_excel(excel_io, sheet_name=sheet)
        except Exception:
            continue
        if df.empty:
            continue
        act_code, act_name, mtype = infer_activity_and_type(sheet)
        # Add context columns
        df["Activity_Code"] = act_code
        df["Activity_Name"] = act_name
        df["Monitoring_Type"] = mtype
        df["Source_Sheet"] = sheet
        annotated_sheets.append(df)
        # Build mapping meta for columns
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
        return None, None, None

    wide_df = pd.concat(annotated_sheets, ignore_index=True)
    mapping_df = pd.DataFrame(meta_rows).drop_duplicates()

    # Identify meta vs indicator columns
    meta_cols = [c for c in wide_df.columns
                 if c in ["Activity_Code", "Activity_Name", "Monitoring_Type", "Source_Sheet"]
                 or is_metadata_column(c)]
    indicator_cols = [c for c in wide_df.columns if c not in meta_cols]

    # Yes/No → binary in wide dataset (new columns with _bin suffix)
    wide_df_binary = wide_df.copy()
    for col in indicator_cols:
        series = wide_df_binary[col]
        bin_series = yes_no_to_binary(series)
        if (bin_series is not None) and (not bin_series.equals(series)):
            wide_df_binary[col + "_bin"] = bin_series

    # Long-format fact table
    id_cols = meta_cols + ["Activity_Code", "Activity_Name", "Monitoring_Type", "Source_Sheet"]
    id_cols = list(dict.fromkeys(id_cols))  # de-duplicate

    try:
        long_df = wide_df.melt(
            id_vars=id_cols,
            value_vars=indicator_cols,
            var_name="Raw_Column_Name",
            value_name="Value"
        )
    except Exception:
        # Fallback if duplicate columns cause melt errors: make columns unique
        wide_df_uniq = wide_df.copy()
        wide_df_uniq.columns = pd.io.parsers.ParserBase({'names': wide_df.columns})._maybe_dedup_names(wide_df.columns)
        indicator_cols = [c for c in wide_df_uniq.columns if c not in meta_cols]
        long_df = wide_df_uniq.melt(
            id_vars=id_cols,
            value_vars=indicator_cols,
            var_name="Raw_Column_Name",
            value_name="Value"
        )

    # Attach mapping
    long_df = long_df.merge(
        mapping_df,
        on=["Activity_Code", "Activity_Name", "Monitoring_Type", "Source_Sheet", "Raw_Column_Name"],
        how="left"
    )

    # KPI type (per indicator) and suggested aggregation
    def _detect_group_type(s: pd.Series) -> str:
        try:
            return detect_kpi_type(s)
        except Exception:
            return "Categorical"

    long_df["KPI_Type"] = long_df.groupby("Raw_Column_Name")["Value"].transform(_detect_group_type)

    def suggest_agg(kpi_type: str) -> str:
        if kpi_type == "Numeric":
            return "Average / Median"
        elif kpi_type == "Date/Time":
            return "Min/Max or distribution"
        else:
            return "% of responses in selected category"

    long_df["Suggested_Aggregation"] = long_df["KPI_Type"].map(suggest_agg)

    return wide_df_binary, long_df, mapping_df


def to_excel_bytes(sheets: Dict[str, pd.DataFrame]) -> bytes:
    """Package multiple DataFrames into a single Excel in memory."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        used_names = set()
        for name, df in sheets.items():
            base = name[:31]  # Excel sheet name limit
            safe_name = base
            i = 1
            while safe_name in used_names:
                suffix = f"_{i}"
                safe_name = (base[:31 - len(suffix)] + suffix)
                i += 1
            used_names.add(safe_name)
            df.to_excel(writer, sheet_name=safe_name, index=False)
    output.seek(0)
    return output.getvalue()

# ------------------------------------------------------------
# Streamlit app layout
# ------------------------------------------------------------

def render_header():
    st.markdown(
        """
        <div style='padding: 0.5rem 1rem; border-radius: 0.5rem; background-color: #0072BC; color: white;'>
          <h3 style='margin-bottom: 0.2rem;'>World Food Programme (WFP) – Ethiopia</h3>
          <p style='margin: 0;'>Somali Region – RAM / M&E Unit <br/>
          Process Monitoring Thematic Cleaner</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)


def render_footer():
    st.markdown("---")
    st.caption(
        "WFP Somali Region – RAM/M&E Unit\n"
        "Internal tool for process monitoring data cleaning,\n"
        "thematic grouping and dashboard-ready outputs."
    )


def render_sidebar():
    st.sidebar.title("📚 App Guide")
    st.sidebar.markdown("**1. Upload file**")
    st.sidebar.markdown(
        "Upload the MoDA/ODK Excel export (multi-sheet) for a given period.\n"
        "Each sheet should represent an activity + monitoring type."
    )
    st.sidebar.markdown("**2. Run processing**")
    st.sidebar.markdown(
        "Click **Run Processing**. The app will:\n"
        "- Detect Activity & Monitoring Type per sheet\n"
        "- Build a column-level thematic mapping\n"
        "- Create a cleaned wide dataset with optional binary flags\n"
        "- Create a long-format fact table."
    )
    st.sidebar.markdown("**3. Download outputs**")
    st.sidebar.markdown(
        "Download the Excel package to feed into Tableau, Power BI or Python for FMPI and other analyses."
    )
    st.sidebar.markdown("**Icons legend**\n- 📂 Input data\n- 🛠️ Processing\n- 📊 Outputs")


def main():
    st.set_page_config(
        page_title="WFP Process Monitoring – Thematic Cleaner",
        layout="wide",
        page_icon="📊",
    )

    render_header()
    render_sidebar()

    st.title("📂 Process Monitoring – Thematic Grouper & Cleaner")
    st.write(
        "This tool helps the **WFP Somali Region RAM/M&E Unit** to transform raw MoDA/ODK process monitoring "
        "exports into a **thematically grouped, dashboard-ready dataset**."
    )

    st.markdown(
        "**Key features:**\n"
        "- Auto-detect Activity and Monitoring Type from sheet names\n"
        "- Auto-generate column-level thematic mapping (Protection, CFM, Entitlement, etc.)\n"
        "- Clean wide dataset with extra Yes/No binary flags (_bin columns)\n"
        "- Long-format fact table for Tableau / Power BI / FMPI."
    )

    st.markdown("---")

    uploaded_file = st.file_uploader("📂 Upload MoDA Excel file (.xlsx)", type=["xlsx"])

    run = st.button("🛠️ Run Processing", disabled=(uploaded_file is None))

    if run:
        if uploaded_file is None:
            st.error("Please upload a file first.")
            render_footer()
            return
        with st.spinner("Processing Excel, building thematic mapping and fact table... This may take a moment."):
            try:
                wide_df, long_df, mapping_df = process_excel_to_wide_and_long(uploaded_file.getvalue())
            except Exception as e:
                wide_df, long_df, mapping_df = None, None, None
        if wide_df is None:
            st.error("No usable sheets found in the file or the file could not be read. Please check the input.")
            render_footer()
            return

        st.success("✅ Processing complete. Scroll down to preview and download outputs.")

        st.subheader("1⃣ Column-level Thematic Mapping")
        st.write("Sample of the mapping (first 50 rows):")
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

        st.info(
            "You can feed **Fact_Long** directly into Tableau or Power BI, using: "
            "`Thematic_Area`, `Clean_Indicator_Name`, `Activity_Code`, `Monitoring_Type`, and location fields.\n\n"
            "For FMPI-style indices, aggregate indicator-level values by monitor / partner / activity and apply your scoring logic."
        )

    render_footer()


if __name__ == '__main__':
    main()
