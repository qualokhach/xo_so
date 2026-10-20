#!/usr/bin/env python3
"""AppNho multi-source collector with station/product-aware parsing and immutable records."""
import json,re,time,os,hashlib,glob
from datetime import datetime,timezone,timedelta
from html.parser import HTMLParser
from urllib.request import Request,urlopen
from urllib.error import URLError,HTTPError

TRADITIONAL = {
 "xsmb":[
  {"id":"kqxs_mb","name":"KQXS.vn miền Bắc","url":"https://m.kqxs.vn/mien-bac"},
  {"id":"ketqua_org","name":"KetQua.org miền Bắc","url":"https://ketqua.org/"},
  {"id":"xskt_io","name":"XSKT.io miền Bắc","url":"https://xskt.io/"},
 ],
 "xsmt":[
  {"id":"kqxs_mt","name":"KQXS.vn miền Trung","url":"https://m.kqxs.vn/mien-trung"},
  {"id":"ketqua_org","name":"KetQua.org miền Trung","url":"https://ketqua.org/"},
  {"id":"xskt_io","name":"XSKT.io miền Trung","url":"https://xskt.io/"},
 ],
 "xsmn":[
  {"id":"kqxs_mn","name":"KQXS.vn miền Nam","url":"https://m.kqxs.vn/mien-nam"},
  {"id":"ketqua_org","name":"KetQua.org miền Nam","url":"https://ketqua.org/"},
  {"id":"xskt_io","name":"XSKT.io miền Nam","url":"https://xskt.io/"},
 ],
}
VIETLOTT=[
 {"id":"mega645","product":"MEGA 6/45","urls":["https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/645","https://xosohn.com/vietlott","https://m.kqxs.vn/xo-so-vietlott"]},
 {"id":"power655","product":"POWER 6/55","urls":["https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/655","https://xosohn.com/vietlott","https://m.kqxs.vn/xo-so-vietlott"]},
 {"id":"max3d","product":"MAX 3D","urls":["https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/max-3D.html","https://xosohn.com/vietlott","https://m.kqxs.vn/xo-so-vietlott"]},
 {"id":"lotto535","product":"LOTTO 5/35","urls":["https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/535","https://xosomoinhat.com/xo-so-lotto-535","https://xosohn.com/vietlott","https://m.kqxs.vn/xo-so-vietlott"]},
]
STATIONS=["Thừa Thiên Huế","Thua Thien Hue","Phú Yên","Phu Yen","Đà Nẵng","Da Nang","Khánh Hòa","Khanh Hoa","Đắk Lắk","Dak Lak","Quảng Nam","Quang Nam","Bình Định","Binh Dinh","Quảng Trị","Quang Tri","Quảng Bình","Quang Binh","Gia Lai","Ninh Thuận","Ninh Thuan","Quảng Ngãi","Quang Ngai","Đắk Nông","Dak Nong","Kon Tum","Hồ Chí Minh","Ho Chi Minh","Đồng Tháp","Dong Thap","Cà Mau","Ca Mau","Bến Tre","Ben Tre","Vũng Tàu","Vung Tau","Bạc Liêu","Bac Lieu","Cần Thơ","Can Tho","Sóc Trăng","Soc Trang","Trà Vinh","Tra Vinh","An Giang","Long An","Tiền Giang","Tien Giang","Kiên Giang","Kien Giang","Đồng Nai","Dong Nai","Bình Dương","Binh Duong","Tây Ninh","Tay Ninh","Bình Phước","Binh Phuoc","Bình Thuận","Binh Thuan","Hậu Giang","Hau Giang","Vĩnh Long","Vinh Long"]
PRIZE_ALIASES={"đb":"Đặc biệt","đặc biệt":"Đặc biệt","giải đặc biệt":"Đặc biệt","giải nhất":"Giải nhất","giải nhì":"Giải nhì","giải ba":"Giải ba","giải tư":"Giải tư","giải năm":"Giải năm","giải sáu":"Giải sáu","giải bảy":"Giải bảy","giải tám":"Giải tám","g.đb":"Đặc biệt","g1":"Giải nhất","g2":"Giải nhì","g3":"Giải ba","g4":"Giải tư","g5":"Giải năm","g6":"Giải sáu","g7":"Giải bảy","g8":"Giải tám"}
TRAD_COUNTS={"Đặc biệt":1,"Giải nhất":1,"Giải nhì":1,"Giải ba":2,"Giải tư":7,"Giải năm":1,"Giải sáu":3,"Giải bảy":1,"Giải tám":1}
XSMB_COUNTS={"Đặc biệt":1,"Giải nhất":1,"Giải nhì":2,"Giải ba":6,"Giải tư":4,"Giải năm":6,"Giải sáu":3,"Giải bảy":4}
DATE_RE=re.compile(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})")
NUM_RE=re.compile(r"(?<!\d)\d{2,6}(?!\d)")
LABEL_RE=re.compile(r"^(?:đb|đặc biệt|giải\s*(?:đặc biệt|nhất|nhì|ba|tư|năm|sáu|bảy|tám)|g\.?đb|g[1-8])\s*:?\s*$",re.I)
class HTML(HTMLParser):
 def __init__(self):
  super().__init__(convert_charrefs=True);self.skip=0;self.stack=[];self.text=[]
 def handle_starttag(self,t,a):
  if t in ("script","style","noscript","svg"):self.skip+=1
  if not self.skip:self.stack.append(t)
 def handle_endtag(self,t):
  if t in ("script","style","noscript","svg") and self.skip:self.skip-=1
  if not self.skip and t in self.stack:
   while self.stack:
    x=self.stack.pop()
    if x==t:break
 def handle_data(self,d):
  if not self.skip and d.strip():self.text.append(d.strip())

