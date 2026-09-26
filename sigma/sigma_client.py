"""Minimal Sigma REST API client (v2).

Auth: client-credentials token from POST /v2/auth/token (Sigma Admin > Developer
Access creates the client id/secret). Endpoints used, per Sigma's API docs and
its sigma-sample-api repo:
  GET  /v2/workbooks                                   list workbooks
  GET  /v2/workbooks/{id}/pages                        list pages
  GET  /v2/workbooks/{id}/pages/{pageId}/elements      list elements
  POST /v2/workbooks/{id}/export  {format, elementId}  start an element export
  GET  /v2/query/{queryId}/download                    200 = ready, 204 = pending
"""
from __future__ import annotations

import csv
import io
import os
import time

import requests

BASE_URLS = {
    "aws": "https://aws-api.sigmacomputing.com",
    "gcp": "https://api.sigmacomputing.com",
    "azure": "https://api.us.azure.sigmacomputing.com",
}


class SigmaClient:
    def __init__(self, client_id: str, client_secret: str, cloud: str = "aws",
                 base_url: str | None = None, session: requests.Session | None = None):
        self.base_url = (base_url or BASE_URLS[cloud]).rstrip("/")
        self.http = session or requests.Session()
        r = self.http.post(f"{self.base_url}/v2/auth/token", data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        })
        r.raise_for_status()
        self.http.headers["Authorization"] = f"Bearer {r.json()['access_token']}"

    @classmethod
    def from_env(cls) -> "SigmaClient":
        return cls(os.environ["SIGMA_CLIENT_ID"], os.environ["SIGMA_CLIENT_SECRET"],
                   cloud=os.environ.get("SIGMA_CLOUD", "aws"),
                   base_url=os.environ.get("SIGMA_API_URL"))

    def _list(self, path: str) -> list[dict]:
        """Follow Sigma's page-token pagination and return all entries."""
        out, page = [], None
        while True:
            params = {"limit": 500, **({"page": page} if page else {})}
            r = self.http.get(f"{self.base_url}/{path}", params=params)
            r.raise_for_status()
            body = r.json()
            out.extend(body.get("entries", []))
            page = body.get("nextPage")
            if not page:
                return out

    def find_workbook(self, name: str) -> dict:
        hits = [w for w in self._list("v2/workbooks") if w.get("name") == name]
        if len(hits) != 1:
            raise LookupError(f"expected exactly one workbook named {name!r}, found {len(hits)}")
        return hits[0]

    def elements_by_title(self, workbook_id: str) -> dict[str, dict]:
        """Map element title -> element across all pages."""
        found = {}
        for page in self._list(f"v2/workbooks/{workbook_id}/pages"):
            for el in self._list(f"v2/workbooks/{workbook_id}/pages/{page['pageId']}/elements"):
                title = el.get("name") or el.get("title")
                if title:
                    found[title] = el
        return found

    def export_element_csv(self, workbook_id: str, element_id: str,
                           poll_seconds: float = 3, timeout_seconds: float = 300) -> list[dict]:
        r = self.http.post(f"{self.base_url}/v2/workbooks/{workbook_id}/export",
                           json={"format": {"type": "csv"}, "elementId": element_id})
        r.raise_for_status()
        query_id = r.json()["queryId"]
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            d = self.http.get(f"{self.base_url}/v2/query/{query_id}/download")
            if d.status_code == 200:
                return list(csv.DictReader(io.StringIO(d.content.decode("utf-8-sig"))))
            if d.status_code != 204:
                d.raise_for_status()
            time.sleep(poll_seconds)
        raise TimeoutError(f"export {query_id} not ready after {timeout_seconds}s")
