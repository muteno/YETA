#!/usr/bin/env python3
"""UI 메뉴킷 포터블 자동 재추출기 — 정본(viewer/index.html) → docs/portable/ 킷 재생성.

구조(Q.14 · 260717 — build_design_mirror '거울' 결 계승):
  값·컴포넌트 정본 = viewer/index.html (:root 토큰 · .ynav 하단 알약 네비 · .ydock 챗 도크)
       │  build  (정본 코어를 앵커로 추출 → 킷 4파일 + .kitmeta.json 지문)
       ▼
  킷    = docs/portable/{KST}_UI메뉴킷_포터블_v{N}/  ← 타 레포 이식용 사본(손편집 금지 — 낡으면 build로 v(N+1))

손 베끼기 폐지: v1은 수제 사본이라 정본이 움직이면 조용히 stale.
이제 check가 정본 코어 지문(.kitmeta.json cores_sha1)을 대조 = 드리프트를 기계가 잡음.

서브커맨드:
  build : 정본 코어 추출 → 새 버전 폴더 생성(v = 기존 최대 + 1 · 폴더명 = CLAUDE.md [12] KST 타임스탬프).
  check : 최신 킷 지문 ↔ 현재 정본 코어 대조. 불일치/수제/부재 = exit 1(check_refs에선 WARN-only).

추출 앵커(라인번호 아님 — 파일이 움직여도 따라감):
  :root        = build_design_mirror.extract_root() 재사용(단일 구현)
  .ynav CSS    = '하단 네비 = 플로팅 알약' 주석 ~ 'ymain.reveal .ynav' 등장 애니 줄
  .ydock CSS   = '안2 도킹 네비' 주석 ~ 'yeta-in:focus-within .ydock' 접힘 줄
  마크업       = <nav class="ynav"> · <nav class="ydock"> 블록(각 첫 등장 ~ 닫는 </nav>)
사용: python3 shared/build_menu_kit.py check
"""
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIEWER = os.path.join(ROOT, "viewer", "index.html")
OUT_BASE = os.path.join(ROOT, "docs", "portable")
KIT_RE = re.compile(r"_UI메뉴킷_포터블_v(\d+)$")
KST = timezone(timedelta(hours=9))   # 러너=UTC — 시각은 KST 강제(CLAUDE.md [12] · naive now 금지)

# (앵커 시작 포함줄, 앵커 끝 포함줄) — 정본 주석·셀렉터 문구 기준
_ANCHORS = {
    "ynav_css": ("하단 네비 = 플로팅 알약", ".ymain.reveal .ynav { animation:ynavRise"),
    "ydock_css": ("안2 도킹 네비", ".yeta-in:focus-within .ydock"),
    "ynav_html": ('<nav class="ynav"', "</nav>"),
    "ydock_html": ('<nav class="ydock"', "</nav>"),
}


def _slice(lines, start_mark, end_mark):
    """start_mark 포함 줄부터 그 뒤 첫 end_mark 포함 줄까지(양끝 포함) verbatim."""
    s = next((i for i, l in enumerate(lines) if start_mark in l), None)
    if s is None:
        raise RuntimeError(f"앵커 못 찾음: {start_mark!r}")
    e = next((i for i in range(s, len(lines)) if end_mark in lines[i]), None)
    if e is None:
        raise RuntimeError(f"닫는 앵커 못 찾음: {end_mark!r} (from {start_mark!r})")
    return "\n".join(lines[s:e + 1])


