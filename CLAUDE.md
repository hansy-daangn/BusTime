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

## API (서울시, ws.bus.go.kr/api/rest)

| 용도 | 엔드포인트 | 비고 |
|---|---|---|
| 노선 검색 | `busRouteInfo/getBusRouteList?strSrch=` | 자동완성 |
| 노선 정류장 | `busRouteInfo/getStaionByRoute?busRouteId=` | 오타(Staion)가 공식 스펙. 정류장 ID 필드는 `station` |
| 도착 정보 | `arrive/getArrInfoByRoute?stId=&busRouteId=&ord=` | 핵심. `traTime1`(초), `arrmsg1`("3분30초후[2번째 전]"), `isArrive1`, `isLast1` |

- `resultType=json` 파라미터로 JSON 응답.
- 키 오류 시 data.go.kr 게이트웨이가 **XML**을 반환 → `res.json()` throw → 다음 키로 폴백하는 구조.
- `arrmsg`의 `[N번째 전]`에서 남은 정거장 파싱. "곧 도착", "출발 대기", "운행 종료"는 special 상태.

## 서비스 키 (2개 내장, JS 상수)

- **기본** `BUILTIN_SERVICE_KEY` (공공데이터포털): 도착정보 4기능 승인, **기능당 1,000회/일**.
  노선/정류장 검색은 미승인일 수 있음 → 실패 시 자동으로 보조 키 사용.
- **보조** `BUILTIN_BACKUP_KEY` (서울 열린데이터광장): 전 기능 폴백.
- 호출 순서: (직접 or 프록시) × (기본 → 보조). 네트워크 오류(TypeError)는 키 교체 없이 다음 경로로.

## 트래픽 설계 (변경 시 재계산 필수)

- 가정: **4명이 키 1개 공유 × 1노선 × 일 4시간** 사용.
- 폴링 상수 `POLL = { near: 60, mid: 120, far: 240 }` (초).
  기준: 도착·출발(도보 차감) 3분 이내 near / 12분 이내 mid / 그 외 far.
- 결과: 일 ~600회 (한도의 60%). 화면은 로컬 카운트다운(매초)이라 폴링이 느슨해도 끊겨 보이지 않는다.
- 사용량 카운터가 localStorage에 쌓이고 개발자 빌드 상태바에만 표시.

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
