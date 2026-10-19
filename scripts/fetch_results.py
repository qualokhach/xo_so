#!/usr/bin/env python3
"""Fetch current lottery result pages and publish a structured JSON file.
This scraper deliberately returns an empty draw list when parsing fails; it never
uses guessed or hard-coded winning numbers.
"""
import json, re, time
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from bs4 import BeautifulSoup

SOURCES = [
    {"id":"xsmb","name":"Xổ số miền Bắc","url":"https://m.kqxs.vn/mien-bac","region":"XSMB"},
    {"id":"xsmt","name":"Xổ số miền Trung","url":"https://m.kqxs.vn/mien-trung","region":"XSMT"},
    {"id":"xsmn","name":"Xổ số miền Nam","url":"https://m.kqxs.vn/mien-nam","region":"XSMN"},
    {"id":"vietlott","name":"Vietlott","url":"https://m.kqxs.vn/xo-so-vietlott","region":"VIETLOTT"},
]
PRIZE_RE = re.compile(r"^(đặc biệt|giải\s*(?:đặc biệt|nhất|nhì|ba|tư|năm|sáu|bảy|tám)|jackpot(?:\s*[12])?|mega\s*6/45|power\s*6/55|max\s*4d|max\s*3d)", re.I)
NUM_RE = re.compile(r"(?<!\d)\d{2,6}(?!\d)")
DATE_RE = re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b")

def get_page(url):
    req=Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; AppNhoLottery/1.0; +https://github.com/qualokhach/xo_so)","Accept":"text/html,application/xhtml+xml"})
    with urlopen(req,timeout=25) as res:
        raw=res.read(5_000_000)
        enc=res.headers.get_content_charset() or "utf-8"
        try: html=raw.decode(enc,errors="replace")
        except LookupError: html=raw.decode("utf-8",errors="replace")
        return html, res.geturl(), res.status

def clean_text(el):
    return re.sub(r"\s+"," ",el.get_text(" ",strip=True)).strip()

def parse_tables(soup, source):
    draws=[]
    # Most result pages use tables with prize labels in the first column.
    for table in soup.find_all("table"):
        rows=[]
        station_headers=[]
        for tr in table.find_all("tr"):
            cells=tr.find_all(["th","td"],recursive=False)
            if not cells: cells=tr.find_all(["th","td"])
            vals=[clean_text(c) for c in cells]
            if not vals: continue
            if any(x and re.search(r"(hồ chí minh|đồng tháp|cà mau|đà nẵng|khánh hòa|huế|mega 6/45|power 6/55|đặc biệt|giải nhất)",x,re.I) for x in vals):
                if all(not NUM_RE.search(x) for x in vals):
                    station_headers=vals
            label=vals[0].strip().rstrip(":")
            if not PRIZE_RE.match(label): continue
            number_groups=[]
            for cell in vals[1:]:
                nums=NUM_RE.findall(cell)
                # Avoid scraping explanatory counts/years; only keep numbers in prize cells.
                if nums: number_groups.append(nums)
            if number_groups:
                rows.append((label,number_groups))
        if not rows: continue
        # For regional multi-station tables, a result cell per station creates columns.
        max_cols=max(len(groups) for _,groups in rows)
        if max_cols>1 and source["id"] in ("xsmt","xsmn"):
            for col in range(max_cols):
                prizes=[]
                for label,groups in rows:
                    if col<len(groups) and groups[col]:
                        prizes.append({"name":label,"numbers":groups[col]})
                if prizes:
                    station=(station_headers[col+1] if len(station_headers)>col+1 else f"Đài {col+1}")
                    draws.append({"title":station,"station":station,"date":find_date(soup),"prizes":prizes,"source_url":source["url"]})
        else:
            prizes=[]
            for label,groups in rows:
                flattened=[n for group in groups for n in group]
                if flattened: prizes.append({"name":label,"numbers":flattened})
            if prizes:
                title=source["name"]
                # Use nearby heading to distinguish Vietlott game products.
                prev=table.find_previous(["h1","h2","h3","h4"])
                if prev and clean_text(prev): title=clean_text(prev)
                draws.append({"title":title,"station":title,"date":find_date(soup),"prizes":prizes,"source_url":source["url"]})
    # Keep only the first two matching tables to avoid unrelated statistics tables.
    unique=[]
    seen=set()
    for d in draws:
        key=(d.get("title"),tuple((p["name"],tuple(p["numbers"])) for p in d["prizes"]))
        if key not in seen:
            seen.add(key); unique.append(d)
    return unique[:12]

