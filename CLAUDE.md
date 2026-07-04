# 말벗 제타(yeta) — 캐릭터챗 (CLAUDE.md)

> 매 세션 자동 로드. yeta는 **캐릭터챗 단독 앱**(nomute-editor에서 260703 분리·독립 레포 `muteno/yeta`). **반말·사족 없이·결론부터.** 응답은 첫 글자부터 한국어(코드·경로·고유명사만 예외).

## 🎬 앱 개요
- **말벗 제타** = 무음동 10인 페르소나와의 랜덤 톡방. 세션 = R2 비공개 **단일 스레드**(맥락·관계노트 공유).
- 페르소나 = **랜덤 뽑기 + 🎲 재뽑기**(고정 선택 없음·화자만 교체·맥락 승계). 내 버블 = 네온레몬(`--bubble-me=var(--brand)`·잉크 글자 · 260704). *나레이션* = 이탤릭.
- 답장 = `claude -p`(구독 OAuth) · GitHub Actions dispatch · **웜 세션 루프**(답장 후 대기 → 후속 메시지 같은 런 즉답).
- 다이얼 = model(opus 4.8 / sonnet-5) × effort(low/''/max) — 턴별 박제. 기본 = opus×low(30초 컷).

## 🎨 디자인 계약 — 계승이 디폴트 (기틀·항상 유효)
> "디자인 기틀이 계속 바뀌는" 것을 기계로 차단하는 3층 방어(nomute 260703 이식). 규칙 SSOT = 이 절.
1. 모든 UI/UX = **기틀에 이미 있는 형태만** 구현. 새 색/px/blur/radius/scale/컴포넌트 임의 창작 **절대 금지**.
2. **값 SSOT = `viewer/index.html` `:root` 단 하나**(34토큰). raw 값 대신 `var()` 토큰.
3. 기틀에 없는 값 필요 → **작업 멈추고 운영자에 질문**(왜 필요 + 가장 가까운 기존 후보). 승인분은 즉시 편입: `:root` 토큰 추가 → `python3 shared/build_design_mirror.py build`(거울 재생성) → `docs/CII_컴포넌트계승인덱스.md` 행 → check_refs baseline 사유.
4. 새 버튼·모달·입력칸·아이콘 = **CII 정본 셀렉터 계승**(재설계 금지). 버튼·눌림 패턴 = `구성도/00_가이드북_버튼인터랙션.html`. 눌림 scale = `--press-*` 토큰.
5. `viewer/tokens.css`·`구성도/base.css` = **build 산출 거울**(직접 수정 금지·다음 build에 덮어씀).
6. **3층 강제**: ① SessionStart/UI턴 = `.claude/hooks/design_digest.py`가 계약 자동 주입 ② UI 파일 저장 후 = `.claude/hooks/design_gate.py`가 check_refs 디자인 게이트(위반 exit 2) ③ 커밋 = `.githooks/pre-commit`이 `check_refs` 강제(`core.hooksPath=.githooks`는 design_digest가 세션마다 자동 설정). 타 모델 = `AGENTS.md`.
7. **색은 yeta 팔레트 — 브랜드 = 네온레몬 고정**(`--brand #CFFF40`·운영자 260704·**이 레포 한정**) + 근흑. nomute 녹색 브랜드와 다름. 구조 토큰(반지름·간격·타이포·모션·눌림)만 계승, 색은 yeta 정체성. 적용 완료(260704): **다크 온리**(운영자 "어두운 메인만") · 메인 = 다크 포스터 히어로 V2(YE·TA 레몬블록 + ZETA 글로우 무대 — `viewer/assets/brand/zeta.png` 삽입 시 자동 표시·그레이스케일 강제) · 챗 = 레몬 버블+잉크(`--m-fg`) · 라이트 V1 팔레트 폐지. 스펙 = 페이지 구성도 01~06(`구성도/01_페이지맵_yeta.html` 색인). **CTA 정본 = `.bpill`**(레몬 아웃라인 알약·운영자 260704 레퍼런스) · **타이포 = UI 전반 Pretendard, LEMONMILK는 워드마크 전용**.

