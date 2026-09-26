"""Offline tests for the Sigma integration.

The fixtures are the dbt sigma_* views exported with Sigma-style Title Case
headers, i.e. what Sigma's CSV export of each element returns when the
workbook is built as specified. Live Sigma calls are mocked; the real API has
not been exercised from this build environment.
"""
import csv
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import sigma_client  # noqa: E402
from verify_workbook import REQUIRED, expectations, num, verify  # noqa: E402

RESULTS = json.loads((HERE.parents[1] / "validation/validation_results.json").read_text())
FILES = {"Lift Summary": "lift_summary", "Campaign Efficiency": "campaign_efficiency",
         "Replication by Sample": "replication_by_sample", "Assignment QA": "assignment_qa"}


def load(title):
    with open(HERE / "fixtures" / f"{FILES[title]}.csv") as f:
        return list(csv.DictReader(f))


def exports():
    return {t: load(t) for t in REQUIRED}


def test_workbook_matching_dbt_marts_passes():
    assert verify(exports(), RESULTS) == []


def test_expectation_count():
    assert len(expectations(RESULTS)) == 20  # 8 lift + 6 replication + 3 campaign + 3 assignment


def test_wrong_number_in_sigma_is_caught():
    ex = exports()
    for r in ex["Campaign Efficiency"]:
        if r["Campaign"] == "1178":
            r["Cost Per Approved Conversion Usd"] = str(float(r["Cost Per Approved Conversion Usd"]) / 2)
    errs = verify(ex, RESULTS)
    assert len(errs) == 1 and "1178" in errs[0]


def test_averaged_ratio_instead_of_ratio_of_sums_is_caught():
    # A common BI mistake: relative lift replaced by a different figure
    ex = exports()
    ex["Lift Summary"][0]["Relative Lift"] = "0.5"
    assert any("relative_lift" in e for e in verify(ex, RESULTS))


def test_missing_element_is_caught():
    ex = exports()
    del ex["Assignment QA"]
    assert "missing element: Assignment QA" in verify(ex, RESULTS)


def test_percent_and_currency_formats_parse():
    assert num("26.6%") == pytest.approx(0.266)
    assert num("$63.83") == 63.83
    assert num("1,677,052") == 1677052


class FakeResp:
    def __init__(self, status=200, body=None, content=b""):
        self.status_code, self._body, self.content = status, body, content

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


class FakeSession:
    """Scripted Sigma API: paginated lists, and an export that is pending once."""
    def __init__(self):
        self.headers, self.calls, self.polls = {}, [], 0

    def post(self, url, data=None, json=None):
        self.calls.append(("POST", url))
        if url.endswith("/v2/auth/token"):
            assert data["grant_type"] == "client_credentials"
            return FakeResp(body={"access_token": "tok"})
        if url.endswith("/export"):
            assert json == {"format": {"type": "csv"}, "elementId": "el-1"}
            return FakeResp(body={"queryId": "q-1"})
        raise AssertionError(url)

    def get(self, url, params=None):
        self.calls.append(("GET", url))
        if url.endswith("/v2/workbooks"):
            if not params.get("page"):
                return FakeResp(body={"entries": [{"workbookId": "w-0", "name": "Other"}], "nextPage": "p2"})
            return FakeResp(body={"entries": [{"workbookId": "w-1", "name": "Ad Incrementality & Campaign Efficiency"}]})
        if url.endswith("/pages"):
            return FakeResp(body={"entries": [{"pageId": "pg-1"}]})
        if url.endswith("/elements"):
            return FakeResp(body={"entries": [{"elementId": "el-1", "name": "Lift Summary"}]})
        if url.endswith("/v2/query/q-1/download"):
            self.polls += 1
            if self.polls == 1:
                return FakeResp(status=204)
            return FakeResp(content=b"Outcome,Relative Lift\nvisit,0.2658\n")
        raise AssertionError(url)


def test_client_auth_pagination_and_export_polling():
    s = FakeSession()
    c = sigma_client.SigmaClient("id", "secret", cloud="aws", session=s)
    assert s.headers["Authorization"] == "Bearer tok"
    wb = c.find_workbook("Ad Incrementality & Campaign Efficiency")
    assert wb["workbookId"] == "w-1"
    els = c.elements_by_title("w-1")
    rows = c.export_element_csv("w-1", els["Lift Summary"]["elementId"], poll_seconds=0)
    assert rows == [{"Outcome": "visit", "Relative Lift": "0.2658"}]
    assert s.polls == 2
    assert s.calls[0] == ("POST", "https://aws-api.sigmacomputing.com/v2/auth/token")
