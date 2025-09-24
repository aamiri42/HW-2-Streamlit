import json
import pandas as pd
import streamlit as st
from google.cloud import storage
from google.oauth2 import service_account

# 🔹 Local configuration (replace with your actual path)
service_account_file = "/Users/sirsn/Downloads/nifty-edge-470418-e5-b140ab3f9228.json"
project_id = "nifty-edge-470418-e5"
bucket_name = "dataacqhw2alexa"
file_name_prefix = "job_search/"

def get_storage_client():
    """Create a GCS client using the local service account JSON file."""
    credentials = service_account.Credentials.from_service_account_file(
        service_account_file
    )
    return storage.Client(project=project_id, credentials=credentials)

def retrieve_data_from_gcs():
    """Retrieve job postings from GCS and merge results."""
    client = get_storage_client()
    bucket = client.bucket(bucket_name)
    blobs = bucket.list_blobs(prefix=file_name_prefix)

    content = []
    job_titles = []
    company_dict = dict()

    for blob in blobs:
        data = json.loads(blob.download_as_text())
        content += data.get("results", [])
        job_titles.append(data.get("job_title", ""))
        company_dict |= data.get("company_dict", {})

    return {
        "results": content,
        "job_titles": sorted(set(job_titles)),
        "company_dict": dict(sorted(company_dict.items()))
    }

if __name__ == "__main__":
    gcs_data = retrieve_data_from_gcs()

    # Debug info (you can remove later)
    st.write("✅ Total results:", len(gcs_data["results"]))
    if gcs_data["results"]:
        st.write("🔍 Sample result:", gcs_data["results"][:2])

    role_name = ", ".join(gcs_data["job_titles"])
    company_dictionary = gcs_data["company_dict"]
    gcs_data_result = gcs_data["results"]

    st.title(f"{role_name} Job Listings")

    with st.sidebar:
        st.write("Filter by Company")
        unique_categories = list(company_dictionary.keys())
        unique_categories.sort()
        selected_categories = []

        for category in unique_categories:
            if st.checkbox(category, value=True, key=f"checkbox_{category}"):
                selected_categories.append(company_dictionary[category])

    # Build dataframe
    df = pd.DataFrame(gcs_data_result).drop_duplicates(subset=["title", "link", "date"])

    if selected_categories:
        mask = df["link"].apply(lambda link: any(link.startswith(sub) for sub in selected_categories))
        df = df[mask]

    if not df.empty:
        st.dataframe(
            df[["date", "title", "link"]],
            hide_index=True,
            column_config={"link": st.column_config.LinkColumn("Job Link")}
        )
    else:
        st.write("⚠️ No job postings match your filter.")