def find_date(soup):
    # Prefer the current result heading near the start of the content.
    text=clean_text(soup.find("body") or soup)
    m=DATE_RE.search(text[:18000])
    return m.group(0) if m else ""

def parse_fallback(soup, source):
    # A conservative fallback: collect text rows such as "Đặc biệt | 12345".
    text=soup.get_text("\n",strip=True)
    lines=[re.sub(r"\s+"," ",x).strip() for x in text.splitlines() if x.strip()]
    prizes=[]
    for i,line in enumerate(lines):
        m=re.match(r"^(Đặc biệt|Giải nhất|Giải nhì|Giải ba|Giải tư|Giải năm|Giải sáu|Giải bảy|Giải tám)\s*(?:\||:|-)\s*(.*)$",line,re.I)
        if m:
            nums=NUM_RE.findall(m.group(2))
            if nums: prizes.append({"name":m.group(1),"numbers":nums})
    if not prizes:
        return []
    return [{"title":source["name"],"station":source["name"],"date":find_date(soup),"prizes":prizes,"source_url":source["url"]}]

def fetch_source(source):
    started=time.time()
    try:
        html,final_url,status=get_page(source["url"])
        soup=BeautifulSoup(html,"html.parser")
        draws=parse_tables(soup,source)
        if not draws: draws=parse_fallback(soup,source)
        ok=bool(draws)
        return {"id":source["id"],"name":source["name"],"source_url":source["url"],"final_url":final_url,"http_status":status,"status":"ok" if ok else "parse_failed","draw_count":len(draws),"draws":draws,"elapsed_seconds":round(time.time()-started,2),"message":"" if ok else "Tải được trang nhưng chưa nhận diện được bảng kết quả; không hiển thị số liệu đoán."}
    except (HTTPError,URLError,TimeoutError,OSError,ValueError) as e:
        return {"id":source["id"],"name":source["name"],"source_url":source["url"],"status":"fetch_failed","draw_count":0,"draws":[],"elapsed_seconds":round(time.time()-started,2),"message":f"{type(e).__name__}: {e}"}

def main():
    now=datetime.now(timezone.utc).isoformat(timespec="seconds")
    statuses=[fetch_source(s) for s in SOURCES]
    results={s["id"]:{"name":s["name"],"source_url":s["url"],"draws":s["draws"],"status":s["status"],"message":s["message"]} for s in statuses}
    data={"updated_at_utc":now,"status":"ok" if all(s["status"]=="ok" for s in statuses) else "partial","results":results,"sources":statuses,"notice":"Dữ liệu tham khảo được thu thập tự động từ các trang nguồn. Khi cấu trúc nguồn thay đổi, dữ liệu có thể không được phân tích; đối chiếu nguồn chính thức."}
    import os
    os.makedirs("data",exist_ok=True)
    with open("data/results.json","w",encoding="utf-8") as f: json.dump(data,f,ensure_ascii=False,indent=2)
    summary=os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary,"a",encoding="utf-8") as f:
            f.write("# AppNho — cập nhật kết quả xổ số\n\n")
            f.write(f"Thời điểm UTC: {now}\n\n| Nguồn | Trạng thái | Bảng kết quả | HTTP |\n|---|---|---:|---:|\n")
            for s in statuses: f.write(f"| {s['name']} | {s['status']} | {s['draw_count']} | {s.get('http_status','—')} |\n")
            f.write("\nLưu ý: nếu phân tích nguồn thất bại, hệ thống không tự tạo kết quả thay thế.\n")
    for s in statuses: print(f"[{s['status']}] {s['name']}: {s['draw_count']} draw(s)")

if __name__=="__main__": main()
