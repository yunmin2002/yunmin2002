A simple HTML/JS/CSS starter template

## 산림청 데이터 갱신 (로컬)

1. https://www.data.go.kr 접속
2. "산불통계데이터" 검색
3. 산림청_산불통계데이터 클릭 → CSV 다운로드
4. `data/raw_forest_fires/forest_fires_raw.csv` 로 저장
5. 실행:
   ```
   python crawling/parse_forest_csv.py
   ```
6. 커밋:
   ```
   git add data/forest_fires.json data/geocode_cache.json
   git commit -m "산림청 화성시 산불 이력 갱신"
   git push
   ```