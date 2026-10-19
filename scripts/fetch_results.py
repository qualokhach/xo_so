#!/usr/bin/env python3
"""Multi-source lottery collector with append-only, immutable published draws."""
import json, re, time, os, hashlib
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# Sources are tried in order. A source is accepted only when the page contains
# recognizable prize rows, a draw date, and enough prize values.
SOURCES = {
 "xsmb": [
  {"id":"kqxs_mb","name":"KQXS.vn — Miền Bắc","url":"https://m.kqxs.vn/mien-bac"},
  {"id":"ketqua_org","name":"KetQua.org — Miền Bắc","url":"https://ketqua.org/"},
  {"id":"xskt_io","name":"XSKT.io — Miền Bắc","url":"https://xskt.io/"},
  {"id":"soketqua","name":"SoKetQua.vn — Miền Bắc","url":"https://soketqua.vn/"},
 ],
 "xsmt": [
  {"id":"kqxs_mt","name":"KQXS.vn — Miền Trung","url":"https://m.kqxs.vn/mien-trung"},
  {"id":"xskt_io","name":"XSKT.io — Miền Trung","url":"https://xskt.io/"},
  {"id":"ketqua_org","name":"KetQua.org — Miền Trung","url":"https://ketqua.org/"},
  {"id":"soketqua","name":"SoKetQua.vn — Miền Trung","url":"https://soketqua.vn/"},
 ],
 "xsmn": [
  {"id":"kqxs_mn","name":"KQXS.vn — Miền Nam","url":"https://m.kqxs.vn/mien-nam"},
  {"id":"xskt_io","name":"XSKT.io — Miền Nam","url":"https://xskt.io/"},
  {"id":"ketqua_org","name":"KetQua.org — Miền Nam","url":"https://ketqua.org/"},
  {"id":"soketqua","name":"SoKetQua.vn — Miền Nam","url":"https://soketqua.vn/"},
 ],
 "vietlott": [
  {"id":"kqxs_vietlott","name":"KQXS.vn — Vietlott","url":"https://m.kqxs.vn/xo-so-vietlott"},
  {"id":"vietlott_official","name":"Vietlott — Trang chính thức","url":"https://vietlott.vn/vi/home"},
  {"id":"xskt_io","name":"XSKT.io — Vietlott (trang tổng hợp)","url":"https://xskt.io/"},
  {"id":"ketqua_org","name":"KetQua.org — Vietlott (trang tổng hợp)","url":"https://ketqua.org/"},
  ],
}
LABEL_RE = re.compile(r"^(?:đb|đặc biệt|giải\s*(?:đặc biệt|nhất|nhì|ba|tư|năm|sáu|bảy|tám|[1-8])|g[1-8]|jackpot(?:\s*[12])?)\b",re.I)
DATE_RE = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b")
NUM_RE = re.compile(r"(?<!\d)\d{2,6}(?!\d)")
class Parser(HTMLParser):
 def __init__(self):
  super().__init__(convert_charrefs=True); self.skip=0; self.cell_depth=0; self.cell=[]; self.row=[]; self.rows=[]; self.text=[]; self.heading=None; self.heading_text=[]; self.headings=[]
 def handle_starttag(self,tag,attrs):
  if tag in ("script","style","noscript","svg"): self.skip+=1
  if self.skip:return
  if tag in ("td","th"): self.cell_depth+=1; self.cell=[]
  elif tag=="tr": self.row=[]
  elif tag in ("h1","h2","h3","h4"): self.heading=tag;self.heading_text=[]
  elif tag=="br" and self.cell_depth:self.cell.append(" ")
 def handle_endtag(self,tag):
  if tag in ("script","style","noscript","svg") and self.skip: self.skip-=1;return
  if self.skip:return
  if tag in ("td","th") and self.cell_depth:
   self.cell_depth-=1; self.row.append(re.sub(r"\s+"," ","".join(self.cell)).strip());self.cell=[]
  elif tag=="tr":
   if self.row:self.rows.append(self.row)
   self.row=[]
  elif self.heading==tag and tag in ("h1","h2","h3","h4"):
   v=re.sub(r"\s+"," ","".join(self.heading_text)).strip()
   if v:self.headings.append(v)
   self.heading=None;self.heading_text=[]
 def handle_data(self,data):
  if self.skip:return
  if data.strip(): self.text.append(data.strip())
  if self.cell_depth:self.cell.append(data)
  if self.heading:self.heading_text.append(data)

def fetch(url):
 req=Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; AppNhoLottery/2.0)","Accept":"text/html,application/xhtml+xml"})
 with urlopen(req,timeout=20) as r:
  raw=r.read(5_000_000); enc=r.headers.get_content_charset() or "utf-8"
  try: html=raw.decode(enc,errors="replace")
  except LookupError: html=raw.decode("utf-8",errors="replace")
  return html,r.geturl(),r.status

def normalize_date(text):
 m=DATE_RE.search(text)
 if not m:return None
 d,mo,y=map(int,m.groups())
 try:return f"{y:04d}-{mo:02d}-{d:02d}"
 except:return None

