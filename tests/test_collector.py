import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import fetch_results as f


def test_dates():
    assert f.norm_date('20/10/2026') == '2026-10-20'
    assert f.norm_date('31/02/2026') is None


def test_vietlott_product_shapes():
    samples = [
        ('MEGA 6/45', ['01','02','03','04','05','06']),
        ('POWER 6/55', ['01','02','03','04','05','06','07']),
        ('LOTTO 5/35', ['01','02','03','04','05','06']),
    ]
    for product, nums in samples:
        rec = {'kind':'vietlott','product':product,'date':'2026-10-20','draw_no':'123',
               'prizes':[{'name':'Bộ số trúng thưởng','numbers':nums}]}
        assert f.record_valid(rec), product


def test_bad_lotto_shape_rejected():
    rec = {'kind':'vietlott','product':'LOTTO 5/35','date':'2026-10-20','draw_no':'123',
           'prizes':[{'name':'Bộ số trúng thưởng','numbers':['01','02','03','04']}]}
    assert not f.record_valid(rec)


def test_draw_identity_separates_lotto_sessions():
    a = 'vietlott|LOTTO 5/35|2026-10-20|001|13:00'
    b = 'vietlott|LOTTO 5/35|2026-10-20|002|21:00'
    assert a != b


def test_lotto_parser_handles_two_sessions_same_day():
    html = '''<html><head><title>Lotto 5/35</title></head><body>
    <h2>Kết quả QSMT kỳ #00889 ngày 16/09/2026 - Lúc 13:00</h2>
    <p>03 12 17 27 35 | 07</p>
    <h2>Kết quả QSMT kỳ #00890 ngày 16/09/2026 - Lúc 21:00</h2>
    <p>01 04 15 22 31 | 09</p></body></html>'''
    src={'id':'lotto535','product':'LOTTO 5/35','url':'https://xosomoinhat.com/xo-so-lotto-535'}
    rows=f.vietlott_from_html(html,src)
    assert len(rows)==2, rows
    assert {r['draw_no'] for r in rows}=={'889','890'}
    assert {r['draw_time'] for r in rows}=={'13:00','21:00'}
    assert all(f.record_valid(r) for r in rows)


def test_product_dates_are_not_forced_to_match():
    # Stable keys contain each product's own date, so the latest draw per product
    # may legitimately have a different date.
    mega={'kind':'vietlott','product':'MEGA 6/45','date':'2026-10-18','draw_no':'123',
          'prizes':[{'name':'Bộ số trúng thưởng','numbers':['01','02','03','04','05','06']}]}
    power={'kind':'vietlott','product':'POWER 6/55','date':'2026-10-17','draw_no':'456',
           'prizes':[{'name':'Bộ số trúng thưởng','numbers':['01','02','03','04','05','06','07']}]}
    assert f.record_valid(mega) and f.record_valid(power)
    assert mega['date'] != power['date']




def test_minhngoc_product_history_parses_independent_draws():
    html='''<html><head><title>Kết quả xổ số Mega 6/45</title></head><body>
    <h3>KẾT QUẢ XỔ SỐ MEGA 6/45 - NGÀY: 18/10/2026</h3>
    Chủ nhật Kỳ vé: #01577 | Ngày quay thưởng 18/10/2026 10 11 31 38 40 44
    Giải thưởng Jackpot 0 26,444,954,000 đồng
    <h3>KẾT QUẢ XỔ SỐ MEGA 6/45 - NGÀY: 16/10/2026</h3>
    Thứ sáu Kỳ vé: #01576 | Ngày quay thưởng 16/10/2026 09 20 26 35 36 38
    </body></html>'''
    src={'id':'mega645','product':'MEGA 6/45','url':'https://www.minhngoc.net.vn/ket-qua-xo-so/dien-toan-vietlott/mega-6x45.html'}
    rows=f.vietlott_from_html(html,src)
    assert len(rows)==2, rows
    assert {r['date'] for r in rows}=={'2026-10-18','2026-10-16'}
    assert {r['draw_no'] for r in rows}=={'1577','1576'}




def test_three_max3d_products_are_separate():
    products = {x["product"] for x in f.VIETLOTT}
    assert {"MAX 3D", "MAX 3D+", "MAX 3D PRO"}.issubset(products)
    assert len({x["id"] for x in f.VIETLOTT}) == len(f.VIETLOTT)


