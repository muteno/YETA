#!/usr/bin/env python3
"""노뮤트 디자인토큰 거울 — viewer :root(값 SSOT) → 구성도/base.css 자동투영.

구조(§🎨 closed-loop ⓐ · 260621):
  값 SSOT = viewer/index.html :root  ← 라이브 앱이 실제 렌더하는 값. 토큰값 수정은 여기서만.
       │  build  (:root 블록 통째로 → base.css AUTO-MIRROR 블록)
       ▼
  거울    = 구성도/base.css AUTO-MIRROR 블록  ← 구성도 데모(사람이 보는 설계도)가 link.

손 베끼기 폐지: 예전엔 base.css에 토큰 몇 개만 손으로 베껴 → viewer 바뀌면 조용히 stale.
이제 build가 viewer :root를 통째 복사 = 거울이 항상 정본을 따름(드리프트 0).

서브커맨드:
  build : viewer :root → base.css AUTO-MIRROR 블록 갱신(기본 동작).
  check : 거울이 현재 viewer :root와 일치하는지 대조. 불일치 = exit 1(드리프트 게이트).

안전: AUTO-MIRROR 블록은 build가 덮어쓴다(직접수정 금지·다음 build에 날아감).
      블록 밖 손글씨 룰(body 폰트·중앙정렬·버튼 볼드·상태 타이포)은 보존.
사용: python3 shared/build_design_mirror.py check
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIEWER = os.path.join(ROOT, "viewer", "index.html")
BASECSS = os.path.join(ROOT, "구성도", "base.css")
TOKENSCSS = os.path.join(ROOT, "viewer", "tokens.css")   # STAGE3: 4뷰어 공유 구조토큰(색 제외) — index :root 파생

START = "/* === AUTO-MIRROR:START — viewer/index.html :root 자동투영. 직접수정 금지(shared/build_design_mirror.py build) === */"
END = "/* === AUTO-MIRROR:END === */"

# viewer 첫 :root {…} 블록(= 토큰 SSOT). :root 안엔 중첩 중괄호 없음 → 첫 '}'가 닫음.
_ROOT = re.compile(r"^[ \t]*:root[ \t]*\{.*?\n[ \t]*\}", re.S | re.M)
_BLOCK = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)


def extract_root():
    html = open(VIEWER, encoding="utf-8").read()
    m = _ROOT.search(html)
    if not m:
        # RuntimeError(SystemExit 아님) — check_refs의 except Exception이 graceful-skip 하도록(감사1·9).
        raise RuntimeError("viewer :root 블록을 못 찾음")
    # viewer 원본 들여쓰기(2/4/2)를 그대로 보존 — 거울이 정본의 바이트를 그대로 비춤.
    return m.group(0).strip("\n")


# ── STAGE3: 공유 구조토큰 tokens.css (색 제외·index :root 파생) ──────────────────
# 분신술 10인(260628) 수렴: 원안 '전체 :root 상속'은 4뷰어 재색칠 회귀 → 폐기. 안전형 =
# 구조 토큰(반지름·간격·blur·버튼·타이포·모션·z·눌림)만 index에서 파생해 4뷰어가 link.
# 색·팔레트(--bg/--fg/--mut/--line/--accent/의미색…)는 *뷰어별 정체성*이라 inline 유지(제외).
# 픽셀0: 4뷰어는 구조값을 raw px로 쓰고 var(구조토큰) 미참조 → link해도 렌더 불변, 신규 컴포넌트만 어휘 획득.
# SSOT는 여전히 index :root. tokens.css는 base.css처럼 build 파생물(직접수정 금지·게이트 정합).
_TOKENS_HEADER = (
    "/* ⚠️ 자동생성 — 직접수정 금지. 값 SSOT = viewer/index.html :root. 다음 build에 덮어씀.\n"
    "   생성: shared/build_design_mirror.py build (§🎨 STAGE3 · 분신술10 260628).\n"
    "   내용 = index :root의 *구조 토큰만*(반지름·간격·blur·버튼·타이포·모션·z·눌림). 색/팔레트는 제외 —\n"
    "   각 뷰어가 자기 :root에 인라인 유지(뷰어별 정체성). 4뷰어(thumb/ly/k/comp)가 link해 신규 var() 통일. */"
)
# 구조 토큰 판정 — 색/의미색/팔레트와 접두사가 겹치지 않음(검증: --bg/--glass/--line/--accent/--fg/--mut/
#   --danger/--warn/--amber/--info/--bias/--on-*/--hist/--arm/--thumb 중 아래 접두사로 시작하는 것 0).
_STRUCT_EXACT = {"--r", "--font-status", "--ease"}
_STRUCT_PREFIX = ("--r-", "--sp-", "--blur-", "--btn", "--fs-", "--fw-", "--lh-", "--dur", "--z-", "--press-")


def _is_struct(name):
    return name in _STRUCT_EXACT or name.startswith(_STRUCT_PREFIX)


def extract_struct_tokens():
    """index :root에서 구조 토큰 (name, value) 목록을 *원본 순서대로* 반환(색 제외)."""
    root = extract_root()
    inner = root[root.index("{") + 1: root.rindex("}")]
    inner = re.sub(r"/\*.*?\*/", "", inner, flags=re.S)   # 주석 통째 제거(선행·줄끝 둘 다) → split 정확
    out = []
    for decl in inner.split(";"):
        decl = decl.strip()
        if not decl.startswith("--") or ":" not in decl:
            continue
        name, val = decl.split(":", 1)
        name, val = name.strip(), val.strip()
        if _is_struct(name) and val:
            out.append((name, val))
    if not out:
        raise RuntimeError("index :root에서 구조 토큰을 못 찾음")
    return out


def render_tokens():
    """tokens.css 전체 텍스트 반환(파일 안 씀). 결정적 — check가 바이트 대조."""
    lines = [_TOKENS_HEADER, ":root {"]
    for name, val in extract_struct_tokens():
        lines.append("  %s: %s;" % (name, val))
    lines.append("}")
    return "\n".join(lines) + "\n"


def build_tokens():
    open(TOKENSCSS, "w", encoding="utf-8").write(render_tokens())
    print("✅ 구조토큰 build — viewer/tokens.css 를 index :root 구조토큰으로 동기화.")
    return 0


def check_tokens():
    if not os.path.exists(TOKENSCSS):
        print("⚠️ 구조토큰 check 스킵 — viewer/tokens.css 없음")
        return 0
    cur = open(TOKENSCSS, encoding="utf-8").read()
    want = render_tokens()
    if cur != want:
        print("❌ 구조토큰 드리프트 — viewer/tokens.css ≠ index :root 구조토큰. "
              "`python3 shared/build_design_mirror.py build` 로 동기화하라(§🎨 STAGE3).")
        return 1
    # tokens.css에 색(hex/rgba) 유입 금지 — 구조 전용 불변식(분신술3).
    if re.search(r"#[0-9a-fA-F]{3,8}\b|rgba?\(", cur):
        print("❌ 구조토큰 오염 — viewer/tokens.css 에 색값(hex/rgba) 발견. 색은 뷰어별 inline :root 로(§🎨 STAGE3).")
        return 1
    print("✅ 구조토큰 정합 — viewer/tokens.css = index :root 구조토큰(색 0).")
    return 0


def render():
    """현재 viewer :root를 박은 base.css 전체 텍스트를 반환(파일 안 씀)."""
    root = extract_root()
    block = START + "\n" + root + "\n" + END
    base = open(BASECSS, encoding="utf-8").read() if os.path.exists(BASECSS) else ""   # 부재 시 빈 베이스→삽입경로 도달(감사9)
    if _BLOCK.search(base):
        return _BLOCK.sub(lambda _: block, base)
    # 최초 1회: 마지막 @import 줄 뒤(없으면 맨 앞)에 삽입.
    imports = list(re.finditer(r"^@import[^\n]*\n", base, re.M))
    if imports:
        pos = imports[-1].end()
        return base[:pos] + "\n" + block + "\n" + base[pos:]
    return block + "\n\n" + base


def build():
    out = render()
    open(BASECSS, "w", encoding="utf-8").write(out)
    print("✅ 디자인 거울 build — 구성도/base.css 의 AUTO-MIRROR 블록을 viewer :root로 동기화.")
    build_tokens()   # STAGE3: viewer/tokens.css 공유 구조토큰도 동시 갱신(거울 2호)
    return 0


def check():
    rc = 0
    if not os.path.exists(BASECSS):
        print("⚠️ 디자인 거울 check 스킵 — 구성도/base.css 없음")
    else:
        cur = open(BASECSS, encoding="utf-8").read()
        want = render()
        if cur != want:
            print("❌ 디자인 거울 드리프트 — 구성도/base.css ≠ viewer :root. "
                  "`python3 shared/build_design_mirror.py build` 로 동기화하라(§🎨 ⓐ).")
            rc = 1
        else:
            print("✅ 디자인 거울 정합 — 구성도/base.css AUTO-MIRROR = viewer :root.")
    if check_tokens() != 0:   # STAGE3: tokens.css 정합·색오염 게이트(거울 2호)
        rc = 1
    return rc


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "check":
        sys.exit(check())
    elif cmd == "build":
        sys.exit(build())
    else:
        print("사용: build_design_mirror.py [build|check]")
        sys.exit(2)