def get_html(url):
 req=Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; AppNhoResults/3.0)","Accept":"text/html,application/xhtml+xml"})
 with urlopen(req,timeout=20) as r:
  raw=r.read(6_000_000);enc=r.headers.get_content_charset() or "utf-8"
  try:return raw.decode(enc,errors="replace"),r.geturl(),r.status
  except LookupError:return raw.decode("utf-8",errors="replace"),r.geturl(),r.status

def norm_date(s):
 m=DATE_RE.search(s or "")
 if not m:return None
 d,mo,y=map(int,m.groups())
 try:
  parsed=datetime(y,mo,d)
  return parsed.strftime("%Y-%m-%d")
 except ValueError:
  return None

def prize_name(s):
 s=re.sub(r"\s+"," ",s.strip()).casefold().rstrip(":.")
 # Common compact labels used by Vietnamese result tables.
 compact=re.sub(r"[ .]", "", s)
 aliases={**PRIZE_ALIASES,"giải đb":"Đặc biệt","gđb":"Đặc biệt","g.đb":"Đặc biệt",
          "g.1":"Giải nhất","g.2":"Giải nhì","g.3":"Giải ba","g.4":"Giải tư",
          "g.5":"Giải năm","g.6":"Giải sáu","g.7":"Giải bảy","g.8":"Giải tám"}
 if s in aliases:return aliases[s]
 compact_alias={re.sub(r"[ .]", "", k):v for k,v in aliases.items()}
 return compact_alias.get(compact)

def split_station_names(text):
 found=[]
 low=text.casefold()
 for name in STATIONS:
  if name.casefold() in low and name not in found:found.append(name)
 # preserve page/table order using occurrence index
 found.sort(key=lambda n:low.find(n.casefold()))
 return found

CENTRAL_CANONICAL={"thua thien hue","hue","kon tum","khanh hoa","da nang","quang nam","quang ngai","binh dinh","phu yen","ninh thuan","dak lak","dak nong","gia lai","quang tri","quang binh"}
SOUTH_CANONICAL={"ho chi minh","tp ho chi minh","dong nai","can tho","soc trang","an giang","binh duong","binh phuoc","binh thuan","bac lieu","ben tre","ca mau","dong thap","hau giang","kien giang","long an","tien giang","tra vinh","vinh long","tay ninh","vung tau"}
def canonical_station(value):
 import unicodedata
 value=unicodedata.normalize("NFKD",str(value)).encode("ascii","ignore").decode("ascii").casefold()
 return re.sub(r"[^a-z0-9]+"," ",value).strip()
def station_belongs_to_kind(station,kind):
 name=canonical_station(station)
 if kind=="xsmt":return name in CENTRAL_CANONICAL
 if kind=="xsmn":return name in SOUTH_CANONICAL
 return kind=="xsmb" and name=="mien bac"

