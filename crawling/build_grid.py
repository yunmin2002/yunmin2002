"""
화성시 1km × 1km 격자 시스템 생성
산불 위험도 예측의 공간 단위가 되는 격자를 만든다.
출력: data/hwaseong_grid.geojson (Leaflet에서 직접 로드 가능)
"""

import json
import os
import math

# 화성시 bbox (기존 main.js의 HWASEONG_BOUNDS와 동일)
BBOX = {
    'min_lat': 37.05, 'max_lat': 37.35,
    'min_lng': 126.65, 'max_lng': 127.12,
}

CELL_SIZE_KM = 1.0  # 격자 한 변 길이 (km)
OUTPUT = 'data/hwaseong_grid.geojson'


def km_to_deg(km, latitude):
    """km를 위도/경도 degree로 변환 (위도별로 경도 변환계수가 다름)"""
    lat_deg = km / 111.0
    lng_deg = km / (111.0 * math.cos(math.radians(latitude)))
    return lat_deg, lng_deg


def build_grid():
    mid_lat = (BBOX['min_lat'] + BBOX['max_lat']) / 2
    lat_step, lng_step = km_to_deg(CELL_SIZE_KM, mid_lat)

    features = []
    row = 0
    lat = BBOX['min_lat']

    while lat < BBOX['max_lat']:
        col = 0
        lng = BBOX['min_lng']

        while lng < BBOX['max_lng']:
            polygon = [[
                [lng,            lat],
                [lng + lng_step, lat],
                [lng + lng_step, lat + lat_step],
                [lng,            lat + lat_step],
                [lng,            lat],
            ]]

            features.append({
                'type': 'Feature',
                'properties': {
                    'grid_id':    f'g_{row:03d}_{col:03d}',
                    'row':        row,
                    'col':        col,
                    'center_lat': round(lat + lat_step / 2, 6),
                    'center_lng': round(lng + lng_step / 2, 6),
                },
                'geometry': {
                    'type':        'Polygon',
                    'coordinates': polygon,
                },
            })

            col += 1
            lng += lng_step
        row += 1
        lat += lat_step

    geojson = {
        'type': 'FeatureCollection',
        'meta': {
            'cell_size_km': CELL_SIZE_KM,
            'bbox':         BBOX,
            'rows':         row,
            'cols':         col,
            'total_cells':  len(features),
        },
        'features': features,
    }

    os.makedirs('data', exist_ok=True)
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, ensure_ascii=False)

    print(f'[OK] 격자 생성 완료: {len(features)}개 셀 → {OUTPUT}')
    print(f'     {row}행 × {col}열, 셀 크기 {CELL_SIZE_KM}km')


if __name__ == '__main__':
    build_grid()
