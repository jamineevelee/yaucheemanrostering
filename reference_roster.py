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

            segments = []
            numbers = df.iloc[row].tolist()[2:]
            routes = df.iloc[row + 1].tolist()[2:] if row + 1 < len(df) else ["" for _ in dates]
            times = df.iloc[row + 2].tolist()[2:] if row + 2 < len(df) else ["" for _ in dates]

            current_pairing = None
            for i in range(len(dates)):
                try:
                    date = pd.to_datetime(dates[i]).date()
                except:
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
                            "source_row": row,
                            "duty_start": None,
                            "duty_end": None
                        }
                    current_pairing["segments"].append({
                        "date": date,
                        "number": number,
                        "route": route,
                        "time": time
                    })
                else:
                    if current_pairing:
                        finalize_pairing(current_pairing, pairings)
                        current_pairing = None

            if current_pairing:
                finalize_pairing(current_pairing, pairings)
            row += 4  # move to next FO block

    except Exception as e:
        st.error(f"❌ Error grouping pairings: {e}")
    return pairings

def finalize_pairing(p, pairings):
    p["end_date"] = p["segments"][-1]["date"]
    p["is_rq_rp"] = any(
        re.search(r"\(RQ|RP\)", s["number"]) or
        re.search(r"\(RQ|RP\)", s["route"]) or
        re.search(r"\(RQ|RP\)", s["time"])
        for s in p["segments"]
    )
    p["length_days"] = (p["end_date"] - p["start_date"]).days + 1

    try:
        dep_time = datetime.strptime(p["segments"][0]["time"].split("-")[0], "%H%M")
        p["duty_start"] = datetime.combine(p["segments"][0]["date"], dep_time.time()) - timedelta(hours=1, minutes=10)
    except:
        p["duty_start"] = "N/A"

    try:
        arr_time = datetime.strptime(p["segments"][-1]["time"].split("-")[-1], "%H%M")
        p["duty_end"] = datetime.combine(p["segments"][-1]["date"], arr_time.time())
    except:
        p["duty_end"] = "N/A"

    p["turnaround"] = p["start_date"] == p["end_date"]
    pairings.append(p)

# --- Layover & Classification Helpers ---
def get_layover(p):
    try:
        if len(p["segments"]) > 1 and "-" in p["segments"][0]["time"] and "-" in p["segments"][1]["time"]:
            arr_str = p["segments"][0]["time"].split("-")[-1]
            dep_str = p["segments"][1]["time"].split("-")[0]
            arr_time = datetime.strptime(arr_str, "%H%M").time()
            dep_time = datetime.strptime(dep_str, "%H%M").time()
            arr_dt = datetime.combine(p["segments"][0]["date"], arr_time)
            dep_dt = datetime.combine(p["segments"][1]["date"], dep_time)
            return round((dep_dt - arr_dt).total_seconds() / 3600, 1)
        else:
            return 0
    except:
        return 0

def is_integrated(p):
    mid = p["segments"][1:-1]
    return any("HKG" in s["route"] for s in mid)

def classify_layover(p):
    if get_layover(p) < 1:
        return "None"
    route_str = " → ".join([s["route"] for s in p["segments"]])
    longhaul = ["LHR", "LAX", "JFK", "CDG", "FRA", "DXB"]
    regional = ["KIX", "HND", "NRT", "ICN", "BKK", "SIN", "DEL"]
    if any(loc in route_str for loc in longhaul):
        return "Long Haul"
    if any(loc in route_str for loc in regional):
        return "Regional"
    return "Other"

# --- File Handling ---
if file:
    df = pd.read_excel(file, header=None)
    all_pairings = group_pairings(df)
    filtered_pairings = [p for p in all_pairings if is_rq_rp or not p["is_rq_rp"]]

    st.success(f"✅ Grouped {len(filtered_pairings)} pairings ({'RQ/RP included' if is_rq_rp else 'FO only'})")
    st.subheader("📋 Grouped Pairings Preview")

    st.dataframe(pd.DataFrame([
        {
            "Duty Start": p["duty_start"],
            "Duty End": p["duty_end"],
            "Pattern Days": p["length_days"],
            "Flight Numbers": " → ".join(s["number"] for s in p["segments"] if s["number"]),
            "Routes": " → ".join(s["route"] for s in p["segments"] if s["route"]),
            "Layover Hrs": get_layover(p),
            "Layover Type": classify_layover(p),
            "RQ/RP": p["is_rq_rp"],
            "Turnaround": p["turnaround"],
            "Integrated": is_integrated(p)
        } for p in filtered_pairings
    ]))

    st.info("🔧 Roster simulation engine coming next...")
