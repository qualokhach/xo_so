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
  {"id":"dovesovn","name":"Dò Vé Số VN (trang tổng hợp)","url":"https://dovesovn.com/"},
  {"id":"kqxs_info","name":"KQXS.info.vn (trang tổng hợp)","url":"https://kqxs.info.vn/"},
 ],
 "xsmt":[
  {"id":"kqxs_mt","name":"KQXS.vn miền Trung","url":"https://m.kqxs.vn/mien-trung"},
  {"id":"ketqua_org","name":"KetQua.org miền Trung","url":"https://ketqua.org/"},
  {"id":"xskt_io","name":"XSKT.io miền Trung","url":"https://xskt.io/"},
  {"id":"dovesovn","name":"Dò Vé Số VN (trang tổng hợp)","url":"https://dovesovn.com/"},
  {"id":"kqxs_info","name":"KQXS.info.vn (trang tổng hợp)","url":"https://kqxs.info.vn/"},
 ],
 "xsmn":[
  {"id":"kqxs_mn","name":"KQXS.vn miền Nam","url":"https://m.kqxs.vn/mien-nam"},
  {"id":"ketqua_org","name":"KetQua.org miền Nam","url":"https://ketqua.org/"},
  {"id":"xskt_io","name":"XSKT.io miền Nam","url":"https://xskt.io/"},
  {"id":"dovesovn","name":"Dò Vé Số VN (trang tổng hợp)","url":"https://dovesovn.com/"},
  {"id":"kqxs_info","name":"KQXS.info.vn (trang tổng hợp)","url":"https://kqxs.info.vn/"},
 ],
}
VIETLOTT=[
 {"id":"mega645","product":"MEGA 6/45","urls":[
  "https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/645",
  "https://www.minhngoc.net.vn/ket-qua-xo-so/dien-toan-vietlott/mega-6x45.html",
  "https://lottpicker.vn/?route=vietlott/mega645.results",
  "https://xosohn.com/vietlott/mega-645",
  "https://cvwork.vn/ket-qua-xo-so/vietlott/mega-645",
  "https://xosovietguide.com/lich-su/",
  "https://xosovietloto.com/lich-su/",
  "https://andromeda.com.vn/vietlott-max3d/",
  "https://www.hpsc.com.vn/xo-so-vietlott.html",
  "https://xosonay.com/vietlott/"]},
 {"id":"power655","product":"POWER 6/55","urls":[
  "https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/655",
  "https://www.minhngoc.net.vn/ket-qua-xo-so/dien-toan-vietlott/power-6x55.html",
  "https://lottpicker.vn/?route=vietlott/power655.results",
  "https://xosovietguide.com/lich-su/",
  "https://xosovietloto.com/lich-su/",
  "https://cvwork.vn/ket-qua-xo-so/vietlott/power-655",
  "https://xosohn.com/vietlott/power-655",
  "https://andromeda.com.vn/",
  "https://www.hpsc.com.vn/xo-so-vietlott.html",
  "https://xosonay.com/vietlott/"]},
 {"id":"lotto535","product":"LOTTO 5/35","urls":[
  "https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/535",
  "https://xosomoinhat.com/xo-so-lotto-535",
  "https://xosovietguide.com/lich-su/",
  "https://cvwork.vn/ket-qua-xo-so/vietlott/power-5-35",
  "https://xosohn.com/vietlott/lotto-535",
  "https://lottpicker.vn/",
  "https://andromeda.com.vn/",
  "https://www.hpsc.com.vn/xo-so-vietlott.html",
  "https://www.vietnamyello.com/lottery/results/history",
  "https://xosonay.com/vietlott/"]},
 {"id":"max3d","product":"MAX 3D","urls":[
  "https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/max-3D.html",
  "https://andromeda.com.vn/vietlott-max3d/",
  "https://lottpicker.vn/?route=vietlott/max3d.results",
  "https://xosovietguide.com/lich-su/",
  "https://xosovietloto.com/lich-su/",
  "https://www.xsmbav.com/xo-so-vietlott",
  "https://www.hpsc.com.vn/xo-so-vietlott.html",
  "https://www.vietnamyello.com/lottery/results/history",
  "https://xosonay.com/vietlott/",
  "https://www.lotteryfool.com/results/vietlott"]},
 {"id":"max3dplus","product":"MAX 3D+","urls":[
  "https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/max-3DPlus.html",
  "https://lottpicker.vn/?route=vietlott/max3d.results",
  "https://andromeda.com.vn/vietlott-max3d/",
  "https://xosovietguide.com/lich-su/",
  "https://xosohn.com/vietlott/max-3d-plus",
  "https://cvwork.vn/ket-qua-xo-so/vietlott/max-3d-plus",
  "https://www.xsmbav.com/xo-so-vietlott",
  "https://www.hpsc.com.vn/xo-so-vietlott.html",
  "https://www.vietnamyello.com/lottery/results/history",
  "https://xosonay.com/vietlott/"]},
 {"id":"max3dpro","product":"MAX 3D PRO","urls":[
  "https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/max-3DPro.html",
  "https://xskt.com.vn/xsmax3dpro",
  "https://xosophonix.vn/vietlott/max-3d-pro",
  "https://doveso.com.vn/vietlott-max-3d-pro/",
  "https://cupdienlamdong.com/xo-so-max-3d-pro/",
  "https://cvwork.vn/ket-qua-xo-so/vietlott/max-3d-pro",
  "https://vineco.net.vn/kqxs-max-3d-pro.html",
  "https://vesophuocdanh.vn/vietlott/max-3d-pro",
  "https://hpsc.com.vn/xs-max-3d-pro.html",
  "https://www.vietnamyello.com/lottery/results/history"]},
]
STATIONS=["Thừa Thiên Huế","Thua Thien Hue","Phú Yên","Phu Yen","Đà Nẵng","Da Nang","Khánh Hòa","Khanh Hoa","Đắk Lắk","Dak Lak","Quảng Nam","Quang Nam","Bình Định","Binh Dinh","Quảng Trị","Quang Tri","Quảng Bình","Quang Binh","Gia Lai","Ninh Thuận","Ninh Thuan","Quảng Ngãi","Quang Ngai","Đắk Nông","Dak Nong","Kon Tum","Hồ Chí Minh","Ho Chi Minh","Đồng Tháp","Dong Thap","Cà Mau","Ca Mau","Bến Tre","Ben Tre","Vũng Tàu","Vung Tau","Bạc Liêu","Bac Lieu","Cần Thơ","Can Tho","Sóc Trăng","Soc Trang","Trà Vinh","Tra Vinh","An Giang","Long An","Tiền Giang","Tien Giang","Kiên Giang","Kien Giang","Đồng Nai","Dong Nai","Bình Dương","Binh Duong","Tây Ninh","Tay Ninh","Bình Phước","Binh Phuoc","Bình Thuận","Binh Thuan","Hậu Giang","Hau Giang","Vĩnh Long","Vinh Long","Đà Lạt","Da Lat","Lâm Đồng","Lam Dong"]
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
 with urlopen(req,timeout=8) as r:
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
SOUTH_CANONICAL={"ho chi minh","tp ho chi minh","dong nai","can tho","soc trang","an giang","binh duong","binh phuoc","binh thuan","bac lieu","ben tre","ca mau","dong thap","hau giang","kien giang","long an","tien giang","tra vinh","vinh long","tay ninh","vung tau","da lat","lam dong"}
def canonical_station(value):
 import unicodedata
 value=str(value).replace("Đ","D").replace("đ","d")
 value=unicodedata.normalize("NFKD",value).encode("ascii","ignore").decode("ascii").casefold()
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
  # DATE SAFETY: a date must belong to this exact result table.
  # Never call norm_date() on the whole table: aggregators sometimes append yesterday's
  # results, next-draw dates, or other station dates to the same table, which can label
  # a 20th result as the 19th. Prefer caption, then a nearby heading, then accept a date
  # embedded in the table only when exactly one distinct calendar date occurs.
  table_text=table.get_text(" ",strip=True)
  table_dates=[]
  for dm in DATE_RE.finditer(table_text):
   candidate=norm_date(dm.group(0))
   if candidate and candidate not in table_dates:
    table_dates.append(candidate)
  # A table that mixes multiple draw dates cannot safely be treated as one draw.
  if len(table_dates)>1:
   continue
  caption=table.find("caption")
  date=norm_date(caption.get_text(" ",strip=True)) if caption else None
  if not date:
   prev=table.find_previous(["h1","h2","h3","h4","time"])
   if prev:
    between=prev.find_next("table")
    if between is table and len(prev.get_text(" ",strip=True)) <= 600:
     heading_text=prev.get_text(" ",strip=True)
     # Do not borrow dates from generic news/update headings.
     if not re.search(r"tin\s*tức|cập\s*nhật|thông\s*báo|bài\s*viết",heading_text,re.I):
      date=norm_date(heading_text)
  if not date:
   if len(table_dates)==1:
    date=table_dates[0]
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

