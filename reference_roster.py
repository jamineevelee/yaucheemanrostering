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
                    pairing = {
                        "start_date": date,
                        "segments": [{
                            "date": date,
                            "number": number,
                            "route": route,
                            "time": time
                        }],
                        "source_row": row,
                        "duty_start": None,
                        "duty_end": None
                    }

                    # Check next day(s) if it's same pattern or separate
                    j = i + 1
                    while j < len(dates):
                        try:
                            next_date = pd.to_datetime(dates[j]).date()
                        except:
                            break

                        next_number = str(numbers[j]) if pd.notna(numbers[j]) else ""
                        next_route = str(routes[j]) if pd.notna(routes[j]) else ""
                        next_time = str(times[j]) if pd.notna(times[j]) else ""
                        if not (next_number or next_route or next_time):
                            break

                        try:
                            last_arr_time = datetime.strptime(pairing["segments"][-1]["time"].split("-")[-1], "%H%M").time()
                            last_arr_dt = datetime.combine(pairing["segments"][-1]["date"], last_arr_time)
                            next_dep_time = datetime.strptime(next_time.split("-")[0], "%H%M").time()
                            next_dep_dt = datetime.combine(next_date, next_dep_time)
                            rest_period = (next_dep_dt - last_arr_dt).total_seconds() / 3600.0
                            if rest_period >= 9:
                                break  # Treat as new pairing
                        except:
                            break

                        pairing["segments"].append({
                            "date": next_date,
                            "number": next_number,
                            "route": next_route,
                            "time": next_time
                        })
                        i = j
                        j += 1

                    pairing["end_date"] = pairing["segments"][-1]["date"]
                    pairing["is_rq_rp"] = any(
                        re.search(r"\(RQ|RP\)", s["number"]) or
                        re.search(r"\(RQ|RP\)", s["route"]) or
                        re.search(r"\(RQ|RP\)", s["time"])
                        for s in pairing["segments"]
                    )
                    pairing["length_days"] = (pairing["end_date"] - pairing["start_date"]).days + 1

                    try:
                        dep_time = datetime.strptime(pairing["segments"][0]["time"].split("-")[0], "%H%M")
                        pairing["duty_start"] = datetime.combine(pairing["segments"][0]["date"], dep_time.time()) - timedelta(hours=1, minutes=10)
                    except:
                        pairing["duty_start"] = "N/A"
                    try:
                        arr_time = datetime.strptime(pairing["segments"][-1]["time"].split("-")[-1], "%H%M")
                        pairing["duty_end"] = datetime.combine(pairing["segments"][-1]["date"], arr_time.time())
                    except:
                        pairing["duty_end"] = "N/A"

                    pairing["turnaround"] = pairing["start_date"] == pairing["end_date"]
                    pairings.append(pairing)

                i += 1
            row += 4
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

    def get_layover(p):
        try:
            if len(p["segments"]) > 1 and "-" in p["segments"][0]["time"] and "-" in p["segments"][1]["time"]:
                arr_str = p["segments"][0]["time"].split("-")[-1]
                dep_str = p["segments"][1]["time"].split("-")[0]
                arr_time = datetime.strptime(arr_str, "%H%M").time()
                dep_time = datetime.strptime(dep_str, "%H%M").time()
                arr_dt = datetime.combine(p["segments"][0]["date"], arr_time)
                dep_dt = datetime.combine(p["segments"][1]["date"], dep_time)
                return str(dep_dt - arr_dt)
            else:
                return "N/A"
        except:
            return "N/A"

    st.dataframe(pd.DataFrame([
        {
            "Duty Start Date": p["start_date"],
            "Duty End Date": p["end_date"],
            "Total Pattern Days": p["length_days"],
            "RQ/RP": p["is_rq_rp"],
            "Routes": " → ".join(s["route"] for s in p["segments"] if s["route"]),
            "Flight Numbers": " → ".join(s["number"] for s in p["segments"] if s["number"]),
            "Duty Start": p["duty_start"],
            "Duty End": p["duty_end"],
            "Layover Duration": get_layover(p),
            "Turnaround": p["turnaround"],
            "Integrated": any("HKG" in s["route"] for s in p["segments"][1:-1])
        }
        for p in filtered_pairings
    ]))

    st.info("🔧 Roster simulation engine coming next...")