def table_rows(table):
 rows=[]
 for tr in table.find_all("tr"):
  cells=tr.find_all(["th","td"],recursive=False)
  if not cells:cells=tr.find_all(["th","td"])
  if cells:rows.append(cells)
 return rows

def traditional_from_html(html,kind,src):
 try:
  from bs4 import BeautifulSoup
 except ImportError:
  return []
 soup=BeautifulSoup(html,"html.parser"); out=[]
 for table in soup.find_all("table"):
  rows=table_rows(table)
  if len(rows)<7:continue
  alltext=" ".join(c.get_text(" ",strip=True) for row in rows for c in row)
  stations=split_station_names(alltext)
  if kind=="xsmb":stations=["Miền Bắc"]
  else:
   # Prefer station labels from the table header; if absent use exact station labels in this table.
   header_text=" ".join(c.get_text(" ",strip=True) for c in rows[0])
   header_stations=split_station_names(header_text)
   if header_stations:stations=header_stations
   # Shared aggregator pages may contain all regions. Never assign a station to a
   # region merely because this source URL was queried for that region.
   stations=[st for st in dict.fromkeys(stations) if station_belongs_to_kind(st,kind)]
   if not stations:continue
  if not stations:continue
  # Date must be from this table's nearby heading/context, not a random date elsewhere in page.
  prev=table.find_previous(["h1","h2","h3","h4","time"])
  date=norm_date(prev.get_text(" ",strip=True) if prev else "")
  if not date:
   date=norm_date(alltext)
  if not date:continue
  collected={}
  for row in rows:
   label=prize_name(row[0].get_text(" ",strip=True))
   if not label:continue
   cells=row[1:]
   cell_nums=[NUM_RE.findall(c.get_text(" ",strip=True)) for c in cells]
   cell_nums=[x for x in cell_nums if x]
   expected=XSMB_COUNTS.get(label) if kind=="xsmb" else TRAD_COUNTS.get(label)
   if not expected:continue
   if kind=="xsmb":
    vals=[n for group in cell_nums for n in group]
    if len(vals)==expected:collected.setdefault("Miền Bắc",{})[label]=vals
   else:
    # Ideal case: one cell per station; otherwise split a flat list by the known prize count per station.
    if len(cell_nums)==len(stations) and all(len(g)==expected for g in cell_nums):
     for station,nums in zip(stations,cell_nums):collected.setdefault(station,{})[label]=nums
    else:
     flat=[n for group in cell_nums for n in group]
     if len(flat)==len(stations)*expected:
      for i,station in enumerate(stations):collected.setdefault(station,{})[label]=flat[i*expected:(i+1)*expected]
  required=set(XSMB_COUNTS if kind=="xsmb" else TRAD_COUNTS)
  for station,prizes in collected.items():
   # Only publish a complete prize table; do not merge partial stations or statistics.
   if required.issubset(prizes.keys()):
    ordered=[{"name":p,"numbers":prizes[p]} for p in (["Đặc biệt","Giải nhất","Giải nhì","Giải ba","Giải tư","Giải năm","Giải sáu","Giải bảy"] if kind=="xsmb" else ["Đặc biệt","Giải nhất","Giải nhì","Giải ba","Giải tư","Giải năm","Giải sáu","Giải bảy","Giải tám"])]
    key=f"{kind}|{date}|{station}"
    out.append({"key":key,"kind":kind,"date":date,"title":station,"station":station,"prizes":ordered,"source_url":src["url"],"source_id":src["id"]})
 return out

