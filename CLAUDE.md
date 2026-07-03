# CLAUDE.md — 작업 맥락 (Claude must read)

이 문서는 이 저장소에서 작업하는 Claude(및 개발자)가 반드시 알아야 할 맥락 전부다.
README는 사용자용으로 의도적으로 짧다. 상세는 여기에만 쓴다.

## 프로젝트 한 줄

서울 버스 실시간 도착을 보여주는 윈도우용 플로팅 위젯. 지금은 HTML 프로토타입, 최종 목표는 Electron/Tauri 네이티브(항상 위) 앱.

## 사용자(발주자)의 불변 요구사항 — 위반 금지

1. **실 API 데이터만.** Mock/가짜 데이터 절대 금지. (proxy.py는 실데이터를 그대로 중계하는 CORS 우회일 뿐 — 가짜 아님)
2. **버스 1대 · 정류장 1개만** 등록 가능. 새로 등록하면 기존 것 대체.
3. **사용자 설정은 딱 5가지**: 시간대(+요일), 버스, 정류장, 이동시간(분), 버스 아이콘.
   연결 모드·프록시·서비스 키·사용량·시나리오 탭·도움말은 **개발자 전용**.
4. **라이트 미니멀 디자인** (다크 금지). 테두리 없는 흰 카드. 단, 게이지에 **정거장 눈금(원)** 필수 — "몇 정거장 남았고 얼마나 왔는지"가 핵심.
5. **배포는 GitHub Pages 링크로.** 사용자는 링크로만 확인한다. 수정 완료 시마다 main에 머지해 자동 배포되게 할 것.
6. README는 두괄식으로 링크+핵심만 짧게. 상세는 이 파일에.
7. 일일 트래픽 한도(1,000회/일)를 넘지 않는 폴링 설계 유지.

## 파일 구조

| 파일 | 역할 |
|---|---|
| `app.html` | 위젯 본체 (단일 파일: CSS+JS 인라인). **DEV 마커 규약** 참고 |
| `proxy.py` | CORS 우회 중계기. 표준 라이브러리만, `ws.bus.go.kr` 화이트리스트, 127.0.0.1:8787, 3xx 차단, 로그에서 키 리댁션 |
| `.github/workflows/pages.yml` | main 푸시 시 GitHub Pages 자동 배포 |
| `index.html`, `designs.html` | 초기 랜딩/디자인 탐색 기록 (다크 시절 유물. 배포에 안 쓰임) |

## DEV 마커 규약 (중요)

`app.html` 안의 개발자 전용 요소는 전부 `<!-- DEV:START -->` … `<!-- DEV:END -->`로 감싼다.
- **배포 빌드**(pages.yml): `index.html` = DEV 블록 제거(사용자용), `dev.html` = 원본 그대로(개발자용).
- JS는 DEV 요소가 없어도 동작해야 한다 — `$("input-mode")` 등은 존재 여부 가드 필수.
- 현재 DEV 블록 4개: 헤더 도움말 버튼, 설정의 "개발자 · 연결" 섹션, 도움말 페이지, 하단 시나리오 탭.

## 배포

- `main` 푸시 → `pages.yml` → https://hansy-daangn.github.io/BusTime/ (사용자), `/dev.html` (개발자).
- 워크플로가 `actions/configure-pages@v4 (enablement: true)`로 Pages를 자동 활성화한다.
- **수정 완료 시마다 브랜치 → PR → main 머지까지가 한 사이클.** 사용자는 위 링크로만 확인한다.

## API 이중 백엔드 (2026-07-03 확장)

앱은 **두 백엔드를 병렬로 사용**한다. 검색은 서울+선택 도시를 동시에 조회해 병합 (`searchRoutesAll`),
watch에 `src: "seoul"|"tago"` 저장, 도착 조회·파서도 src별 분기.

### SEOUL (ws.bus.go.kr/api/rest) — 서울 면허 노선용
- 노선검색 `busRouteInfo/getBusRouteList?strSrch=` / 정류장 `busRouteInfo/getStaionByRoute?busRouteId=` / 도착 `arrive/getArrInfoByRoute?stId=&busRouteId=&ord=`
- `resultType=json`. 응답 `msgHeader.headerCd("0")`, `msgBody.itemList`.
- 도착은 item 하나에 1·2번째 버스(traTime1/2, arrmsg1/2 "[N번째 전]" 파싱, isArrive/isLast).
- **키 상태: 아직 SERVICE KEY IS NOT REGISTERED** — 서울특별시_버스도착정보조회 활용신청의 인증모듈 전파 대기(수 시간 걸릴 수 있음). 승인 전파되면 코드 수정 없이 작동.

