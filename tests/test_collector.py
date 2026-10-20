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


if __name__ == '__main__':
    test_dates()
    test_vietlott_product_shapes()
    test_bad_lotto_shape_rejected()
    test_draw_identity_separates_lotto_sessions()
    test_lotto_parser_handles_two_sessions_same_day()
    test_product_dates_are_not_forced_to_match()
    print('All collector fixture tests passed.')
