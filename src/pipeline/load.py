"""Fetch the 25 allowlisted scheme pages and store their text.

Each run requests only the URLs in config/urls.yaml. Links found on a page,
including factsheet links, are not fetched.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from src.config import Scheme, Settings, load_settings

USER_AGENT = "Mozilla/5.0 (compatible; GrowwFaqPrototype/0.1; facts-only demo)"
REDIRECT_STATUSES = {301, 302, 303, 307, 308}

# Top-level fields of this scheme only. Nested blocks such as peerComparison
# are other funds and are intentionally left out.
SCHEME_FIELDS = (
    ("scheme_name", "Scheme name"),
    ("fund_house", "Fund house"),
    ("amc", "AMC"),
    ("category", "Category"),
    ("sub_category", "Sub category"),
    ("plan_type", "Plan"),
    ("scheme_type", "Scheme type"),
    ("description", "Description"),
    ("expense_ratio", "Expense ratio"),
    ("base_expense_ratio", "Base expense ratio"),
    ("exit_load", "Exit load"),
    ("min_sip_investment", "Minimum SIP"),
    ("min_investment_amount", "Minimum investment"),
    ("mini_additional_investment", "Minimum additional investment"),
    ("benchmark", "Benchmark"),
    ("benchmark_name", "Benchmark name"),
    ("stamp_duty", "Stamp duty"),
    ("fund_manager", "Fund manager"),
    ("launch_date", "Launch date"),
    ("aum", "AUM"),
    ("nav", "NAV"),
    ("nav_date", "NAV date"),
    ("isin", "ISIN"),
    ("sip_allowed", "SIP allowed"),
    ("lumpsum_allowed", "Lumpsum allowed"),
)


def load_corpus(settings: Settings | None = None, client: httpx.Client | None = None) -> str:
    settings = settings or load_settings()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = settings.root / "data" / "artifacts" / "load" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    own_client = client is None
    if own_client:
        client = httpx.Client(
            timeout=settings.request_timeout_seconds,
            follow_redirects=False,
            headers={"User-Agent": USER_AGENT},
        )

    successes: list[str] = []
    failures: list[dict] = []
    try:
        for scheme in settings.schemes:
            record = fetch_scheme(client, scheme)
            _write_json(out_dir / f"{scheme.slug}.json", record)
            if record["text"] and not record["error"]:
                successes.append(scheme.slug)
            else:
                failures.append({"slug": scheme.slug, "error": record["error"] or "empty page"})
    finally:
        if own_client:
            client.close()

    loaded_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if successes else ""
    _write_json(
        out_dir / "manifest.json",
        {
            "run_id": run_id,
            "loaded_at": loaded_at,
            "successes": successes,
            "failures": failures,
        },
    )
    if not successes:
        raise SystemExit(1)
    return run_id


def fetch_scheme(client, scheme: Scheme) -> dict:
    requested = scheme.url
    allowed = canonical(requested)
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    current = requested
    final_url = requested
    response = None
    error = ""

    try:
        for _ in range(4):
            if canonical(current) != allowed:
                error = "redirect left the allowlist"
                final_url = current
                break
            response = client.get(current, follow_redirects=False)
            final_url = str(getattr(response, "url", current))
            if response.status_code in REDIRECT_STATUSES:
                location = _header(response, "location")
                if not location:
                    error = "redirect missing location"
                    break
                nxt = urljoin(final_url, location)
                if canonical(nxt) != allowed:
                    error = "redirect left the allowlist"
                    final_url = nxt
                    break
                current = nxt
                continue
            break
        else:
            error = "too many redirects"
    except Exception as exc:
        return _record(
            scheme,
            final_url=requested,
            http_status=0,
            fetched_at=fetched_at,
            text="",
            factsheet_url="",
            error=str(exc),
        )

    if error:
        return _record(
            scheme,
            final_url=final_url,
            http_status=getattr(response, "status_code", 0) or 0,
            fetched_at=fetched_at,
            text="",
            factsheet_url="",
            error=error,
        )

    status = response.status_code
    if status != 200:
        return _record(
            scheme,
            final_url=final_url,
            http_status=status,
            fetched_at=fetched_at,
            text="",
            factsheet_url="",
            error=f"HTTP {status}",
        )

    html = response.text or ""
    text = extract_text(html)
    if not text:
        return _record(
            scheme,
            final_url=final_url,
            http_status=status,
            fetched_at=fetched_at,
            text="",
            factsheet_url="",
            error="no scheme text extracted",
        )
    return _record(
        scheme,
        final_url=final_url,
        http_status=status,
        fetched_at=fetched_at,
        text=text,
        factsheet_url=find_factsheet_url(html, requested),
        error="",
    )


def extract_text(html: str) -> str:
    from_json = extract_scheme_fields(html)
    if from_json:
        return from_json
    return extract_visible_html(html)


def extract_scheme_fields(html: str) -> str:
    fund = _fund_object(html)
    if not isinstance(fund, dict):
        return ""
    lines: list[str] = []
    for key, label in SCHEME_FIELDS:
        value = fund.get(key)
        if value is None or value == "" or isinstance(value, (dict, list)):
            continue
        lines.append(f"{label}: {value}")
    lock_line = _lock_in_line(fund.get("lock_in"))
    if lock_line:
        lines.append(lock_line)
    risk = _scheme_risk(fund.get("return_stats"))
    if risk:
        lines.append(f"Riskometer: {risk}")
    return "\n".join(lines).strip()


def extract_visible_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(["script", "style", "noscript"]):
        tag.decompose()
    lines: list[str] = []
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"])]
            cells = [cell for cell in cells if cell]
            if len(cells) >= 2:
                lines.append(f"{cells[0]}: {' '.join(cells[1:])}")
            elif cells:
                lines.append(cells[0])
        table.decompose()
    for heading in soup.find_all(["h1", "h2", "h3", "h4"]):
        text = heading.get_text(" ", strip=True)
        if text:
            lines.append(text)
    return "\n".join(lines).strip()


def find_factsheet_url(html: str, page_url: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"]).strip()
        label = anchor.get_text(" ", strip=True).lower()
        if "factsheet" in href.lower() or "factsheet" in label:
            return urljoin(page_url, href)
    fund = _fund_object(html)
    if isinstance(fund, dict):
        for key in ("brochure_link", "scheme_info_link"):
            value = fund.get(key)
            if isinstance(value, str) and value.startswith("http") and _looks_like_factsheet(value):
                return value
    return ""


def canonical(url: str) -> str:
    parsed = urlparse(url.strip())
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    path = parsed.path.rstrip("/") or "/"
    return f"{parsed.scheme.lower()}://{host}{path}"


def _fund_object(html: str) -> dict | None:
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    fund = data.get("props", {}).get("pageProps", {}).get("mfServerSideData")
    return fund if isinstance(fund, dict) else None


def _scheme_risk(return_stats: object) -> str:
    """Keep the scheme risk label and leave return figures out of the text."""
    if not isinstance(return_stats, list) or not return_stats:
        return ""
    first = return_stats[0]
    if not isinstance(first, dict):
        return ""
    risk = first.get("risk")
    return str(risk).strip() if isinstance(risk, str) else ""


def _lock_in_line(lock_in: object) -> str:
    if not isinstance(lock_in, dict):
        return ""
    parts = []
    for unit in ("years", "months", "days"):
        amount = lock_in.get(unit)
        if amount:
            parts.append(f"{amount} {unit}")
    if not parts:
        return ""
    return "Lock-in: " + " ".join(parts)


def _looks_like_factsheet(url: str) -> bool:
    lowered = url.lower()
    return "factsheet" in lowered or "brochure" in lowered or lowered.endswith(".pdf")


def _header(response, name: str) -> str:
    headers = getattr(response, "headers", {}) or {}
    for key, value in headers.items():
        if str(key).lower() == name:
            return str(value)
    return ""


def _record(scheme: Scheme, final_url: str, http_status: int, fetched_at: str, text: str, factsheet_url: str, error: str) -> dict:
    return {
        "slug": scheme.slug,
        "scheme_name": scheme.name,
        "requested_url": scheme.url,
        "final_url": final_url,
        "http_status": http_status,
        "fetched_at": fetched_at,
        "text": text,
        "factsheet_url": factsheet_url,
        "error": error,
    }


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    settings = load_settings()
    try:
        run_id = load_corpus(settings)
    except SystemExit:
        print("load failed: no pages returned text")
        raise
    manifest_path = settings.root / "data" / "artifacts" / "load" / run_id / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    print(f"run_id: {run_id}")
    print(f"successes: {len(manifest['successes'])}")
    print(f"failures: {len(manifest['failures'])}")
    for failure in manifest["failures"]:
        print(f"  {failure['slug']}: {failure['error']}")


if __name__ == "__main__":
    main()
