// 화성시 경계 bbox
const HWASEONG_BOUNDS = { minLat: 37.05, maxLat: 37.35, minLng: 126.65, maxLng: 127.12 };

function inHwaseong(lat, lng) {
  return lat  >= HWASEONG_BOUNDS.minLat && lat  <= HWASEONG_BOUNDS.maxLat
      && lng >= HWASEONG_BOUNDS.minLng && lng <= HWASEONG_BOUNDS.maxLng;
}

// ── 전역 핫스팟 (NASA FIRMS 실데이터만) ──────────────────────────────
let HOTSPOTS = [];

// ── 지도 초기화 ──────────────────────────────────────────────────────
const map = L.map('map', { zoomControl: true }).setView([37.1996, 126.8312], 11);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '© OpenStreetMap contributors',
  maxZoom: 18,
}).addTo(map);

// ── 레이어 ────────────────────────────────────────────────────────────
let heatLayer  = null;
const markerLayer = L.layerGroup().addTo(map);
const routeLayer  = L.layerGroup().addTo(map);

// ── 상태 변수 ────────────────────────────────────────────────────────
let startMarker  = null;
let pickingStart = false;

// ── UI 요소 ──────────────────────────────────────────────────────────
const riskSlider   = document.getElementById('riskThreshold');
const topNSlider   = document.getElementById('topN');
const riskVal      = document.getElementById('riskVal');
const topNVal      = document.getElementById('topNVal');
const btnPickStart = document.getElementById('btnPickStart');
const btnRoute     = document.getElementById('btnRoute');
const btnReset     = document.getElementById('btnReset');
const routeInfo    = document.getElementById('routeInfo');
const dataStatus   = document.getElementById('dataStatus');

riskSlider.addEventListener('input', () => { riskVal.textContent = riskSlider.value; });
topNSlider.addEventListener('input', () => { topNVal.textContent = topNSlider.value; });

// ── NASA FIRMS 데이터 로드 ────────────────────────────────────────────
async function loadFirmsData() {
  try {
    const res  = await fetch('./data/korea_fires.json');
    const json = await res.json();

    if (json.fires && json.fires.length > 0) {
      HOTSPOTS = json.fires.filter(f => inHwaseong(f.lat, f.lng));

      const updatedKST = json.updated
        ? new Date(json.updated).toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' })
        : '-';

      dataStatus.innerHTML =
        `🛰 NASA FIRMS 실시간 데이터 | 화성시 화점 ${HOTSPOTS.length}건<br>`
        + `<small>갱신: ${updatedKST}</small>`;
      dataStatus.className = 'data-status live';
    } else {
      HOTSPOTS = [];
      dataStatus.innerHTML = '📡 현재 화성시 활성 화점 없음';
      dataStatus.className = 'data-status fallback';
    }
  } catch {
    HOTSPOTS = [];
    dataStatus.innerHTML = '⚠ 데이터 로드 실패';
    dataStatus.className = 'data-status fallback';
  }

  renderMap();
}

// ── 지도 렌더링 ───────────────────────────────────────────────────────
function getRiskColor(risk) {
  if (risk >= 0.8) return '#ff1a1a';
  if (risk >= 0.6) return '#ff8c00';
  if (risk >= 0.4) return '#ffd700';
  return '#90ee90';
}

function renderMap() {
  markerLayer.clearLayers();
  if (heatLayer) map.removeLayer(heatLayer);

  // 히트맵
  const heatData = HOTSPOTS.map(h => [h.lat, h.lng, h.risk]);
  heatLayer = L.heatLayer(heatData, {
    radius: 35, blur: 25, maxZoom: 13, max: 1.0,
    gradient: { 0.3: '#00ff00', 0.5: '#ffff00', 0.7: '#ff8c00', 1.0: '#ff0000' },
  }).addTo(map);

  // 마커
  HOTSPOTS.forEach(h => {
    const color   = getRiskColor(h.risk);
    const isFirms = h.source === 'NASA FIRMS';
    const icon = L.divIcon({
      className: '',
      html: `<div style="
        width:${isFirms ? 16 : 13}px; height:${isFirms ? 16 : 13}px;
        border-radius:50%; background:${color};
        border:${isFirms ? '2px solid #fff' : '1px solid rgba(255,255,255,0.6)'};
        box-shadow:0 0 ${isFirms ? 8 : 5}px ${color};
      "></div>`,
      iconSize: [16, 16], iconAnchor: [8, 8],
    });
    L.marker([h.lat, h.lng], { icon })
      .bindPopup(`
        <div class="popup-title">${h.name}</div>
        <div class="popup-risk">위험도: <b style="color:${color}">${(h.risk * 100).toFixed(0)}%</b></div>
        ${isFirms ? `<div class="popup-risk">FRP: <b>${h.frp} MW</b> | 신뢰도: ${h.confidence}</div>` : ''}
        <div class="popup-risk">출처: ${h.source}${h.date ? ' | ' + h.date : ''}</div>
      `)
      .addTo(markerLayer);
  });
}

// ── 출발지 클릭 선택 ─────────────────────────────────────────────────
btnPickStart.addEventListener('click', () => {
  pickingStart = !pickingStart;
  btnPickStart.classList.toggle('active', pickingStart);
  btnPickStart.textContent = pickingStart ? '🖱 지도를 클릭하세요...' : '🖱 지도에서 클릭으로 선택';
  map.getContainer().style.cursor = pickingStart ? 'crosshair' : '';
});

