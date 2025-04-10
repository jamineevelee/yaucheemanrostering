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

# --- Bid Preferences ---
st.sidebar.header("🎯 Bid Preferences")
want_jfk = st.sidebar.checkbox("Prefer JFK Layover")
avoid_lax = st.sidebar.checkbox("Avoid LAX")
want_gdo_sundays = st.sidebar.checkbox("Want GDO on Sundays")
latest_sign_on = st.sidebar.time_input("Earliest Acceptable Sign-On", value=datetime.strptime("08:00", "%H:%M"))

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

    row = date_row + 1
    while row < len(df):
        name_cell = df.iloc[row, 0]
        if pd.isna(name_cell):
            row += 1
            continue

        trip_ids = df.iloc[row].tolist()[2:]
        routes = df.iloc[row + 1].tolist()[2:]
        times = df.iloc[row + 2].tolist()[2:]

        for i in range(len(trip_ids)):
            trip_id = trip_ids[i]
            if pd.isna(trip_id):
                continue
            trip_str = str(trip_id)
            route = routes[i] if i < len(routes) else ""
            time = times[i] if i < len(times) else ""
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

        row += 4  # jump to next pilot block

    return pairings

# --- Main App ---
if file:
    df = pd.read_excel(file, sheet_name=0)
    pairing_list = extract_pairings(df)

    if category == "FO" and not is_rq_rp:
        pairing_list = [p for p in pairing_list if not p['is_rq_rp']]

    st.success(f"✅ Loaded {len(pairing_list)} pairings ({'RQ/RP included' if is_rq_rp or category != 'FO' else 'FO only'})")

    # Show filtered pairings
    st.subheader("📋 Filtered Pairings")
    df_pairings = pd.DataFrame(pairing_list)
    st.dataframe(df_pairings)

    st.info("🛠️ Roster simulation engine coming next...")
else:
    st.warning("⬅️ Please upload a pairing Excel file to begin.")
