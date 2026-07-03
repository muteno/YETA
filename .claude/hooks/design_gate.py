#!/usr/bin/env python3
"""PostToolUse 디자인 게이트(260702) — Edit/Write 대상이 UI 파일이면 즉시 check_refs 디자인 검사.
위반 = exit 2 → stderr가 모델에 피드백돼 같은 턴에서 자가수정(§🎨 계승 강제의 세션내 버전).
커밋 게이트보다 한 단계 엄격: '방금 편집한 파일'의 raw 증가 WARN도 여기선 차단(지금 고치는 게 제일 쌈).
비UI 파일은 무간섭(exit 0·출력 0) — 일반 작업 마찰 없음."""
import json, sys, os, io, re, contextlib

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)
fp = (data.get('tool_input') or {}).get('file_path') or ''
root = os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()
if not fp:
    sys.exit(0)
try:
    rel = os.path.relpath(os.path.abspath(fp), root).replace(os.sep, '/')
except ValueError:
    sys.exit(0)
if not re.match(r'^(viewer/.*\.(html|css)|구성도/.*\.(html|css))$', rel):
    sys.exit(0)

os.chdir(root)
sys.path.insert(0, os.path.join(root, 'shared'))
buf, rc = io.StringIO(), 0
with contextlib.redirect_stdout(buf):
    try:
        import check_refs
        for fn in ('check_design', 'check_icon_ssot', 'check_tokens_link',
                   'check_soremeori', 'check_autocomplete', 'check_viewer_js'):
            try:
                rc |= (getattr(check_refs, fn)() or 0)
            except Exception as e:
                print('%s 스킵(비차단): %s' % (fn, e))
        try:
            import build_design_mirror
            if hasattr(build_design_mirror, 'check'):
                rc |= (build_design_mirror.check() or 0)
        except Exception as e:
            print('mirror 검사 스킵(비차단): %s' % e)
    except Exception as e:
        print('check_refs 로드 실패(비차단): %s' % e)
out = buf.getvalue()
# 방금 편집한 파일의 raw 증가 WARN → 세션내 승격 차단(죽은토큰·× 문자 등 기존 WARN은 경고 유지)
esc = re.escape(rel)
if re.search(r'raw (hex|blur|accent_\w+) \d+ > baseline', out) and re.search(esc + r': raw ', out):
    rc = 1
if rc:
    sys.stderr.write(
        '🎨 디자인 게이트 위반 — 계승이 디폴트(CLAUDE.md §🎨). raw 값 창작 금지 → viewer/index.html :root의 '
        'var() 토큰 사용. 컴포넌트는 docs/CII_컴포넌트계승인덱스.md 정본 셀렉터 계승. '
        '기틀에 없는 값이 정말 필요하면 임의로 만들지 말고 운영자에게 물어라 — 승인 시 :root 토큰+거울 재생성+CII 행+baseline 사유로 기틀 편입이 먼저다:\n' + out)
    sys.exit(2)
print(out.strip() or '✅ 디자인 게이트 통과')
sys.exit(0)