map.on('click', (e) => {
  if (!pickingStart) return;
  const { lat, lng } = e.latlng;
  document.getElementById('startLat').value = lat.toFixed(4);
  document.getElementById('startLng').value = lng.toFixed(4);
  setStartMarker(lat, lng);
  pickingStart = false;
  btnPickStart.classList.remove('active');
  btnPickStart.textContent = '🖱 지도에서 클릭으로 선택';
  map.getContainer().style.cursor = '';
});

function setStartMarker(lat, lng) {
  if (startMarker) map.removeLayer(startMarker);
  const icon = L.divIcon({
    className: '',
    html: `<div style="
      width:20px; height:20px; border-radius:50%;
      background:#58a6ff; border:3px solid #fff;
      box-shadow:0 0 10px #58a6ff;
    "></div>`,
    iconSize: [20, 20], iconAnchor: [10, 10],
  });
  startMarker = L.marker([lat, lng], { icon })
    .bindPopup('<b style="color:#58a6ff">📍 출발 위치</b>')
    .addTo(map);
}

// ── Haversine 거리 (km) ───────────────────────────────────────────────
function haversine(a, b) {
  const R    = 6371;
  const dLat = (b.lat - a.lat) * Math.PI / 180;
  const dLng = (b.lng - a.lng) * Math.PI / 180;
  const sin2 = Math.sin(dLat / 2) ** 2
    + Math.cos(a.lat * Math.PI / 180) * Math.cos(b.lat * Math.PI / 180)
    * Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.asin(Math.sqrt(sin2));
}

// ── Nearest Neighbor TSP ─────────────────────────────────────────────
function nearestNeighborTSP(start, points) {
  const unvisited = [...points];
  const route = [];
  let current = start;
  while (unvisited.length > 0) {
    let nearestIdx = 0, nearestDist = Infinity;
    unvisited.forEach((p, i) => {
      const d = haversine(current, p);
      if (d < nearestDist) { nearestDist = d; nearestIdx = i; }
    });
    route.push(unvisited.splice(nearestIdx, 1)[0]);
    current = route[route.length - 1];
  }
  return route;
}

// ── 경로 계산 ────────────────────────────────────────────────────────
btnRoute.addEventListener('click', () => {
  const lat = parseFloat(document.getElementById('startLat').value);
  const lng = parseFloat(document.getElementById('startLng').value);

  if (isNaN(lat) || isNaN(lng)) {
    alert('출발 위치를 입력하거나 지도에서 선택해 주세요.');
    return;
  }

  setStartMarker(lat, lng);

  const threshold = parseFloat(riskSlider.value);
  const topN      = parseInt(topNSlider.value);

  const candidates = HOTSPOTS
    .filter(h => h.risk >= threshold)
    .sort((a, b) => b.risk - a.risk)
    .slice(0, topN);

  if (candidates.length === 0) {
    alert('해당 위험도 기준의 지점이 없습니다.\n기준값을 낮춰보세요.');
    return;
  }

  const start = { lat, lng };
  const route = nearestNeighborTSP(start, candidates);

  routeLayer.clearLayers();

  const coords = [[lat, lng], ...route.map(p => [p.lat, p.lng])];
  L.polyline(coords, {
    color: '#58a6ff', weight: 3, opacity: 0.85, dashArray: '8, 6',
  }).addTo(routeLayer);

  route.forEach((p, i) => {
    const icon = L.divIcon({
      className: '',
      html: `<div style="
        width:24px; height:24px; border-radius:50%;
        background:${getRiskColor(p.risk)}; border:2px solid #fff;
        display:flex; align-items:center; justify-content:center;
        font-size:0.7rem; font-weight:700; color:#fff;
        box-shadow:0 2px 6px rgba(0,0,0,0.5);
      ">${i + 1}</div>`,
      iconSize: [24, 24], iconAnchor: [12, 12],
    });
    L.marker([p.lat, p.lng], { icon })
      .bindPopup(`
        <div class="popup-title">${i + 1}번째: ${p.name}</div>
        <div class="popup-risk">위험도: <b style="color:${getRiskColor(p.risk)}">${(p.risk * 100).toFixed(0)}%</b></div>
        <div class="popup-risk">출처: ${p.source}</div>
      `)
      .addTo(routeLayer);
  });

  let totalDist = haversine(start, route[0]);
  for (let i = 0; i < route.length - 1; i++) totalDist += haversine(route[i], route[i + 1]);

  const avgRisk = route.reduce((s, p) => s + p.risk, 0) / route.length;

  document.getElementById('totalDist').textContent    = totalDist.toFixed(1) + ' km';
  document.getElementById('waypointCount').textContent = route.length + '개';
  document.getElementById('avgRisk').textContent       = (avgRisk * 100).toFixed(0) + '%';

  document.getElementById('waypointList').innerHTML = route.map((p, i) => {
    const rClass = p.risk >= 0.8 ? 'risk-very-high' : p.risk >= 0.6 ? 'risk-high' : 'risk-mid';
    return `
      <div class="waypoint-item">
        <span class="wp-num">${i + 1}</span>
        <span>${p.name}</span>
        <span class="wp-risk ${rClass}">${(p.risk * 100).toFixed(0)}%</span>
      </div>`;
  }).join('');

  routeInfo.style.display = 'block';
  map.fitBounds(L.latLngBounds(coords).pad(0.1));
});

// ── 초기화 ───────────────────────────────────────────────────────────
btnReset.addEventListener('click', () => {
  routeLayer.clearLayers();
  if (startMarker) { map.removeLayer(startMarker); startMarker = null; }
  document.getElementById('startLat').value = '';
  document.getElementById('startLng').value = '';
  routeInfo.style.display = 'none';
  map.setView([37.1996, 126.8312], 11);
});

// ── 초기 로드 ────────────────────────────────────────────────────────
loadFirmsData();
