"""BigQuery source adapter: authenticates, executes SQL, and returns raw result rows."""
from __future__ import annotations
import json
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request


def _gcloud(*args):
    command = os.environ.get("GCLOUD_CMD", r"C:\Users\hkara\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd")
    return subprocess.check_output(["cmd", "/c", command, *args], text=True, stderr=subprocess.DEVNULL).strip()


def execute_query(query: str):
    token = _gcloud("auth", "print-access-token")
    project = os.environ.get("GOOGLE_CLOUD_PROJECT") or _gcloud("config", "get-value", "project")
    url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{project}/queries"
    body = json.dumps({"query": query, "useLegacySql": False, "timeoutMs": 30000, "maxResults": 10000}).encode()
    request = urllib.request.Request(url, data=body, headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            data = json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"BigQuery HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')}") from exc
    if data.get("errors"):
        raise RuntimeError(str(data["errors"]))
    job_reference = data.get("jobReference", {})
    location, job = job_reference.get("location"), job_reference.get("jobId")
    if data.get("jobComplete") is False:
        if not job:
            raise RuntimeError("BigQuery returned an incomplete job without a job id")
        print(f"BigQuery job {job} is running; waiting for query results...", flush=True)
        for attempt in range(60):
            time.sleep(2)
            poll = f"https://bigquery.googleapis.com/bigquery/v2/projects/{project}/queries/{job}" + (f"?location={location}" if location else "")
            poll_request = urllib.request.Request(poll, headers={"Authorization": "Bearer " + token})
            with urllib.request.urlopen(poll_request, timeout=30) as response:
                data = json.load(response)
            if data.get("jobComplete"):
                break
            if (attempt + 1) % 5 == 0:
                print(f"BigQuery job {job} is still running ({(attempt + 1) * 2}s elapsed).", flush=True)
        if not data.get("jobComplete"):
            raise RuntimeError("BigQuery query exceeded 120-second wait")
        if data.get("errors"):
            raise RuntimeError(str(data["errors"]))
    fields = data.get("schema", {}).get("fields", [])
    results = []

    def append_page(page):
        page_fields = page.get("schema", {}).get("fields", fields)
        results.extend({field["name"]: cell.get("v") for field, cell in zip(page_fields, row["f"])} for row in page.get("rows", []))

    append_page(data)
    page_token = data.get("pageToken")
    page_number = 1
    while page_token:
        if not job:
            raise RuntimeError("BigQuery returned a result page without a job id")
        params = {"pageToken": page_token, "maxResults": 10000}
        if location:
            params["location"] = location
        poll = f"https://bigquery.googleapis.com/bigquery/v2/projects/{project}/queries/{job}?{urllib.parse.urlencode(params)}"
        page_request = urllib.request.Request(poll, headers={"Authorization": "Bearer " + token})
        with urllib.request.urlopen(page_request, timeout=90) as response:
            page = json.load(response)
        if page.get("errors"):
            raise RuntimeError(str(page["errors"]))
        append_page(page)
        page_number += 1
        if page_number % 10 == 0:
            print(f"BigQuery results: fetched {page_number} pages / {len(results)} rows so far.", flush=True)
        page_token = page.get("pageToken")
    return results