def vietlott_from_html(html,src):
 """Extract one or more draws from a product page without mixing draw dates.

 Supports common Vietnamese headings such as:
   Kết quả QSMT kỳ #00889 ngày 16/09/2026 - Lúc 13:00
   Kết quả quay số mở thưởng kỳ quay thưởng #123 ngày 16/09/2026
   Kỳ quay thưởng #123 ngày 16/09/2026

 For Lotto 5/35, every heading is a separate session. Only the five main balls
 and optional bonus ball immediately following that heading are accepted.
 """
 try:
  from bs4 import BeautifulSoup
 except ImportError:
  return []
 soup=BeautifulSoup(html,"html.parser")
 # Use rendered text in document order; remove spaces introduced by HTML layout.
 text=re.sub(r"\s+"," ",soup.get_text(" ",strip=True))
 product=src["product"]
 width=3 if product=="MAX 3D" else 2
 # Different publishers vary the wording and whether the draw id has a # sign.
 heading_re=re.compile(
  r"(?:(?:kết quả(?: quay số mở thưởng)?|quay số mở thưởng)\s*)?"
  r"(?:qsm[dt]\s*)?(?:kỳ(?:\s+quay(?:\s+thưởng)?)?\s*)#?\s*(\d{3,6})"
  r"\s*(?:ngày|[-–|]\s*)(\d{1,2}[/-]\d{1,2}[/-]\d{4})"
  r"(?:\s*[-–|,]?\s*(?:lúc|vào lúc|giờ)\s*(\d{1,2}:\d{2}|\d{1,2}\s*[hH]))?",re.I)
 matches=list(heading_re.finditer(text))
 # Some official pages render a shorter label.
 if not matches:
  heading_re=re.compile(r"(?:kỳ quay thưởng|kỳ quay|kỳ)\s*#?(\d{3,6})\s*(?:ngày\s*)?(\d{1,2}[/-]\d{1,2}[/-]\d{4})(?:\s*[-–,]?\s*(?:lúc|giờ)\s*(\d{1,2}:\d{2}|\d{1,2}\s*[hH]))?",re.I)
  matches=list(heading_re.finditer(text))
 if not matches:
  return []
 aliases={"MEGA 6/45":("mega 6/45","mega645"),"POWER 6/55":("power 6/55","power655"),"MAX 3D":("max 3d","max3d"),"LOTTO 5/35":("lotto 5/35","lotto535","lotto-535")}
 # A product-specific page is safe by URL/title. A mixed fallback must identify the
 # product near each draw heading, otherwise never relabel its first draw.
 specific_url=(product=="LOTTO 5/35" and "lotto-535" in src.get("url", "")) or ("vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/" in src.get("url", ""))
 page_title=(soup.title.get_text(" ",strip=True) if soup.title else "").casefold()
 out=[]
 for i,m in enumerate(matches):
  draw_no=m.group(1).lstrip("0") or "0"
  date=norm_date(m.group(2))
  if not date:continue
  # Only consider the text belonging to this draw, ending before the next heading.
  seg_end=matches[i+1].start() if i+1<len(matches) else min(len(text),m.end()+900)
  segment=text[m.end():seg_end]
  if src.get("generic_fallback") and not specific_url:
   context=text[max(0,m.start()-220):min(len(text),m.end()+300)].casefold()
   terms=aliases.get(product,())
   if not any(a in context for a in terms) and not any(a in page_title for a in terms):
    continue
  draw_time=None
  time_match=re.search(r"(?:lúc|vào lúc|giờ)\s*(\d{1,2}:\d{2}|\d{1,2}\s*[hH])",text[m.start():min(len(text),m.end()+100)],re.I)
  if time_match:
   draw_time=time_match.group(1).replace(" ","").lower()
   if re.fullmatch(r"\d{1,2}h",draw_time):draw_time=draw_time[:-1]+":00"
  prizes=[]
  if product=="LOTTO 5/35":
   # Lotto result is five 01-35 balls plus one bonus ball, commonly printed as six values.
   seq=re.search(r"(?<!\d)(\d{2}(?:\s+\d{2}){5})(?!\d)",segment)
   if seq:
    nums=re.findall(r"\d{2}",seq.group(1))
    if all(1<=int(n)<=35 for n in nums[:5]) and 1<=int(nums[5])<=12:
     prizes=[{"name":"Bộ số trúng thưởng","numbers":nums[:5]+[nums[5]]}]
   if not prizes:
    # Sites may put a separator between the five main balls and bonus ball.
    seq=re.search(r"(?<!\d)(\d{2}(?:\s+\d{2}){4})\s*[|+·]\s*(\d{2})(?!\d)",segment)
    if seq:
     nums=re.findall(r"\d{2}",seq.group(1));bonus=seq.group(2)
     if all(1<=int(n)<=35 for n in nums) and 1<=int(bonus)<=12:
      prizes=[{"name":"Bộ số trúng thưởng","numbers":nums+[bonus]}]
  elif product in ("MEGA 6/45","POWER 6/55"):
   need=6 if product=="MEGA 6/45" else 7
   seq=re.search(r"(?<!\d)(\d{2}(?:\s+\d{2}){"+str(need-1)+r"})(?!\d)",segment)
   if seq:
    nums=re.findall(r"\d{2}",seq.group(1));limit=45 if product=="MEGA 6/45" else 55
    if all(1<=int(n)<=limit for n in nums[:6]) and (need==6 or 1<=int(nums[6])<=55):
     prizes=[{"name":"Bộ số trúng thưởng","numbers":nums}]
  else: # MAX 3D: use only a result-like table, not prize counts/payouts.
   for table in soup.find_all("table"):
    table_text=table.get_text(" ",strip=True)
    if draw_no not in table_text and date not in table_text:continue
    nums=re.findall(r"(?<!\d)\d{3}(?!\d)",table_text)
    if nums:
     prizes=[{"name":"Bộ số trúng thưởng","numbers":nums[:3]}];break
   if not prizes:
    seq=re.search(r"(?<!\d)(\d{3}(?:\s+\d{3}){1,5})(?!\d)",segment)
    if seq:prizes=[{"name":"Bộ số trúng thưởng","numbers":re.findall(r"\d{3}",seq.group(1))}]
  if not prizes:continue
  key=f"vietlott|{product}|{date}|{draw_no}"
  rec={"key":key,"kind":"vietlott","product":product,"product_id":src["id"],"draw_no":draw_no,"date":date,"title":product,"station":product,"prizes":prizes,"source_url":src["url"],"source_id":src["id"]}
  if draw_time:rec["draw_time"]=draw_time
  # Keep each Lotto session unique even if a provider accidentally reuses a draw number.
  if product=="LOTTO 5/35" and draw_time:rec["key"] += "|"+draw_time
  if record_valid(rec):out.append(rec)
 # Preserve source order while deduplicating repeated headings/tables.
 dedup={r["key"]:r for r in out}
 return list(dedup.values())

