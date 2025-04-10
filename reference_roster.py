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
latest_sign_on = st.sidebar.time_input("Earliest Acceptable Sign-On", value=datetime.strptime("08:00", "%H:%M"))

# --- Helper Functions ---
def group_pairings(df):
    pairings = []
    try:
        dates = df.iloc[3].tolist()[2:]  # Use row 3 for dates
        current_pairing = None

        row = 5  # data starts from row 5
        while row + 2 < len(df):
            routes = df.iloc[row + 1].tolist()[2:]
            times = df.iloc[row + 2].tolist()[2:]

            i = 0
            while i < len(dates):
                try:
                    date = pd.to_datetime(dates[i]).date()
                except:
                    i += 1
                    continue

                route = routes[i]
                time = times[i]
                has_flight = pd.notna(route) or pd.notna(time)

                if has_flight:
                    if current_pairing is None:
                        current_pairing = {
                            "start_date": date,
                            "segments": []
                        }

                    current_pairing["segments"].append({
                        "date": date,
                        "route": route if pd.notna(route) else "",
                        "time": time if pd.notna(time) else ""
                    })
                else:
                    if current_pairing:
                        current_pairing["end_date"] = current_pairing["segments"][-1]["date"]
                        current_pairing["is_rq_rp"] = any(
                            re.search(r"\((RQ|RP)\)", s["time"]) or "MEL" in s["route"]
                            for s in current_pairing["segments"] if s["time"] or s["route"]
                        )
                        current_pairing["length_days"] = (current_pairing["end_date"] - current_pairing["start_date"]).days + 1
                        pairings.append(current_pairing)
                        current_pairing = None
                i += 1

            row += 4

        if current_pairing:
            current_pairing["end_date"] = current_pairing["segments"][-1]["date"]
            current_pairing["is_rq_rp"] = any(
                re.search(r"\((RQ|RP)\)", s["time"]) or "MEL" in s["route"]
                for s in current_pairing["segments"] if s["time"] or s["route"]
            )
            current_pairing["length_days"] = (current_pairing["end_date"] - current_pairing["start_date"]).days + 1
            pairings.append(current_pairing)

    except Exception as e:
        st.error(f"❌ Error grouping pairings: {e}")

    return pairings

# --- Main App ---
if file:
    df = pd.read_excel(file, sheet_name=0)

    st.subheader("🧪 Raw Data Preview (Top 40 Rows)")
    st.dataframe(df.head(40))

    all_pairings = group_pairings(df)

    # only show FO logic if FO selected
    if category == "FO":
        if not is_rq_rp:
            all_pairings = [p for p in all_pairings if not p['is_rq_rp']]

    st.success(f"✅ Grouped {len(all_pairings)} pairings ({'RQ/RP included' if is_rq_rp or category != 'FO' else 'FO only'})")

    st.subheader("📋 Grouped Pairings Preview")
    preview = [{
        "Start": p["start_date"],
        "End": p["end_date"],
        "Days": p["length_days"],
        "RQ/RP": p["is_rq_rp"],
        "Routes": " → ".join([s["route"] for s in p["segments"] if s["route"]])
    } for p in all_pairings]
    st.dataframe(pd.DataFrame(preview))

    st.info("✅ Pairing grouping ready — roster simulation coming next...")
else:
    st.warning("⬅️ Please upload a pairing Excel file to begin.")
