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
 {"id":"mega645","product":"MEGA 6/45","url":"https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/645"},
 {"id":"power655","product":"POWER 6/55","url":"https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/655"},
 {"id":"max3d","product":"MAX 3D","url":"https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/max-3D.html"},
 {"id":"lotto535","product":"LOTTO 5/35","url":"https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/535"},
]
STATIONS=["Thừa Thiên Huế","Thua Thien Hue","Phú Yên","Phu Yen","Đà Nẵng","Da Nang","Khánh Hòa","Khanh Hoa","Đắk Lắk","Dak Lak","Quảng Nam","Quang Nam","Bình Định","Binh Dinh","Quảng Trị","Quang Tri","Quảng Bình","Quang Binh","Gia Lai","Ninh Thuận","Ninh Thuan","Quảng Ngãi","Quang Ngai","Đắk Nông","Dak Nong","Kon Tum","Hồ Chí Minh","Ho Chi Minh","Đồng Tháp","Dong Thap","Cà Mau","Ca Mau","Bến Tre","Ben Tre","Vũng Tàu","Vung Tau","Bạc Liêu","Bac Lieu","Cần Thơ","Can Tho","Sóc Trăng","Soc Trang","Trà Vinh","Tra Vinh","An Giang","Long An","Tiền Giang","Tien Giang","Kiên Giang","Kien Giang","Đồng Nai","Dong Nai","Bình Dương","Binh Duong","Tây Ninh","Tay Ninh"]
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
 try:return f"{y:04d}-{mo:02d}-{d:02d}"
 except:return None

def prize_name(s):
 s=re.sub(r"\s+"," ",s.strip()).casefold().rstrip(":")
 return PRIZE_ALIASES.get(s)

def split_station_names(text):
 found=[]
 low=text.casefold()
 for name in STATIONS:
  if name.casefold() in low and name not in found:found.append(name)
 # preserve page/table order using occurrence index
 found.sort(key=lambda n:low.find(n.casefold()))
 return found

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
   if not stations:continue
   # The source page sometimes nests multiple station labels inside one cell; keep exact known names.
   stations=list(dict.fromkeys(stations))
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
 try:
  from bs4 import BeautifulSoup
 except ImportError:return []
 soup=BeautifulSoup(html,"html.parser")
 text=re.sub(r"\s+"," ",soup.get_text(" ",strip=True))
 # Official product pages expose draw number/date near the beginning.
 m=re.search(r"(?:Kỳ quay thưởng|Kỳ quay)\s*#?\s*(\d{3,6})\s*ngày\s*(\d{1,2}/\d{1,2}/\d{4})",text,re.I)
 if not m:
  m=re.search(r"#\s*(\d{3,6})\s*(\d{1,2}/\d{1,2}/\d{4})",text)
 if not m:return []
 draw_no=m.group(1);date=norm_date(m.group(2))
 product=src["product"]
 prizes=[]
 # Parse only prize rows from the result table. Avoid rows from payout/rules tables.
 for table in soup.find_all("table"):
  local=[]
  for row in table_rows(table):
   if len(row)<2:continue
   label=row[0].get_text(" ",strip=True)
   if not re.search(r"(đặc biệt|giải nhất|giải nhì|giải ba|giải tư|giải năm|giải sáu|jackpot)",label,re.I):continue
   # Result cells contain 2-digit lottery balls or 3-digit Max3D combinations.
   raw=row[1].get_text(" ",strip=True)
   if re.search(r"trùng|đồng|VNĐ|vnd|tỷ|triệu",raw,re.I):continue
   width=3 if "3D" in product else 2
   nums=re.findall(rf"(?<!\d)\d{{{width}}}(?!\d)",raw)
   if nums:local.append({"name":re.sub(r"\s+"," ",label),"numbers":nums})
  if local:
   # Keep first result-like table with enough recognizable result rows.
   if len(local)>=1:
    prizes=local;break
 if not prizes:
  # Mega/Power result line often appears as six two-digit numbers, optionally followed by Power ball.
  segment=text[max(0,m.start()-100):m.end()+800]
  width=3 if "3D" in product else 2
  if width==2:
   matches=list(re.finditer(r"(?<!\d)(\d{2}(?:\s+\d{2}){5})(?:\s*[|+]\s*(\d{2}))?(?!\d)",segment))
   if matches:
    nums=re.findall(r"\d{2}",matches[0].group(1));extra=matches[0].group(2)
    prizes=[{"name":"Bộ số trúng thưởng","numbers":nums+( [extra] if extra else [])}]
 if not prizes:return []
 key=f"vietlott|{product}|{date}|{draw_no}"
 return [{"key":key,"kind":"vietlott","product":product,"draw_no":draw_no,"date":date,"title":product,"station":product,"prizes":prizes,"source_url":src["url"],"source_id":src["id"]}]

def record_valid(rec):
 kind=rec.get("kind");prizes=rec.get("prizes") or []
 if not rec.get("date") or not prizes:return False
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
  if "3D" in prod:return any(len(n)==3 for n in vals)
  return bool(vals)
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
  urls=[src["url"],"https://xosohn.com/vietlott","https://m.kqxs.vn/xo-so-vietlott"]
  for url in urls:
   started=time.time();candidate={**src,"url":url}
   try:
    html,final_url,http=get_html(url);draws=vietlott_from_html(html,candidate)
    new=[d for d in draws if d["key"] not in records and record_valid(d) and is_in_retention(d,today)]
    attempts.append({"source":url,"status":"new_valid_draws" if new else "no_new_valid_draws","draw_count":len(draws),"new_count":len(new),"seconds":round(time.time()-started,2)})
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
