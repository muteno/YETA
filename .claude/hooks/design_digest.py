#!/usr/bin/env python3
"""디자인 계약 다이제스트 주입(260702) — "기틀 계승해줘"의 기계화.
SessionStart(startup·resume·compact 직후) = 항상 주입 → 긴 세션·컨텍스트 압축에도 계약 생존.
UserPromptSubmit(--if-ui-prompt) = UI 어휘 감지 턴에만 리마인더(컨텍스트 절약).
토큰 어휘는 viewer/index.html :root에서 라이브 추출 = 절대 안 낡음(inject_guidelines.sh 철학: 읽으라 하지 말고 떠먹인다)."""
import os, re, sys, json, subprocess

root = os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()

if '--if-ui-prompt' in sys.argv:
    try:
        prompt = (json.load(sys.stdin).get('prompt') or '')
    except Exception:
        prompt = ''
    UI = ('버튼', '모달', '팝업', '팝오버', '닫기', '아이콘', '마진', '간격', '여백', '색', '컬러',
          '글래스', 'hover', 'css', 'CSS', '스타일', '레이아웃', '폰트', '타이포', 'radius', 'blur',
          'UI', 'ui', 'UX', '뷰어', '디자인', '애니메이션', '모션', '눌림', '그림자', '테두리', '시안')
    if not any(k in prompt for k in UI):
        sys.exit(0)
    print('[🎨 UI 작업 감지 — 제타 디자인 계약 리마인더] 계승이 디폴트: raw 값 창작 금지, '
          'viewer/index.html :root var() 토큰 사용, 컴포넌트는 docs/CII_컴포넌트계승인덱스.md 정본 셀렉터 계승, '
          '버튼 패턴은 구성도/00_가이드북_버튼인터랙션.html. 규칙 전문 = CLAUDE.md §🎨.')
    sys.exit(0)

# pre-commit 자동 활성화(셋업 제로·멱등) — git이 repo 내 훅을 자동 활성화 안 하므로 여기서(첨부 할일A 반영·260703)
try:
    if os.path.isdir(os.path.join(root, '.githooks')):
        subprocess.run(['git', '-C', root, 'config', 'core.hooksPath', '.githooks'], capture_output=True, timeout=5)
except Exception:
    pass

toks = []
try:
    s = open(os.path.join(root, 'viewer', 'index.html'), encoding='utf-8').read()
    m = re.search(r':root\s*\{(.*?)\}', s, re.S)
    if m:
        toks = sorted(set(re.findall(r'--[a-zA-Z0-9-]+(?=\s*:)', m.group(1))))
except Exception:
    pass

print('''[🔒 절대명령#1 — 디자인 = 루트 토큰 「계승」 또는 「갱신」 (레포 제1·최상단 · CLAUDE.md §🔒)]
· 계승(디폴트·안 물음): 정확 토큰 var() → 없으면 가장 가까운 토큰 자동 계승.
· 갱신(근접조차 없을 때만): 운영자에게 "갱신할지 / 뭘 계승할지(근사 후보)" 물어 승인 후. 구조 토큰 신설=기틀=교차검증.
· 기계강제: design-tokens.lock — :root 새 토큰이 락 미등재면 check_refs 커밋 차단(승인=락 등재·PR diff 리뷰).
· 예외(raw 허용·물음X): 기하·키프레임 안무·광학1px·OS(safe-area)·로컬z·토큰없는 축(box-shadow). 초록 게이트≠전면 준수.

[🎨 제타 디자인 계약 — SessionStart 자동 주입(사용자가 매번 말 안 해도 항상 유효)]
1. 모든 UI/UX 작업 = **기틀에 이미 있는 형태만** 구현(토큰·정본 컴포넌트 계승이 디폴트). 새 색/px/blur/radius/scale/컴포넌트 임의 창작 절대 금지.
2. 값 SSOT = `viewer/index.html` `:root` 단 하나. raw 값 대신 `var()` 토큰.
2-1. **기틀에 없는 게 필요하면 → 작업 멈추고 운영자에게 명시적으로 물어라**(어떤 값/형태가 왜 필요한지 + 가장 가까운 기존 기틀 후보 제시). 임의 진행 금지.
2-2. 운영자 승인분은 **그 자리에서 즉시 기틀 편입**: :root 토큰 추가 → `python3 shared/build_design_mirror.py build` 거울 재생성 → docs/CII_컴포넌트계승인덱스.md 행 추가 → check_refs baseline 사유 기록. 편입 없이 코드에만 박지 마라(고아 변수 = 드리프트 씨앗).
3. 새 버튼·모달·입력칸·아이콘 = `docs/CII_컴포넌트계승인덱스.md` 표의 정본 셀렉터를 복사·계승(재설계 금지). 버튼·눌림·모션 패턴 = `구성도/00_가이드북_버튼인터랙션.html`. 눌림 scale = `--press-*` 토큰 사다리. 시맨틱 아이콘 모션 = 위임 1핸들러(개별 모션 창작 금지). 규칙 전문 = CLAUDE.md §🎨.
4. `구성도/base.css`·`viewer/tokens.css` = build 산출 거울 — 직접 수정 금지.
5. UI 파일 저장 시 PostToolUse 훅이 check_refs 디자인 게이트를 자동 실행 — 위반이면 그 자리에서 고쳐라. 커밋 전 `python3 shared/check_refs.py` 전체 게이트 필수.
사용 가능 토큰(%d개): %s''' % (len(toks), ' '.join(toks)))