def record_valid(rec):
 kind=rec.get("kind");prizes=rec.get("prizes") or []
 if not rec.get("date") or not prizes:return False
 try: datetime.strptime(str(rec.get("date")), "%Y-%m-%d")
 except ValueError: return False
 if kind in ("xsmb","xsmt","xsmn"):
  if not rec.get("station") or re.match(r"Đài\s*\d+$",rec.get("station",""),re.I):return False
  names=[p.get("name","") for p in prizes]
  expected=list(XSMB_COUNTS if kind=="xsmb" else TRAD_COUNTS)
  if any(names.count(n)!=1 for n in expected):return False
  if len(names)!=len(expected):return False
  for p in prizes:
   exp=(XSMB_COUNTS if kind=="xsmb" else TRAD_COUNTS).get(p["name"])
   if exp is None or len(p.get("numbers",[]))!=exp:return False
  return True
 if kind=="vietlott":
  prod=rec.get("product") or rec.get("title","")
  vals=[n for p in prizes for n in p.get("numbers",[])]
  if "MEGA" in prod or "POWER" in prod:
   main=next((p for p in prizes if p["name"]=="Bộ số trúng thưởng"),None)
   if main:return len(main["numbers"])==(7 if "POWER" in prod else 6)
   return any(len(p.get("numbers",[])) in (6,7) and all(re.fullmatch(r"\d{2}",n) for n in p["numbers"]) for p in prizes)
  if prod=="LOTTO 5/35":
   main=next((p for p in prizes if p.get("name")=="Bộ số trúng thưởng"),None)
   return bool(main and len(main.get("numbers",[])) in (5,6) and all(re.fullmatch(r"\d{2}",n) for n in main["numbers"][:5]) and len(set(main["numbers"][:5]))==5 and all(1 <= int(n) <= 35 for n in main["numbers"][:5]) and (len(main["numbers"])==5 or (1 <= int(main["numbers"][5]) <= 12)))
  if "3D" in prod:return any(re.fullmatch(r"\d{3}",n) for n in vals)
  return False
 return False

def get_json(path,default):
 try:
  with open(path,encoding="utf-8") as f:return json.load(f)
 except (OSError,ValueError):return default

def month_key(rec):
 return str(rec.get("date", ""))[:7]