## 🗺 구조
- `viewer/` = 뷰어. `index.html`(값 SSOT `:root` + yeta UI) · `tokens.css`(구조토큰 거울) · `nm-svg.js`(아이콘 SSOT) · `_headers`(정적 no-cache)
- `functions/api/yeta.js` = Cloudflare Pages Function 게이트웨이. 7 op = `chars`(로스터)·`get`(세션)·`send`(유저턴+dispatch)·`draw`(페르소나 뽑기)·`warm`(프리웜)·`retry`(재시도)·`reset`. `REPO='muteno/yeta'`·`originOk`=`.pages.dev`.
- `functions/_middleware.js` = pages.dev 우회차단 리다이렉트 **자리(현재 무력화)**. 커스텀 도메인+Access 붙일 때 재활성(⚠️ `yeta.js` originOk도 **동시** 수정 — 안 하면 403 자폭). **현재 = originOk가 `.pages.dev`+`soong.kr`(루트+서브) 허용**(260704 · nomute 도메인 미사용)·**라이브 = `https://yeta.soong.kr`**(+ `soong.kr` 루트 · 둘 다 활성·SSL·실측 통과 260704)·**무인증 공개**(운영자 260704 '공개 유지' — 언제든 Zero Trust Access로 잠금 가능).
- `.github/workflows/yeta-chat.yml` + `.github/scripts/yeta_chat.sh` = 답장 생성(claude -p·페르소나 카드 주입·웜 루프). `push_send.py` = 실패 웹푸시.
- `.github/workflows/yeta-face.yml` + `.github/scripts/yeta_face.py` = 캐릭터 얼굴(프로필) 생성 — **수동 dispatch 전용**(OpenAI gpt-image·⚠️유료 종량제·챗 구독OAuth와 별개 축). 10인 1:1 초상 → 공개 R2 `yeta_face/` → `roster.json` `avatar` 주입 커밋. 멱등(채워진 건 skip·`force=1` 재생성)·자립형(thumb_gen 의존 없음). 얼굴 산출물은 이미 roster에 주입됨 = 이건 *재생성* 도구(260703 이식).
- `.github/workflows/yeta-bg.yml` + `.github/scripts/yeta_bg.py` = 무대 **배경**(bg) 생성 — **수동 dispatch 전용**(Gemini `gemini-3.1-flash-image`·⚠️유료·챗 구독OAuth와 별개 축). 무음동 8무대 9:16(+무드 배리언트 warm/tense/blue = `<<MOOD:x>>` 크로스페이드용) → 공개 R2 `yeta_bg/` → `roster.json` `bg` 주입. 멱등(채워진 건 skip·R2 기존 객체 재과금0·`force=1` 재생성)·자립형(thumb_gen 의존 제거·Gemini 호출·R2 업로드 인라인·260704 이식). 배경도 이미 roster 주입 완료 = *재생성/신규 무드* 도구.
- `shared/` = `claude_transient.sh`(폴오버 SSOT)·`claude_meter.sh`·`inject_character.sh`(카드 강제주입) · `check_refs.py`(게이트)·`build_design_mirror.py`(거울 빌드).
- `apps/yeta/` = 캐릭터 **10인**(`characters/*.md`)·`roster.json`(뷰어 표시 SSOT)·`apps/yeta/00_지침_캐릭터챗.md`·`apps/yeta/10_세계관.md`·`apps/yeta/PEXELS_배경_큐레이션_설계.md`.
- `구성도/`·`docs/CII_컴포넌트계승인덱스.md` = 디자인 블루프린트·계승 인덱스. **페이지 구성도 01~06**(260704) = 유저가 클릭하는 전 화면(페이지맵·메인·PIN·캐릭터선택·대화방·대화상태) — 화면 구조·클릭 전이·상태·네온레몬 브랜드 매핑의 SSOT. **4메뉴 타깃 흐름**(로그인·캐릭터·채팅방 리스트·설정 + room 모델·op 확장·P0 계획) = `docs/흐름설계_기본채팅_4메뉴.md`(운영자 260704 · P0 착수는 §7 확인 2개 답 후).

