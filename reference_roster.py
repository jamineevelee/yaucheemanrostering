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
def calculate_layover_hours(segments):
    if len(segments) < 2:
        return 0
    layovers = []
    for i in range(1, len(segments)):
        try:
            prev_arr = segments[i-1]
            next_dep = segments[i]
            if "-" in prev_arr["time"] and "-" in next_dep["time"]:
                arr_str = prev_arr["time"].split("-")[-1]
                dep_str = next_dep["time"].split("-")[0]
                arr_dt = datetime.combine(prev_arr["date"], datetime.strptime(arr_str, "%H%M").time())
                dep_dt = datetime.combine(next_dep["date"], datetime.strptime(dep_str, "%H%M").time())
                diff = (dep_dt - arr_dt).total_seconds() / 3600
                if diff > 4:  # only consider as layover if more than 4 hours
                    layovers.append(diff)
        except:
            continue
    return round(max(layovers), 1) if layovers else 0

def is_integrated(segments):
    for i in range(1, len(segments)):
        if "HKG" in segments[i-1]["route"].split("-")[-1] and "HKG" in segments[i]["route"].split("-")[0]:
            try:
                arr_str = segments[i-1]["time"].split("-")[-1]
                dep_str = segments[i]["time"].split("-")[0]
                arr_dt = datetime.combine(segments[i-1]["date"], datetime.strptime(arr_str, "%H%M").time())
                dep_dt = datetime.combine(segments[i]["date"], datetime.strptime(dep_str, "%H%M").time())
                if (dep_dt - arr_dt).total_seconds() / 3600 <= 4:
                    return True
            except:
                continue
    return False

def group_pairings(df):
    pairings = []
    try:
        dates = df.iloc[3].tolist()[2:]
        row = 5
        while row < len(df):
            if not str(df.iloc[row, 1]).strip() == "FO":
                row += 1
                continue

            current_pairing = None
            segments = []
            numbers = df.iloc[row].tolist()[2:]
            routes = df.iloc[row+1].tolist()[2:] if row+1 < len(df) else ["" for _ in dates]
            times = df.iloc[row+2].tolist()[2:] if row+2 < len(df) else ["" for _ in dates]

            i = 0
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
                            "source_row": row,
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
                        break
                i += 1
            if current_pairing:
                segs = current_pairing["segments"]
                current_pairing["is_rq_rp"] = any("(RQ" in s["number"] or "(RP" in s["number"] for s in segs)
                current_pairing["length_days"] = (segs[-1]["date"] - segs[0]["date"]).days + 1
                current_pairing["flight_numbers"] = " → ".join(s["number"] for s in segs if s["number"])
                current_pairing["routes"] = " → ".join(s["route"] for s in segs if s["route"])

                try:
                    dep_time = datetime.strptime(segs[0]["time"].split("-")[0], "%H%M")
                    current_pairing["duty_start"] = datetime.combine(segs[0]["date"], dep_time.time()) - timedelta(hours=1, minutes=10)
                except:
                    current_pairing["duty_start"] = "N/A"

                try:
                    arr_time = datetime.strptime(segs[-1]["time"].split("-")[-1], "%H%M")
                    current_pairing["duty_end"] = datetime.combine(segs[-1]["date"], arr_time.time())
                except:
                    current_pairing["duty_end"] = "N/A"

                current_pairing["turnaround"] = current_pairing["start_date"] == current_pairing["end_date"]
                current_pairing["layover_hours"] = calculate_layover_hours(segs)
                current_pairing["integrated"] = is_integrated(segs)
                pairings.append(current_pairing)
            row += 4
    except Exception as e:
        st.error(f"❌ Error grouping pairings: {e}")
    return pairings

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
            "Total Days": p["length_days"],
            "RQ/RP": p["is_rq_rp"],
            "Routes": p["routes"],
            "Flight Numbers": p["flight_numbers"],
            "Layover Hours": p["layover_hours"],
            "Turnaround": p["turnaround"],
            "Integrated": p["integrated"]
        }
        for p in filtered_pairings
    ]))

    st.info("🔧 Roster simulation engine coming next...")
