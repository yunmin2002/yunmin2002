"""
산림청 산불통계데이터 CSV 파싱 스크립트
공공데이터포털에서 다운로드한 CSV → 화성시 필터 → 좌표 변환 → JSON

입력:  data/raw_forest_fires/forest_fires_raw.csv
출력:  data/forest_fires.json
"""

import os
import csv
import json
import time
import datetime
import requests

INPUT_CSV  = 'data/raw_forest_fires/forest_fires_raw.csv'
OUTPUT     = 'data/forest_fires.json'
CACHE_FILE = 'data/geocode_cache.json'


def load_cache():
    try:
        with open(CACHE_FILE, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_cache(cache):
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def geocode(address, cache):
    if address in cache:
        return cache[address]

    try:
        resp = requests.get(
            'https://nominatim.openstreetmap.org/search',
            params={'q': address, 'format': 'json', 'limit': 1, 'countrycodes': 'kr'},
            headers={'User-Agent': 'HwaseongFirePatrol/1.0'},
            timeout=10
        )
        results = resp.json()
        if results:
            lat = float(results[0]['lat'])
            lng = float(results[0]['lon'])
            cache[address] = [lat, lng]
            time.sleep(1.1)
            return lat, lng
    except Exception as e:
        print(f'[GEOCODE ERROR] {address}: {e}')

    cache[address] = None
    return None


def build_address(row):
    sido = (row.get('발생장소_시도') or '').strip()
    sgg  = (row.get('발생장소_시군구') or '').strip()
    emd  = (row.get('발생장소_읍면') or '').strip()
    dr   = (row.get('발생장소_동리') or '').strip()

    if sido == '경기':
        sido = '경기도'
    if sgg and not sgg.endswith(('시', '군', '구')):
        sgg = sgg + '시'
    if emd and not emd.endswith(('읍', '면', '동')):
        emd = emd + '면'
    if dr and not dr.endswith(('리', '동')):
        dr = dr + '리'

    parts = [p for p in [sido, sgg, emd, dr] if p]
    return ' '.join(parts)


def parse_csv():
    fires = []

    with open(INPUT_CSV, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            sgg = (row.get('발생장소_시군구') or '').strip()
            if '화성' not in sgg:
                continue

            year  = (row.get('발생일시_년') or '').strip()
            month = (row.get('발생일시_월') or '').strip()
            day   = (row.get('발생일시_일') or '').strip()
            time_ = (row.get('발생일시_시간') or '').strip()

            try:
                dmge = float(row.get('피해면적_합계', 0) or 0)
            except ValueError:
                dmge = 0

            cause = (row.get('발생원인_구분') or '').strip()
            cause_detail = (row.get('발생원인_세부원인') or '').strip()

            date = f'{year}-{month.zfill(2)}-{day.zfill(2)}' if year else ''

            fires.append({
                'address':      build_address(row),
                'name':         f'화성시 {(row.get("발생장소_읍면") or "").strip()} 산불 이력',
                'dmge':         dmge,
                'cause':        cause,
                'cause_detail': cause_detail,
                'date':         date,
                'time':         time_,
            })

    return fires


def main():
    if not os.path.exists(INPUT_CSV):
        print(f'[ERROR] CSV 없음: {INPUT_CSV}')
        return

    print(f'[READ] {INPUT_CSV}')
    fires_raw = parse_csv()
    print(f'[FILTER] 화성시 산불 {len(fires_raw)}건')

    if not fires_raw:
        return

    year_count = {}
    for f in fires_raw:
        y = f['date'][:4] if f['date'] else 'unknown'
        year_count[y] = year_count.get(y, 0) + 1
    print(f'[STATS] 연도별: {dict(sorted(year_count.items()))}')

    print(f'\n[GEOCODE] {len(fires_raw)}건 좌표 변환 시작')
    cache = load_cache()

    result = []
    success = 0
    for i, f in enumerate(fires_raw, 1):
        coords = geocode(f['address'], cache)
        if not coords:
            print(f'  [{i}/{len(fires_raw)}] [SKIP] {f["address"]}')
            continue

        lat, lng = coords
        result.append({
            'lat':          lat,
            'lng':          lng,
            'dmge':         f['dmge'],
            'date':         f['date'],
            'time':         f['time'],
            'name':         f['name'],
            'cause':        f['cause'],
            'cause_detail': f['cause_detail'],
            'source':       '산림청 산불통계데이터(CSV)',
        })
        success += 1
        print(f'  [{i}/{len(fires_raw)}] [OK]   {f["address"]}')

    save_cache(cache)

    output = {
        'updated': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'count':   len(result),
        'fires':   result,
    }

    os.makedirs('data', exist_ok=True)
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f'\n[RESULT] 성공: {success}/{len(fires_raw)} ({success/len(fires_raw)*100:.1f}%)')
    print(f'[SAVE] {OUTPUT}')


if __name__ == '__main__':
    main()