def parse_max3d_prizes(text):
 """Parse Max 3D numbers under their prize labels when labels are present."""
 area=re.split(r"(?:giải thưởng\s*\|\s*kết quả|bảng thống kê|các lần quay trước|điều kiện lĩnh thưởng)",text,maxsplit=1,flags=re.I)[0]
 matches=list(re.finditer(r"giải\s*(đặc biệt|nhất|nhì|ba|tư|năm|sáu|bảy|tám|khuyến khích)",area,re.I))
 aliases={"đặc biệt":"Giải Đặc biệt","nhất":"Giải nhất","nhì":"Giải nhì","ba":"Giải ba","tư":"Giải tư","năm":"Giải năm","sáu":"Giải sáu","bảy":"Giải bảy","tám":"Giải tám","khuyến khích":"Giải khuyến khích"}
 result=[]
 for i,m in enumerate(matches):
  end=matches[i+1].start() if i+1<len(matches) else len(area)
  chunk=area[m.end():end]
  nums=re.findall(r"(?<!\d)(\d{3})(?!\d)",chunk)
  if not nums:
   runs=re.findall(r"(?<!\d)(?:\d[\s\u00a0]*){6,90}(?!\d)",chunk)
   for run in runs:
    digits=re.findall(r"\d",run)
    if len(digits)>=3:
     nums=["".join(digits[j:j+3]) for j in range(0,len(digits)-2,3)]
     break
  if nums: result.append({"name":aliases[m.group(1).casefold()],"numbers":nums[:30]})
 return result if len(result)>=2 else []


