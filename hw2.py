import json
import pandas as pd
import streamlit as st
from google.cloud import storage
from google.oauth2 import service_account

# -------------------------------------------------------------------
# Try local first, then fall back to Streamlit secrets
# -------------------------------------------------------------------
try:
    from user_definition import (
        service_account_file_path,
        project_id,
        bucket_name,
        file_name_prefix,
    )
    USE_LOCAL = True
except ImportError:
    USE_LOCAL = False
    project_id = st.secrets["gcp"]["project_id"]
    bucket_name = st.secrets["gcp"]["bucket_name"]
    file_name_prefix = st.secrets["gcp"]["file_name_prefix"]

# -------------------------------------------------------------------
# Helper: Build GCS client
# -------------------------------------------------------------------
def get_storage_client():
    if USE_LOCAL:
        credentials = service_account.Credentials.from_service_account_file(
            service_account_file_path
        )
        return storage.Client(project=project_id, credentials=credentials)
    else:
        # Service account JSON is stored as a string in secrets.toml
        service_account_info = json.loads(st.secrets["gcp"]["service_account"])
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info
        )
        return storage.Client(project=project_id, credentials=credentials)

# -------------------------------------------------------------------
# Function: Retrieve job postings from GCS
# -------------------------------------------------------------------
def retrieve_data_from_gcs(
    project_id: str, bucket_name: str, file_name_prefix: str
) -> dict:
    """Retrieve job postings from all files starting with prefix in the bucket."""
    client = get_storage_client()
    bucket = client.bucket(bucket_name)
    blobs = bucket.list_blobs()

    content, job_titles, company_dict = [], [], {}

    for blob in blobs:
        if blob.name.startswith(file_name_prefix):
            blob_data = json.loads(blob.download_as_bytes())
            content.extend(blob_data["results"])
            job_titles.append(blob_data["job_title"])
            company_dict = {**company_dict, **blob_data["company_dict"]}

    return {
        "results": content,
        "job_titles": sorted(set(job_titles)),
        "company_dict": dict(sorted(company_dict.items())),
    }

# -------------------------------------------------------------------
# Streamlit App
# -------------------------------------------------------------------
if __name__ == "__main__":
    gcs_data = retrieve_data_from_gcs(project_id, bucket_name, file_name_prefix)

    role_name = ", ".join(gcs_data["job_titles"])
    company_dictionary = gcs_data["company_dict"]
    gcs_data_result = gcs_data["results"]

    st.title(f"{role_name} Job Listings")

    with st.sidebar:
        st.write("Filter by Company")
        unique_categories = sorted(company_dictionary.keys())
        selected_categories = [
            company_dictionary[cat]
            for cat in unique_categories
            if st.checkbox(cat, value=True, key=f"checkbox_{cat}")
        ]

    df = pd.DataFrame(gcs_data_result).drop_duplicates()

    if selected_categories:
        mask = df["link"].apply(
            lambda link: any(link.startswith(sub) for sub in selected_categories)
        )
        df = df[mask]

    if not df.empty:
        st.dataframe(
            df[["date", "title", "link"]],
            hide_index=True,
            column_config={"link": st.column_config.LinkColumn("Job Link")},
        )
    else:
        st.write("No job postings match your filter.")
