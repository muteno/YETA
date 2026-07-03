# 노뮤트 웹UI 공통 규약 (라우터 참조 정본)

> **목적** — comp·ly·k·뉴스 등 메뉴마다 어긋나던 버튼·배치·색·아이콘·정렬·타이포를 한 곳에 못박는다. 라우터/에이전트는 신규·수정 UI를 만들 때 이 문서를 SSOT로 따른다. 매번 디테일을 다시 잡지 않게 하는 것이 목표.
>
> **값 SSOT** = `viewer/index.html` `:root` 토큰 블록 (규칙 정본 = `CLAUDE.md §🎨`·`§📐`). 도구 페이지(comp·ly·k)는 이 토큰을 따르는 것이 곧 "통일".
>
> **사람이 보는 사인오프 버전** = `구성도/*.html` (인터랙티브). 이 MD는 그 확정값을 코드 적용용으로 옮긴 것.
>
> ⚠️ **단일정본 위계 (기틀 · 260621):** ① **값 = `viewer/index.html :root`가 유일 정본** → ② **`base.css` AUTO-MIRROR 블록 = viewer :root *전체 자동거울***(`shared/build_design_mirror.py build`가 :root 통째 복사 — 손 베끼기·"부분거울" 시절 폐지, 직접수정 금지·다음 build에 덮어씀 · 정정 260702) → ③ **이 MD·구성도 HTML = 규칙·시각화**. **충돌나면 viewer가 옳다** — 이 문서를 거기 맞춘다(반대 아님). ⚠️ 이 MD의 hex/px은 대부분 *viewer 추출본(descriptive)*이나, §0 opacity 스케일·일부 §6~8은 *목표(prescriptive)*라 viewer 현 raw값과 다를 수 있음(그건 지향점). 상세 = `CLAUDE.md §🎨`.

---

## 0. 토큰 베이스라인 (도구 페이지가 맞춰야 할 정본)

도구 페이지가 중립 회색 팔레트(`#0b0b0c` 등)를 쓰고 있으면 **아래 warm-green 정본으로 교체**한다.

```css
:root {
  /* 표면 */
  --bg:#0a120d;                      /* 초록빛 블랙 (중립 #0b0b0c 아님) */
  --glass:rgba(38,64,46,.42);
  --glass2:rgba(14,26,18,.55);
  --line:rgba(255,255,255,.08);
  --line2:rgba(255,255,255,.06);
  /* 텍스트 */
  --fg:#eef7f0; --fg-2:#cfd8d0; --mut:#8fa697;
  /* 브랜드/강조 */
  --accent:#0FFD02; --accent-rgb:15,253,2;
  --accent-dim:rgba(15,253,2,.13); --on-accent:#062108;
  /* 의미색 */
  --danger:#ff5b4a; --warn:#ffd24a; --amber:#ff9614; --info:#0cd0f7;
  /* 재확인(arm) */
  --arm:#ffd93d; --arm-rgb:255,217,61; --on-arm:#1a1205;
  /* radius — 4단 (그 외 7·10·20·22 난립 금지). --r:24=배너·큰 패널(viewer 정본 :root에 생존). */
  --r-s:9px; --r-m:11px; --r-l:16px; --r:24px; --r-pill:999px;
  /* 간격 4배수 */
  --sp-1:6px; --sp-2:12px; --sp-3:18px; --sp-4:24px;
  /* 모션 */
  --ease:cubic-bezier(.2,.7,.3,1); --dur-fast:.12s; --dur:.18s;
  /* 상태 타이포 — Orbitron 폐지(운영자 260621)·Pretendard 통일, var(--font-status)는 호환 위해 유지 */
  --font-status:'Pretendard Variable',-apple-system,BlinkMacSystemFont,sans-serif;
}
```

**투명도(accent alpha) 스케일** — 즉흥 10값(.06~.85) 금지. 의미별 7값만:
`glow .06` · `soft .12` · `ring .08` · `line .26` · `focus .35` · `edge .45` · `shine .85`.
※ 기존에 정의만 하고 안 쓰던 `--accent-dim(.13)` 토큰을 실제로 참조해 살릴 것. 인라인 매직넘버 금지.