def product_label_matches(product, label):
 """Strictly classify a Vietlott label; MAX 3D must not steal 3D+ or 3D Pro."""
 import unicodedata
 text=unicodedata.normalize("NFKC",str(label or "")).casefold()
 text=text.replace("điện toán", " ").replace("vietlott", " ")
 compact=re.sub(r"[^a-z0-9+]+", "", text)
 has_pro=bool(re.search(r"max\s*3d\s*(?:pro|professional)\b|max3dpro|3d\s*pro\b",text)) or "max3dpro" in compact
 has_plus=bool(re.search(r"max\s*3d\s*(?:\+|plus)(?:\b|$)|max3dplus|3d\s*(?:\+|plus)(?:\b|$)",text)) or "max3d+" in compact or "max3dplus" in compact
 has_max3d=bool(re.search(r"max\s*3d",text)) or "max3d" in compact
 if product == "MAX 3D PRO": return has_pro
 if product == "MAX 3D+": return has_plus and not has_pro
 if product == "MAX 3D": return has_max3d and not has_plus and not has_pro
 if product == "MEGA 6/45": return bool(re.search(r"mega\s*6\s*/?\s*45|mega645",text))
 if product == "POWER 6/55": return bool(re.search(r"power\s*6\s*/?\s*55|power655",text))
 if product == "LOTTO 5/35": return bool(re.search(r"lotto\s*5\s*/?\s*35|lotto535|lotto-535",text))
 return False

