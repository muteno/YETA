---
name: yeta-design
description: 말벗 제타(yeta) 디자인 폴리시 — 인터페이스가 "느낌 좋게" 다듬어지는 디테일 원칙(yeta 한정 · nomute-design 이식·YETA화 260705). UI 컴포넌트 제작·프론트엔드 리뷰·애니메이션·hover/press 상태·그림자·테두리·타이포·micro-interaction·등장/퇴장 전환·아이콘 모션·시안 작업 시 자동 적용. Triggers / 트리거: UI polish, design details, "느낌 좋게", "어색해", "유려하게", "다듬어", "make it feel better", "feels off", 버튼, 모달, 닫기, 아이콘, stagger animation, border radius, 동심원, optical alignment, 광학정렬, font smoothing, tabular numbers, 표 정렬, image outline, box shadow, 글래스, 글래스모피즘, 마진, 간격.
---

# 말벗 제타(yeta) 디자인 폴리시 (yeta 한정)

> 범용 "make-interfaces-feel-better"를 **yeta 현실에 맞춰 녹인 버전**(nomute-editor `nomute-design` 이식 → YETA 토큰·컴포넌트·경로로 고정). 좋은 인터페이스는 작은 디테일이 복리로 쌓여 나온다. **단, 이 프로젝트엔 이미 자기 디자인 시스템이 있다 — 그걸 따르는 게 1순위.** 범용 원칙은 우리 시스템과 충돌하면 항상 진다.

## ⛓ 정본(SSOT)·우선순위 — 제일 먼저 읽어라

yeta는 **순수 CSS/`var()` 토큰 + 바닐라 JS**다(React·Tailwind·framer-motion 아님 — `className`·`active:scale-[..]`·`AnimatePresence` 같은 건 없다). 값은 절대 새로 창작하지 말고 **기존 정본을 계승**한다:

