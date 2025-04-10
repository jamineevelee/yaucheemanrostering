import streamlit as st
import pandas as pd
import re
from datetime import datetime, timedelta

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
prefer_lhr_40h = st.sidebar.checkbox("Prefer LHR with >40h Layover")
avoid_na = st.sidebar.checkbox("Avoid North America")
latest_sign_on = st.sidebar.time_input("Earliest Acceptable Sign-On", value=datetime.strptime("08:00", "%H:%M"))

# --- Helper Functions ---
def group_pairings(df):
    pairings = []
    try:
        dates = df.iloc[3].tolist()[2:]
        row = 5
        while row < len(df):
            if not str(df.iloc[row, 1]).strip() == "FO":
                row += 1
                continue

            numbers = df.iloc[row].tolist()[2:]
            routes = df.iloc[row+1].tolist()[2:] if row+1 < len(df) else ["" for _ in dates]
            times = df.iloc[row+2].tolist()[2:] if row+2 < len(df) else ["" for _ in dates]

            i = 0
            current_pairing = None
            while i < len(dates):
                try:
                    date = pd.to_datetime(dates[i]).date()
                except:
                    i += 1
                    continue
                number = str(numbers[i]) if pd.notna(numbers[i]) else ""
                route = str(routes[i]) if pd.notna(routes[i]) else ""
                time = str(times[i]) if pd.notna(times[i]) else ""
                has_flight = bool(number or route or time)
                if has_flight:
                    if current_pairing is None:
                        current_pairing = {
                            "start_date": date,
                            "segments": [],
                            "source_row": row
                        }
                    current_pairing["segments"].append({
                        "date": date,
                        "number": number,
                        "route": route,
                        "time": time
                    })
                else:
                    if current_pairing:
                        current_pairing["end_date"] = current_pairing["segments"][-1]["date"]
                        pairings.append(current_pairing)
                        current_pairing = None
                i += 1
            if current_pairing:
                current_pairing["end_date"] = current_pairing["segments"][-1]["date"]
                pairings.append(current_pairing)
            row += 3
    except Exception as e:
        st.error(f"❌ Error grouping pairings: {e}")
    return pairings

# --- File Handling ---
if file:
    df = pd.read_excel(file, header=None)
    pairings = group_pairings(df)
    st.success(f"✅ Grouped {len(pairings)} pairings (FO only)")

    st.subheader("📋 Grouped Pairings Preview")
    st.dataframe(pd.DataFrame([
        {
            "Start": p["start_date"],
            "End": p["end_date"],
            "Days": (p["end_date"] - p["start_date"]).days + 1,
            "Routes": " → ".join(s["route"] for s in p["segments"] if s["route"])
        } for p in pairings
    ]))