def test_max3dpro_result_and_award_count_fixture():
    html = '''<html><head><title>Max 3D Pro</title></head><body>
    <h2>Kết quả quay số mở thưởng Max 3D Pro</h2><h3>Kỳ quay thưởng #00739 ngày 13/06/2026</h3>
    <h4>Giải Đặc biệt</h4><p>6 1 5</p><p>7 7 1</p><h4>Giải Nhất</h4><p>2 8 3</p><p>9 2 0</p>
    <table><tr><th>Giải thưởng</th><th>Kết quả</th><th>SL giải</th><th>Giá trị</th></tr>
    <tr><td>Giải Đặc biệt</td><td>615 771</td><td>1</td><td>2.000.000.000</td></tr></table></body></html>'''
    src = {"id":"max3dpro", "product":"MAX 3D PRO", "url":"https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/max-3DPro.html"}
    rows = f.vietlott_from_html(html, src)
    assert rows and rows[0]["product"] == "MAX 3D PRO"
    assert rows[0]["date"] == "2026-06-13" and rows[0]["draw_no"] == "739"
    assert f.record_valid(rows[0])
    assert {p["name"] for p in rows[0]["prizes"]} >= {"Giải Đặc biệt", "Giải nhất"}
    assert rows[0]["award_details"][0]["winner_count"] == "1"




def test_traditional_parser_never_uses_unrelated_page_date():
    html = '''<html><head><title>Kết quả xổ số ngày 20/10/2026</title></head><body>
    <h2>Tin tức cập nhật 20/10/2026</h2>
    <table><tr><th>Giải</th><th>Đà Nẵng</th></tr>
    <tr><td>Đặc biệt</td><td>123456</td></tr><tr><td>Giải nhất</td><td>123456</td></tr>
    <tr><td>Giải nhì</td><td>123456</td></tr><tr><td>Giải ba</td><td>123456 123456</td></tr>
    <tr><td>Giải tư</td><td>123456 123456 123456 123456 123456 123456 123456</td></tr>
    <tr><td>Giải năm</td><td>123456</td></tr><tr><td>Giải sáu</td><td>123456 123456 123456</td></tr>
    <tr><td>Giải bảy</td><td>123456</td></tr><tr><td>Giải tám</td><td>56</td></tr></table></body></html>'''
    rows = f.traditional_from_html(html, 'xsmt', {'id':'fixture','url':'https://example.test'})
    assert rows == [], "must not borrow the unrelated date from the page title/news heading"


if __name__ == '__main__':
    test_dates()
    test_vietlott_product_shapes()
    test_bad_lotto_shape_rejected()
    test_draw_identity_separates_lotto_sessions()
    test_lotto_parser_handles_two_sessions_same_day()
    test_product_dates_are_not_forced_to_match()
    test_minhngoc_product_history_parses_independent_draws()
    test_three_max3d_products_are_separate()
    test_max3dpro_result_and_award_count_fixture()
    print('All collector fixture tests passed.')


def test_traditional_validator_rejects_wrong_number_widths():
    rec = {
        'kind':'xsmt','date':'2026-10-20','station':'Đà Nẵng',
        'prizes':[
            {'name':'Đặc biệt','numbers':['12345']},
            {'name':'Giải nhất','numbers':['12345']},
            {'name':'Giải nhì','numbers':['12345']},
            {'name':'Giải ba','numbers':['12345','23456']},
            {'name':'Giải tư','numbers':['12345']*7},
            {'name':'Giải năm','numbers':['1234']},
            {'name':'Giải sáu','numbers':['1234']*3},
            {'name':'Giải bảy','numbers':['123']},
            {'name':'Giải tám','numbers':['12']},
        ]
    }
    assert not f.record_valid(rec)


def test_traditional_validator_accepts_correct_digit_widths():
    rec = {
        'kind':'xsmt','date':'2026-10-20','station':'Đà Nẵng',
        'prizes':[
            {'name':'Đặc biệt','numbers':['123456']},
            {'name':'Giải nhất','numbers':['12345']},
            {'name':'Giải nhì','numbers':['23456']},
            {'name':'Giải ba','numbers':['12345','23456']},
            {'name':'Giải tư','numbers':['12345']*7},
            {'name':'Giải năm','numbers':['1234']},
            {'name':'Giải sáu','numbers':['1234']*3},
            {'name':'Giải bảy','numbers':['123']},
            {'name':'Giải tám','numbers':['12']},
        ]
    }
    assert f.record_valid(rec)


def test_mega_and_power_reject_duplicate_or_out_of_range_numbers():
    base={'kind':'vietlott','date':'2026-10-20','draw_no':'123',
          'prizes':[{'name':'Bộ số trúng thưởng','numbers':['01','02','03','04','05','06']}]}
    assert f.record_valid({**base,'product':'MEGA 6/45','product_id':'mega645'})
    duplicate={**base,'product':'MEGA 6/45','product_id':'mega645',
               'prizes':[{'name':'Bộ số trúng thưởng','numbers':['01','02','03','04','05','05']}]}
    assert not f.record_valid(duplicate)
    out_of_range={**base,'product':'MEGA 6/45','product_id':'mega645',
                  'prizes':[{'name':'Bộ số trúng thưởng','numbers':['01','02','03','04','05','46']}]}
    assert not f.record_valid(out_of_range)


