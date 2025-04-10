import streamlit as st
import pandas as pd
import re
from datetime import datetime
from PyPDF2 import PdfReader

st.set_page_config(page_title="Reference Roster Generator", layout="wide")
st.title("✈️ Reference Roster Generator")

# --- Sidebar Input ---
st.sidebar.header("👤 Pilot Profile")
category = st.sidebar.selectbox("Category", ["FO", "SO", "CN"])

is_rq_rp = False
if category == "FO":
    is_rq_rp = st.sidebar.checkbox("I am RQ/RP Qualified", value=False)

st.sidebar.header("📥 Upload Pairing PDF")
file = st.sidebar.file_uploader("Upload the PDF file (Pairing Book)", type=["pdf"])

# --- Bid Preferences ---
st.sidebar.header("🎯 Bid Preferences")
want_jfk = st.sidebar.checkbox("Prefer JFK Layover")
avoid_lax = st.sidebar.checkbox("Avoid LAX")
want_gdo_sundays = st.sidebar.checkbox("Want GDO on Sundays")
latest_sign_on = st.sidebar.time_input("Earliest Acceptable Sign-On", value=datetime.strptime("08:00", "%H:%M"))

# --- PDF Parsing Function ---
def extract_pairings_from_pdf(uploaded_file):
    reader = PdfReader(uploaded_file)
    full_text = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())

    st.subheader("🧪 Raw PDF Text Preview (First 3000 chars)")
    st.code(full_text[:3000])

    # Match blocks starting with 'Trip Id:'
    trip_blocks = re.findall(r"Trip Id:.*?(?=(\nTrip Id:|\Z))", full_text, re.DOTALL)
    pairings = []

    for block in trip_blocks:
        trip_id_match = re.search(r"Trip Id:\s*(\S+)", block)
        flight_match = re.search(r"\n(\d{3,4})\n", block)
        sign_on_match = re.search(r"\n(\d{2}:\d{2})\n", block)
        port_match = re.search(r"\n([A-Z]{3})\n", block)

        if trip_id_match:
            trip_id = trip_id_match.group(1)
            flight = flight_match.group(1) if flight_match else ""
            sign_on = sign_on_match.group(1) if sign_on_match else ""
            port = port_match.group(1) if port_match else ""
            is_rq_rp_trip = "(RQ)" in trip_id or "(RP)" in trip_id

            pairings.append({
                "trip_id": trip_id,
                "first_flight": flight,
                "sign_on": sign_on,
                "port": port,
                "is_rq_rp": is_rq_rp_trip
            })

    return pairings

# --- Main App ---
if file:
    pairing_list = extract_pairings_from_pdf(file)

    if category == "FO" and not is_rq_rp:
        pairing_list = [p for p in pairing_list if not p['is_rq_rp']]

    st.success(f"✅ Loaded {len(pairing_list)} pairings from PDF ({'RQ/RP included' if is_rq_rp or category != 'FO' else 'FO only'})")

    # Show filtered pairings
    st.subheader("📋 Filtered Pairings")
    df_pairings = pd.DataFrame(pairing_list)
    st.dataframe(df_pairings)

    st.info("🛠️ Roster simulation engine coming next...")
else:
    st.warning("⬅️ Please upload a pairing PDF file to begin.")
