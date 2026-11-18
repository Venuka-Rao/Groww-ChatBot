import json
from pathlib import Path

from src.config import Scheme, Settings
from src.pipeline.load import extract_text, fetch_scheme, find_factsheet_url, load_corpus

FIXTURE = Path(__file__).parent / "fixtures" / "scheme_page.html"
PAGE = "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth"
SCHEME = Scheme(
    slug="hdfc-large-cap-fund-direct-growth",
    name="HDFC Large Cap Fund Direct Growth",
    url=PAGE,
    aliases=("HDFC Large Cap Fund",),
)


class FakeResponse:
    def __init__(self, status_code, url, text="", headers=None):
        self.status_code = status_code
        self.url = url
        self.text = text
        self.headers = headers or {}


class FakeClient:
    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def get(self, url, **kwargs):
        assert kwargs.get("follow_redirects") is False
        self.calls.append(url)
        if url not in self.routes:
            raise AssertionError(f"unexpected fetch: {url}")
        return self.routes[url]


def test_table_text_is_kept_and_other_links_are_not_fetched():
    html = FIXTURE.read_text(encoding="utf-8")
    client = FakeClient({PAGE: FakeResponse(200, PAGE, html)})
    record = fetch_scheme(client, SCHEME)
    assert "Expense ratio: 0.99%" in record["text"]
    assert record["factsheet_url"] == "https://www.hdfcfund.com/docs/factsheet.pdf"
    assert client.calls == [PAGE]
    assert "example.com/blog" not in "".join(client.calls)


def test_factsheet_link_is_stored_and_not_requested():
    html = FIXTURE.read_text(encoding="utf-8")
    assert find_factsheet_url(html, PAGE).endswith("factsheet.pdf")
    client = FakeClient({PAGE: FakeResponse(200, PAGE, html)})
    fetch_scheme(client, SCHEME)
    assert all("factsheet" not in call for call in client.calls)


def test_peer_fund_fields_are_not_copied_into_the_page_text():
    payload = {
        "props": {
            "pageProps": {
                "mfServerSideData": {
                    "expense_ratio": "1.0",
                    "exit_load": "Exit load of 1% if redeemed within 1 year",
                    "return_stats": [{"risk": "Very High", "return1y": 42.5, "alpha": 3.2}],
                    "peerComparison": [
                        {
                            "scheme_name": "Other Fund",
                            "expense_ratio": "9.99",
                            "url": "https://groww.in/mutual-funds/other-fund",
                        }
                    ],
                    "amc_page_url": "https://groww.in/mutual-funds/amc/hdfc-mutual-funds",
                }
            }
        }
    }
    html = f'<html><script id="__NEXT_DATA__" type="application/json">{json.dumps(payload)}</script></html>'
    text = extract_text(html)
    assert "Expense ratio: 1.0" in text
    assert "Riskometer: Very High" in text
    assert "42.5" not in text
    assert "9.99" not in text
    assert "other-fund" not in text
    assert "amc/hdfc" not in text


def test_redirect_off_the_scheme_url_drops_the_body():
    other = "https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-growth"
    client = FakeClient(
        {
            PAGE: FakeResponse(302, PAGE, "<html>secret</html>", {"location": other}),
        }
    )
    record = fetch_scheme(client, SCHEME)
    assert record["text"] == ""
    assert record["error"] == "redirect left the allowlist"
    assert client.calls == [PAGE]


def test_failed_url_is_recorded_and_the_other_page_is_kept(tmp_path):
    ok = SCHEME
    bad = Scheme(
        slug="hdfc-liquid-fund-direct-growth",
        name="HDFC Liquid Fund Direct Growth",
        url="https://groww.in/mutual-funds/hdfc-liquid-fund-direct-growth",
        aliases=("HDFC Liquid Fund",),
    )
    html = FIXTURE.read_text(encoding="utf-8")
    client = FakeClient(
        {
            ok.url: FakeResponse(200, ok.url, html),
            bad.url: FakeResponse(500, bad.url, "nope"),
        }
    )
    settings = Settings(
        root=tmp_path,
        embedding_model="sentence-transformers/all-MiniLM-L6-v2",
        chroma_path=tmp_path / "chroma",
        llm_provider="groq",
        top_k=4,
        min_score=0.35,
        request_timeout_seconds=5,
        llm_model_id="",
        schemes=(ok, bad),
    )
    run_id = load_corpus(settings, client)
    manifest = json.loads(
        (tmp_path / "data" / "artifacts" / "load" / run_id / "manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["successes"] == [ok.slug]
    assert manifest["failures"] == [{"slug": bad.slug, "error": "HTTP 500"}]
    failed = json.loads(
        (tmp_path / "data" / "artifacts" / "load" / run_id / f"{bad.slug}.json").read_text(encoding="utf-8")
    )
    assert failed["text"] == ""