def extract_cores():
    """정본 코어 6종 추출(전부 verbatim — 창작 0)."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import build_design_mirror   # :root 추출 = 거울 빌더와 단일 구현 공유
    html = open(VIEWER, encoding="utf-8").read()
    lines = html.split("\n")
    cores = {k: _slice(lines, a, b) for k, (a, b) in _ANCHORS.items()}
    cores["root"] = build_design_mirror.extract_root()
    m = re.search(r"^[ \t]*@media \(prefers-reduced-motion:reduce\)\{ :root\{.*$", html, re.M)
    if not m:
        raise RuntimeError("reduced-motion :root 가드 줄을 못 찾음")
    cores["press_guard"] = m.group(0)
    return cores


def cores_sha1(cores):
    return hashlib.sha1("\n@@\n".join(cores[k] for k in sorted(cores)).encode("utf-8")).hexdigest()[:12]


def _git_head():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True, timeout=10).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _kits():
    """(버전N, 폴더 절대경로) 목록 — vN 오름차순."""
    if not os.path.isdir(OUT_BASE):
        return []
    out = []
    for d in os.listdir(OUT_BASE):
        m = KIT_RE.search(d)
        if m and os.path.isdir(os.path.join(OUT_BASE, d)):
            out.append((int(m.group(1)), os.path.join(OUT_BASE, d)))
    return sorted(out)


# ── 킷 파일 템플릿(고정 골격 — 코어는 위 추출분 주입 · 데모 무대/안내문은 킷 전용) ──

def _tokens_css(c, stamp, head):
    return f"""/* ═══════════════════════════════════════════════════════════════════
   YETA UI 메뉴킷 · tokens.css — 디자인 토큰(값 사본 · 자동 추출)
   원본(값 SSOT) = YETA 레포 viewer/index.html :root
   추출 = {stamp} · main {head} · 생성기 = shared/build_menu_kit.py (직접수정 금지 — 낡으면 build 재추출)
   ⚠ 타 레포 이식 후: --accent / --accent-rgb 두 줄만 그 레포 브랜드색으로 바꾸면
     활성 필·글로우·라벨색이 전부 자동으로 따라온다(개별 셀렉터 덧칠 금지).
   ═══════════════════════════════════════════════════════════════════ */
{c["root"]}
/* reduced-motion = 눌림 토큰 전역 무효화(1) */
{c["press_guard"]}
"""


def _menu_css(c, stamp, head):
    return f"""/* ═══════════════════════════════════════════════════════════════════
   YETA UI 메뉴킷 · menu.css — 메뉴 컴포넌트(정본 셀렉터 계승 · 재설계 금지)
   원본 = YETA 레포 viewer/index.html (.ynav · .ydock 블록 verbatim)
   추출 = {stamp} · main {head} · 생성기 = shared/build_menu_kit.py (직접수정 금지 — 낡으면 build 재추출)
   선행 로드 = tokens.css · 셀렉터명(.ynav/.ydock/.on)은 바꾸지 말 것 — 이름까지가 계승이다.
   ═══════════════════════════════════════════════════════════════════ */

/* ── 공통 베이스(메뉴 동작에 필수인 최소분만 · 킷 전용 축약) ── */
* {{ box-sizing:border-box; -webkit-tap-highlight-color:transparent; }}   /* 탭 하이라이트 봉합 — 안드로이드 사각 잔상 방지 */

/* ── ① 하단 네비 = 플로팅 알약 (.ynav) — 표시 게이트 = .ymain.unlocked ── */
{c["ynav_css"]}

/* ── ② 챗 도크 = 컴팩트 아이콘-온리 네비 (.ydock) ── */
{c["ydock_css"]}