1. **값 정본 = `viewer/index.html` `:root` 토큰**(= 절대명령#1 값 SSOT) — 색(`--fg`·`--fg-2`·`--mut`·`--bg`·`--accent`·`--cobalt`·글래스 `--glass`·`--glass-2`·`--glass-line`)·반지름(`--r-s`·`--r-m`·`--r-l`·`--r-modal`·`--r-pill`)·간격(`--sp-2`·`--sp-3`)·글래스 blur(`--blur-m`·`--blur-l`)·버튼크기(`--btn`)·타이포(`--fs-*`·`--fw-x`·`--fw-b`·`--lh-base`)·모션(`--ease`)·눌림(`--press-s`·`--press-m`·`--press-l`). **raw hex/px 창작 금지 → `var()` 토큰 사용**(정확한 게 없으면 가장 가까운 토큰 계승, 정 없으면 운영자 승인 후 `:root`에 토큰부터 추가 = 기틀). 값을 이 스킬·문서에 복붙하지 마라(드리프트 원천).
2. **규칙·컴포넌트 정본 = `CLAUDE.md` §🎨 디자인 계약** — 계승=디폴트, 재설계 금지. 컴포넌트 인벤토리(닫기 `.tool-x`·전송 `.yeta-send`·챗 버블 `.yb.me`/`.yb.ai`·`<dialog>`+`history.pushState` 모달[`#yetadlg`]·PIN 패드 `.lk-key`·SNS 리스트 `.ypick-row`·하단 네비 `.ynav`·토스트 `.nm-toast`·아이콘 SSOT `nm-svg.js`)를 **그대로 이식**한다.
3. **버튼·인터랙션 마스터 = `구성도/00_가이드북_버튼인터랙션.html`** — 모든 버튼·토큰·크기·여백·눌림/시맨틱 모션/탭 피드백/재확인·픽토그램 총정리. 새 버튼·이식은 여기 패턴 계승.
4. **거울·게이트** = `구성도/base.css`·`viewer/tokens.css`(viewer :root 자동거울) + `shared/check_refs.py`(raw 값 게이트 — accent_raw/accent_hex는 **하드차단 rc=1**, hex/blur/죽은토큰은 baseline 경고·비차단) + `design-tokens.lock`(승인 원장 — 미등재 `:root` 신규 토큰 = 커밋 차단). raw 줄이면 baseline도 낮춰라.
5. **컴포넌트 인덱스(CII) = `docs/CII_컴포넌트계승인덱스.md`**(절대명령#2 정본 위치) — 정본 셀렉터·크기·:active·아이콘 표. 새 컴포넌트는 표 계승. **표·토큰에 없으면 임의로 만들지 말고 운영자에게 먼저 질문**(필요 이유 + 가장 가까운 기존 후보 제시) — 승인분만 제작하고 즉시 기틀 편입: `:root` 토큰 추가 → `python3 shared/build_design_mirror.py build`(거울 재생성) → CII 행 등재 → `design-tokens.lock` 등재 → check_refs baseline 사유. 시맨틱 아이콘 모션은 **위임 1핸들러** 자동 상속 — 개별 모션 코드 창작 금지.

⚠️ **충돌 처분: 항상 yeta(viewer `:root`·§🎨·가이드북·CII)가 이긴다.** 아래 원칙은 *그 위에서* 디테일을 보강할 뿐, 우리 값을 덮어쓰지 않는다.

## 핵심 원칙 (yeta 매핑)

### 1. 동심원 border radius
바깥 radius = 안쪽 radius + padding. 중첩 요소의 radius 불일치가 "어색함"의 최다 원인. → 우리 `--r-s`(9)·`--r-m`(11)·`--r-l`(16)·`--r-modal`(22) 토큰으로 계산해 맞춘다(임의 px 금지). 버블 꼬리쪽 모서리만 `--r-s`(`.yb` 결).

### 2. 광학 정렬 > 기하 정렬
기하학적 중앙이 어색하면 광학적으로 맞춘다. 아이콘 버튼·재생 삼각형·종이비행기(`.yeta-send`)·비대칭 SVG는 수동 보정. SVG path 자체를 고치거나 padding으로 미세조정(1px 광학 보정 = raw 허용 예외축).

### 3. 테두리보다 그림자 / 글래스
딱딱한 1px 테두리 대신 깊이를 준다. 우리 시스템은 **글래스모피즘(`backdrop-filter: blur(var(--blur-m|l))` + `--glass`/`--glass-2` 표면 + `--glass-line` 엣지 하이라이트 + `inset 0 1px 0 var(--glass-line)` 시트sheen)** 이 기본 깊이 수단 — 챗 버블(`.yb.ai`)·헤더·입력바·소개 카드·PIN 패드(`.lk-pad`)·네비(`.ynav`)·수신 콜 자막(`.ycall-line`)이 다 글래스다. 새 면도 글래스 토큰 계승(테두리 새로 긋지 마). box-shadow는 토큰 없는 축 = raw 허용.

### 4. 중단 가능한 애니메이션
상호작용 상태 변화(hover/press/토글)는 **CSS `transition`** 으로 — 중간에 끊겨도 자연스럽다. `@keyframes`는 1회 재생 연출(등장 `ybIn`·`ypickIn`·`msgUnfold`·`ycallPulse` 등)에만. 커브·시간은 `var(--ease)`(`cubic-bezier(.2,.7,.3,1)`) 계승.

### 5. 등장은 쪼개고 stagger
컨테이너 하나를 통째로 띄우지 말고, 의미 단위로 쪼개 ~40–100ms 지연 stagger. 우리엔 이미 캐릭터 선택 리스트 `ypickIn`(촤르륵 nth-child 40ms 계단)·챗 버블 `ybIn`(신규 노드만 `.in`) 패턴이 있다 — **그 패턴·커브(`cubic-bezier(.22,.61,.36,1)`)를 재사용**, 새로 만들지 마. 폴 재렌더 재트리거 방지 = JS가 신규 노드만 키드(`_yLastN`).

### 6. 퇴장은 더 은은하게
전체 높이 대신 작은 고정 `translateY`로. 퇴장은 등장보다 약하게. 우리 `ybOut`(회수/삭제 = 접힘 후 제거) 패턴 계승(운영자 "지워도 촤르륵").

### 7. 아이콘 전환 = opacity·scale·blur 크로스페이드
visibility 토글 말고 `opacity`+`scale`(+`blur`)로 부드럽게. **이 프로젝트엔 모션 라이브러리가 없다** → 두 SVG를 DOM에 두고(하나 `position:absolute`) CSS transition으로 크로스페이드(`var(--ease)`). 무대 배경 2겹 크로스페이드(`.ybg`·`yPaintBg`)·`.tool-x` 회전180°(`:active`)가 이 결. (framer-motion `spring`/`bounce:0` 지침은 우리에 해당 없음 — 무시.)

### 8. 폰트 스무딩
루트에 `-webkit-font-smoothing: antialiased`(이미 `body`에 적용 — 유지). 디스플레이 폰트 = LEMONMILK(로컬)·본문 = Pretendard.

### 9. tabular 숫자
동적으로 바뀌는 숫자(카운트·소요초·타이머·PIN 시도)는 `font-variant-numeric: tabular-nums`로 레이아웃 시프트 차단. 우리 다이얼 캡션 `.yb-cap`(소요초)에 이미 적용 — 새 동적 숫자에도 동일 적용.

### 10. 텍스트 줄바꿈
제목엔 `text-wrap: balance`(`.yintro-name`), 본문엔 `text-wrap: pretty`(`.yintro-desc` — 고아줄 방지). §표기표준 머리표 계층(`1. → 1) → a) → 가)`)과 타이포 토큰(`--fs-*`) 정합.

### 11. 이미지 아웃라인
이미지에 미묘한 `1px` 저투명 아웃라인으로 깊이 통일. 색은 **순수 흑/백 또는 브랜드 라임만** — 다크 기본이라 흰색 계열 저투명(`var(--glass-line)`=`rgba(255,255,255,.14)`) 또는 얼굴 채운 아바타는 은은한 라임 테(`rgba(var(--accent-rgb),.22)`). slate·zinc 같은 *틴트된* 중성색 금지(가장자리가 때처럼 더러워 보임). 캐릭터 얼굴 아바타(`.yava.has-img`·`.yintro-ava.has-img`)가 이 결.

### 12. 누름 scale — ⚠️ 고정값 아님, press 토큰 티어 계승
누름 피드백 `transform: scale(...)`은 **요소마다 다르다**(범용 "항상 0.96"은 우리에 틀림). 정본 = `viewer/index.html :root`의 눌림 3토큰 사다리 **`--press-s`(.9)·`--press-m`(.9)·`--press-l`(.95)**(값·용도는 `:root` 주석이 정본, 여기 복붙 금지[위 §⛓ 1번]). 티어 감각: s = 작은 아이콘·네비 픽토(`.ynav button`) · m = 닫기·전송·마이크·다이스·큰 액션(`.tool-x`·`.yeta-send`·`.ycall-mic`) · l = 프로필·리스트 행·큰 버튼(`.yeta-who`·`.ypick-row`). 클수록 덜 줄임(물리적).

**규칙 = 새 요소는 가장 가까운 형제 컴포넌트의 press 토큰 티어를 계승, `transform:scale(var(--press-*,폴백))` 참조로 쓴다**(하나 바꾸면 그 tier 전부) — **raw scale 창작 금지**·임의 0.96 박지 마라. reduced-motion 무효화는 `:root` 전역 `@media (prefers-reduced-motion)` 블록이 담당(`--press-*`을 1로 · 개별 가드 신설 금지).

### 13. 페이지 로드 시 등장 억제
원치 않는 첫 렌더 등장 애니는 억제(React `AnimatePresence` 없으니 — 의도된 등장[`ybIn`·`ypickIn`]은 살리고, 첫 렌더[재진입·히스토리 복원]는 무애니 = JS가 `_yLastN<0`·`first`로 가드). `@media (prefers-reduced-motion)`이면 즉시 전환. 무대 배경 전환은 **크로스페이드 디졸브 유지**(슬라이드·즉시교체 금지).

### 14. `transition: all` 금지
항상 정확한 속성만: `transition: transform .3s var(--ease)`처럼 속성 명시. `all`은 의도 안 한 속성까지 전환돼 성능·버그 유발.

### 15. `will-change`는 아껴서
`transform`·`opacity`·`filter`(GPU 합성 가능)에만. `will-change: all` 금지. 첫 프레임 끊김이 *실제로* 보일 때만 추가.

### 16. 최소 히트 영역
상호작용 요소는 최소 40×40px 탭 영역(폰 우선). 보이는 요소가 작으면(픽토 아이콘 등) pseudo-element/padding으로 탭 영역 확장. 두 요소의 히트 영역 겹침 금지. `touch-action:manipulation`(폰 탭 신뢰성) 계승.

## 흔한 실수 → 교정
| 실수 | 교정 |
| --- | --- |
| 부모·자식 같은 radius | `--r-*`로 `바깥=안+padding` 계산 |
| 임의 px/hex 창작 | `var()` 토큰 계승(없으면 승인 후 `:root`+락 등재) |
| raw 강조색(`#CFFF40`·`rgba(207,255,64)`) | `var(--accent)`/`var(--accent-rgb)`(하드차단 게이트) |
| 딱딱한 1px 테두리로 구획 | 글래스 `blur(var(--blur-m|l))` 깊이 |
| 누름 scale 일괄 0.96 | 가장 가까운 형제 `--press-*` 티어 계승 |
| 동적 숫자 레이아웃 시프트 | `tabular-nums` |
| `transition: all` | 정확한 속성만 명시 |
| 새 버튼 재설계 | `.tool-x`/`.yeta-send`/가이드북 패턴 이식 |
| 무대·아이콘 즉시교체 | 크로스페이드 디졸브(`.ybg`·`--ease`) |
| `:root` 신규 토큰 임의 추가 | 운영자 승인 → `design-tokens.lock` 등재 → 거울 재생성 |

## 작업·리뷰 출력 형식
- 실질 변경이면 **전/후 비교** 표 + 작업 4대 표준②(전후·장단점·효율·품질저하 리스크)로 제시. 원칙별로 헤딩 묶고, 한 행=한 diff. 바뀐 게 없으면 그 표는 생략(빈 표=노이즈).
- 시각 제안·미리보기는 **PNG 아닌 `HTML`로**(실제 CSS·애니·클릭효과 정확). 큰 산출은 `docs/reports/{yymmdd}_{라벨}.html`(인라인 CSS·다크·시스템폰트).
- **디자인 제안 = 플레이그라운드식이 디폴트**(확립본 = `docs/reports/260706_언락밝기_플레이그라운드.html` · 정본인덱스 4절 등재). 구성 5요소: ① 실물 재현 미리보기{폰 프레임 · `:root` 토큰 사본 + 정본 컴포넌트·커브 계승 · 현행 상태 = 비교 기준으로 함께 재현} ② 프리셋 3~4개(현행 포함 · 추천 ★ 표시) ③ 미세조정 컨트롤{축별 그룹 라벨 · 값 = tabular-nums · **옵션 규모 = 평균 50개 안팎**(단순 대상만 축소 허용) · **축 3분류(기틀 인지)**: 정렬·간격·높이 = 자유 / 글자·라운드 등 확립 축 = 자유 조절 + 실존값 사다리 눈금(사다리 밖 = ⚠ 실시간) / 색 = 팔레트·토큰 폐쇄 셀렉트(자유 hex 금지 · 역할 재지정 = ⚠ · 같은 토큰 알파 변주 = 자유) · 확립 축을 아예 잠그는 것도 금지 = 막지 말고 역제안으로 승격} ④ 선택값 출력+복사 버튼{값마다 현행 병기 · 계승/갱신 후보 자동 표기 · 기틀 축 = ⚠ 딱지 · **⚠ 축 있으면 복사 시 알림창 + 「기틀 갱신 역제안」 블록**(현행 기틀값→제안값·적용 범위 = 전 앱 동축 명시 · 회신 = 기틀 갱신 승인 정문 경로)} ⑤ 재현 한계 각주(폴백·근사·실물 차이 명시). 자산 = base64 임베드(자기완결 1파일). 전달 = 레포 커밋(정본) + 채팅 파일 직접 첨부(원탭) · Artifact = 재열람·공유 보조. 상세 골격·판정 코드 = `docs/플레이그라운드_포터블.md` §3-2′.
  - ⚠️ **플그·적용은 "표면별 raw"가 아니라 "토큰을 돌린다"가 원칙(운영자 260707 재발방지 · 절대명령1 = 값 SSOT·일괄 배포)**: 슬라이더 축은 가능하면 `:root` 토큰(블러·라운드·간격·유리 등)에 매핑해, 고른 값이 **그 토큰을 쓰는 전 표면에 일괄 전파**되게 한다(예: 블러 = `--blur-m`↔`--blur-l` 토글이지, .ycrow만 24px 박기 아님). 토큰 사다리에 없는 값(⚠ 갱신 축)은 **표면마다 raw로 조용히 박지 말고** 운영자에 ㉮ 새 토큰 신설(전 표면 공유·락 등재) ㉯ 최근접 토큰 스냅 중 택일받아 처리. 토큰 없는 축(아바타 px·레이아웃 gap 등)만 표면 raw 허용.
- 토큰 새로 추가했으면 `python3 shared/build_design_mirror.py build`(거울 `구성도/base.css`·`viewer/tokens.css` 동기화) + `python3 shared/check_refs.py` 통과 확인 + `design-tokens.lock` 등재.

## 체크리스트
- [ ] 값은 `viewer :root` `var()` 토큰 계승(raw 창작 0 · 강조색 raw 0)
- [ ] 중첩 요소 동심원 radius(`--r-*`)
- [ ] 아이콘 광학 중앙 정렬
- [ ] 깊이는 글래스/그림자(딱딱한 테두리 X)
- [ ] 등장=쪼개기+stagger(기존 `ybIn`/`ypickIn` 커브 재사용) · 퇴장은 은은(`ybOut`)
- [ ] 동적 숫자 `tabular-nums`
- [ ] 제목 `text-wrap: balance` · §표기표준 머리표 정합
- [ ] 이미지 저투명 흑/백/라임 아웃라인(틴트 X)
- [ ] 누름 scale = 가까운 형제 `--press-*` 계승(고정 0.96 X)
- [ ] `transition: all` 없음 · `will-change` 최소
- [ ] 히트 영역 ≥40×40 · `touch-action:manipulation`
- [ ] 새 버튼은 `.tool-x`/`.yeta-send`/가이드북 패턴 이식(재설계 X)
- [ ] 무대·아이콘 크로스페이드 유지
- [ ] `:root` 신규 토큰 = 운영자 승인 + `design-tokens.lock` 등재

## 🔭 디자인 리서치 상시 체계 (운영자 260707 신설)
- **디자인 작업(개선·시안·아이데이션) 착수 전 = 리서치 분신 발사가 디폴트**: READ-ONLY 웹서치 에이전트를 **여러 기·각기 다른 앵글**(메신저 UI·캐릭터챗 앱[Character.AI·Talkie·Zeta 등]·다크/글래스 트렌드·소셜 몰입 패턴 등)로 병렬 발사, **각 기 10분 제약**(깊이보다 수확 — 시간 되면 모은 것만 정리) 명시.
- 예타 디자인 정본(§⛓)이 항상 이기되, 레퍼런스는 "디테일·아이데이션 연료"로: 수확 → 예타 토큰·컴포넌트로 번역해 적용(raw 이식 금지).
- 적용 기준 = **사용자 이용에 지장 없게**(기능 무파괴·점진·reduced-motion 가드·기존 배선 보존).
- **북극성(운영자 260707)**: 예타 = **반(半) 메타버스** 구현 · 목표 = "UX 진짜 쩐다" 소리 나올 편리함 · **딱딱한 전환구간 절대 금지** — 모든 화면/탭/시트/모달의 등장·퇴장·전환에 트랜지션 필수(즉발 display 토글 = 위반). 새 UI 검수 시 1순위 체크.
