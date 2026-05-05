"""
NASA FIRMS VIIRS 위성 화점 데이터 수집 스크립트
인증 없이 접근 가능한 공개 CSV 파일 사용 (전체 글로벌 → 한반도 필터)
"""

import json
import requests
import datetime
import os

OUTPUT = 'data/korea_fires.json'

# 한반도 bbox
LAT_MIN, LAT_MAX = 33.0, 39.0
LNG_MIN, LNG_MAX = 124.0, 130.0

# NASA FIRMS 공개 CSV (인증 불필요, 7일치)
PUBLIC_SOURCES = [
    # VIIRS SNPP (가장 신뢰도 높음)
    'https://firms.modaps.eosdis.nasa.gov/data/active_fire/suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_Global_7d.csv',
    # VIIRS NOAA-20 (백업)
    'https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-20-viirs-c2/csv/J1_VIIRS_C2_Global_7d.csv',
    # MODIS (백업)
    'https://firms.modaps.eosdis.nasa.gov/data/active_fire/c6.1/csv/MODIS_C6_1_Global_7d.csv',
]


def fetch_and_filter(url):
    print(f'[FETCH] {url}')
    resp = requests.get(url, timeout=60, stream=True)
    resp.raise_for_status()

    lines = resp.text.strip().split('\n')
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
            lat = float(row['latitude'])
            lng = float(row['longitude'])

            # 한반도 bbox 필터
            if not (LAT_MIN <= lat <= LAT_MAX and LNG_MIN <= lng <= LNG_MAX):
                continue

            frp        = float(row.get('frp', 0))
            confidence = row.get('confidence', 'nominal').strip()
            acq_date   = row.get('acq_date', '').strip()

            # FRP → 위험도 정규화
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


def main():
    fires = []

    for url in PUBLIC_SOURCES:
        try:
            fires = fetch_and_filter(url)
            print(f'[OK] 한반도 화점 {len(fires)}건 파싱 완료')
            break
        except Exception as e:
            print(f'[WARN] 실패: {e}')

    if not fires:
        print('[INFO] 현재 한반도 활성 화점 없음 (정상)')

    output = {
        'updated': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'count': len(fires),
        'fires': fires,
    }

    os.makedirs('data', exist_ok=True)
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f'[SAVE] {OUTPUT} 저장 완료 ({len(fires)}건)')


if __name__ == '__main__':
    main()
