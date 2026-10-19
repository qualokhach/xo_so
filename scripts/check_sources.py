#!/usr/bin/env python3
"""Check candidate public lottery pages for automated-fetch feasibility.

This is a source-accessibility test only. It does not publish lottery results
or claim that a third-party page grants permission to reuse its data.
Uses Python standard library only.
"""
from __future__ import annotations
import json, os, re, sys, time
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

SOURCES = [
    {
        "id": "xsmb",
        "name": "Xổ số miền Bắc (XSMB)",
        "url": "https://m.kqxs.vn/mien-bac",
        "keywords": ["kết quả xổ số miền bắc", "đặc biệt", "giải nhất"],
        "number_pattern": r"\b\d{5}\b",
    },
    {
        "id": "xsmt",
        "name": "Xổ số miền Trung (XSMT)",
        "url": "https://m.kqxs.vn/mien-trung",
        "keywords": ["xổ số miền trung", "đặc biệt", "giải nhất"],
        "number_pattern": r"\b\d{5,6}\b",
    },
    {
        "id": "xsmn",
        "name": "Xổ số miền Nam (XSMN)",
        "url": "https://m.kqxs.vn/mien-nam",
        "keywords": ["xổ số miền nam", "đặc biệt", "giải nhất"],
        "number_pattern": r"\b\d{5,6}\b",
    },
    {
        "id": "vietlott",
        "name": "Vietlott (trang tổng hợp ứng viên)",
        "url": "https://m.kqxs.vn/xo-so-vietlott",
        "keywords": ["vietlott", "mega", "power"],
        "number_pattern": r"\b\d{1,2}\b",
    },
]

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self._skip = 0
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self._skip += 1
    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self._skip:
            self._skip -= 1
    def handle_data(self, data):
        if not self._skip and data.strip():
            self.parts.append(data.strip())


def fetch(source):
    req = Request(source["url"], headers={
        "User-Agent": "AppNhoSourceCheck/0.1 (+manual source feasibility test)",
        "Accept": "text/html,application/xhtml+xml",
    })
    started = time.time()
    try:
        with urlopen(req, timeout=20) as response:
            raw = response.read(3_000_000)
            status = response.status
            final_url = response.geturl()
            content_type = response.headers.get("Content-Type", "")
        # Try common Vietnamese encodings when the server omits/incorrectly sets charset.
        html = raw.decode("utf-8", errors="replace")
        parser = TextExtractor(); parser.feed(html)
        text = " ".join(parser.parts)
        normalized = re.sub(r"\s+", " ", text).casefold()
        matched = [kw for kw in source["keywords"] if kw.casefold() in normalized]
        nums = re.findall(source["number_pattern"], text)
        ok = 200 <= status < 300 and len(matched) >= min(2, len(source["keywords"])) and len(nums) >= 3
        return {
            "id": source["id"], "name": source["name"], "url": source["url"],
            "final_url": final_url, "http_status": status, "content_type": content_type,
            "page_chars": len(text), "matched_keywords": matched,
            "numeric_tokens_found": len(nums), "elapsed_seconds": round(time.time()-started, 2),
            "status": "candidate_accessible" if ok else "needs_review",
            "note": "Accessibility/content check only; not proof of official accuracy, stable structure, or reuse permission.",
        }
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        return {
            "id": source["id"], "name": source["name"], "url": source["url"],
            "status": "unreachable", "error": f"{type(exc).__name__}: {exc}",
            "elapsed_seconds": round(time.time()-started, 2),
            "note": "Could be a temporary network block, anti-bot protection, or source outage.",
        }


def main():
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    report = {"checked_at_utc": now, "purpose": "source feasibility only", "sources": []}
    for src in SOURCES:
        result = fetch(src)
        report["sources"].append(result)
        print(f"[{result['status']}] {result['name']} — {result.get('http_status', result.get('error', ''))}")
    os.makedirs("reports", exist_ok=True)
    path = "reports/source-status.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    lines = ["# AppNho lottery source check", "", f"Checked (UTC): {now}", "", "This checks access and basic page content only; it does not validate winning numbers or permission to reuse data.", "", "| Source | Status | HTTP | Matched keywords | Number tokens |", "|---|---|---:|---|---:|"]
    for r in report["sources"]:
        lines.append(f"| {r['name']} | {r['status']} | {r.get('http_status', '—')} | {', '.join(r.get('matched_keywords', [])) or '—'} | {r.get('numeric_tokens_found', '—')} |")
    lines += ["", "Full JSON report: `reports/source-status.json` (workflow artifact)."]
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    # Keep the workflow successful even if every source is unreachable.
    # The report itself records failures and is still published for the index page.
    if all(r["status"] == "unreachable" for r in report["sources"]):
        print("WARNING: all candidate sources were unreachable; report was still generated.")

if __name__ == "__main__":
    main()
