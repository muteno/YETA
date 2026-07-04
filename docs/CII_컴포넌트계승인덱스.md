# 📑 CII — 컴포넌트 계승 인덱스 (Component Inheritance Index)

> **운영자 정본 · 260628 · 분신술 10인 도출.** UI/UX 컴포넌트를 **표로 인덱싱**해 "항상 계승"시키는 기틀. §🎨 "📦 정본 컴포넌트 인벤토리"(불릿)의 **기계가독 표 승격판**. 새 버튼·입력칸·모달·아이콘을 만들거나 이식할 때 **반드시 이 표의 정본 셀렉터를 계승**(재설계 금지). 충돌 시 §🎨·viewer `:root`가 정본.

## 왜 (재발 방지)
드리프트 2대 근원: ① thumb/ly/k/comp가 index `:root` 토큰 미상속(raw 값 박힘) ② 같은 컴포넌트 4중 복제(한 곳만 고쳐짐). 이 표 = "어떤 컴포넌트는 *무엇을* 계승해야 하는가"의 단일 출처. 코드가 표와 어긋나면 드리프트.

## 위계 (값·규칙·강제 3층 — §🎨 그대로)
1. **값 SSOT** = `viewer/index.html :root` 토큰 (색·`--btn*`·`--r*`·`--sp*`·`--blur*`·`--z*`·타이포·모션).
2. **규칙·인덱스** = 이 표 + §🎨 + `구성도/00_가이드북_버튼인터랙션.html`.
3. **강제** = `shared/check_refs.py check_design()`(raw 값 baseline·5파일 커버) + `build_design_mirror.py`(거울 정합).

## 표기 규칙
- **크기·마진·반지름·z = 토큰만**(raw px 금지). 없으면 가장 가까운 토큰, 정 없으면 `:root`에 토큰부터 추가.
- **아이콘 = SVG만**(이모지·`✕`문자 금지). 같은 의미는 같은 path.
- **닫기/최소화/버튼묶음 = 헤더 우측**(`margin-left:auto`는 *묶음 래퍼*에 — 개별 버튼에 걸면 갇혀 좌측붙음 = editdlg 버그).
- **이미지 위 오버레이 버튼 = 검정 20%**(아이콘색만 accent). 일반 다운로드 = `.dlbtn`(accent 10%). ⚠️ **카드 위 다운로드류(저장 `.save`·오버레이 PNG `.ovl` 등)는 빠짐없이 `.dlbtn`** = 클릭 액티브 통일(안 붙이면 누락 · 260629 `.ovl` 교정).
- **누름 :active = press *토큰 티어* 계승** — viewer :root `--press-pico/xs/s/m/l` 5토큰 사다리(아래 「:active 눌림 효과 토큰화(260628)」 항목 = 현행 · 티어 용도는 :root 주석 정본)를 `scale(var(--press-*,폴백))`로 참조. 게이지·보라·카드는 셀렉터 화이트리스트 제외. raw scale 창작·고정 0.96 금지(옛 리터럴 표기 폐기 · 260702).
- **소머리(구분자) `•` = 텍스트 흰색(`--fg`)·`--fw-x`(800) / 블릿 형광(`--accent`)·`--fw-b`(700) · `--fs-label`(13px)** — 크기·굵기 *토큰*(리터럴 금지). 특수(이전제작·최소화)만 블릿 보라(`--hist-accent`) · 텍스트는 *항상* 흰색. **회색(`--mut`) 소머리·블릿 없는 소머리 금지.** 블릿 메커니즘 = **블록은 `::before content:'• '`(공백·뉴스 정본 동일), flex(`.csec`)는 `content:'•'`+`gap:6px`**(둘 다 6px급 간격·layout별). 정본 = 뉴스 `index .cref-lbl`. `.gospec`(명세 readout)은 소머리 아님(예외). ⚠️ **flex `.csec`에 토글(`.ovfmt`/`.onoff`) 붙으면 토글 세로패딩(3px·탭영역)이 행을 키워 `•`가 ~3px 내려앉음 → `.csec .ovfmt, .csec .onoff { margin-block:-3px }`로 행높이 기여 상쇄**(탭영역 보존·토글 유무 무관 첫 블릿 화면선 통일·운영자 260629 저작권탭 교정). 강제 = `check_refs.check_soremeori()`.

## 인덱스 표

