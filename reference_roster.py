
import streamlit as st
import pandas as pd
import re
from datetime import datetime

st.set_page_config(page_title="Reference Roster Generator", layout="wide")
st.title("✈️ Reference Roster Generator")

# --- Sidebar Input ---
st.sidebar.header("👤 Pilot Profile")
category = st.sidebar.selectbox("Category", ["FO", "SO", "CN"])

is_rq_rp = False
if category == "FO":
    is_rq_rp = st.sidebar.checkbox("I am RQ/RP Qualified", value=False)

st.sidebar.header("📥 Upload Pairing File")
file = st.sidebar.file_uploader("Upload the Excel file (Pairing Book)", type=["xlsx"])

# --- Helper Functions ---
def extract_pairings(df):
    pairings = []
    date_row = None
    for i, row in df.iterrows():
        if 'Homebase' in row.values:
            date_row = i + 1
            break
    if date_row is None:
        return []

    dates = df.iloc[date_row].tolist()[2:]
    for idx in range(date_row + 1, len(df), 4):
        name = df.iloc[idx, 0]
        if pd.isna(name):
            continue
        for i, val in enumerate(df.iloc[idx].tolist()[2:]):
            trip_id = val
            if pd.isna(trip_id):
                continue
            route = df.iloc[idx + 1, i + 2]
            time = df.iloc[idx + 2, i + 2]
            trip_str = str(trip_id)
            is_rq_rp_trip = bool(re.search(r"\((RQ|RP)\)", trip_str))
            try:
                date = pd.to_datetime(dates[i]).date()
            except:
                continue
            pairings.append({
                "date": date,
                "trip_id": trip_str,
                "route": route,
                "time": time,
                "is_rq_rp": is_rq_rp_trip
            })
    return pairings

# --- Main App ---
if file:
    df = pd.read_excel(file, sheet_name=0)
    pairing_list = extract_pairings(df)

    if category == "FO" and not is_rq_rp:
        pairing_list = [p for p in pairing_list if not p['is_rq_rp']]

    st.success(f"✅ Loaded {len(pairing_list)} pairings ({'RQ/RP included' if is_rq_rp or category != 'FO' else 'FO only'})")

    st.dataframe(pd.DataFrame(pairing_list))

    st.info("💡 Bid entry and roster simulation coming next...")
else:
    st.warning("⬅️ Please upload a pairing Excel file to begin.")