/* ── 모션 최소화 가드(메뉴 해당분 · 킷 전용 축약 — 원본 reduce 블록의 메뉴 축) ── */
@media (prefers-reduced-motion:reduce){{ .ynav button, .ynav button span {{ transition:none; }} .ymain.reveal .ynav {{ animation:none; }} }}
"""


def _demo_html(c, stamp, head):
    ydock = c["ydock_html"]
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>YETA UI 메뉴킷 — 단독 데모 ({stamp} · main {head} · 자동 추출)</title>
<link rel="stylesheet" href="tokens.css">
<link rel="stylesheet" href="menu.css">
<style>
/* ═══ 데모 전용 무대(이식 대상 아님 — 실제 이식은 tokens.css + menu.css + 아래 마크업만) ═══
   무대 배경 = 팔레트 토큰만으로 만든 글래스 확인용 그라디언트(새 색 창작 0) */
html,body {{ margin:0; height:100%; }}
body {{ background:var(--bg); color:var(--fg); font:var(--fs-body)/var(--lh-base) system-ui,'Pretendard',sans-serif; }}
.ymain {{ position:relative; max-width:420px; height:100dvh; margin:0 auto; overflow:hidden;
  background:
    radial-gradient(60% 42% at 22% 18%, rgba(var(--cobalt-rgb),.28), transparent 70%),
    radial-gradient(52% 38% at 82% 34%, rgba(var(--season-rgb),.22), transparent 70%),
    radial-gradient(70% 50% at 50% 88%, rgba(var(--accent-rgb),.12), transparent 72%),
    var(--bg); }}
.demo-panel {{ position:absolute; inset:0; display:none; place-items:center; padding:var(--sp-3); text-align:center; }}
.demo-panel.on {{ display:grid; }}
.demo-panel b {{ font-size:var(--fs-h2); font-weight:var(--fw-x); display:block; }}
.demo-panel p {{ color:var(--mut); font-size:var(--fs-sm); max-width:30em; }}
.demo-dockrow {{ position:absolute; left:50%; transform:translateX(-50%); bottom:calc(88px + env(safe-area-inset-bottom));
  display:flex; align-items:center; gap:6px; padding:5px 8px; border:1px solid var(--glass-line); border-radius:var(--r-pill);
  background:var(--glass); backdrop-filter:blur(var(--blur-l)); -webkit-backdrop-filter:blur(var(--blur-l)); }}
.demo-dockrow i {{ color:var(--mut); font-size:var(--fs-xs); font-style:normal; padding-right:4px; }}
</style>
</head>
<body>
<!-- 루트 컨테이너 — 원본 게이트 계승: unlocked = 네비 표시 · reveal = 첫 등장 슬라이드업 안무 -->
<div class="ymain unlocked reveal" id="ymain">

  <!-- 데모 패널(이식 대상 아님 · 탭 전환 확인용) -->
  <div class="demo-panel on" data-panel="char"><div><b>캐릭터 탭</b><p>하단 알약 네비를 탭해봐 — 활성 탭은 라임 글래스 필이 늘어나며 라벨이 등장한다(비활성 = 픽토그램-온리).</p></div></div>
  <div class="demo-panel" data-panel="list"><div><b>대화 탭</b><p>같은 메뉴 구조 = 같은 모양. 활성 필 레시피(채움 16% · 테 38% · 인셋 엣지 + 은은 글로우)는 .on 클래스 하나로 전환된다.</p></div></div>
  <div class="demo-panel" data-panel="map"><div><b>지도 탭</b><p>알약 전체는 초투명 글래스(--glass 50% + blur) — 뒤 배경이 비쳐야 정상이다.</p></div></div>
  <div class="demo-panel" data-panel="settings"><div><b>설정 탭</b><p>--accent 토큰 하나만 그 레포 브랜드색으로 바꾸면 활성 필·글로우가 전부 따라온다.</p></div></div>

  <!-- ② 챗 도크(.ydock) 시연 — 원본 마크업 verbatim(자동 추출) -->
  <div class="demo-dockrow"><i>챗 도크 ↓</i>
{ydock}
  </div>

  <!-- ① 하단 네비(.ynav) — 원본 마크업 verbatim(자동 추출) · 픽토그램 = 단일 path SVG(stroke=currentColor) -->
{c["ynav_html"]}
</div>

<script>
// 탭 전환 배선 — 원본 yTab 축약 계승: data-tab → 버튼 .on 토글 + 패널 전환
function yTab(tab) {{
  document.querySelectorAll('#ynav button').forEach(b => b.classList.toggle('on', b.dataset.tab === tab));
  document.querySelectorAll('.demo-panel').forEach(p => p.classList.toggle('on', p.dataset.panel === tab));
}}
document.getElementById('ynav').addEventListener('click', e => {{
  const b = e.target.closest('button[data-tab]'); if (b) yTab(b.dataset.tab);
}});
</script>
</body>
</html>
"""