**토큰 밖 매직 색 → 토큰화**: `#cfd2d7→--fg-2`, `#ff8a8a→--danger(#ff5b4a)`, `#d8ff3d→--accent-bright`(밝은 그린·그라데 끝 — ⚠️ `--accent-2`는 viewer에서 **앰버 #ff9614**(스크랩 테마)라 다름·260621 정정).

---

## 1. 전송 버튼 상태머신 (비용 드는 액션)

러너 발사·카드 합성·Gemini 생성·API 호출 등 **돈/시간이 나가거나 외부 발사되는** 액션은 한 흐름으로 고정.

### 두 축 분리 (중요)
- **A. 확인 게이트** — 짧음·오발사 방지·코스메틱: `대기 → 재확인(arm) → 게이지 .72s → 발사`
- **B. 작업 수명주기** — 긺·async·서버 상태 반영: `Picking…(진행) → PICKED ┊ 일부만 생성됨 ┊ Failed → 소진(잠금)`

> 기존 오류: 확인 게이지(.72s)를 "전송 진행"으로 오표기. 둘은 다른 축. **작업 완료는 원복하지 않는다** — PICKED는 소진(회색·비활성)으로 잠그고 탭하면 해당 피드로 이동. "1.2s 후 원복"은 복사 같은 단순 액션에만.

### 상태별 사양
| 단계 | 색 | 라벨(버튼 안) | 동작 |
|---|---|---|---|
| 대기 idle | `--accent-dim` 글래스, border .4 | "전송"(대기 라벨만 메뉴 동사 가변: 발사/합성/생성) | — |
| 재확인 arm | `--arm` 앰버 | **"재확인"** | 3s 무동작 시 대기 복귀(타임아웃) |
| 전송 firing | 초록 게이지 좌→우 | "전송 중…" | .72s, 클릭 잠금 |
| 진행 Picking | 미결정 shine / 결정형 세그 | **`Picking…`** | aria-busy=true |
| 완료 PICKED | 솔리드 초록 + 체크 pop | **`PICKED`** | 소진 잠금, 탭=피드 |
| 부분 partial | 앰버 세그 | "일부만 생성됨" | 재발사 버튼 노출 |
| 실패 Failed | 노랑 빗금 + 빨강 라벨 | **`Failed`** | 풀폭 칩, 롱프레스→진단/전문입력 |

### 규칙
- 전송 버튼은 **메뉴 대표색을 따르지 않는다** — 비용·위험 신호(초록↔앰버)는 전 메뉴 공통이라야 손이 기억함. 메뉴색은 헤더·아이콘에만.
- **버튼 안 라벨**: 대기 라벨만 메뉴 동사로 가변. **재확인·전송 중·Picking…·PICKED·Failed는 전 메뉴 고정**(viewer 실문자열 = `Picking…`·`Failed` 대소문자 정합·260621).
- **흉터(scar)**: 한 번이라도 깨진 단계는 성공·재시도 후에도 세그에 빨강 표식 영속(`failedOnce`). "과거에 깨진 적 있음" 신뢰 신호.
- 재확인 게이트는 **비용·되돌리기 어려운** 액션에만. 복사·파일선택·미리보기 등 공짜·즉시·되돌리기 쉬운 액션엔 붙이지 말 것(`클릭→즉시 ✓→1.5s 원복`).

### 접근성
- 재확인 타임아웃: `aria-live="polite"` "다시 누르세요" 안내, `prefers-reduced-motion`이면 타임아웃 연장/해제.
- 진행 중: `aria-busy="true"` + 라벨 텍스트 갱신(색만 X).
- Failed: `role="alert"` 또는 live 영역에 실패 사유. 빗금색만으로 의미 전달 금지.
- 모든 상태 칩·버튼 최소 높이 **34px**. Failed 롱프레스 480ms.

---

## 2. 버튼 배치 (정렬·쏠림)

### 1차 CTA
- 파일 입력 있음 → **좌우 한 줄**: `[파일칸 flex:1.4] + [생성 flex:1]`, gap:10px. 세로 풀폭 스택 금지(자리 낭비).
- 파일 입력 없음 → `.go` **풀폭 하단**.
- 컨테이너 안 단독 1차 버튼은 풀폭(좌측 쏠림 금지). 폭을 줄여야 하면 `justify-content:center`. "기본 flow에 그냥 둠" 금지 — 정렬을 항상 명시.

### 정렬 4분류 (성격 = 자리 고정)
| 성격 | 정렬 | 예 |
|---|---|---|
| 1차 액션 | `width:100%` 풀폭 | 생성·전송·합성 |
| 인라인 보조 | `margin-left:auto` 우측 | 복사·수정 |
| 미디어 액션 | `absolute` 우상단 글래스 행 | 저장·확대·재생성 |
| 중앙 단일 | `justify-content:center` | 더보기·페이지네이션 |

### 다운로드·저장 위치
미디어 결과물의 저장·다운로드·확대·재생성 = **미디어 우상단 글래스 `.sbtn` 행** 하나로 통일. 하단 중앙 텍스트 링 폐지. (텍스트 결과 복사는 인라인 보조 = 우측.)

---

## 3. 텍스트 위계 (뉴스요약 #mdbody 정본)

대주제·섹션·소제목·문단·항목을 역할별 1:1 계단으로 고정. 머리표 4계층(`CLAUDE.md §📐`).

| 계단 | 크기/굵기 | 색 | 비고 |
|---|---|---|---|
| 부제/대주제 | 19~18px / 800 | 흰색 | ls −.4, 강조색 X. 복사 영역이면 카드(박스). |
| 섹션 h2 | 15px / 800 | `--accent` | 위 구분선 + pt14 (viewer `--fs-h2`) |
| 소제목 h3 | 14px / 800 | `--accent` | 구분선 없음 (viewer `--fs-h3`) |
| 문단 p | 15px / 400 | `--fg` | line-height 1.65, 완결 산문 |
| 항목 • | 14px | 머리 `--accent` | 들여 16px, 본문보다 1단 작게 |
| 메타/부연 | 11px | `--mut` | 괄호 부연 = 흰색 400 |

- **강조색은 섹션·소제목·항목 머리에만.** 본문 문단·정적 제목·메타엔 칠하지 않는다.
- 역할=계단 건너뛰기/섞기 금지. 시사점은 항상 섹션(h2).

---

## 4. 표면·테두리·강조

### 표면 3단 (테두리·배경 기준)
| 단 | 테두리 | 배경 | 용도 |
|---|---|---|---|
| 평면 flat | X | X | 인라인 텍스트·메타·카테고리 칩(색글자만) |
| 연면 soft | X | O (`rgba(255,255,255,.04)`) | 상태/진행 안내·게이지 트랙 |
| 카드 card | O (`--line`) | O + inset highlight | 카드·코드박스·복사영역·모달·입력칸 |

한 영역은 한 단 기준. 같은 줄에 평면 칩과 카드 칩 혼용 금지.

### 강조색(형광) 절제
accent는 "지금 핵심"을 가리키는 손가락. **화면당 2~3곳 이내.**
- 허용: 섹션·소제목 머리 / 활성 칩 / "지금" 라이브 값(N시간 전·진행 중) / 1차 버튼.
- 금지: 날짜 라벨·글자수·괄호 부연·정적 제목. (IN/WRITE·괄호 부연은 형광 폐지 → 흰색.)

---

## 5. 메뉴별 대표색 = 상단 배너색

새 색 지어내지 않음. 메뉴 = 그 메뉴의 배너 글로우색.

| 메뉴 | 대표색 | 토큰 |
|---|---|---|
| 피드·큐레이션 | 라임 `#0FFD02` | `--accent` |
| 스크랩(레거시) | 앰버 `#ff9614` | `--amber` |
| SNS | 시안 `#0cd0f7` | `--info` |
| 썸네일 생성기 | 노랑 `#ffce54` | (요약요청 초록과 구분) |
| ly·k | 라임(기본) | 별도 색 없음 |

**전파**: 메뉴 진입 시 배너 글로우·프로필 링·배지·활성 칩·입력 focus/hover가 전부 그 한 색. **단, 1차 버튼은 예외 — 항상 라임/앰버 공통 신호(§1).**
**대표색 vs 의미색 겹침**: 앰버·시안은 정체성 색이자 의미색. 의미(경고·오류)는 아이콘·문맥과 함께 써 구분. 단독 색면으로 의미 전달 금지.

---

## 6. 픽토그램

조작 UI 아이콘 = **라인 SVG, 한 규격으로 통일.**
```
fill:none; stroke:currentColor; stroke-width:2; stroke-linecap:round; stroke-linejoin:round; viewBox:0 0 24 24
```
- 색은 버튼이 상속(메뉴 대표색/강조색).
- 크기: `.sbtn 34→15px` · `30→14px` · `xs 22→13px` · 타일/픽토 `20px`. 버튼 크기 토큰에 비례.
- 코어셋: 복사·체크·다운로드·닫기·전송·재생성·확대·검색·파일·생성(spark).
- 메뉴당 대표 픽토그램 1개 + 메뉴 대표색 고정.
- **이모지 정책**: 조작 버튼·아이콘 자리엔 이모지 금지(OS·폰트마다 모양/정렬 깨짐 → 라인 SVG). 이모지는 **콘텐츠 의미 표식만** 허용 — 💡 시사점 · 📊 핵심정리 · 🚨 긴급 · 🍌 생성 안내.

---

## 7. 상태 타이포 — Orbitron 폐지(운영자 260621)·현행 Pretendard 통일

~~영문 상태어·배지 숫자 = Orbitron~~ → **폐지(운영자 260621)**: 상태어·배지 숫자도 **Pretendard로 통일**(정본 주석 = `viewer/index.html:15`·base.css §상태 타이포 동일). `var(--font-status)`는 **호환 위해 유지**하되 이제 Pretendard로 렌더 — Orbitron `@import` 재도입 금지.
```css
/* @import Orbitron — 폐지(260621) · 재도입 금지 */
:root { --font-status:'Pretendard Variable',-apple-system,BlinkMacSystemFont,sans-serif; }
/* 적용 대상: PICK·Picking…·PICKED·PASS·Failed·thumb 상태어, 라벨사전 영문, 버튼 안 숫자(OPA 등) · viewer 실셀렉터 = .sc-got/.sc-fail/.sc-tg/.sc-pick span/.sc-cross/#qbadge/.qb (아래 .stat 등은 구성도 데모 클래스) */
.stat,.ind-bar span,.fail-chip,.picked-chip,.pickbtn,
.sc-got,.sc-tg { font-family:var(--font-status); letter-spacing:.04em; }   /* viewer 실클래스 = .sc-tg(.pass/.down) — 옛 .sc-pass/.sc-down 오기 정정(260621) */
.statnum { font-family:var(--font-status); font-weight:700; letter-spacing:.02em; } /* 얇아 보이는 숫자 교정 */
```
- 버튼 볼드 역할 고정: 1차(`.go·.send·.pickbtn·.mkbtn`) 800 · 보조(`.ctrl·.reset·.sbtn`) 700.

### 진행 인디케이터(PICKING) 매트릭스 코드비 (선택 모티프)
PICKING 미결정 바 배경에 떨어지는 세로 라임 스트림. 추가 DOM 없이 `::before`(라임 유지, reduced-motion이면 정지). 구현 = `구성도/전송 버튼 상태머신.html` `.ind-bar::before` 참조.

---

## 8. 모션 통일
- 모든 transition은 `--ease` + `--dur`(.18s) / `--dur-fast`(.12s) 두 토큰만 참조. 곳곳 `.12s/.15s linear` 난립 금지.
- 누름: `:active { transform:scale(.978); filter:brightness(.94); }` (제자리 복귀만 X).
- disabled: `opacity:.42 + grayscale(.85)` (opacity:.5만으론 "톤다운된 활성"처럼 보임).
- focus-visible: `outline:2px solid var(--accent); outline-offset:3px` (마우스 X, 키보드만).
- 결과 등장: fade + 6~9px riseIn .5s. reduced-motion이면 즉시.
- 복사 ✓ 전환·파일선택 완료엔 pop(scale .4→1.25→1).

---

## 9. 컴포넌트 인벤토리 (계승 = 디폴트 · 정본 = CLAUDE.md §🎨)
신규/이식 시 **그대로 계승**(다시 그리지 말 것). 값·마크업 정본 = `viewer/index.html` + CLAUDE.md §🎨.
- **글래스 아이콘 버튼** `.sbtn` — `--btn` 34px·blur·둥근사각·`:active` scale .85·`.ok`(초록 플래시)·`.busy`/`:disabled`. 아이콘 = SVG만(이모지 금지).
- **닫기(X)** `.tool-x`/`.dlg-x` — `--btn-sm` 30px·우상단·SVG X-path 단일(`M6 6 18 18M18 6 6 18`·stroke 1.8). `.dlg-x`=absolute 우상단.
- **모달/팝업 + 폰 뒤로가기** `<dialog>` + `history.pushState`(열 때)·`popstate`로 닫기 → 백버튼=직전 화면.
- **캐러셀/스와이프** scroll-snap 트랙 + 드래그 넘김.
- **복사/붙여넣기 1버튼** `.askclip` — 비면 PASTE·차면 COPY·성공 CHECK 플래시.
- **아이콘 SVG 상수** `COPY/PASTE/CHECK/DOWNLOAD/EDIT/LAYERS/THUMBUP/THUMBDOWN` 등(24뷰박스·stroke 2·round).

## 10. 시각 시스템 — 풀페이지 배경 · 배너 (viewer 정본)
- **풀페이지 네온 배경** `.bgfx` = radial **3겹**(좌상 420×300·우상 720×460·하단 640×720) + 탭별 색 전환(`--bgfx`): **피드=라임**(15,253,2) / **스크랩=앰버**(255,150,20) / **SNS=시안**(12,208,247). (구성도 1겹 데모는 단순화 — 라이브는 3겹.)
- **배너** `.bannerframe` = radius **20px** + 글로우 + **호흡 애니** `bannerbreath 5.5s` ease-in-out 무한(밝기·드롭섀도 맥동). 탭 전환 = **2겹 크로스페이드 디졸브**(`.banner.layer-*` opacity .6s) — 즉시교체·슬라이드 금지. `prefers-reduced-motion`이면 즉시.

## 11. 부속 설명 · 정렬 (viewer #mdbody/#cardsec 정본)
- **상태문구** `.genstat` = 14px 마진·박스(border+radius16)·`.live`(라임·pulse 1.6s). 생성/진행 상태 표시.
- **소머리(•)** `#cardsec p.lbl`·`.cref-lbl` = `::before content:'• '`(mut·700) — 카드 텍스트/이미지프롬프트 라벨. 이모지 금지(§📐 머리표 = `📍` 말머리 → `•` 소머리).
- **상대시간** 사다리(피드 메타) = <30분 방금·NEW → 30분 전 → N시간 전(1h·복합없음) → N일(1~6) → N주일(1~4) → N달. 색=보도(≤6h 라임/7~11h 흰/12h 회)·스크랩(NEW 라임/≤6h 흰/7h 회).
- **수집함 배지** 긴급(빨강)/이슈(노랑) = **메타라인 인라인 텍스트**(`카테고리 · 매체 N · 배지` 한 줄, 좌측 메타군 + 상대시간 우측 · `.sc-badge`). 글래스 칩·절대배치(`.tagrow`) 폐지(운영자 260621). 강조색 = 카테고리(고유 CAT_COLOR 유지)·매체 N(라임)·이슈(노랑)·긴급(빨강) · 구분점(·)·"매체"라벨 = 뮤트 · 시간 = 흰. 폰트=Pretendard·자간0(Orbitron 미사용). 점등(테두리 b-brk/b-iss·글로우 lit-*)은 별개 조건 유지.
- **내어쓰기**(따옴표·블록) = 카드뉴스 합성(`card_news.py`·`ovlOffsets`) 도메인 — 여는 따옴표가 줄 넘어 닫힐 때 그 사이 줄 들여쓰기. 뉴스요약 본문은 좌측정렬 기본.

## 적용 순서 (라우터)
1. 도구 페이지(comp·ly·k) `:root`를 §0 정본으로 교체 → 중립 회색·매직넘버 제거.
2. 생성/전송 버튼을 §1 상태머신으로 교체(라벨·색·재확인 게이트·소진).
3. §2 배치·§3 위계·§4 표면 규칙으로 마크업 정리.
4. §5 메뉴색·§6 픽토그램·§7 상태타이포(Pretendard·Orbitron 폐지)·§8 모션·§9 컴포넌트·§10 시각시스템·§11 부속설명 적용.
5. 게이트 = `shared/check_refs.py check_design()` 통과 확인.