def vietlott_from_html(html,src):
 # Minh Ngoc exposes several historic draws on one product page. Parse each
 # product/date block independently; do not assign a mixed page's first draw to every product.
 try:
  from bs4 import BeautifulSoup
 except ImportError:
  return []
 soup=BeautifulSoup(html,"html.parser")
 product=src["product"]
 host_url=src.get("url","").casefold()
 title=(soup.title.get_text(" ",strip=True) if soup.title else "").casefold()
 flat=re.sub(r"\s+"," ",soup.get_text(" ",strip=True))
 product_pattern={
  "MEGA 6/45":r"mega\s*6\s*/?\s*45|mega645",
  "POWER 6/55":r"power\s*6\s*/?\s*55|power655",
  "MAX 3D PRO":r"(?:max\s*3d\s*(?:pro|professional)|max3dpro|3d\s*pro)",
  "MAX 3D+":r"(?:max\s*3d\s*(?:\+|plus)|max3dplus|3d\s*(?:\+|plus))",
  "MAX 3D":r"max\s*3d(?!\s*(?:pro|professional|\+|plus))",
  "LOTTO 5/35":r"lotto\s*5\s*/?\s*35|lotto535|lotto-535",
 }[product]
 # History-list layout used by Minh Ngoc: each result starts with a product title/date,
 # then a ticket/draw number and the winning balls. A window ends at the next result heading.
 if "minhngoc.net.vn" in host_url or "minhngoc.me" in host_url:
  headings=list(re.finditer(r"KẾT QUẢ XỔ SỐ\s+(.{0,35}?)\s*[-–]\s*NGÀY\s*:\s*(\d{1,2}/\d{1,2}/\d{4})",flat,re.I))
  out=[]
  for i,h in enumerate(headings):
   label=h.group(1).casefold()
   if not re.search(product_pattern,label) or not product_label_matches(product,label):
    continue
   date=norm_date(h.group(2))
   if not date: continue
   end=headings[i+1].start() if i+1<len(headings) else min(len(flat),h.end()+1000)
   seg=flat[h.end():end]
   drawm=re.search(r"Kỳ\s*(?:vé|quay(?:\s*thưởng)?)\s*:\s*#?0*(\d{3,6})",seg,re.I)
   if not drawm: continue
   draw_no=str(int(drawm.group(1)))
   # Numbers immediately after ticket metadata; never use payout/statistics tables.
   meta=re.search(r"Ngày\s*quay\s*thưởng\s*\d{1,2}/\d{1,2}/\d{4}",seg,re.I)
   start=meta.end() if meta else drawm.end()
   nums_region=seg[start:start+240]
   if product in ("MEGA 6/45","POWER 6/55"):
    need=7 if product=="POWER 6/55" else 6
    # Accept separators commonly used on pages: whitespace, hyphen, vertical bar, bullet.
    vals=re.findall(r"(?<!\d)(\d{1,2})(?!\d)",nums_region)
    vals=[f"{int(x):02d}" for x in vals[:need]]
    limit=55 if product=="POWER 6/55" else 45
    if len(vals)!=need or any(not 1<=int(x)<=limit for x in vals[:6]):continue
    if product=="POWER 6/55" and not 1<=int(vals[6])<=55:continue
   elif product=="LOTTO 5/35":
    vals=re.findall(r"(?<!\d)(\d{1,2})(?!\d)",nums_region)
    vals=[f"{int(x):02d}" for x in vals[:6]]
    if len(vals)<5 or any(not 1<=int(x)<=35 for x in vals[:5]) or len(set(vals[:5]))<5:continue
    vals=vals[:6]
   else:
    # Max 3D-family fallback: parse the result segment, not payout/statistics values.
    result_area=re.split(r"(?:giải thưởng\s*\|\s*kết quả|các lần quay trước|điều kiện lĩnh thưởng)", nums_region, maxsplit=1, flags=re.I)[0]
    vals=re.findall(r"(?<!\d)\d{3}(?!\d)",result_area)
    if not vals:
     digits=re.findall(r"\d",result_area)
     if len(digits)>=6: vals=["".join(digits[j:j+3]) for j in range(0,len(digits)-2,3)]
    vals=[v for v in vals if len(v)==3][:20]
    if len(vals)<2:continue
   rec={"key":f"vietlott|{product}|{date}|{draw_no}","kind":"vietlott","product":product,"product_id":src["id"],"draw_no":draw_no,"date":date,"title":product,"station":product,"prizes":[{"name":"Bộ số trúng thưởng","numbers":vals}],"source_url":src["url"],"source_id":src["id"]}
   time_match=re.search(r"(?:lúc|vào lúc|tường thuật trực tiếp vào lúc)\s*(\d{1,2}:\d{2}:?\d{0,2})",seg,re.I)
   if time_match:rec["draw_time"]=time_match.group(1)[:5]
   rec["award_details"]=extract_award_details(soup,date,draw_no,product)
   if record_valid(rec):out.append(rec)
  if out:
   return list({r["key"]:r for r in out}.values())
 # For non-history pages, use the general product-aware parser below.
 """Extract one or more draws from a product page without mixing draw dates.

 Supports common Vietnamese headings such as:
   Kết quả QSMT kỳ #00889 ngày 16/09/2026 - Lúc 13:00
   Kết quả quay số mở thưởng kỳ quay thưởng #123 ngày 16/09/2026
   Kỳ quay thưởng #123 ngày 16/09/2026

 For Lotto 5/35, every heading is a separate session. Only the five main balls
 and optional bonus ball immediately following that heading are accepted.
 """
 text=re.sub(r"\s+"," ",soup.get_text(" ",strip=True))
 product=src["product"]
 width=3 if product in ("MAX 3D","MAX 3D+","MAX 3D PRO") else 2
 # Different publishers vary the wording and whether the draw id has a # sign.
 heading_re=re.compile(
  r"(?:(?:kết quả(?: quay số mở thưởng)?|quay số mở thưởng)\s*)?"
  r"(?:qsm[dt]\s*)?(?:kỳ(?:\s+quay(?:\s+thưởng)?)?\s*)#?\s*(\d{3,6})"
  r"\s*(?:(?:thứ\s*[2-7]|chủ\s*nhật|thứ\s*hai|thứ\s*ba|thứ\s*tư|thứ\s*năm|thứ\s*sáu|thứ\s*bảy)\s*)?"
  r"(?:ngày\s*|[-–|—]\s*(?:(?:thứ\s*[2-7]|chủ\s*nhật)\s*[-–|—]?\s*)?)(\d{1,2}[/-]\d{1,2}[/-]\d{4})"
  r"(?:\s*[-–|,]?\s*(?:lúc|vào lúc|giờ)\s*(\d{1,2}:\d{2}|\d{1,2}\s*[hH]))?",re.I)
 matches=list(heading_re.finditer(text))
 # Some official pages render a shorter label.
 if not matches:
  heading_re=re.compile(r"(?:kỳ quay thưởng|kỳ quay|kỳ)\s*#?(\d{3,6})\s*(?:ngày\s*)?(\d{1,2}[/-]\d{1,2}[/-]\d{4})(?:\s*[-–,]?\s*(?:lúc|giờ)\s*(\d{1,2}:\d{2}|\d{1,2}\s*[hH]))?",re.I)
  matches=list(heading_re.finditer(text))
 if not matches:
  return []
 aliases={"MEGA 6/45":("mega 6/45","mega645"),"POWER 6/55":("power 6/55","power655"),"MAX 3D":("max 3d","max3d"),"MAX 3D+":("max 3d+","max 3d plus","max3dplus","3d plus","3d+"),"MAX 3D PRO":("max 3d pro","max3dpro","3d pro","max 3d professional"),"LOTTO 5/35":("lotto 5/35","lotto535","lotto-535")}
 # A product-specific page is safe by URL/title. A mixed fallback must identify the
 # product near each draw heading, otherwise never relabel its first draw.
 url_lc=src.get("url", "").casefold()
 official_path={"MEGA 6/45":"/645", "POWER 6/55":"/655", "LOTTO 5/35":"/535", "MAX 3D":"/max-3d.html", "MAX 3D+":"/max-3dplus.html", "MAX 3D PRO":"/max-3dpro.html"}.get(product, "")
 official_specific=("vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/" in url_lc and official_path and url_lc.endswith(official_path))
 specific_url = bool((product == "LOTTO 5/35" and "lotto-535" in url_lc) or official_specific or ("minhngoc.net.vn" in url_lc and product in ("MEGA 6/45", "POWER 6/55")) or (product == "MAX 3D PRO" and any(x in url_lc for x in ("xskt.com.vn/xsmax3dpro", "xosophonix.vn/vietlott/max-3d-pro", "doveso.com.vn/vietlott-max-3d-pro", "cupdienlamdong.com/xo-so-max-3d-pro", "cvwork.vn/ket-qua-xo-so/vietlott/max-3d-pro", "vineco.net.vn/kqxs-max-3d-pro.html", "vesophuocdanh.vn/vietlott/max-3d-pro", "hpsc.com.vn/xs-max-3d-pro.html", "tracuuxoso.vn/vietlott/max-3d-pro"))) or (product == "MAX 3D+" and "lottpicker.vn/?route=vietlott/max3d.results" in url_lc) or (product == "MAX 3D" and "andromeda.com.vn/vietlott-max3d" in url_lc))
 page_title=(soup.title.get_text(" ",strip=True) if soup.title else "").casefold()
 out=[]
 for i,m in enumerate(matches):
  draw_no=m.group(1).lstrip("0") or "0"
  date=norm_date(m.group(2))
  if not date:continue
  # Only consider the text belonging to this draw, ending before the next heading.
  seg_end=matches[i+1].start() if i+1<len(matches) else min(len(text),m.end()+900)
  segment=text[m.end():seg_end]
  if not specific_url:
   context=text[max(0,m.start()-220):min(len(text),m.end()+300)].casefold()
   terms=aliases.get(product,())
   context_ok=product_label_matches(product,context) or product_label_matches(product,page_title)
   if not context_ok:
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
  else: # MAX 3D / MAX 3D+ / MAX 3D PRO
   # Keep prize labels if the source exposes them; do not flatten distinct prize ranks.
   grouped=parse_max3d_prizes(segment)
   result_area=re.split(r"(?:giải thưởng\s*\|\s*kết quả|các lần quay trước|điều kiện lĩnh thưởng)",segment,maxsplit=1,flags=re.I)[0]
   nums=re.findall(r"(?<!\d)(\d{3})(?!\d)",result_area)
   if not nums:
    digit_runs=re.findall(r"(?<!\d)(?:\d[\s\u00a0]*){6,120}(?!\d)",result_area)
    for run in digit_runs:
     digits=re.findall(r"\d",run)
     if len(digits)>=6:
      nums=["".join(digits[j:j+3]) for j in range(0,len(digits)-2,3)]
      break
   if grouped:prizes=grouped
   elif nums:prizes=[{"name":"Bộ số trúng thưởng","numbers":nums[:20]}]
  if not prizes:continue
  key=f"vietlott|{product}|{date}|{draw_no}"
  rec={"key":key,"kind":"vietlott","product":product,"product_id":src["id"],"draw_no":draw_no,"date":date,"title":product,"station":product,"prizes":prizes,"source_url":src["url"],"source_id":src["id"]}
  if draw_time:rec["draw_time"]=draw_time
  rec["award_details"]=extract_award_details(soup,date,draw_no,product)
  # Keep each Lotto session unique even if a provider accidentally reuses a draw number.
  if product=="LOTTO 5/35" and draw_time:rec["key"] += "|"+draw_time
  if record_valid(rec):out.append(rec)
 # Preserve source order while deduplicating repeated headings/tables.
 dedup={r["key"]:r for r in out}
 return list(dedup.values())