| 컴포넌트 | 정본 셀렉터 | 크기 | 플레이트 | :active | 아이콘 | 위치 | 마진 | a11y | 정본 |
|---|---|---|---|---|---|---|---|---|---|
| 닫기 X | `.tool-x`(별칭 `.dlg-x/.ed-x/.askx/.mx`) | `--btn-sm`(30) | glass `.06`+`--line` | 회전180 .92 | path `M6 6 18 18M18 6 6 18` sw1.8 | 헤더 우측묶음 / abs 우상단 | — | `aria-label="닫기"` | index `.tool-x` |
| 최소화 − | `#toolMin`·`.askmin`·`.ed-min`·`.rmin` | `--btn-sm` / 28(rfab) | glass(헤더) / glass border:0(rfab) | 헤더 .8 · rfab=픽토 .55 | path `M6 12h12` | 닫기 좌측(헤더) | — | `aria-label="최소화"` | index `#toolMin` |
| 복원 ▲ | `#toolRestore` + `.min-pick` | `--btn-sm` | glass `--blur-l` | scale .82 | ▲ | 우하단·`--z-min`(200) | — | focus 이동 | index |
| 최소화 라벨 | `MIN_REG` label | — | — | — | — | picker | — | — | "부모 메뉴 - 세부"(이미지-썸네일/영상-자막/뉴스 요약-신청/카드뉴스-이미지-수정) |
| 입력칸 focus | `input/textarea:focus` | — | — | — | — | — | — | `:focus-visible` 2px accent 링 | 4파일 통일 `rgba(var(--accent-rgb),.35)`+`.08` 링 |
| 클립 3버튼 | `.iobtn-edge`(별칭 `.urlclip/.scnclip/.askclip` → 통일 대상) | 26 | glass `.06`/blur13 opacity.6 | scale .85 | COPY/PASTE/CHECK/ERASE/UNDO `_SVG` | **입력칸 우측 걸침 2케이스**(우하단=base / 우상단=`.asktawrap.clip-top`) · 가로 right 14/46/78px 사다리(우측 기준) · 다른 버튼 위치 따라 상/하 선택 · **케이스 2개 고정**(과증식 금지·운영자 260629) | — | — | thumb `attachCopyPaste` · index `.asktawrap.clip-top` |
| 다운로드 | `.dlbtn`(+컨텍스트) | `--btn` | accent 10% / 이미지위 검정20% · **받음=`.dl-done`→흰색(`--fg`)** | ↓바운스 + ✓팝·링(클립) · 클릭 후 흰색 영속(URL키 `DLED` 복원·260701) | `DOWNLOAD_SVG` | abs 우상단행 | — | `aria-label` | index/thumb `.dlbtn` |
| 소머리(구분자) `•` | `.cref-lbl`(정본)·`p.lbl`·thumb `.csec`·k/ly/comp/thumb포스트 `label.fl`·`.hist-bul`(특수) | `--fs-label`(13)·텍스트`--fw-x`/블릿`--fw-b` | 텍스트 흰색`--fg` · 블릿 형광`--accent`(특수=보라`--hist-accent`) | — | 블록=`::before content:'• '` / flex(.csec)=`content:'•'`+gap6 | 섹션·폼 머리 | 14~16 0 | 블릿 ::before/`aria-hidden`=SR 무시 | index `.cref-lbl` |
| 최외곽 박스(뷰) | 레거시 `.scrap-cols`·뉴스요약 `.card`·SNS `.soc-item` | radius `--r-l`(16) | — | — | — | 각 뷰 최바깥 | — | — | 전 뷰 16px 통일(레거시 기준·운영자 260701) · 모달은 예외 `--r-modal`(22) · 내부 중첩(sc-item13·failtray14)은 각자 유지 |
| 모달 헤더 | `.tool-h`(+`.tool-hbtns`) | — | — | — | — | 제목 좌 + 버튼묶음 우(`margin-left:auto` 래퍼) | `11px 16px` | `aria-labelledby` | index `.tool-h` |
| 모달/팝업 | `<dialog>` + `history.pushState` | — | glass blur | `@starting-style`(등장) | — | top-layer | radius 22px · **헤더↔입력 간격 = 15px 단일표준**(`.askhead margin-bottom` · ask-family[askdlg·revdlg·crevdlg·tredodlg(이미지 수정 요청)] 전부 동일 · 클립 하단걸침이라 상단 클리어런스 불필요 · 모달별 override 금지 · 운영자 260629) · **스크롤형 모달 둥근 모서리 음영 차단(260630)**: 모달이 스크롤 컨테이너면 `scrollbar-gutter:stable both-edges`(PC 세로 스크롤바가 우측에만 거터 생겨 우상단 둥근 모서리에 음영 누출하던 것 = 좌우 대칭 예약으로 차단) **+** sticky 헤더에 top `border-radius`=모달 radius(헤더 직각 배경이 둥근 모서리 덮음 차단) / `overflow:hidden` 가능한 모달(#tooldlg)은 그걸로 갈음(둘 다 불필요) · 모바일 `radius:0`이라 무해 | 백버튼=닫기 | index `tooldlg`·`.askhead` |
| FAB 빠른메뉴 | `#rfab`(.rc/.ro/.rmin) | 54/35/28 | glass `rgba(0,0,0,.34)`+blur14 | rotate135(코어) | + / 도구 픽토 | 우하단·z70 | — | PC=숨김 | thumb `#rfab`(ly/k 동기) |
| 토스트 | `.nm-toast`(긴급 빨강)/`.nm-toast.fail`(실패 앰버) | 버튼 28(`.ft-act`)·이동 min54 | 글래스 `.86`+blur18(색만 구분) | 버튼 `.sbtn` press-s | `.ft-act`=.sbtn·svg14 · 이동↗=`.go-ready`(초록 요약완료)/`.go-wait`(회색 준비중·실패) · 클릭 시맨틱모션(`data-motion`) | fixed 하단·bottom 86·`--z-float` | — | ⚠ `role=alert` 필요 | index `showToast`(긴급 [✓체크][이동])/`showFailToast`(실패 [✓확인][↻재시도][↗원문]) |
| 아이콘 누름 모션 | 위임 click(캡처·1핸들러) | — | — | — | `ic-spin`(회전·기본)·`ic-bounce`(↓다운로드/저장)·`ic-rise`(↗이동 7시→2시 상승)·`ic-check`(✓팝)·`ic-share`(별자리 훑기 — 공유 3점 위→아래 순차 강조색 플레어+선 드로우 · SHARE_SVG 전용[원3+선2 path분리·pathLength=1 훅 필요] · 운영자 260703) · 버튼 `data-motion="rise/check/share"` 우선(없으면 다운로드=bounce/그외=spin) | — | — | reduced-motion 무효 | index 위임핸들러(§🎨) |
| 픽토그램-온리 액션(발행본) | `.pubpop .pub-ico`(`.pub-share`/`.pub-rm`) | 34(히트 `::before -4px`=42) | **무도형**(배경·테두리 0) · **상시 의미색**(공유 `--accent`/삭제 `--danger` — rest 무채는 운영자 260703 폐지) | 공유=`data-motion="share"` 별자리 훑기 · 삭제=`:active` scale `--press-xs` | SHARE_SVG·`_TRASHSVG` | 행 우측(qrow gap 유지) | svg 18px | disabled=`--mut` 40%·행높이 51px(`.pubpop .qlist` basis 정합) · 별자리 훑기 도입처 = 발행본 `.pub-share` + 요약 헤더 `.dlg-pdf`(okflash 초록 플래시와 병행·260703) | index pubRowHtml(#1377 복원·260703) |
| 채팅 버블(yeta) | `.yb.me`/`.yb.ai`(+`.sys`/`.fail`) · 캐릭터 = `.ymsg`(아바타+이름+버블) | me max-w 78%·msg 86% | me=`--bubble-me`(제타 보라 #7c5cfc)·ai=`--bubble-ai`(#1e2023) — :root 토큰(260703 v2) | — | *나레이션*=`i.yn` 이탤릭 | 꼬리쪽 모서리만 `--r-s` | radius `--r-l`·pad 10/13 | 캡션 `.yb-cap`=tabular | index `#yetadlg`(yRender·yAiMsg) |
| 다이얼 세그먼트(yeta) | `.ydial`(radiogroup)+`button.on` | h~30·flex:1 | 무채 `.04`+선택 `.07`·선택색=`--yeta-ac`(페르소나색) | `--press-m`(.9) | 텍스트만 | `.yeta-dials`(입력행 위) | gap 4/6·동심원 r=`--r-m`-3 | `role=radio`·`aria-checked` | index `yPaintDials` |
| 캐릭터 챗 모달 | `#yetadlg`(dialog+pushState) | min(600px,94vw)×min(88dvh,760px) | 무채 그라데 .92/.96(불투명 — backdrop-filter:none 명시) | — | 닫기=`.tool-x`·전송=`.yeta-send`(모션 위임 등재) | 중앙(모바일 margin:auto 필수) | radius `--r-modal` | 뒤로가기=popstate | index `openYeta`·greeting SSOT=roster.json(카드 frontmatter와 동기 유지) |
| 캐러셀 | scroll-snap 트랙 | — | — | — | — | — | — | — | `feed-ui`/`cardRefCarousel` |
| 수정 진행바 | `.reshoot-badge`+`.reshoot-bar`(썸네일) · 카드=`.reshoot-badge`(텍스트만·바 없음) | 바 118px·h4 | 배지 glass `rgba(8,15,11,.62)`blur10 · 바 track `rgba(255,255,255,.16)`·채움 `--accent` | — | 없음(텍스트 "수정 중…" + 인디터미넌트 스윕) | 이미지/슬롯 정중앙 abs·z3 · dim `brightness(.5)` | radius `--r-pill` | reduced-motion=감속(2.4s) | 썸네일 index `markSlotReshooting` · 카드 `markReshooting` |
| 수신 콜 화면(yeta) | `#calldlg`(dialog)+`.ycall-btn`(.take/.drop) | 버튼 `--btn`+`--sp-3`×2 원형 | 페르소나 bg+`--bg-scrim` · 자막 `--glass`+`--blur-m` · dialog=`#yetadlg` 결(글래스 엣지·`::backdrop`·모바일 margin:auto) | `--press-m` | 수화기 SVG 단일 path(거절=회전135°) · 파동 링=키프레임(안무 예외) | top-layer(dialog) | pad `--sp-3` | `aria-label` 받기/거절 · Esc=거절 · 뒤로가기=거절 | viewer/call.js(플러그인 · CLAUDE.md §🗺 ☎️) |
| 무전 마이크(yeta) | `#yetaMic`(`.ycall-mic`) | `--btn` 원형 | 무채 글래스 `--glass`+`--glass-line`(CTA 아님) · 녹음=`--danger` 점멸 | `--press-m` | 마이크 SVG 단일 path | `.yeta-in` 좌측(모듈 주입) | — | `aria-label` 무전 · 녹음중 placeholder 교체 | viewer/call.js `initPtt` |
| 프리미엄 보이스 배지(yeta) | `.yprem` | `--fs-xs`·`--fw-b` | accent 12% 플레이트+40% 테두리(`.dlbtn` 결) | — | 파형 SVG 단일 path | 캐릭터 이름 우측(`yPremBadge(c)` 훅) | ml 6 | `title="전용 음색(프리미엄)"` · roster `voice` 존재 시만 | viewer/call.js `yPremBadge` |

⚠ = 현 드리프트(후속 교정). 별칭 셀렉터(`.ed-x` 등)는 `.tool-x` 스펙을 *복제*가 아니라 *계승*해야 함 — 단일화 후속.

## 적용 절차 (새 컴포넌트·이식)
1. 이 표에서 해당 행 찾기 → **정본 셀렉터를 그대로 계승**(클래스 추가만, 재설계 금지).
2. 표에 없는 새 컴포넌트면 → 위 표기 규칙대로 만들고 **이 표에 행 추가**(인덱스 갱신 = 등재).
3. 4뷰어(index/thumb/ly/k) 공통이면 같은 패턴으로 미러(SVG 상수·토큰).
4. `python3 shared/check_refs.py` 통과 확인(raw 값 baseline·거울 정합).

## 강제·후속 로드맵
- ✅ `check_design` 5파일 커버(ly/k/comp 편입·260628) · ✅ ly/k 토큰화 · ✅ 도구앱 focus-visible.
- ✅ **이모지→SVG 전면**(4뷰어 UI 이모지 픽토그램화 · PR #1119·1120·1121·1125 · 핀·블릿·💡 외 전부 · 운영자 "전부 무조건").
- ✅ **P1 = `nm-svg.js` 아이콘 SSOT**(260628) — 공유 아이콘 10종(CHECK·COPY·PASTE·ERASE·UNDO·WAIT·ERR·OK·DOWNLOAD·WARN) 단일정본·4뷰어 `<script src="nm-svg.js">` 로드(`cscroll.js` 패턴)·인라인 복제 제거. 발산본 통일=정본(DOWNLOAD=14px[thumb CSS 12px 재지정 무관]·WARN=index/ly/k 다수본). **하드 게이트** = `check_refs.check_icon_ssot()`(인라인 재선언=섀도잉·미로드=ReferenceError 차단 → "하나 바꾸면 다 바뀜" 보장).
- ✅ **:active 눌림 효과 토큰화**(260628 · PR #1133·1135 · 분신술 10인) — 14개 임의 scale → 4뷰어 `:root` 5토큰 사다리(`--press-pico/xs/s/m/l` = `.55/.82/.85/.9/.95`, 기존 우세값 스냅·델타 ≤.03) + `scale(var(--press-*,fallback))` + reduced-motion 무효화 블록(`--press-*:1`). **픽토온리 = `:active svg{scale}`로 강제**(배경 plate 안 따라움직임 — `.vh-fbtn`·`.jvar-dl` 버그픽스). **제외=셀렉터 화이트리스트**(값 기반 금지 — `.mergebox(.95)`·`.rev-fab(.9)` 충돌): 게이지(`.go/.mkbtn/.ed-go/.edattach/.sc-pick/.unmerge-go/.hist-clr`)·보라(`.mergebox/.mb-x/#histRemote/.rev-fab`)·카드(`.card/.abadd .99`). 색플래시(복사 형광) 보존. ⚠️ 4뷰어 `:root` 독립(상속 0) → 토큰 4곳 각각·index만 거울 대상. ⏳ 잔여 = 이모지 SVG도 nm-svg 편입 검토 · `check_press_tokens` 게이트(raw scale 재등장 차단).
- ⏳ P2 = `tokens.css` 공유 `<link>` + `build_design_mirror` 확장(thumb/ly/k에 `--r/sp/blur/btn/z` 주입).
- ⏳ P3 = `구성도/00_컴포넌트_인덱스.html` 시각본 + (선택) `build_components_index.py`로 표↔코드 diff 하드게이트(`build_library` 패턴).
- ⏳ 잔여 = 닫기 X 13클래스 단일화 · 토스트 토큰화+`role=alert` · z충돌(`.totop`/`.nm-top`) · radius/gap 토큰화.

> 상세 감사·전후·우선순위 = `docs/reports/260628_UIUX_기틀_분신술10인.html`.

## 🎨 브랜드 팔레트 v2 (260704 · 운영자 그린 전환)
> yeta 색 정체성 = **다크·그린·글래스**로 통일(옛 네온보라·라이트 코발트 폐지). 값 SSOT = viewer :root(색은 base.css 거울·구조 blur는 tokens.css 거울).
- **강조 2색만**: `--accent:#CFFF40`(브랜드 라임 · 1차 · 버튼·링·PIN·챗버블·픽토 액티브) · `--cobalt:#3D6BFF`(2차 · 링크/정보/대비 · `::selection`). 그 외 = 흰(`--fg`)·스포티파이 블랙(`--bg:#121212`).
- **글래스모피즘**: `--glass`/`--glass-2`(프로스티드 표면) · `--glass-line`(엣지 하이라이트) · `--blur-m:16`/`--blur-l:24`(구조토큰). 계승 적용처 = PIN 패드(`.lk-pad`)·하단 네비(`.ynav`)·히어로 카드(`.ym-access-card`).
- **그림자·스크림**(절대1: raw 금지→토큰): `--shadow-card`(글래스 카드·히어로 포스터 그림자) · `--bg-scrim`(step1 포스터 전면 하단 딤·가독).
- **픽토그램 액티브** = 브랜드 라임(`.ynav button.on{color:var(--accent)}`) — nomute 하단바 계승, **색만 브랜드**(재설계 금지). 비활성 픽토 = `--mut`.
- 폐지: `--bubble-me` 보라→`var(--accent)` · `--accent-1/2`(오렌지/코발트)·`--m-*`(라이트)·`--sky`·`--cream` 제거 · 메인 화면 라이트→다크.
- 강제: `check_refs.check_design()` accent 패턴 = `rgba(207,255,64)`/`#cfff40`·baseline 0(새 브랜드 raw = var() 강제). 미러 = base.css/tokens.css(`build_design_mirror.py build`).
- **절대명령#1 기계강제(260704 · 15인 교차검증 v2)**: `design-tokens.lock`(승인 원장) — `:root` 새 토큰이 락 미등재면 `check_refs.check_token_lock()` rc=1(커밋 차단·승인=락 등재). 계승 3티어(정확→근접 자동→갱신) · 갱신 2티어(값=승인+check / 구조 토큰 신설=기틀=교차검증) · raw 예외축(기하·안무·광학·OS·로컬z·box-shadow). 포터블 이식판 = `docs/절대명령1_포터블.md`.
- **팔레트 확립본(시각 정본·260704)** = `docs/브랜드_팔레트_확립본.html` — 강조 2(라임 `--accent`+코발트 `--cobalt`)·의미 `--danger`/`--arm`·중립 흰/스포티파이블랙·글래스. **이 팔레트 밖 색 금지.** 챗창 `--yeta-bg`=`--bg`(스포티파이 블랙) 통일 + 글래스 엣지. nomute 전용(편향·수집함·서브코어 accent-3~5·이력 보라) 제거.