def is_in_retention(rec, today):
 try:
  dt=datetime.strptime(rec.get("date", ""), "%Y-%m-%d").date()
 except Exception:
  return False
 product=(rec.get("product") or "").upper()
 if product=="LOTTO 5/35":
  return dt >= today - timedelta(days=29) and dt <= today
 return dt >= today - timedelta(days=729) and dt <= today

def load_partitioned_records():
 records={}
 for path in glob.glob("data/archive/*.json"):
  obj=get_json(path,{})
  for k,v in (obj.get("records",{}) if isinstance(obj,dict) else {}).items():
   if record_valid(v): records[k]=v
 # Migration from the earlier single-file archive, if present.
 legacy=get_json("data/archive.json",{})
 for k,v in (legacy.get("records",{}) if isinstance(legacy,dict) else {}).items():
  if record_valid(v): records.setdefault(k,v)
 return records

def main():
 now=datetime.now(timezone(timedelta(hours=7)))
 now_iso=now.isoformat(timespec="seconds")
 today=now.date()
 os.makedirs("data/archive",exist_ok=True)
 records=load_partitioned_records()
 quarantine=get_json("data/archive-quarantine.json",{"schema_version":1,"records":{}})
 # Quarantine invalid records from the legacy monolithic archive; never publish them.
 legacy=get_json("data/archive.json",{})
 for k,v in (legacy.get("records",{}) if isinstance(legacy,dict) else {}).items():
  if not record_valid(v): quarantine.setdefault("records",{}).setdefault(k,v)
 # Collect new records from multiple source candidates; only append previously unseen keys.
 report={"updated_at_vietnam":now_iso,"sources":{},"added":[],"kept_existing":len(records),"quarantined_count":len(quarantine.get("records",{})),"retention":{"traditional_and_vietlott_standard_days":730,"lotto_5_35_days":30}}
 for kind,sources in TRADITIONAL.items():
  attempts=[];found=[]
  for src in sources:
   started=time.time()
   try:
    html,final_url,http=get_html(src["url"]);draws=traditional_from_html(html,kind,src)
    new=[d for d in draws if d["key"] not in records and record_valid(d) and is_in_retention(d,today)]
    attempts.append({"source":src["name"],"url":src["url"],"status":"new_valid_draws" if new else "no_new_valid_draws","draw_count":len(draws),"new_count":len(new),"seconds":round(time.time()-started,2)})
    if new: found=new;break
   except Exception as e: attempts.append({"source":src["name"],"url":src["url"],"status":"error","error":f"{type(e).__name__}: {e}","seconds":round(time.time()-started,2)})
  added=0
  for d in found:
   if d["key"] not in records:
    d["locked_at_utc"]=now.astimezone(timezone.utc).isoformat(timespec="seconds")
    d["first_source_id"]=d["source_id"]
    d["content_sha256"]=hashlib.sha256(json.dumps(d,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    records[d["key"]]=d;report["added"].append(d["key"]);added+=1
  report["sources"][kind]={"attempts":attempts,"selected_source":found[0]["source_id"] if found else None,"new_records_locked":added}
 for src in VIETLOTT:
  attempts=[];found=[]
  # Only query the product-specific official page. Generic Vietlott pages can expose
  # another product's latest draw and must never be mislabeled as this product.
  urls=src.get("urls",[src.get("url")])
  for index,url in enumerate(urls):
   started=time.time();candidate={**src,"url":url,"generic_fallback":index>0}
   try:
    html,final_url,http=get_html(url);draws=vietlott_from_html(html,candidate)
    valid=[d for d in draws if record_valid(d) and is_in_retention(d,today)]
    new=[d for d in valid if d["key"] not in records]
    attempts.append({"source":url,"status":"new_valid_draws" if new else ("valid_existing_only" if valid else "no_product_specific_valid_draws"),"draw_count":len(draws),"valid_count":len(valid),"new_count":len(new),"seconds":round(time.time()-started,2)})
    if new: found=new;break
   except Exception as e: attempts.append({"source":url,"status":"error","error":f"{type(e).__name__}: {e}","seconds":round(time.time()-started,2)})
  added=0
  for d in found:
   if d["key"] not in records:
    d["locked_at_utc"]=now.astimezone(timezone.utc).isoformat(timespec="seconds")
    d["first_source_id"]=d["source_id"]
    d["content_sha256"]=hashlib.sha256(json.dumps(d,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    records[d["key"]]=d;report["added"].append(d["key"]);added+=1
  report["sources"][src["id"]]={"product":src["product"],"attempts":attempts,"selected_source":found[0]["source_id"] if found else None,"new_records_locked":added}
 # Enforce retention and product allow-list. This only affects the active published dataset.
 allowed={"MEGA 6/45","POWER 6/55","LOTTO 5/35","MAX 3D"}
 expired=[];retained={}
 for k,v in records.items():
  if v.get("kind")=="vietlott" and (v.get("product") or "").upper() not in allowed:
   continue
  if is_in_retention(v,today): retained[k]=v
  else: expired.append(k)
 records=retained
 # Store monthly partitions for normal draws and one rolling file for Lotto 5/35.
 partitions={}
 for k,v in records.items():
  if (v.get("product") or "").upper()=="LOTTO 5/35": p="data/archive/lotto-5-35.json"
  else:
   mk=month_key(v)
   if not re.fullmatch(r"\d{4}-\d{2}",mk): continue
   p=f"data/archive/{mk}.json"
  partitions.setdefault(p,{})[k]=v
 existing=set(glob.glob("data/archive/*.json"))
 desired=set(partitions)
 for path in existing-desired:
  try: os.remove(path)
  except OSError: pass
 for path,items in partitions.items():
  payload={"schema_version":3,"updated_at_vietnam":now_iso,"records":dict(sorted(items.items(),key=lambda kv:(kv[1].get("date",""),kv[0]),reverse=True))}
  tmp=path+".tmp"
  with open(tmp,"w",encoding="utf-8") as f: json.dump(payload,f,ensure_ascii=False,separators=(",",":"))
  os.replace(tmp,path)
 if quarantine.get("records"):
  with open("data/archive-quarantine.json","w",encoding="utf-8") as f: json.dump(quarantine,f,ensure_ascii=False,indent=2)
 # Public manifest points to month/product files. The browser fetches these instead of a giant results.json.
 files=[]
 for path,items in sorted(partitions.items()):
  rel=path.replace("\\","/")
  kinds=sorted(set(v.get("kind") for v in items.values()))
  products=sorted(set(v.get("product") for v in items.values() if v.get("product")))
  files.append({"url":rel,"count":len(items),"kinds":kinds,"products":products,"from":min(v["date"] for v in items.values()),"to":max(v["date"] for v in items.values())})
 manifest={"schema_version":3,"updated_at_vietnam":now_iso,"status":"ok" if records else "empty","record_count":len(records),"files":files,"retention":{"traditional_days":730,"vietlott_power_mega_3d_days":730,"lotto_5_35_days":30},"collection_report":report,"notice":"Chỉ công bố bản ghi hợp lệ; kỳ quay đã khóa không bị ghi đè. Dữ liệu đang hoạt động được giới hạn theo thời gian lưu đã cấu hình."}
 with open("data/index.json","w",encoding="utf-8") as f: json.dump(manifest,f,ensure_ascii=False,indent=2)
 # Remove old monolithic active files so Git stops tracking a growing archive/results blob.
 for old in ("data/archive.json","data/results.json"):
  if os.path.exists(old): os.remove(old)
 summary=os.environ.get("GITHUB_STEP_SUMMARY")
 if summary:
  with open(summary,"a",encoding="utf-8") as f:
   f.write("# AppNho — kết quả xổ số đã chuẩn hóa\n\n")
   f.write(f"- Bản ghi đang lưu: {len(records)}\n- Bản ghi mới khóa: {len(report['added'])}\n- Bản ghi hết hạn đã loại khỏi dữ liệu hoạt động: {len(expired)}\n- Tệp dữ liệu phân vùng: {len(files)}\n- Bản ghi sai từ kho cũ cách ly: {report['quarantined_count']}\n\n")
   f.write("| Nhóm/nguồn | Nguồn đã thử | Bản ghi mới |\n|---|---:|---:|\n")
   for k,v in report["sources"].items(): f.write(f"| {k} | {len(v['attempts'])} | {v['new_records_locked']} |\n")
 print(f"Valid records={len(records)}; newly locked={len(report['added'])}; expired={len(expired)}; partitions={len(files)}")
 for k,v in report["sources"].items(): print(k,"attempts",len(v["attempts"]),"new",v["new_records_locked"],"selected",v["selected_source"])
if __name__=="__main__": main()