def extract_award_details(soup, date, draw_no, product):
 """Extract prize counts and payout values only from a matching result-summary table."""
 details=[]
 for table in soup.find_all("table"):
  rows=table_rows(table)
  if len(rows)<2: continue
  text=table.get_text(" ",strip=True)
  # The summary table must explicitly expose winner count and payout/value columns.
  if not re.search(r"(?:SL giải|số lượng|số vé trúng|số người trúng)",text,re.I): continue
  if not re.search(r"(?:giá trị|tiền thưởng|mức thưởng)",text,re.I): continue
  # Avoid taking a different product/draw's summary from a combined homepage.
  prior_headings=table.find_all_previous(["h1","h2","h3","h4","h5"])
  context=" ".join(h.get_text(" ",strip=True) for h in reversed(prior_headings[:8]))
  if date and norm_date(text+" "+context) not in (None,date): continue
  if draw_no and not re.search(r"#?0*"+re.escape(str(draw_no))+r"(?!\d)",text+" "+context):
   # Product-specific page may not repeat draw number inside the table, but must repeat date.
   if not date or norm_date(text+" "+context)!=date: continue
  headers=[re.sub(r"\s+"," ",c.get_text(" ",strip=True)).casefold() for c in rows[0]]
  if not any("giải" in h or "hạng" in h for h in headers): continue
  for row in rows[1:]:
   cells=[re.sub(r"\s+"," ",c.get_text(" ",strip=True)) for c in row]
   if len(cells)<3: continue
   label=cells[0]
   # Winner count is often a numeric cell; amount is the final cell.
   count_match=re.search(r"\d[\d.,]*",cells[-2])
   value_match=re.search(r"\d[\d.,]*",cells[-1])
   if not label or not value_match: continue
   details.append({"prize":label,"winner_count":count_match.group(0) if count_match else None,"value_vnd":re.sub(r"\D","",value_match.group(0))})
  if details: break
 return details