def category_matches(kind, text):
 t=text.casefold()
 if kind=="xsmb": return any(x in t for x in ("miền bắc","mien-bac","xsmb","xsm b","xổ số miền bắc"))
 if kind=="xsmt": return any(x in t for x in ("miền trung","mien-trung","xsmt","xổ số miền trung"))
 if kind=="xsmn": return any(x in t for x in ("miền nam","mien-nam","xsmn","xổ số miền nam"))
 return any(x in t for x in ("vietlott","mega 6/45","power 6/55","max 3d"))

def canonical_prize(label):
 s=label.strip().casefold().replace(" ","")
 mapping={"đb":"Đặc biệt","đặcbiệt":"Đặc biệt","jackpot":"Jackpot","jackpot1":"Jackpot 1","jackpot2":"Jackpot 2",
 "g1":"Giải nhất","giải1":"Giải nhất","giảinhất":"Giải nhất",
 "g2":"Giải nhì","giải2":"Giải nhì","giảinhì":"Giải nhì",
 "g3":"Giải ba","giải3":"Giải ba","giảiba":"Giải ba",
 "g4":"Giải tư","giải4":"Giải tư","giảitư":"Giải tư",
 "g5":"Giải năm","giải5":"Giải năm","giảinăm":"Giải năm",
 "g6":"Giải sáu","giải6":"Giải sáu","giảisáu":"Giải sáu",
 "g7":"Giải bảy","giải7":"Giải bảy","giảibảy":"Giải bảy",
 "g8":"Giải tám","giải8":"Giải tám","giảitám":"Giải tám"}
 return mapping.get(s,label.strip())

def parse_html(html, kind, src):
 p=Parser();p.feed(html)
 body=" ".join(p.text)
 # Find a date in a title/heading or page text; this is the identity key for a traditional draw.
 date=None
 for h in p.headings:
  date=normalize_date(h)
  if date:break
 if not date: date=normalize_date(body[:30000])
 # Page title text helps avoid taking a generic table from the wrong section.
 page_context=" ".join(p.headings[:12])+" "+body[:5000]
 if not category_matches(kind,page_context) and src["id"] not in ("kqxs_mb","kqxs_mt","kqxs_mn","kqxs_vietlott"):
  # Broad portal pages may not mention category in first text segment; continue only if full body has it.
  if not category_matches(kind,body):return []
 draws=[]; prize_rows=[]
 for row in p.rows:
  if len(row)<2:continue
  label=re.sub(r"\s+"," ",row[0]).strip().rstrip(":")
  if not LABEL_RE.match(label):continue
  groups=[]
  for cell in row[1:]:
   nums=NUM_RE.findall(cell)
   if nums:groups.append(nums)
  if groups:prize_rows.append((canonical_prize(label),groups))
 if not date or not prize_rows:return []
 # Require at least five distinct prize categories for traditional results; Vietlott needs jackpot + main numbers.
 labels={x[0] for x in prize_rows}
 if kind!="vietlott" and len(labels)<5:return []
 if kind=="vietlott" and not any("jackpot" in x.casefold() for x in labels) and not any("đặc biệt" in x.casefold() for x in labels):
  # Some Vietlott result pages present game number draw without prize table. Do not accept incomplete parse.
  return []
 maxcols=max(len(groups) for _,groups in prize_rows)
 if kind in ("xsmt","xsmn") and maxcols>1:
  # Column header labels are usually station names in the first row of the same table.
  station_names=[]
  for row in p.rows:
   if len(row)>1 and any(re.search(r"(đài|bình|hồ chí minh|đồng|cần thơ|an giang|phú yên|huế|khánh hòa|vĩnh long|trà vinh|tiền giang)",c,re.I) for c in row):
    station_names=row[1:];break
  for col in range(maxcols):
   prizes=[]
   for label,groups in prize_rows:
    if col<len(groups):prizes.append({"name":label,"numbers":groups[col]})
   if len(prizes)>=5:
    station=station_names[col] if col<len(station_names) else f"Đài {col+1}"
    draws.append({"key":f"{kind}|{date}|{station.strip()}","kind":kind,"date":date,"title":station.strip(),"station":station.strip(),"prizes":prizes,"source_url":src["url"],"source_id":src["id"]})
 else:
  prizes=[]
  for label,groups in prize_rows:
   nums=[n for group in groups for n in group]
   if nums:prizes.append({"name":label,"numbers":nums})
  if prizes:
   title=next((h for h in p.headings if re.search(r"(mega|power|vietlott|miền bắc|miền trung|miền nam|xsmb)",h,re.I)),f"{src['name']}")
   game=re.search(r"(mega\s*6/45|power\s*6/55|max\s*3d|max\s*3d pro)",body,re.I)
   if kind=="vietlott" and game:title=game.group(1).upper()
   draws.append({"key":f"{kind}|{date}|{title.strip()}","kind":kind,"date":date,"title":title.strip(),"station":title.strip(),"prizes":prizes,"source_url":src["url"],"source_id":src["id"]})
 return draws

