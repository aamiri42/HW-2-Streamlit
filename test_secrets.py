import streamlit as st
import json

st.title("🔑 Secrets Debugger")

try:
    # Show all secret sections
    st.write("Available sections in st.secrets:", list(st.secrets.keys()))

    # Grab the raw service account string
    raw_service_account = st.secrets["gcp"]["service_account"]

    st.subheader("Raw service_account (first 200 chars)")
    st.code(raw_service_account[:200] + "...", language="json")

    # Try to parse it as JSON
    service_account_info = json.loads(raw_service_account)

    st.success("✅ JSON parsed successfully!")
    st.json(service_account_info)

except KeyError as e:
    st.error(f"❌ Missing key in st.secrets: {e}")
except json.JSONDecodeError as e:
    st.error(f"❌ JSON failed to parse: {e}")
