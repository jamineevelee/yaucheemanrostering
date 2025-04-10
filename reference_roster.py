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

            current_pairing = None
            segments = []
            sub_row = row + 1
            while sub_row < len(df) and pd.isna(df.iloc[sub_row, 1]):
                segments.append(sub_row)
                sub_row += 1

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
                        current_pairing["end_date"] = current_pairing["segments"][-1]["date"]
                        current_pairing["is_rq_rp"] = any(
                            re.search(r"\(RQ|RP\)", s["number"]) or
                            re.search(r"\(RQ|RP\)", s["route"]) or
                            re.search(r"\(RQ|RP\)", s["time"])
                            for s in current_pairing["segments"]
                        )
                        current_pairing["length_days"] = (current_pairing["end_date"] - current_pairing["start_date"]).days + 1

                        # Calculate duty start and end
                        first_seg = current_pairing["segments"][0]
                        last_seg = current_pairing["segments"][-1]
                        try:
                            dep_time = datetime.strptime(first_seg["time"].split("-")[0], "%H%M")
                            current_pairing["duty_start"] = datetime.combine(first_seg["date"], dep_time.time()) - timedelta(hours=1, minutes=10)
                        except:
                            current_pairing["duty_start"] = "N/A"
                        try:
                            arr_time = datetime.strptime(last_seg["time"].split("-")[-1], "%H%M")
                            current_pairing["duty_end"] = datetime.combine(last_seg["date"], arr_time.time())
                        except:
                            current_pairing["duty_end"] = "N/A"

                        pairings.append(current_pairing)
                        current_pairing = None
                i += 1
            if current_pairing:
                current_pairing["end_date"] = current_pairing["segments"][-1]["date"]
                current_pairing["is_rq_rp"] = any(
                    re.search(r"\(RQ|RP\)", s["number"]) or
                    re.search(r"\(RQ|RP\)", s["route"]) or
                    re.search(r"\(RQ|RP\)", s["time"])
                    for s in current_pairing["segments"]
                )
                current_pairing["length_days"] = (current_pairing["end_date"] - current_pairing["start_date"]).days + 1

                # Calculate duty start and end
                first_seg = current_pairing["segments"][0]
                last_seg = current_pairing["segments"][-1]
                try:
                    dep_time = datetime.strptime(first_seg["time"].split("-")[0], "%H%M")
                    current_pairing["duty_start"] = datetime.combine(first_seg["date"], dep_time.time()) - timedelta(hours=1, minutes=10)
                except:
                    current_pairing["duty_start"] = "N/A"
                try:
                    arr_time = datetime.strptime(last_seg["time"].split("-")[-1], "%H%M")
                    current_pairing["duty_end"] = datetime.combine(last_seg["date"], arr_time.time())
                except:
                    current_pairing["duty_end"] = "N/A"

                pairings.append(current_pairing)
            row = sub_row
    except Exception as e:
        st.error(f"❌ Error grouping pairings: {e}")
    return pairings

# --- File Handling ---
if file:
    df = pd.read_excel(file, header=None)
    st.subheader("📝 Raw Data Preview (Top 20 Rows)")
    st.dataframe(df.head(20))

    all_pairings = group_pairings(df)
    filtered_pairings = [p for p in all_pairings if is_rq_rp or not p["is_rq_rp"]]

    st.success(f"✅ Grouped {len(filtered_pairings)} pairings ({'RQ/RP included' if is_rq_rp else 'FO only'})")
    st.subheader("📋 Grouped Pairings Preview")
    st.dataframe(pd.DataFrame([
        {
            "Start": p["start_date"],
            "End": p["end_date"],
            "Days": p["length_days"],
            "RQ/RP": p["is_rq_rp"],
            "Routes": " → ".join(s["route"] for s in p["segments"] if s["route"]),
            "Flight Numbers": " → ".join(s["number"] for s in p["segments"] if s["number"]),
            "Duty Start": p["duty_start"],
            "Duty End": p["duty_end"],
            "Layover Duration": (lambda: (
                str(
                    datetime.combine(p["segments"][1]["date"], datetime.strptime(p["segments"][1]["time"].split("-")[0], "%H%M").time())
                    - datetime.combine(p["segments"][0]["date"], datetime.strptime(p["segments"][0]["time"].split("-")[-1], "%H%M").time())
                )
            ) if len(p["segments"]) > 1 and "-" in p["segments"][0]["time"] and "-" in p["segments"][1]["time"] else "N/A")(),
            "Turnaround": p["start_date"] == p["end_date"],
            "Integrated": any("HKG" in s["route"] for s in p["segments"][1:-1])
        }
        for p in filtered_pairings
    ]))

    st.info("🔧 Roster simulation engine coming next...")
