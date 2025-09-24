import streamlit as st
import json

st.header("🔍 Debugging Secrets")

# Show the raw type of the service account string
st.write("Type of service_account secret:", type(st.secrets["gcp"]["service_account"]))

# Show the raw value (so you can compare with your JSON file)
st.text(st.secrets["gcp"]["service_account"])

# Try to parse it
try:
    creds = json.loads(st.secrets["gcp"]["service_account"])
    st.success("✅ JSON parsed successfully!")
    st.json(creds)  # pretty-print
except Exception as e:
    st.error(f"❌ JSON failed to parse: {e}")
