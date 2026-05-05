"""
산림청 산불이력 + NASA FIRMS 데이터 병합 → korea_fires.json
"""

import json
import datetime
import os
import random

OUTPUT = 'data/korea_fires.json'


def load_json(path):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f'[SKIP] {path} 로드 실패: {e}')
        return {'fires': []}


def main():
    forest = load_json('data/forest_fires.json')
    firms  = load_json('data/firms_fires.json')

    forest_fires = forest.get('fires', [])
    firms_fires  = firms.get('fires', [])

    # 중복 좌표 오프셋 처리 (같은 좌표에 겹치지 않도록)
    seen = {}
    for f in forest_fires:
        key = (round(f['lat'], 4), round(f['lng'], 4))
        if key in seen:
            f['lat'] += random.uniform(-0.005, 0.005)
            f['lng'] += random.uniform(-0.005, 0.005)
        seen[key] = True

    # 산림청 이력 + NASA FIRMS 합산 (산림청 먼저 — 이력 데이터 우선)
    merged = forest_fires + firms_fires

    print(f'[MERGE] 산림청: {len(forest_fires)}건 + NASA FIRMS: {len(firms_fires)}건 = {len(merged)}건')

    output = {
        'updated': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'count':   len(merged),
        'fires':   merged,
    }

    os.makedirs('data', exist_ok=True)
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f'[SAVE] {OUTPUT} 저장 완료')


if __name__ == '__main__':
    main()
