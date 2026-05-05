"""
산림청_산불발생통계(대국민포털) API 수집 스크립트
공공데이터포털 (data.go.kr)
"""

import os
import json
import requests
import datetime
import xml.etree.ElementTree as ET

API_KEY   = os.environ.get('FOREST_FIRE_API_KEY', '')
OUTPUT    = 'data/korea_fires.json'
THIS_YEAR = datetime.datetime.now().year

# 화성시 bbox
LAT_MIN, LAT_MAX = 37.05, 37.35
LNG_MIN, LNG_MAX = 126.65, 127.12

BASE_URL = 'https://apis.data.go.kr/1400119/forestFireInfoService2/getForestFireInfo'


def fetch_fire_data(year):
    params = {
        'serviceKey': API_KEY,
        'pageNo':     1,
        'numOfRows':  1000,
        'year':       year,
    }
    print(f'[FETCH] {year}년 산불 데이터 요청')
    resp = requests.get(BASE_URL, params=params, timeout=30)
    resp.raise_for_status()
    return resp.text


def parse_response(xml_text):
    fires = []
    try:
        root = ET.fromstring(xml_text)

        # 에러 응답 확인
        result_code = root.findtext('.//resultCode') or root.findtext('.//errCode')
        if result_code and result_code not in ('00', '0000', '000'):
            print(f'[WARN] API 응답 코드: {result_code} / {root.findtext(".//resultMsg") or ""}')
            return fires

        items = root.findall('.//item')
        print(f'[PARSE] {len(items)}건 파싱 중')

        for item in items:
            try:
                # 좌표 필드 (API마다 필드명 다를 수 있음)
                lat = float(
                    item.findtext('wgs84_lat') or
                    item.findtext('lat') or
                    item.findtext('latitude') or 0
                )
                lng = float(
                    item.findtext('wgs84_lon') or
                    item.findtext('lon') or
                    item.findtext('longitude') or 0
                )

                if lat == 0 or lng == 0:
                    continue

                # 피해면적 → 위험도 (ha 기준)
                dmge = float(item.findtext('frfr_dmge_ar') or item.findtext('dmgeAr') or 0)
                risk = min(dmge / 10.0, 1.0)   # 10ha 기준 cap
                risk = max(round(risk, 3), 0.2)  # 최소 0.2

                date     = item.findtext('occrrnc_dt') or item.findtext('occrrncDt') or ''
                sigungu  = item.findtext('sigungu_nm') or item.findtext('sigunguNm') or ''
                cause    = item.findtext('frfr_casuse_nm') or item.findtext('frfrCasuseNm') or ''

                fires.append({
                    'lat':    lat,
                    'lng':    lng,
                    'risk':   risk,
                    'dmge':   dmge,
                    'date':   date[:10] if date else '',
                    'name':   f'{sigungu} 산불 이력',
                    'cause':  cause,
                    'source': '산림청 산불발생통계',
                })
            except (ValueError, TypeError):
                continue

    except ET.ParseError as e:
        print(f'[ERROR] XML 파싱 실패: {e}')
        print(f'[DEBUG] 응답 앞부분: {xml_text[:300]}')

    return fires


def filter_hwaseong(fires):
    return [f for f in fires
            if LAT_MIN <= f['lat'] <= LAT_MAX
            and LNG_MIN <= f['lng'] <= LNG_MAX]


def main():
    if not API_KEY:
        print('[SKIP] FOREST_FIRE_API_KEY 없음')
        return

    all_fires = []

    # 최근 5년치 수집
    for year in range(THIS_YEAR - 4, THIS_YEAR + 1):
        try:
            xml_text = fetch_fire_data(year)
            fires    = parse_response(xml_text)
            all_fires.extend(fires)
            print(f'[OK] {year}년: {len(fires)}건')
        except Exception as e:
            print(f'[WARN] {year}년 실패: {e}')

    hwaseong = filter_hwaseong(all_fires)
    print(f'\n[RESULT] 전체: {len(all_fires)}건 / 화성시: {len(hwaseong)}건')

    output = {
        'updated': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'count':   len(hwaseong),
        'fires':   hwaseong,
    }

    os.makedirs('data', exist_ok=True)
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f'[SAVE] {OUTPUT} 저장 완료')


if __name__ == '__main__':
    main()
