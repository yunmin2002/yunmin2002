"""
산림청_산불발생통계(대국민포털) API 수집 스크립트
주소 기반 데이터 → Nominatim 지오코딩 → 좌표 변환
"""

import os
import json
import time
import requests
import datetime
import xml.etree.ElementTree as ET

API_KEY   = os.environ.get('FOREST_FIRE_API_KEY', '')
OUTPUT    = 'data/forest_fires.json'
THIS_YEAR = datetime.datetime.now().year
BASE_URL  = 'https://apis.data.go.kr/1400000/forestStusService/getfirestatsservice'

# 지오코딩 캐시 파일
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
    """Nominatim으로 주소 → 좌표 변환 (캐시 활용)"""
    if address in cache:
        return cache[address]

    try:
        resp = requests.get(
            'https://nominatim.openstreetmap.org/search',
            params={'q': address, 'format': 'json', 'limit': 1},
            headers={'User-Agent': 'HwaseongFirePatrol/1.0'},
            timeout=10
        )
        results = resp.json()
        if results:
            lat = float(results[0]['lat'])
            lng = float(results[0]['lon'])
            cache[address] = (lat, lng)
            time.sleep(1.1)  # Nominatim 요청 제한 (1req/sec)
            return lat, lng
    except Exception as e:
        print(f'[GEOCODE ERROR] {address}: {e}')

    cache[address] = None
    return None


def fetch_year(year):
    params = {
        'serviceKey': API_KEY,
        'pageNo':     1,
        'numOfRows':  1000,
        'year':       year,
    }
    resp = requests.get(BASE_URL, params=params, timeout=30)
    resp.raise_for_status()
    return resp.text


def normalize_address(locsi, locgungu, locdong, locbunji):
    """API 필드값을 Nominatim이 인식할 수 있는 주소로 변환"""
    if locsi == '경기':
        locsi = '경기도'

    if locgungu and not locgungu.endswith(('시', '군', '구')):
        locgungu = locgungu + '시'

    if locdong and not locdong.endswith(('동', '읍', '면', '리')):
        locdong = locdong + '동'

    parts = [p for p in [locsi, locgungu, locdong, locbunji] if p]
    return ' '.join(parts)


def parse_hwaseong(xml_text):
    """화성시 데이터만 필터링"""
    fires = []
    try:
        root  = ET.fromstring(xml_text)
        items = root.findall('.//item')

        for item in items:
            locsi    = (item.findtext('locsi')    or '').strip()
            locgungu = (item.findtext('locgungu') or '').strip()

            # 화성시 필터
            if '화성' not in locgungu:
                continue

            locdong  = (item.findtext('locdong')  or '').strip()
            locbunji = (item.findtext('locbunji') or '').strip()
            dmge     = item.findtext('damagearea') or '0'
            cause    = (item.findtext('firecause') or '').strip()
            syear    = (item.findtext('startyear') or '').strip()
            smonth   = (item.findtext('startmonth') or '').strip()
            sday     = (item.findtext('startday') or '').strip()

            date = f'{syear}-{smonth.zfill(2)}-{sday.zfill(2)}' if syear else ''

            fires.append({
                'address': normalize_address(locsi, locgungu, locdong, locbunji),
                'name':    f'화성시 {locdong} 산불 이력',
                'dmge':    float(dmge) if dmge else 0,
                'cause':   cause,
                'date':    date,
            })
    except ET.ParseError as e:
        print(f'[ERROR] XML 파싱 실패: {e}')

    return fires


def main():
    if not API_KEY:
        print('[SKIP] FOREST_FIRE_API_KEY 없음')
        return

    cache = load_cache()
    all_raw = []

    # 최근 5년치 수집
    for year in range(THIS_YEAR - 4, THIS_YEAR + 1):
        try:
            xml_text = fetch_year(year)
            fires    = parse_hwaseong(xml_text)
            all_raw.extend(fires)
            print(f'[OK] {year}년 화성시: {len(fires)}건')
        except Exception as e:
            print(f'[WARN] {year}년 실패: {e}')

    print(f'\n[GEOCODE] 총 {len(all_raw)}건 주소 변환 시작')

    result = []
    for f in all_raw:
        coords = geocode(f['address'], cache)
        if not coords:
            print(f'[SKIP] 좌표 없음: {f["address"]}')
            continue

        lat, lng = coords
        dmge = f['dmge']
        risk = min(dmge / 10.0, 1.0)
        risk = max(round(risk, 3), 0.2)

        result.append({
            'lat':    lat,
            'lng':    lng,
            'risk':   risk,
            'dmge':   dmge,
            'date':   f['date'],
            'name':   f['name'],
            'cause':  f['cause'],
            'source': '산림청 산불발생통계',
        })

    save_cache(cache)
    print(f'[RESULT] 화성시 산불 이력 {len(result)}건 좌표 변환 완료')

    output = {
        'updated': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'count':   len(result),
        'fires':   result,
    }

    os.makedirs('data', exist_ok=True)
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f'[SAVE] {OUTPUT} 저장 완료')


if __name__ == '__main__':
    main()
