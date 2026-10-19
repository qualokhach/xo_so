#!/usr/bin/env python3
"""Collect lottery pages with Python standard library only; no pip dependencies."""
import json, re, time, os
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

SOURCES=[
 {"id":"xsmb","name":"Xổ số miền Bắc","url":"https://m.kqxs.vn/mien-bac"},
 {"id":"xsmt","name":"Xổ số miền Trung","url":"https://m.kqxs.vn/mien-trung"},
 {"id":"xsmn","name":"Xổ số miền Nam","url":"https://m.kqxs.vn/mien-nam"},
 {"id":"vietlott","name":"Vietlott","url":"https://m.kqxs.vn/xo-so-vietlott"},
]
NUM_RE=re.compile(r"(?<!\d)\d{2,6}(?!\d)")
DATE_RE=re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b")
PRIZE_RE=re.compile(r"^(đặc biệt|giải\s*(?:nhất|nhì|ba|tư|năm|sáu|bảy|tám)|jackpot(?:\s*[12])?)\b",re.I)
SKIP={"script","style","noscript","svg"}

class PageParser(HTMLParser):
 def __init__(self):
  super().__init__(convert_charrefs=True); self.skip=0; self.in_cell=0; self.cell=[]; self.row=[]; self.rows=[]; self.text=[]; self.headings=[]; self.heading_tag=None; self.heading_text=[]
 def handle_starttag(self,tag,attrs):
  if tag in SKIP:self.skip+=1
  if self.skip:return
  if tag in ("td","th"): self.in_cell+=1; self.cell=[]
  elif tag=="tr": self.row=[]
  elif tag in ("h1","h2","h3","h4"): self.heading_tag=tag;self.heading_text=[]
  elif tag=="br" and self.in_cell:self.cell.append(" ")
 def handle_endtag(self,tag):
  if tag in SKIP and self.skip:self.skip-=1;return
  if self.skip:return
  if tag in ("td","th") and self.in_cell:
   self.in_cell-=1
   value=re.sub(r"\s+"," ","".join(self.cell)).strip()
   self.row.append(value);self.cell=[]
  elif tag=="tr":
   if self.row:self.rows.append(self.row)
   self.row=[]
  elif self.heading_tag==tag and tag in ("h1","h2","h3","h4"):
   val=re.sub(r"\s+"," ","".join(self.heading_text)).strip()
   if val:self.headings.append(val)
   self.heading_tag=None;self.heading_text=[]
 def handle_data(self,data):
  if self.skip:return
  t=data.strip()
  if t:
   self.text.append(t)
   if self.in_cell:self.cell.append(data)
   if self.heading_tag:self.heading_text.append(data)

def fetch(src):
 req=Request(src["url"],headers={"User-Agent":"Mozilla/5.0 (compatible; AppNhoLottery/1.0)","Accept":"text/html,application/xhtml+xml"})
 with urlopen(req,timeout=25) as res:
  raw=res.read(5_000_000); charset=res.headers.get_content_charset() or "utf-8"
  try: html=raw.decode(charset,errors="replace")
  except LookupError: html=raw.decode("utf-8",errors="replace")
  return html,res.geturl(),res.status

def parse_page(html,src):
 p=PageParser();p.feed(html);text=" ".join(p.text);date_match=DATE_RE.search(text[:20000]);date=date_match.group(0) if date_match else ""
 draws=[]
 # Parse prize rows from tables. Require recognizable prize labels and number values.
 prize_rows=[]
 for row in p.rows:
  if len(row)<2:continue
  label=re.sub(r"\s+"," ",row[0]).strip().rstrip(":")
  if not PRIZE_RE.match(label):continue
  groups=[]
  for cell in row[1:]:
   nums=NUM_RE.findall(cell)
   if nums:groups.append(nums)
  if groups:prize_rows.append((label,groups))
 if prize_rows:
  maxcols=max(len(groups) for _,groups in prize_rows)
  if src["id"] in ("xsmt","xsmn") and maxcols>1:
   for col in range(maxcols):
    prizes=[]
    for label,groups in prize_rows:
     if col<len(groups):prizes.append({"name":label,"numbers":groups[col]})
    if prizes:
     title=f"Đài {col+1}"
     draws.append({"title":title,"station":title,"date":date,"prizes":prizes,"source_url":src["url"]})
  else:
   prizes=[]
   for label,groups in prize_rows:
    nums=[n for group in groups for n in group]
    if nums:prizes.append({"name":label,"numbers":nums})
   if prizes:
    title=src["name"]
    # use a relevant heading only if it looks like a result/game title
    for h in p.headings:
     if re.search(r"xổ số|vietlott|mega|power|kết quả",h,re.I):
      title=h;break
    draws.append({"title":title,"station":title,"date":date,"prizes":prizes,"source_url":src["url"]})
 # Deduplicate exact table interpretations
 unique=[];seen=set()
 for d in draws:
  key=(d["title"],tuple((r["name"],tuple(r["numbers"])) for r in d["prizes"]))
  if key not in seen:seen.add(key);unique.append(d)
 return unique[:12]

def one(src):
 start=time.time()
 try:
  html,final_url,http=fetch(src);draws=parse_page(html,src)
  status="ok" if draws else "parse_failed"
  msg="" if draws else "Trang tải được nhưng không nhận diện được cấu trúc giải thưởng. Không tự tạo số liệu."
  return {"id":src["id"],"name":src["name"],"source_url":src["url"],"final_url":final_url,"http_status":http,"status":status,"draw_count":len(draws),"draws":draws,"elapsed_seconds":round(time.time()-start,2),"message":msg}
 except Exception as e:
  return {"id":src["id"],"name":src["name"],"source_url":src["url"],"status":"fetch_failed","draw_count":0,"draws":[],"elapsed_seconds":round(time.time()-start,2),"message":f"{type(e).__name__}: {e}"}

def main():
 now=datetime.now(timezone.utc).isoformat(timespec="seconds")
 statuses=[one(s) for s in SOURCES]
 results={s["id"]:{"name":s["name"],"source_url":s["url"],"draws":s["draws"],"status":s["status"],"message":s["message"]} for s in statuses}
 data={"updated_at_utc":now,"status":"ok" if all(s["status"]=="ok" for s in statuses) else "partial","results":results,"sources":statuses,"notice":"Kết quả tham khảo tự động. Khi nguồn thay đổi, dữ liệu có thể không phân tích được; hãy đối chiếu nguồn chính thức."}
 os.makedirs("data",exist_ok=True)
 with open("data/results.json","w",encoding="utf-8") as f:json.dump(data,f,ensure_ascii=False,indent=2)
 summary=os.environ.get("GITHUB_STEP_SUMMARY")
 if summary:
  with open(summary,"a",encoding="utf-8") as f:
   f.write(f"# AppNho — cập nhật kết quả xổ số\n\nThời điểm UTC: {now}\n\n| Nguồn | Trạng thái | Bảng kết quả | HTTP |\n|---|---|---:|---:|\n")
   for s in statuses:f.write(f"| {s['name']} | {s['status']} | {s['draw_count']} | {s.get('http_status','—')} |\n")
   f.write("\nNếu có `parse_failed`, cần điều chỉnh bộ phân tích nguồn; không coi đó là kết quả hợp lệ.\n")
 for s in statuses:print(f"[{s['status']}] {s['name']}: {s['draw_count']} bảng; {s.get('message','')}")
if __name__=="__main__":main()