def record_valid(rec):
 """Strict structural validation. Unknown or incomplete draws fail closed."""
 kind=rec.get("kind");prizes=rec.get("prizes") or []
 date=rec.get("date")
 if not isinstance(date,str): return False
 try: datetime.strptime(date, "%Y-%m-%d")
 except (ValueError,TypeError): return False
 if not isinstance(prizes,list) or not prizes:return False
 for p in prizes:
  if not isinstance(p,dict) or not isinstance(p.get("name"),str) or not p["name"].strip():return False
  nums=p.get("numbers")
  if not isinstance(nums,list) or not nums:return False
  if any(not isinstance(n,(str,int)) or not re.fullmatch(r"\d{1,6}",str(n)) for n in nums):return False
 if kind in ("xsmb","xsmt","xsmn"):
  station=rec.get("station")
  if not isinstance(station,str) or not station.strip() or re.match(r"Đài\s*\d+$",station,re.I):return False
  if not station_belongs_to_kind(station,kind):return False
  counts=XSMB_COUNTS if kind=="xsmb" else TRAD_COUNTS
  names=[p.get("name","") for p in prizes]
  if len(names)!=len(counts) or any(names.count(n)!=1 for n in counts):return False
  # Each regional prize has a fixed number of digits. Reject fabricated-looking
  # tables where the row counts match but the actual number widths do not.
  widths=(
   {"Đặc biệt":5,"Giải nhất":5,"Giải nhì":5,"Giải ba":5,"Giải tư":4,"Giải năm":4,"Giải sáu":3,"Giải bảy":2}
   if kind=="xsmb" else
   {"Đặc biệt":6,"Giải nhất":5,"Giải nhì":5,"Giải ba":5,"Giải tư":5,"Giải năm":4,"Giải sáu":4,"Giải bảy":3,"Giải tám":2}
  )
  for p in prizes:
   label=p["name"]
   if label not in counts or len(p["numbers"])!=counts[label]:return False
   if any(len(str(n))!=widths[label] for n in p["numbers"]):return False
  return True
 if kind!="vietlott":return False
 prod=rec.get("product")
 allowed={x["product"] for x in VIETLOTT}
 if prod not in allowed:return False
 if rec.get("product_id") and rec["product_id"] != next((x["id"] for x in VIETLOTT if x["product"]==prod), None):return False
 if prod in ("MEGA 6/45","POWER 6/55"):
  main=next((p for p in prizes if p.get("name")=="Bộ số trúng thưởng"),None)
  expected=6 if prod=="MEGA 6/45" else 7
  limit=45 if prod=="MEGA 6/45" else 55
  if not main or len(main["numbers"])!=expected:return False
  vals=[str(n) for n in main["numbers"]]
  if any(not re.fullmatch(r"\d{2}",n) or not 1<=int(n)<=limit for n in vals):return False
  return len(set(vals))==len(vals)
 if prod=="LOTTO 5/35":
  main=next((p for p in prizes if p.get("name")=="Bộ số trúng thưởng"),None)
  if not main or len(main["numbers"])!=6:return False
  vals=[str(n) for n in main["numbers"]]
  return (all(re.fullmatch(r"\d{2}",n) and 1<=int(n)<=35 for n in vals[:5])
          and len(set(vals[:5]))==5
          and re.fullmatch(r"\d{2}",vals[5]) is not None
          and 1<=int(vals[5])<=12)
 if prod in ("MAX 3D","MAX 3D+","MAX 3D PRO"):
  vals=[str(n) for p in prizes for n in p["numbers"]]
  if len(vals)<2 or any(not re.fullmatch(r"\d{3}",n) for n in vals):return False
  # Product draw identity must be present; do not accept undated/unnumbered pages.
  return bool(rec.get("draw_no"))
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
 quarantine=get_json("data/archive-quarantine.json",{"schema_version":1,"records":{}})
 quarantine.setdefault("schema_version",1)
 quarantine.setdefault("records",{})
 # Quarantine invalid records found in existing active partitions before loading.
 # This makes rejection auditable instead of silently dropping malformed history.
 for path in glob.glob("data/archive/*.json"):
  obj=get_json(path,{})
  for k,v in (obj.get("records",{}) if isinstance(obj,dict) else {}).items():
   if not record_valid(v):
    quarantine["records"].setdefault(k,{"source_partition":path,"record":v,"quarantined_reason":"record_valid_failed"})
 records=load_partitioned_records()
 # Quarantine invalid records from the legacy monolithic archive; never publish them.
 legacy=get_json("data/archive.json",{})
 for k,v in (legacy.get("records",{}) if isinstance(legacy,dict) else {}).items():
  if not record_valid(v): quarantine.setdefault("records",{}).setdefault(k,v)
 # Collect new records from multiple source candidates; only append previously unseen keys.
 report={"updated_at_vietnam":now_iso,"sources":{},"added":[],"kept_existing":len(records),"quarantined_count":len(quarantine.get("records",{})),"retention":{"traditional_and_vietlott_standard_days":730,"lotto_5_35_days":30}}
 for kind,sources in TRADITIONAL.items():
  attempts=[];found=[];found_valid=[]
  for src in sources:
   started=time.time()
   try:
    html,final_url,http=get_html(src["url"]);draws=traditional_from_html(html,kind,src)
    valid=[d for d in draws if record_valid(d) and is_in_retention(d,today)]
    new=[d for d in valid if d["key"] not in records]
    attempts.append({"source":src["name"],"url":src["url"],"status":"new_valid_draws" if new else ("valid_existing_only" if valid else "no_valid_draws"),"draw_count":len(draws),"valid_count":len(valid),"new_count":len(new),"seconds":round(time.time()-started,2)})
    if valid: found_valid.extend(valid)
    if new: found.extend(new)
   except Exception as e: attempts.append({"source":src["name"],"url":src["url"],"status":"error","error":f"{type(e).__name__}: {e}","seconds":round(time.time()-started,2)})
  found=list({d["key"]:d for d in found}.values())
  added=0
  for d in found:
   if d["key"] not in records:
    d["locked_at_utc"]=now.astimezone(timezone.utc).isoformat(timespec="seconds")
    d["first_source_id"]=d["source_id"]
    d["content_sha256"]=hashlib.sha256(json.dumps(d,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    records[d["key"]]=d;report["added"].append(d["key"]);added+=1
  report["sources"][kind]={"attempts":attempts,"selected_source":(found_valid[0]["source_id"] if found_valid else None),"valid_records_seen":len({d["key"] for d in found_valid}),"new_records_locked":added,"source_warning":None if found_valid else "No valid result parsed from configured sources."}
 for src in VIETLOTT:
  attempts=[];found=[];found_valid=[]
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
    if valid: found_valid.extend(valid)
    if new: found.extend(new)
   except Exception as e: attempts.append({"source":url,"status":"error","error":f"{type(e).__name__}: {e}","seconds":round(time.time()-started,2)})
  found=list({d["key"]:d for d in found}.values())
  added=0
  for d in found:
   if d["key"] not in records:
    d["locked_at_utc"]=now.astimezone(timezone.utc).isoformat(timespec="seconds")
    d["first_source_id"]=d["source_id"]
    d["content_sha256"]=hashlib.sha256(json.dumps(d,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    records[d["key"]]=d;report["added"].append(d["key"]);added+=1
  report["sources"][src["id"]]={"product":src["product"],"attempts":attempts,"selected_source":(found_valid[0]["source_id"] if found_valid else None),"valid_records_seen":len({d["key"] for d in found_valid}),"new_records_locked":added,"source_warning":None if found_valid else "No valid draw parsed from any configured source; do not fabricate a result."}
 # Enforce retention and product allow-list. This only affects the active published dataset.
 allowed={"MEGA 6/45","POWER 6/55","LOTTO 5/35","MAX 3D","MAX 3D+","MAX 3D PRO"}
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
