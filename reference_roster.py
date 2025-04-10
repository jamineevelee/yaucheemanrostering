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
def parse_pairings(df):
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
            while i < len(dates):
                current = {
                    "segments": [],
                    "source_row": row
                }
                while i < len(dates):
                    try:
                        date = pd.to_datetime(dates[i]).date()
                    except:
                        i += 1
                        continue

                    number = str(numbers[i]) if pd.notna(numbers[i]) else ""
                    route = str(routes[i]) if pd.notna(routes[i]) else ""
                    time = str(times[i]) if pd.notna(times[i]) else ""

                    if number or route or time:
                        current["segments"].append({"date": date, "number": number, "route": route, "time": time})
                        i += 1
                    else:
                        break

                if current["segments"]:
                    segs = current["segments"]
                    current["start_date"] = segs[0]["date"]
                    current["end_date"] = segs[-1]["date"]
                    current["length_days"] = (current["end_date"] - current["start_date"]).days + 1

                    # Duty start
                    try:
                        dep_time = datetime.strptime(segs[0]["time"].split("-")[0], "%H%M")
                        current["duty_start"] = datetime.combine(segs[0]["date"], dep_time.time()) - timedelta(hours=1, minutes=10)
                    except:
                        current["duty_start"] = None

                    # Duty end
                    try:
                        arr_time = datetime.strptime(segs[-1]["time"].split("-")[-1], "%H%M")
                        current["duty_end"] = datetime.combine(segs[-1]["date"], arr_time.time())
                    except:
                        current["duty_end"] = None

                    # RQ/RP check
                    current["is_rq_rp"] = any(re.search(r"\(RQ|RP\)", s["number"] + s["route"] + s["time"]) for s in segs)

                    # Turnaround = 1-day same start and end
                    current["turnaround"] = current["start_date"] == current["end_date"]

                    # Layover: if >9h between last arr and next dep (if multiple segs)
                    layover_hours = 0
                    if len(segs) > 1:
                        try:
                            arr1 = datetime.combine(segs[0]["date"], datetime.strptime(segs[0]["time"].split("-")[-1], "%H%M").time())
                            dep2 = datetime.combine(segs[1]["date"], datetime.strptime(segs[1]["time"].split("-")[0], "%H%M").time())
                            delta = (dep2 - arr1).total_seconds() / 3600
                            layover_hours = round(delta, 1)
                        except:
                            layover_hours = 0
                    current["layover_hours"] = layover_hours

                    # Layover type
                    dests = " ".join([s["route"] for s in segs])
                    if any(x in dests for x in ["LHR", "JFK", "FRA", "CDG", "DXB"]):
                        current["layover_type"] = "Long Haul"
                    elif any(x in dests for x in ["NRT", "CTS", "KIX", "ICN", "BKK", "DEL"]):
                        current["layover_type"] = "Regional"
                    else:
                        current["layover_type"] = "None"

                    # Integrated: if return to HKG in middle of pattern
                    current["integrated"] = False
                    for j in range(1, len(segs)-1):
                        if "HKG" in segs[j]["route"]:
                            try:
                                arr = datetime.strptime(segs[j]["time"].split("-")[-1], "%H%M")
                                dep = datetime.strptime(segs[j+1]["time"].split("-")[0], "%H%M")
                                delta = (datetime.combine(segs[j+1]["date"], dep.time()) - datetime.combine(segs[j]["date"], arr.time())).total_seconds() / 3600
                                if delta < 4:
                                    current["integrated"] = True
                            except:
                                pass

                    pairings.append(current)
            row += 3
    except Exception as e:
        st.error(f"❌ Error grouping pairings: {e}")
    return pairings

# --- Main Logic ---
if file:
    df = pd.read_excel(file, header=None)
    all_pairings = parse_pairings(df)
    filtered = [p for p in all_pairings if is_rq_rp or not p["is_rq_rp"]]
    st.success(f"✅ Grouped {len(filtered)} pairings ({'RQ/RP included' if is_rq_rp else 'FO only'})")

    st.subheader("📋 Grouped Pairings Preview")
    st.dataframe(pd.DataFrame([
        {
            "Duty Start": p["duty_start"].strftime("%Y-%m-%d %H:%M") if p["duty_start"] else None,
            "Duty End": p["duty_end"].strftime("%Y-%m-%d %H:%M") if p["duty_end"] else None,
            "Pattern Days": p["length_days"],
            "Flight Numbers": " → ".join(s["number"] for s in p["segments"] if s["number"]),
            "Routes": " → ".join(s["route"] for s in p["segments"] if s["route"]),
            "Layover Hrs": p["layover_hours"],
            "Layover Type": p["layover_type"],
            "RQ/RP": p["is_rq_rp"],
            "Turnaround": p["turnaround"],
            "Integrated": p["integrated"]
        }
        for p in filtered
    ]))

    st.info("🔧 Roster simulation engine coming next...")
