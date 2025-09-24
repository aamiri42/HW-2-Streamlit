import datetime
import json


from fastapi import FastAPI
from fastapi.responses import JSONResponse
from google.oauth2 import service_account
from google.cloud import storage
from pydantic import BaseModel
import requests

app = FastAPI()


class GoogleSearch(BaseModel):
    url: str  # GoogleAPI URLs Ex. "https://www.googleapis.com/customsearch/v1"
    search_engine_id: str  # Google API's customsearch engine id
    # GCP API Key (different from service account key
    # this is for custom search)
    api_key: str
    no_days: int  # For the search restuls
    job_title: str
    company_dictionary: dict


class GcsStringUpload(BaseModel):
    service_account_key: str
    project_id: str
    bucket_name: str
    file_name: str
    data: str


def parse_google_search_results(search_results: dict,
                                job_list: list) -> None:
    """    
    Extend job_list to be a list of dictionaries.
    Each dictionary should include title, link, snippet and date.
    title, link, and snippet are from search_results' "items".
    date is based on the snippet's "xx days ago". 
    You can use the current date and xx days to calculate the date.

    Args:
        search_results (dict) : search request's response.json()
        job_list (list) : a list of dictionary with title, link,
                          snippet and date.

    """
    items = search_results["items"]
    for item in items:
        if " days ago" in item["snippet"]:
            day_diff = int(item["snippet"].split(" days ago")[0])
        else:
            day_diff = 0
        date = datetime.date.today() - datetime.timedelta(days=day_diff)
        job_list.append({"title": item["title"],
                         "link": item["link"],
                         "snippet": item["snippet"],
                         "date": date})


@app.post("/search/jobs")
def call_google_search(search_param: GoogleSearch):
    """
    Refer to https://developers.google.com/custom-search/v1/reference/rest/v1/Search
    parameters should be properly assigned including
    key, cx, query, and dateRestrict, etc.
    If the search returns more than 100 matches, it should limit the matches 
    to 100.
    """
    company_string = " OR site:".join(search_param.company_dictionary.values())
    query = f"{search_param.job_title} jobs on site:{company_string}"
    params = {
        "key": search_param.api_key,
        "cx": search_param.search_engine_id,
        "q": query,
        # d/w/m/y[number] : last [number] of days
        "dateRestrict": f"d{search_param.no_days}"
    }

    # Make the API request
    try:
        response = requests.get(search_param.url, params=params)
        # Raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status()
        no_results = int(response.json()["searchInformation"]["totalResults"])
        job_list = []
        print(response.request.url)
        # it can only return up to 100s.
        for i in range(0, min(no_results, 100), 10):
            params["start"] = i
            response = requests.get(search_param.url, params=params)

            search_results = response.json()
            # Raise an exception for bad status codes (4xx or 5xx)
            response.raise_for_status()
            parse_google_search_results(search_results, job_list)
        return {"company_dict": search_param.company_dictionary,
                "job_title": search_param.job_title,
                "results": job_list}

    except requests.exceptions.RequestException as e:
        print(f"Error making API request: {e}")
        if response is not None:
            print(f"Response status code: {response.status_code}")
            print(f"Response body: {response.text}")
        return JSONResponse(
            status_code=response.status_code,
            content={
                "message": f"Error making API request: {e}"},
        )


@app.put("/save_to_gcs")
def save_to_gcs(gcs_upload_param: GcsStringUpload):
    """
    Access the bucket with service_account_key, and upload the object(blob)
    the the storage.
    It should return a dictionary of message.
    """
    credentials = service_account.Credentials.\
        from_service_account_file(gcs_upload_param.service_account_key)
    client = storage.Client(project=gcs_upload_param.project_id,
                            credentials=credentials)
    bucket = client.bucket(gcs_upload_param.bucket_name)
    file = bucket.blob(gcs_upload_param.file_name)
    blob_data = gcs_upload_param.data
    file.upload_from_string(blob_data)
    return {"message": f"file {gcs_upload_param.file_name} has been uploaded\
            to {gcs_upload_param.bucket_name} successfully."}