### TAGO (apis.data.go.kr/1613000) — 인천·경기 (9802 등)

| 용도 | 엔드포인트 | 비고 |
|---|---|---|
| 노선 검색 | `BusRouteInfoInqireService/getRouteNoList?cityCode=&routeNo=` | **활용신청 필요(미승인 시 403)** |
| 경유 정류소 | `BusRouteInfoInqireService/getRouteAcctoThrghSttnList?cityCode=&routeId=` | `nodeid/nodenm/nodeord/gpslati` |
| 도착 정보 | `ArvlInfoInqireService/getSttnAcctoSpcifyRouteBusArvlPrearngeInfoList?cityCode=&nodeId=&routeId=` | **승인·인증 확인 완료.** `arrtime`(초), `arrprevstationcnt`(남은 정거장 숫자!) |

- `_type=json`. 응답: `response.header.resultCode("00")`, `response.body.items.item` — item이 **단일 객체**이거나 items가 **빈 문자열**일 수 있음(정규화 필수).
- HTTPS 지원 → Pages에서 mixed content 문제 없음. 단 CORS 헤더는 없어서 브라우저 직접 호출은 여전히 차단 → 프록시 폴백.
- 버스 한 대 = item 하나. 도착 임박(≤30초)을 arriving으로 간주. 빈 목록 = "도착 예정 없음".
- TAGO는 **서울시 미포함** — 도시 목록 상수 `CITY_CODES`(인천 23 + 경기 주요). 서울 면허 노선이 필요해지면 서울시 API 키 별도 발급.

## 서비스 키 (JS 상수)

- **기본** `BUILTIN_SERVICE_KEY` (공공데이터포털 103d…): **국토교통부_(TAGO)_버스도착정보 승인·인증 실측 확인**(2026-07-03, resultCode 00). 1,000회/일.
  - 노선·정류소 검색은 **국토교통부_(TAGO)_버스노선정보 / 버스정류소정보** 활용신청(자동승인)이 추가로 필요 — 미승인 시 403 → 앱이 "미승인 API — 활용신청 필요"로 안내.
- **보조** `BUILTIN_BACKUP_KEY` (415a…): ws.bus.go.kr 기준 무효 판명. 자리만 유지.
- 호출 순서: (직접 or 프록시) × (기본 → 보조). 네트워크 오류(TypeError)는 키 교체 없이 다음 경로로.

## 트래픽 설계 (변경 시 재계산 필수)

- 가정: **4명이 키 1개 공유 × 1노선 × 일 4시간** 사용.
- 폴링 상수 `POLL = { near: 60, mid: 120, far: 240 }` (초).
  기준: 도착·출발(도보 차감) 3분 이내 near / 12분 이내 mid / 그 외 far.
- 결과: 일 ~600회 (한도의 60%). 화면은 로컬 카운트다운(매초)이라 폴링이 느슨해도 끊겨 보이지 않는다.
- 사용량 카운터가 localStorage에 쌓이고 개발자 빌드 상태바에만 표시.

## 실 API 검증 결과 2차 (2026-07-03) — TAGO 전환 근거

- ✅ **TAGO 도착정보 인증 성공**: `ArvlInfoInqireService` 호출 → `resultCode 00 NORMAL SERVICE` (apis.data.go.kr는 HTTPS라 샌드박스에서 직접 실측).
- ❌ TAGO 버스노선정보/버스정류소정보 → HTTP 403 Forbidden (활용신청 안 된 상태).
- ❌ 서울시 계열(ws.bus.go.kr)은 이 키로 전부 "SERVICE KEY IS NOT REGISTERED" — 키는 TAGO 전용.
- 사용자 계정 승인 화면 확인: 국토교통부_(TAGO)_버스도착정보, End Point `https://apis.data.go.kr/1613000/ArvlInfoInqireService`, 활용기간 2026-07-03~.
- 9802·논현역 자동 확정(resolveWatch)은 노선정보 서비스 승인 후 첫 조회 때 이뤄짐. 인천 논현동 동명 정류장과의 혼동은 `hintLat`(서울 논현역 37.5112) 최근접 매칭으로 방지 — 스텁 검증 완료.

