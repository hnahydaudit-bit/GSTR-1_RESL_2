import streamlit as st
import pandas as pd
import os
import tempfile

st.set_page_config(page_title="GSTR-1 Processor", layout="centered")
st.title("GSTR-1 Excel Processor")

# ---------------- Utilities ---------------- #

def normalize_columns(df):
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
    )
    return df


def find_column_by_keywords(df, keywords, label):
    """
    Finds a column containing ALL keywords (case-insensitive).
    This is hardened against:
    - Acct vs Account
    - Presence/absence of colon
    - Minor SAP naming variations
    """
    for col in df.columns:
        col_l = col.lower()
        if all(k.lower() in col_l for k in keywords):
            return col

    # Enhanced error with suggestions
    possible_matches = [col for col in df.columns if any(k.lower() in col.lower() for k in keywords)]
    raise KeyError(
        f"{label} column not found.\n"
        f"Expected keywords: {keywords}\n"
        f"Found columns: {list(df.columns)}\n"
        f"Possible matches (partial): {possible_matches}"
    )

# ---------------- UI ---------------- #

company_code = st.text_input("Company Code (XXXX)")

sd_file = st.file_uploader("Upload SD File", type="xlsx")
sr_file = st.file_uploader("Upload SR File", type="xlsx")
tb_file = st.file_uploader("Upload TB File", type="xlsx")
gl_file = st.file_uploader("Upload GL Dump File", type="xlsx")

# ---------------- Processing ---------------- #

if st.button("Process Files"):

    if not company_code:
        st.error("Company Code is mandatory")
        st.stop()

    if not all([sd_file, sr_file, tb_file, gl_file]):
        st.error("All files must be uploaded")
        st.stop()

    try:
        with tempfile.TemporaryDirectory() as tmpdir:

            # ---------- Save uploaded files ---------- #

            paths = {}
            for f, name in [
                (sd_file, "sd.xlsx"),
                (sr_file, "sr.xlsx"),
                (tb_file, "tb.xlsx"),
                (gl_file, "gl.xlsx"),
            ]:
                path = os.path.join(tmpdir, name)
                with open(path, "wb") as out:
                    out.write(f.getbuffer())
                paths[name] = path

            # ---------- SD + SR ---------- #

            df_sd = normalize_columns(pd.read_excel(paths["sd.xlsx"]))
            df_sr = normalize_columns(pd.read_excel(paths["sr.xlsx"]))

            df_consolidated = pd.concat(
                [df_sd, df_sr.iloc[1:]],
                ignore_index=True
            )

            consolidated_path = os.path.join(
                tmpdir, f"{company_code}_SD_SR_Consolidated.xlsx"
            )
            df_consolidated.to_excel(consolidated_path, index=False)

            # ---------- GL ---------- #

            df_gl = normalize_columns(pd.read_excel(paths["gl.xlsx"]))

            gl_text_col = find_column_by_keywords(
                df_gl,
                ["g/l", "account", "long", "text"],
                "GL Long Text"
            )

            gl_account_col = find_column_by_keywords(
                df_gl,
                ["g/l", "account"],
                "GL Account"
            )

            value_col = find_column_by_keywords(
                df_gl,
                ["value"],
                "GL Amount"
            )

            gst_accounts = [
                "Central GST Payable",
                "Integrated GST Payable",
                "State GST Payable",
            ]

            df_gst = df_gl[df_gl[gl_text_col].isin(gst_accounts)]
            df_revenue = df_gl[
                df_gl[gl_account_col].astype(str).str.startswith("3")
            ]

            gstr_path = os.path.join(
                tmpdir, f"{company_code}_GSTR-1_Workbook.xlsx"
            )

            with pd.ExcelWriter(gstr_path, engine="openpyxl") as writer:
                df_gst.to_excel(writer, sheet_name="GST Payable", index=False)
                df_revenue.to_excel(writer, sheet_name="Revenue", index=False)

            # ---------- TB ---------- #

            df_tb = normalize_columns(pd.read_excel(paths["tb.xlsx"]))

            # Debug: Show TB columns (remove after testing)
            st.write(f"TB columns after normalization: {list(df_tb.columns)}")

            # Fallback for TB GL Long Text column (based on your error)
            tb_text_col = None
            if 'G/L Acct Long Text' in df_tb.columns:
                tb_text_col = 'G/L Acct Long Text'
                st.write(f"Using fallback column for TB GL Long Text: {tb_text_col}")
            else:
                tb_text_col = find_column_by_keywords(
                    df_tb,
                    ["g/l", "acct", "long", "text"],
                    "TB GL Long Text"
                )

            debit_col = find_column_by_keywords(
                df_tb,
                ["period", "d"],
                "TB Debit"
            )

            credit_col = find_column_by_keywords(
                df_tb,
                ["period", "c"],
                "TB Credit"
            )

            df_tb_gst = df_tb[df_tb[tb_text_col].isin(gst_accounts)].copy()
            df_tb_gst["Difference"] = (
                df_tb_gst[credit_col] - df_tb_gst[debit_col]
            )

            # ---------- Summary ---------- #

            gst_summary = (
                df_gst.groupby(gl_text_col)[value_col].sum()
            )

            tb_summary = (
                df_tb_gst.groupby(tb_text_col)["Difference"].sum()
            )

            summary_df = pd.DataFrame({
                "GST Type": gst_summary.index,
                "GST Payable as per GL": gst_summary.values,
                "Difference as per TB": tb_summary.reindex(gst_summary.index).values,
            })

            summary_df["Net Difference"] = (
                summary_df["GST Payable as per GL"]
                - summary_df["Difference as per TB"]
            )

            summary_path = os.path.join(
                tmpdir, f"{company_code}_Summary.xlsx"
            )
            summary_df.to_excel(summary_path, index=False)

            # ---------- Downloads ---------- #

            st.success("Processing completed successfully")

            for label, path in {
                "Download SD-SR Consolidated": consolidated_path,
                "Download GSTR-1 Workbook": gstr_path,
                "Download Summary": summary_path,
            }.items():
                with open(path, "rb") as f:
                    st.download_button(
                        label,
                        f,
                        file_name=os.path.basename(path)
                    )

    except Exception as e:
        st.error(str(e))
