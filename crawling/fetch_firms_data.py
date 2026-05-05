"""
NASA FIRMS VIIRS 위성 화점 데이터 수집 스크립트
1순위: Country API (KOR)
2순위: Area API (bbox)
"""

import os
import json
import requests
import datetime

API_KEY   = os.environ.get('FIRMS_API_KEY', '')
DAY_RANGE = 7
OUTPUT    = 'data/korea_fires.json'

SOURCES = ['VIIRS_SNPP_NRT', 'VIIRS_NOAA20_NRT', 'MODIS_NRT']


def validate_key():
    """API 키 유효성 확인"""
    url = f'https://firms.modaps.eosdis.nasa.gov/mapserver/mapkey_status/?MAP_KEY={API_KEY}'
    try:
        resp = requests.get(url, timeout=10)
        text = resp.text.strip()
        print(f'[KEY] 상태: {text[:100]}')
        return 'Not valid' not in text and resp.status_code == 200
    except Exception as e:
        print(f'[KEY] 확인 실패: {e}')
        return True  # 확인 안 되면 일단 시도


def fetch_by_country(source):
    """Country API: KOR"""
    url = f'https://firms.modaps.eosdis.nasa.gov/api/country/csv/{API_KEY}/{source}/KOR/{DAY_RANGE}'
    print(f'[FETCH Country] {source}')
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def fetch_by_area(source):
    """Area API: 한반도 bbox"""
    bbox = '124,33,130,39'
    url = f'https://firms.modaps.eosdis.nasa.gov/api/area/csv/{API_KEY}/{source}/{bbox}/{DAY_RANGE}'
    print(f'[FETCH Area] {source}')
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def parse_csv(text):
    lines = text.strip().split('\n')
    if len(lines) < 2:
        return []

    headers = [h.strip() for h in lines[0].split(',')]
    fires = []

    for line in lines[1:]:
        vals = line.split(',')
        if len(vals) < len(headers):
            continue
        row = dict(zip(headers, vals))
        try:
            lat        = float(row['latitude'])
            lng        = float(row['longitude'])
            frp        = float(row.get('frp', 0))
            confidence = row.get('confidence', 'nominal').strip()
            acq_date   = row.get('acq_date', '').strip()

            risk = min(frp / 100.0, 1.0)
            if confidence == 'high':
                risk = min(risk * 1.2, 1.0)
            elif confidence == 'low':
                risk *= 0.8
            risk = max(round(risk, 3), 0.1)

            fires.append({
                'lat': lat, 'lng': lng,
                'frp': frp, 'risk': risk,
                'confidence': confidence,
                'date': acq_date,
                'name': f'위성감지 화점 ({acq_date})',
                'source': 'NASA FIRMS',
            })
        except (ValueError, KeyError):
            continue

    return fires


def fetch_firms():
    if not API_KEY:
        print('[SKIP] FIRMS_API_KEY 없음')
        return []

    if not validate_key():
        print('[ERROR] API 키가 유효하지 않습니다. FIRMS 사이트에서 키를 확인하세요.')
        return []

    for source in SOURCES:
        # 1순위: Country API
        try:
            text = fetch_by_country(source)
            fires = parse_csv(text)
            print(f'[OK] Country/{source}: {len(fires)}건')
            if fires or len(text.strip().split('\n')) >= 1:
                return fires
        except Exception as e:
            print(f'[WARN] Country/{source} 실패: {e}')

        # 2순위: Area API
        try:
            text = fetch_by_area(source)
            fires = parse_csv(text)
            print(f'[OK] Area/{source}: {len(fires)}건')
            return fires
        except Exception as e:
            print(f'[WARN] Area/{source} 실패: {e}')

    print('[ERROR] 모든 소스 실패')
    return []


def main():
    fires = fetch_firms()

    output = {
        'updated': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'count': len(fires),
        'fires': fires,
    }

    os.makedirs('data', exist_ok=True)
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f'[SAVE] {len(fires)}건 저장 완료 → {OUTPUT}')


if __name__ == '__main__':
    main()