## 실 API 검증 결과 1차 (2026-07-02, r.jina.ai 릴레이 실측 — 서울 API 시절)

- ✅ `ws.bus.go.kr` 응답 확인. `resultType=json` 동작 (data.go.kr 문서엔 XML만 표기돼 있지만 백엔드는 JSON 지원 — 오류 응답도 JSON으로 수신됨).
- ✅ 응답 스키마 = 코드 기대와 일치 (`msgHeader.headerCd/headerMsg`, `msgBody.itemList`). headerCd ≠ "0" 오류 경로 실동작 확인.
- ✅ URL 경로는 대소문자 구분 (`busRouteInfo` 소문자로 치면 404).
- ❌ **기본 키(103d…) 인증 실패** — "SERVICE KEY IS NOT REGISTERED ERROR (에러코드 30)". 승인 목록·서비스 일치는 문서로 확인(서울특별시_버스도착정보조회, 15000314). 발급 직후 인증모듈 전파 지연(수십 분~수 시간)일 가능성이 높음 → 시간 두고 재시도.
- ❌ **보조 키(415a…) 무효** — 동일 에러. 재발급 필요.
- ❌ **노선 검색(busRouteInfo/*)은 별도 서비스**(서울특별시_버스노선정보조회) → 기본 키 승인 범위 밖. data.go.kr에서 추가 활용신청(자동승인) 해야 자동완성·resolveWatch가 작동함.
- ⚠️ **9802는 서울 면허가 아님** — 인천 광역버스(연수·송도↔강남, 논현역~양재 경유; 인천시청 공지로 확인). 경기 수원행 9802도 별개로 존재(GBIS 241005300). 서울시 API 노선 DB에 없으므로 현 구조로는 기본값(9802·논현역) 해석 불가 → 국토부 TAGO 또는 인천 BIS 연동 필요하거나 기본 노선을 서울 면허로 교체해야 함.

## 알려진 제약

- **HTTPS 페이지(Pages)에서 API 직접 호출은 mixed content로 차단** (API가 http) → auto 모드가 로컬 proxy.py(http://localhost:8787)로 폴백. localhost는 브라우저가 secure context로 취급해 허용됨. 즉 Pages에서 실데이터를 보려면 각자 PC에서 `python proxy.py` 실행 필요. Electron 단계에서 이 제약 소멸.
- 서울시 면허 노선만 검색됨. 9802가 경기 면허면 GBIS API 추가 필요 (아직 미확인 — 로컬 실행으로 확인할 것).
- 기본 등록(9802·논현역)은 `pending: true` 상태로 시작 → 첫 조회 때 실 API로 busRouteId/stId/ord 자동 확정(`resolveWatch`). 샌드박스에서 실 ID를 박을 수 없었기 때문.

## 검증 방법 (수정 시 최소한)

```bash
# JS 문법 (전체 + DEV 제거 빌드)
node -e "const fs=require('fs');const h=fs.readFileSync('app.html','utf8');
for(const v of [h, h.replace(/<!-- DEV:START -->[\s\S]*?<!-- DEV:END -->/g,'')])
  new Function(v.match(/<script>([\s\S]*?)<\/script>/)[1]);
console.log('OK')"
# 프록시
python3 -c "import ast; ast.parse(open('proxy.py').read())"
```
- normalizeConfig/gaugeProgress 같은 순수 로직은 스텁 eval로 단위 검증해온 전례 있음 (git log 참고).

## 히스토리 요약

다크 Aurora Minimal → (사용자 피드백) → 라이트 미니멀 + 정거장 눈금, 설정 5개로 축소, 단일 버스, 사용자/개발자 분리, Mock 완전 제거, 이중 키, 적응형 폴링. Claude 아티팩트 배포 → GitHub Pages로 전환.

## 다음 단계

- [ ] 로컬 실데이터 검증 (9802 서울 면허 여부 확인)
- [ ] Electron 또는 Tauri 래핑: 항상 위, 트레이, 프록시 불필요(메인 프로세스에서 fetch)
- [ ] 필요 시 팀 공용 릴레이(프록시에 20초 캐시 한 겹)로 다인원 트래픽 통합
