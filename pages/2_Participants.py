import streamlit as st
import pandas as pd

st.title("Participant Setup")

# ---- 1) Define the columns your model expects ----
# Update these to match your real schema
REQUIRED_COLS = ["Participant_ID", "Expertise", "Lived_Experience", "Minnesota"]

def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure required columns exist (adds any missing as empty)."""
    df = df.copy()
    for c in REQUIRED_COLS:
        if c not in df.columns:
            df[c] = ""
    # Keep only required columns (optional; remove if you want to allow extras)
    df = df[REQUIRED_COLS]
    return df

# ---- 2) Choose input method ----
mode = st.radio(
    "How would you like to provide participant data?",
    ["Upload Excel", "Add manually"],
    horizontal=True
)

df = None

# ---- 3A) Upload path ----
if mode == "Upload Excel":
    uploaded = st.file_uploader("Upload participant Excel file", type=["xlsx"])
    if uploaded is None:
        st.info("Upload an Excel file to continue, or switch to 'Add manually'.")
        st.stop()

    df = pd.read_excel(uploaded)
    df = ensure_columns(df)

# ---- 3B) Manual entry path ----
else:
    st.caption("Add participants below. You can paste from a spreadsheet, add rows, and edit cells.")

    # Initialize an empty template once
    if "manual_df" not in st.session_state:
        st.session_state["manual_df"] = pd.DataFrame(columns=REQUIRED_COLS)

    edited = st.data_editor(
        st.session_state["manual_df"],
        num_rows="dynamic",           # lets user add/remove rows
        use_container_width=True,
        key="manual_editor",
    )

    # Keep session state synced
    st.session_state["manual_df"] = ensure_columns(edited)
    df = st.session_state["manual_df"]

    # Optional: allow download of what they entered
    st.download_button(
        "Download as CSV",
        df.to_csv(index=False).encode("utf-8"),
        file_name="participants.csv",
        mime="text/csv",
        disabled=df.empty
    )

# ---- 4) Validate & save to session_state ----
df = ensure_columns(df)

# Basic validation example: require at least 1 row
if df.empty:
    st.warning("No participants yet. Add at least one row to continue.")
    st.stop()

# Example: require Participant_ID not blank
missing_ids = df["Participant_ID"].astype(str).str.strip().eq("").sum()
if missing_ids > 0:
    st.warning(f"{missing_ids} participant(s) are missing Participant_ID. Please fill them in.")

st.session_state["df"] = df

st.subheader("Current Participant Data")
st.dataframe(df, use_container_width=True)

# ---- 5) Continue ----
if st.button("Generate Groupings"):
    st.switch_page("pages/3_Run_and_Results.py")