def _readme(stamp, head, ver):
    return f"""# YETA UI 메뉴킷 (포터블 v{ver} · 자동 추출)

> YETA 웹앱의 **메뉴 UIUX만** 떼어낸 이식용 킷. 폴더째 다른 레포에 복사하면 바로 쓰인다.
> 추출 = {stamp} · YETA main `{head}` · 생성기 = `shared/build_menu_kit.py`(이 폴더 손편집 금지 — 낡으면 `build`로 v{ver + 1} 재추출).

## 뭐가 들었나 (파일 3 + 이 안내)

| 파일 | 역할 | 원본(정본 앵커 자동 추출) |
|---|---|---|
| `tokens.css` | 디자인 토큰 = 값의 원천(색·크기·반지름·blur·모션·눌림) | `viewer/index.html` `:root` |
| `menu.css` | 메뉴 컴포넌트 2종 — ① 하단 플로팅 알약 네비 `.ynav` ② 챗 도크 `.ydock` | 같은 파일 `.ynav`/`.ydock` 블록 |
| `demo.html` | 단독 실행 데모(브라우저로 열면 끝) + 정본 마크업·픽토그램·탭 전환 JS 견본 | 같은 파일 `<nav>` 마크업 |

## 다른 레포에 넣는 법 (3단계)

1. **복사** — 이 폴더를 통째로 가져간다(파일 3개면 충분).
2. **로드** — `tokens.css` → `menu.css` 순서로 `<link>` (토큰이 먼저).
3. **마크업** — `demo.html` 안의 `.ynav`/`.ydock` 블록을 그대로 복사해 배선한다.
   - 네비 표시 게이트: 루트 컨테이너에 `class="ymain unlocked"` (첫 등장 슬라이드업까지 원하면 `reveal` 추가).
   - 탭 전환 = `demo.html` 하단 `yTab()` 12줄이 전부(활성 = `.on` 클래스 하나).

## 브랜드색 갈아입히기 (제일 자주 할 일)

`tokens.css`에서 딱 두 줄:

```css
--accent:#CFFF40; --accent-rgb:207,255,64;
```

이걸 그 레포 브랜드색으로 바꾸면 활성 필 채움·테두리·글로우·라벨색이 **전부 자동으로** 따라온다. 개별 셀렉터에 색을 덧칠하지 말 것.

## 활성 필 레시피 (이 킷의 심장)

활성 탭 하나에 3층이 겹친다 — 이 조합이 "라임 유리 알약" 느낌의 실체:

```css
background:rgba(var(--accent-rgb),.16);    /* ① 채움 16% — 유리에 색 물들이기 */
border-color:rgba(var(--accent-rgb),.38);  /* ② 테두리 38% — 형태 잡기 */
box-shadow:inset 0 1px 0 var(--glass-line),
           0 0 18px rgba(var(--accent-rgb),.14);  /* ③ 인셋 엣지 + 은은한 글로우 */
```

색만 바꾼 변주도 같은 공식(예: YETA 상황 모드 = `--think` 터콰이즈로 동일 3층).

## 지켜야 할 규율 (YETA 디자인방식론 요약 — 어기면 드리프트)

1. **계승이 디폴트** — 새 메뉴를 만들 때 값을 새로 짓지 말고 `var(--token)`으로 참조. raw hex/px 창작 금지.
2. **셀렉터명 유지** — `.ynav`/`.ydock`/`.on`을 리네임하지 않는다. 이름까지가 계승이라 원본과 diff 대조가 산다.
3. **픽토그램 = SVG 단일 path** — 이모지·유니코드 문자 도형(✕ ▲ 등) 금지. `stroke="currentColor"`라 색은 부모가 준다.
4. **눌림 = 토큰 사다리** — `:active`는 `scale(var(--press-s))` 참조. `0.96` 같은 raw scale 창작 금지.
5. **무채 크롬** — 메뉴 알약 자체는 무채 글래스(활성·비활성 = `--accent`/`--mut`뿐). 크롬에 색 틴트를 얹지 않는다.
6. **reduced-motion 존중** — 두 CSS의 `@media (prefers-reduced-motion:reduce)` 블록을 지우지 말 것(접근성).
7. **같은 기능 = 같은 모양** — 픽토 크기·마진·정렬·팔레트가 화면마다 제각각이면 실패작. 도크(`.ydock .on`)도 네비와 같은 필 레시피를 쓰는 이유.

## 원본 정본 위치 (YETA 레포 기준 — 더 가져올 때)

- 값 SSOT = `viewer/index.html` `:root` · 컴포넌트 인덱스 = `docs/CII_컴포넌트계승인덱스.md`
- 버튼·눌림 패턴 = `구성도/00_가이드북_버튼인터랙션.html` · 방식론 전문 = `docs/디자인방식론_YETA.md`
- 팔레트 시각 정본 = `docs/브랜드_팔레트_확립본.html`

> ⚠ 이 킷은 **기계 생성 사본**이다(`.kitmeta.json` = 정본 지문). YETA 안에서 디자인을 고칠 땐 위 정본을 고쳐라 —
> `shared/check_refs.py`가 정본↔킷 어긋남을 감지해 재추출을 리마인드한다(사본 손편집 = 드리프트).
"""