## 📰 파이프라인 (한 답장 = 이 체인)
뷰어 `send` → `functions/api/yeta.js`(R2 세션 append + `dispatch`) → `yeta-chat.yml` → `yeta_chat.sh`(claude -p · 카드 주입 · 앵커-ts insert) → R2 세션 → 뷰어 폴(적응형 4s).
- 세션 = R2 비공개 `sessions/main.json`. ⚠️ **대화는 레포에 커밋 금지**(public 레포 = 공개 박제 · `contents:read`).
- 지침 강제주입 = `inject_character.sh`가 `00→10→카드` 전문 cat(해시 도장 = 지침 바뀌면 재생성).

## 🔑 인프라 (완전 신규)
- **Cloudflare Pages**: build command **공란**(정적 서빙 · build-viewer 불필요) · output **`viewer`** · `functions/` 자동 인식.
- **R2 바인딩** `YETA_R2`(비공개 세션 버킷) + Pages env `GH_TOKEN`(actions:write PAT) · `YETA_MAX_PER_DAY`(선택).
- **GitHub Secrets**: `CLAUDE_CODE_OAUTH_TOKEN_MUTENO`(필수·가장 먼저) · `R2_ACCOUNT_ID`·`R2_ACCESS_KEY_ID`·`R2_SECRET_ACCESS_KEY`·`YETA_R2_BUCKET` · `VAPID_PRIVATE_KEY`/`VAPID_SUBJECT`(푸시). Variable `ACTIVE_ACCOUNT`(기본 MUTENO). **3계정 폴오버** MUTENO→NOMUTEFB→EMS1130G(운영자 260704·⚠️쿼터 nomute 공유).
- **레포 = public**(roster raw fetch 전제). **첫 실행 순서**: OAuth 토큰을 R2보다 **먼저**(없으면 잡 RED).
- ⚠️ **보안**: middleware 무력화 = `yeta.pages.dev` 무인증 공개. Access 없이 `YETA_R2` 바인딩하면 **대화 노출** → 커스텀 도메인+Cloudflare Access 후 배포(또는 pages.dev에 Access 직접 부착).
- **이미지 파이프(선택·수동)** — 얼굴 `yeta-face.yml`(OpenAI `gpt-image` · GH Secret `OPENAI_API_KEY`, 폴백 `OPENAI_API_KEY_nomute`) · 배경 `yeta-bg.yml`(Gemini `gemini-3.1-flash-image` · GH Secret `GEMINI_API_KEY`). 둘 다 **공개** R2 `R2_BUCKET`·`R2_PUBLIC_BASE`(계정키 `R2_ACCOUNT_ID`/`R2_ACCESS_KEY_ID`/`R2_SECRET_ACCESS_KEY`는 챗과 공용)에 올림. ⚠️ **공개 버킷은 비공개 세션 `YETA_R2_BUCKET`과 별도**(하나는 public 접근 켜야 함) — 공개 R2 5개 없으면 git 폴백(`viewer/assets/yeta_face|yeta_bg/` 커밋). ⚠️ **유료 종량제 = 자동 트리거 금지·수동 dispatch만**. 얼굴·배경은 이미 생성·주입 완료(현재 **nomute R2** `pub-83f8…r2.dev` 서빙)라 이 시크릿·공개버킷은 *재생성/신규 무드·완전독립 이전* 시에만 필요.

## 🤖 모델
- 답장 생성 = **opus 4.8**(`claude-opus-4-8`) 기본 · sonnet-5 다이얼 선택 · effort는 다이얼.
- ⚠️ **`--bare` 절대 금지**(OAuth 안 읽어 인증 즉사). `--safe-mode`는 카나리아 통과 후(`YETA_SAFE`).
- 폴오버 = 3계정 로테이션 MUTENO→NOMUTEFB→EMS1130G(⚠️쿼터 nomute 공유·운영자 260704). 세션 작업자·검증은 opus 4.8 유지.

## ✂️ 수정·검증·커밋
- 커밋 전 **`python3 shared/check_refs.py` rc=0 필수**(pre-commit 자동 강제). UI 변경은 design_gate가 저장 즉시 검사.
- 기틀(구조·`:root`·파이프라인) 변경 = 운영자 확인 필수. 주변부(문구·캐릭터 카드·임계) = 자유.
- 실질 변경은 실측 검증 후 보고. `git show origin/main:<파일>`로 반영 확인.
