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
        dates = df.iloc[3].tolist()[2:]
        row = 5
        while row + 2 < len(df):
            current_pairing = None
            routes = df.iloc[row + 1].tolist()[2:]
            times = df.iloc[row + 2].tolist()[2:]
            numbers = df.iloc[row].tolist()[2:]
            i = 0
            while i < len(dates):
                try:
                    date = pd.to_datetime(dates[i]).date()
                except:
                    i += 1
                    continue
                route = routes[i]
                time = times[i]
                number = numbers[i]
                has_flight = pd.notna(route) or pd.notna(time) or pd.notna(number)
                if has_flight:
                    if current_pairing is None:
                        current_pairing = {"start_date": date, "segments": [], "source_row": row}
                    current_pairing["segments"].append({
                        "date": date,
                        "route": route or "",
                        "time": time or "",
                        "number": str(number) if pd.notna(number) else ""
                    })
                else:
                    if current_pairing:
                        current_pairing["end_date"] = current_pairing["segments"][-1]["date"]
                        current_pairing["is_rq_rp"] = any(
                            re.search(r"\((RQ|RP)\)", s["time"])
                            or re.search(r"\((RQ|RP)\)", s["route"])
                            or re.search(r"\((RQ|RP)\)", s["number"])
                            for s in current_pairing["segments"] if s["time"] or s["route"] or s["number"]
                        )
                        current_pairing["length_days"] = (current_pairing["end_date"] - current_pairing["start_date"]).days + 1
                        pairings.append(current_pairing)
                        current_pairing = None
                i += 1
            if current_pairing:
                current_pairing["end_date"] = current_pairing["segments"][-1]["date"]
                current_pairing["is_rq_rp"] = any(
                    re.search(r"\((RQ|RP)\)", s["time"])
                    or re.search(r"\((RQ|RP)\)", s["route"])
                    or re.search(r"\((RQ|RP)\)", s["number"])
                    for s in current_pairing["segments"] if s["time"] or s["route"] or s["number"]
                )
                current_pairing["length_days"] = (current_pairing["end_date"] - current_pairing["start_date"]).days + 1
                pairings.append(current_pairing)
            row += 4
    except Exception as e:
        st.error(f"❌ Error grouping pairings: {e}")
    return pairings

def simulate_reference_roster(pairings):
    sorted_pairings = sorted(pairings, key=lambda p: p["start_date"])
    roster = []
    last_end = None
    for pairing in sorted_pairings:
        if last_end is None or pairing["start_date"] > last_end:
            score = 0
            for seg in pairing["segments"]:
                route = seg["route"].upper()
                if want_jfk and "JFK" in route:
                    score += 100
                if avoid_lax and "LAX" in route:
                    score -= 100
                if want_gdo_sundays and seg["date"].weekday() == 6:
                    score -= 50
                if seg["time"] and seg["time"][:5] < latest_sign_on.strftime("%H:%M"):
                    score -= 30
            pairing["score"] = score
            roster.append(pairing)
            last_end = pairing["end_date"]
    return roster

# --- Main App ---
if file:
    df = pd.read_excel(file, sheet_name=0)
    st.subheader("🧪 Raw Data Preview (Top 40 Rows)")
    st.dataframe(df.head(40))
    all_pairings = group_pairings(df)
    if category == "FO" and not is_rq_rp:
        all_pairings = [p for p in all_pairings if not p.get("is_rq_rp", False)]
    st.success(f"✅ Grouped {len(all_pairings)} pairings ({'RQ/RP included' if is_rq_rp or category != 'FO' else 'FO only'})")

    st.subheader("📋 Reference Roster Preview")
    final_roster = simulate_reference_roster(all_pairings)
    preview = [{
        "Start": p["start_date"],
        "End": p["end_date"],
        "Days": p["length_days"],
        "Score": p["score"],
        "Routes": " → ".join([s["route"] for s in p["segments"] if s["route"]]),
        "From Row": p["source_row"]
    } for p in final_roster]
    st.dataframe(pd.DataFrame(preview))

    st.success(f"🧠 Reference Roster simulated with {len(final_roster)} pairings.")
else:
    st.warning("⬅️ Please upload a pairing Excel file to begin.")