def build():
    cores = extract_cores()
    now = datetime.now(KST)
    stamp = now.strftime("%Y-%m-%d %H:%M KST")
    head = _git_head()
    ver = (_kits()[-1][0] + 1) if _kits() else 1
    dirname = f"{now.strftime('%Y%m%d_%H%M%S')}_UI메뉴킷_포터블_v{ver}"   # CLAUDE.md [12] 네이밍
    out = os.path.join(OUT_BASE, dirname)
    os.makedirs(out, exist_ok=False)
    files = {
        "tokens.css": _tokens_css(cores, stamp, head),
        "menu.css": _menu_css(cores, stamp, head),
        "demo.html": _demo_html(cores, stamp, head),
        "README.md": _readme(stamp, head, ver),
        ".kitmeta.json": json.dumps({"cores_sha1": cores_sha1(cores), "source_commit": head,
                                     "built_kst": stamp, "version": ver}, ensure_ascii=False, indent=1) + "\n",
    }
    for name, body in files.items():
        with open(os.path.join(out, name), "w", encoding="utf-8") as f:
            f.write(body)
    print(f"✅ 메뉴킷 v{ver} 생성 — docs/portable/{dirname}/ (코어 지문 {cores_sha1(cores)} · main {head})")
    return 0


def check():
    """최신 킷 신선도 대조 — 0=일치 · 1=재추출 필요(부재/수제/드리프트). check_refs에선 WARN-only 호출."""
    try:
        cur = cores_sha1(extract_cores())
    except Exception as e:
        print("⚠️ 메뉴킷 게이트 스킵 — 정본 코어 추출 실패:", e)
        return 0   # 앵커 유실 = 추출기 정비 사안 — 커밋 게이트에선 소음 차단
    kits = _kits()
    if not kits:
        print("⚠️ 메뉴킷 없음 — python3 shared/build_menu_kit.py build 로 생성")
        return 1
    ver, latest = kits[-1]
    meta_p = os.path.join(latest, ".kitmeta.json")
    if not os.path.exists(meta_p):
        print(f"⚠️ 메뉴킷 v{ver} = 수제 사본(지문 없음) — build 로 기계판 재추출 권장")
        return 1
    meta = json.load(open(meta_p, encoding="utf-8"))
    if meta.get("cores_sha1") != cur:
        print(f"⚠️ 메뉴킷 드리프트 — 정본 코어(:root/.ynav/.ydock)가 v{ver}({meta.get('cores_sha1')}) 이후 변경({cur})"
              " → python3 shared/build_menu_kit.py build 재추출")
        return 1
    print(f"✅ 메뉴킷 신선 — v{ver} 지문 {cur} = 현재 정본 코어 일치.")
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "check":
        sys.exit(check())
    elif cmd == "build":
        sys.exit(build())
    print(f"사용법: build_menu_kit.py [build|check] (받은 인자: {cmd})")
    sys.exit(2)
