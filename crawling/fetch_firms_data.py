"""
NASA FIRMS VIIRS 위성 화점 데이터 수집 스크립트
한반도 영역 (bbox: 124,33,130,39) 기준 최근 7일치 수집
"""

import os
import json
import requests
import datetime

API_KEY   = os.environ.get('FIRMS_API_KEY', '')
BBOX      = '124,33,130,39'   # W,S,E,N (한반도 전체)
DAY_RANGE = 7                  # 최근 N일
SOURCE    = 'VIIRS_SNPP_NRT'
OUTPUT    = 'data/korea_fires.json'


def fetch_firms():
    if not API_KEY:
        print('[SKIP] FIRMS_API_KEY 환경변수가 없습니다.')
        return []

    url = (
        f'https://firms.modaps.eosdis.nasa.gov/api/area/csv'
        f'/{API_KEY}/{SOURCE}/{BBOX}/{DAY_RANGE}'
    )
    print(f'[FETCH] {url}')

    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        print(f'[ERROR] 요청 실패: {e}')
        return []

    lines = resp.text.strip().split('\n')
    if len(lines) < 2:
        print('[INFO] 화점 데이터 없음 (응답 행 부족)')
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

            # FRP(MW) → 위험도 0~1 정규화 (100MW 기준 cap)
            risk = min(frp / 100.0, 1.0)
            if confidence == 'high':
                risk = min(risk * 1.2, 1.0)
            elif confidence == 'low':
                risk *= 0.8
            risk = max(round(risk, 3), 0.1)  # 최소 0.1

            fires.append({
                'lat':        lat,
                'lng':        lng,
                'frp':        frp,
                'risk':       risk,
                'confidence': confidence,
                'date':       acq_date,
                'name':       f'위성감지 화점 ({acq_date})',
                'source':     'NASA FIRMS',
            })
        except (ValueError, KeyError):
            continue

    print(f'[OK] 화점 {len(fires)}건 파싱 완료')
    return fires


def main():
    fires = fetch_firms()

    output = {
        'updated': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'count':   len(fires),
        'fires':   fires,
    }

    os.makedirs('data', exist_ok=True)
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f'[SAVE] {OUTPUT} 저장 완료 ({len(fires)}건)')


if __name__ == '__main__':
    main()
