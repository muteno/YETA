# AGENTS.md — 제타(yeta) 공통 계약 (모델 불문·260702)

Claude 외 모델/도구로 이 저장소를 작업할 때도 아래는 동일하게 유효하다. (Claude Code는 CLAUDE.md + .claude/ 훅이 자동 적용.)

## 🎨 디자인 — 계승이 디폴트
1. 모든 UI/UX 작업 = 기존 토큰·컴포넌트 **계승이 디폴트**. 새 색/px/blur/radius/scale 창작 금지(예외는 운영자 명시 때만).
2. 값 SSOT = `viewer/index.html` `:root` 단 하나. raw 값 대신 `var()` 토큰 — 없으면 :root에 토큰 추가가 먼저(추가 후 `python3 shared/build_design_mirror.py build`).
3. 새 버튼·모달·입력칸·아이콘 = `docs/CII_컴포넌트계승인덱스.md` 정본 셀렉터 복사·계승(재설계 금지). 버튼·눌림 패턴 = `구성도/00_가이드북_버튼인터랙션.html`. 눌림 scale = `--press-*` 토큰.
4. `구성도/base.css`·`viewer/tokens.css` = build 산출 거울 — 직접 수정 금지.
5. **기틀에 없는 값/형태가 필요하면 → 작업 멈추고 운영자에게 명시적으로 질문**(임의 창작 금지). 승인분은 즉시 기틀 편입: :root 토큰 → 거울 재생성 → CII 행 → baseline 사유(운영자 지시 260702).

## 게이트
- 커밋 전 `python3 shared/check_refs.py` 필수(pre-commit 훅이 자동 강제 — 셋업: `git config core.hooksPath .githooks`).
- 규칙 전문·프로젝트 구조 = `CLAUDE.md` (특히 §🎨).
