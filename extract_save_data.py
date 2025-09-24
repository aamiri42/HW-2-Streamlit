import datetime
import json
import requests
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from google.cloud import storage
from google.oauth2 import service_account
from pydantic import BaseModel
import streamlit as st  # only needed for secrets fallback

app = FastAPI()

# -------------------------------------------------------------------
# Models
# -------------------------------------------------------------------
class GoogleSearch(BaseModel):
    url: str
    search_engine_id: str
    api_key: str
    no_days: int
    job_title: str
    company_dictionary: dict


class GcsStringUpload(BaseModel):
    service_account_key: str  # only used locally
    project_id: str
    bucket_name: str
    file_name: str
    data: str

# -------------------------------------------------------------------
# Helper: Get credentials
# -------------------------------------------------------------------
def get_credentials(service_account_path: str = None):
    """Return credentials for GCS (local or Streamlit Cloud)."""
    if service_account_path:
        return service_account.Credentials.from_service_account_file(service_account_path)
    else:
        # secrets["gcp"]["service_account"] contains JSON string
        service_account_info = json.loads(st.secrets["gcp"]["service_account"])
        return service_account.Credentials.from_service_account_info(service_account_info)

# -------------------------------------------------------------------
# Utils
# -------------------------------------------------------------------
def parse_google_search_results(search_results: dict, job_list: list) -> None:
    """Parse search API results and append job postings."""
    items = search_results.get("items", [])
    for item in items:
        snippet = item.get("snippet", "")
        if " days ago" in snippet:
            try:
                day_diff = int(snippet.split(" days ago")[0].split()[-1])
            except Exception:
                day_diff = 0
        else:
            day_diff = 0

        date = datetime.date.today() - datetime.timedelta(days=day_diff)
        job_list.append(
            {
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": snippet,
                "date": str(date),
            }
        )

# -------------------------------------------------------------------
# Routes
# ----------------------------
