import streamlit as st
import pandas as pd

from ui import inject_global_styles, render_hero, render_progress, render_start_over_button

st.set_page_config(page_title="Participants | Group Formation Studio", page_icon="groups", layout="wide")
inject_global_styles()
render_progress(3)
render_start_over_button("start_over_participants")

st.title("Participant Setup")
render_hero(
    "Add or import participant data",
    "Provide participant records, validate key fields, then continue to run your grouping logic.",
)

REQUIRED_COLS = ["Participant_ID", "Expertise", "Lived_Experience", "Minnesota"]


def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in REQUIRED_COLS:
        if col not in df.columns:
            df[col] = ""
    return df[REQUIRED_COLS]


mode = st.radio(
    "Input method",
    ["Upload Excel", "Add manually"],
    horizontal=True,
)

df = None

if mode == "Upload Excel":
    uploaded = st.file_uploader("Upload participant Excel file", type=["xlsx"])
    if uploaded is None:
        st.info("Upload a .xlsx file to continue, or switch to manual entry.")
        st.stop()

    df = pd.read_excel(uploaded)
    df = ensure_columns(df)
else:
    st.caption("Use the editor below to add rows, paste from a spreadsheet, and adjust values.")

    if "manual_df" not in st.session_state:
        st.session_state["manual_df"] = pd.DataFrame(columns=REQUIRED_COLS)

    edited = st.data_editor(
        st.session_state["manual_df"],
        num_rows="dynamic",
        use_container_width=True,
        key="manual_editor",
    )

    st.session_state["manual_df"] = ensure_columns(edited)
    df = st.session_state["manual_df"]

    st.download_button(
        "Download manual entries (CSV)",
        df.to_csv(index=False).encode("utf-8"),
        file_name="participants.csv",
        mime="text/csv",
        disabled=df.empty,
    )

df = ensure_columns(df)

if df.empty:
    st.warning("No participants yet. Add at least one row to continue.")
    st.stop()

missing_ids = df["Participant_ID"].astype(str).str.strip().eq("").sum()
if missing_ids > 0:
    st.warning(f"{missing_ids} participant(s) are missing Participant_ID.")

st.session_state["df"] = df

metric1, metric2 = st.columns(2)
metric1.metric("Participant rows", len(df))
metric2.metric("Missing Participant_ID", int(missing_ids))

st.subheader("Current Participant Data")
st.dataframe(df, use_container_width=True)

left, right = st.columns(2)
with left:
    if st.button("Back to Event Setup"):
        st.switch_page("pages/1_Event_Setup.py")
with right:
    if st.button("Generate Groupings", type="primary"):
        st.switch_page("pages/3_Run_and_Results.py")