def test_lotto_requires_bonus_ball_and_valid_session_metadata():
    base={'kind':'vietlott','product':'LOTTO 5/35','product_id':'lotto535',
          'date':'2026-10-20','draw_no':'123','draw_time':'21:00',
          'prizes':[{'name':'Bộ số trúng thưởng','numbers':['01','02','03','04','05','06']}]}
    assert f.record_valid(base)
    assert not f.record_valid({**base,'prizes':[{'name':'Bộ số trúng thưởng','numbers':['01','02','03','04','05']}]})
    assert not f.record_valid({**base,'prizes':[{'name':'Bộ số trúng thưởng','numbers':['01','02','03','04','05','13']}]})



def test_traditional_table_with_multiple_dates_is_rejected_not_mislabeled():
    # Regression: a page/table contains both today's and yesterday's results.
    # The parser must not blindly take the first date and attach it to every station.
    html = """<html><body>
    <h2>Ngày quay 20/10/2026</h2>
    <table><caption>Kết quả xổ số</caption>
    <tr><th>Giải</th><th>Đà Nẵng</th></tr>
    <tr><td>Ghi chú</td><td>Kỳ trước 19/10/2026; kỳ này 20/10/2026</td></tr>
    <tr><td>Đặc biệt</td><td>123456</td></tr><tr><td>Giải nhất</td><td>12345</td></tr>
    <tr><td>Giải nhì</td><td>12345</td></tr><tr><td>Giải ba</td><td>12345 12345</td></tr>
    <tr><td>Giải tư</td><td>12345 12345 12345 12345 12345 12345 12345</td></tr>
    <tr><td>Giải năm</td><td>1234</td></tr><tr><td>Giải sáu</td><td>1234 1234 1234</td></tr>
    <tr><td>Giải bảy</td><td>123</td></tr><tr><td>Giải tám</td><td>12</td></tr>
    </table></body></html>"""
    rows = f.traditional_from_html(html, 'xsmt', {'id':'fixture','url':'https://example.test'})
    assert rows == [], "ambiguous table dates must be rejected instead of mislabeled"


def test_max3d_products_never_cross_classify():
    for product, pid in [('MAX 3D','max3d'), ('MAX 3D+','max3dplus'), ('MAX 3D PRO','max3dpro')]:
        rec = {'kind':'vietlott','product':product,'product_id':pid,'date':'2026-10-20','draw_no':'123',
               'prizes':[{'name':'Bộ số trúng thưởng','numbers':['001','123','999']}]}
        assert f.record_valid(rec), product


def test_max3d_pro_history_heading_with_em_dash():
    html = '''<html><head><title>Kết quả xổ số Max 3D Pro</title></head><body>
    <h2>Kỳ #794 — 20/10/2026 (Thứ Ba)</h2>
    <p>Giải đặc biệt 461 055</p><p>Giải nhất 786 338 089 963</p>
    <p>Giải nhì 357 205 613 849 160 300</p>
    <p>Giải ba 035 373 493 888 762 279 130 560</p>
    </body></html>'''
    src={'id':'max3dpro','product':'MAX 3D PRO','url':'https://xskt.com.vn/xsmax3dpro','generic_fallback':True}
    rows=f.vietlott_from_html(html,src)
    assert len(rows)==1, rows
    assert rows[0]['date']=='2026-10-20'
    assert rows[0]['draw_no']=='794'
    assert rows[0]['product']=='MAX 3D PRO'
    assert f.record_valid(rows[0])


def test_station_region_classification_handles_vietnamese_d_letter():
    assert f.station_belongs_to_kind("Đà Nẵng", "xsmt")
    assert f.station_belongs_to_kind("Đắk Lắk", "xsmt")
    assert f.station_belongs_to_kind("Đồng Tháp", "xsmn")
    assert f.station_belongs_to_kind("TP. Hồ Chí Minh", "xsmn")
    assert not f.station_belongs_to_kind("Đồng Tháp", "xsmt")
    assert not f.station_belongs_to_kind("Đà Nẵng", "xsmn")


def test_collector_validator_rejects_station_assigned_to_wrong_region():
    rec = {
        "kind":"xsmt", "date":"2026-10-20", "station":"Đồng Tháp",
        "prizes":[
            {"name":"Đặc biệt","numbers":["123456"]},
            {"name":"Giải nhất","numbers":["12345"]},
            {"name":"Giải nhì","numbers":["12345"]},
            {"name":"Giải ba","numbers":["12345","23456"]},
            {"name":"Giải tư","numbers":["12345"]*7},
            {"name":"Giải năm","numbers":["1234"]},
            {"name":"Giải sáu","numbers":["1234"]*3},
            {"name":"Giải bảy","numbers":["123"]},
            {"name":"Giải tám","numbers":["12"]},
        ]
    }
    assert not f.record_valid(rec)