def scan_kind(kind, existing_keys):
 logs=[]; candidates=SOURCES[kind]
 for src in candidates:
  started=time.time()
  try:
   html,final_url,http=fetch(src["url"])
   draws=parse_html(html,kind,src)
   new_draws=[d for d in draws if d["key"] not in existing_keys]
   status="usable_new_draws" if new_draws else ("only_already_locked_draws" if draws else "no_valid_draw_found")
   logs.append({"source":src["name"],"url":src["url"],"http":http,"status":status,"draws":len(draws),"new_draws":len(new_draws),"seconds":round(time.time()-started,2)})
   # If a source only has a previously locked draw, keep scanning for a newer draw.
   if new_draws:return new_draws,logs
  except Exception as e:
   logs.append({"source":src["name"],"url":src["url"],"status":"error","error":f"{type(e).__name__}: {e}","seconds":round(time.time()-started,2)})
 return [],logs

def read_json(path,default):
 try:
  with open(path,encoding="utf-8") as f:return json.load(f)
 except (OSError,ValueError):return default

def main():
 now=datetime.now(timezone.utc).isoformat(timespec="seconds")
 archive=read_json("data/archive.json",{"schema_version":1,"records":{},"updated_at_utc":None})
 records=archive.setdefault("records",{})
 report={"updated_at_utc":now,"sources":{},"added":[],"kept_existing":0,"notice":"Bản ghi đã xuất bản là bất biến: lần chạy sau chỉ bổ sung key mới, không sửa key đã tồn tại."}
 for kind in SOURCES:
  draws,logs=scan_kind(kind,set(records));report["sources"][kind]={"attempts":logs,"selected_source":draws[0]["source_id"] if draws else None,"candidate_count":len(SOURCES[kind])}
  new_count=0
  for draw in draws:
   key=draw["key"]
   if key in records:
    report["kept_existing"]+=1
    continue
   # Lock the first valid copy permanently with the source and timestamp.
   draw["locked_at_utc"]=now
   draw["first_source_id"]=draw.get("source_id")
   draw["content_sha256"]=hashlib.sha256(json.dumps(draw,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
   records[key]=draw
   report["added"].append(key);new_count+=1
  report["sources"][kind]["new_records_locked"]=new_count
 archive["updated_at_utc"]=now
 archive["records"]=records
 os.makedirs("data",exist_ok=True)
 with open("data/archive.json","w",encoding="utf-8") as f:json.dump(archive,f,ensure_ascii=False,indent=2)
 # The public JSON is rebuilt from immutable records. It never reads current source results directly.
 grouped={}
 for rec in records.values():grouped.setdefault(rec["kind"],[]).append(rec)
 results={}
 for kind in SOURCES:
  items=sorted(grouped.get(kind,[]),key=lambda x:(x.get("date",""),x.get("title","")),reverse=True)
  results[kind]={"name":{"xsmb":"Xổ số miền Bắc","xsmt":"Xổ số miền Trung","xsmn":"Xổ số miền Nam","vietlott":"Vietlott"}[kind],"draws":items,"status":"ok" if items else "empty","message":"" if items else "Chưa có bản ghi đã khóa."}
 public={"updated_at_utc":now,"status":"ok" if any(v["draws"] for v in results.values()) else "empty","results":results,"archive_count":len(records),"collection_report":report,"notice":"Kết quả đã được lưu vào kho bất biến của AppNho. Bản ghi đã khóa không bị nguồn bên ngoài ghi đè."}
 with open("data/results.json","w",encoding="utf-8") as f:json.dump(public,f,ensure_ascii=False,indent=2)
 summary=os.environ.get("GITHUB_STEP_SUMMARY")
 if summary:
  with open(summary,"a",encoding="utf-8") as f:
   f.write("# AppNho — quét nguồn và khóa kết quả\n\n")
   f.write(f"- Bản ghi đã khóa: {len(records)}\n- Bản ghi mới thêm lần này: {len(report['added'])}\n- Bản ghi cũ được giữ nguyên: {report['kept_existing']}\n\n")
   f.write("| Loại | Số nguồn đã thử | Nguồn được chọn | Bản ghi mới khóa |\n|---|---:|---|---:|\n")
   for k,v in report["sources"].items():f.write(f"| {k} | {len(v['attempts'])} | {v['selected_source'] or 'Không có nguồn hợp lệ'} | {v['new_records_locked']} |\n")
   f.write("\n## Chi tiết quét\n")
   for k,v in report["sources"].items():
    f.write(f"\n### {k}\n")
    for a in v["attempts"]:f.write(f"- {a['source']}: {a['status']} — {a.get('draws',0)} bảng\n")
 for k,v in report["sources"].items():
  print(f"{k}: tried {len(v['attempts'])}/{len(SOURCES[k])}; new locked={v['new_records_locked']}; selected={v['selected_source']}")
 print(f"ARCHIVE: {len(records)} immutable records; added {len(report['added'])}; kept existing {report['kept_existing']}")
if __name__=="__main__":main()
