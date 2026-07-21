#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""yeta_aeri_cand.py — 신규 캐릭터 '애리쌤' 초상 시안 후보 생성(운영자 260721 "제미나이로 몇 개 뽑아주면 내가 골라줄게").

기존 초상 파이프(yeta_char_art.py = OpenAI 10인 확정본)와 별개 축 = **운영자 픽 대기용 후보 N장**(2:3 · Gemini).
수동 dispatch 전용(⚠️ Gemini 유료 = 자동 트리거 금지 · 이미지 파이프 공통 규약).
산출 = viewer/assets/yeta_char/cand/aeri_v<n>.png(+webp 768w) — roster 주입 없음(운영자가 고르면 그때 av 크롭·배선).
멱등: 이미 있는 버전은 skip(FORCE=1 재생성). 게이트 = GEMINI_API_KEY(없으면 no-op).
"""
import base64, json, os, shutil, subprocess, sys, time, urllib.error, urllib.request

KEY = os.environ.get("GEMINI_API_KEY", "").strip()
MODEL = "gemini-3.1-flash-image-preview"
API = "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent".format(MODEL)
FORCE = os.environ.get("FORCE", "") == "1"
OUT = "viewer/assets/yeta_char/cand"

# 공통 결 = yeta_char_art BASE 계승(무음동 만화 키아트) — 단 '미형 보정' 가드 반전: 애리쌤 = 평범한 인상이 정체성(카드 정본).
BASE = ("Character portrait, polished Korean manhwa / webtoon key-art illustration, painterly semi-realistic, "
        "half-body (waist-up) shot, vertical 2:3 composition, one single original fictional character, "
        "a plain ordinary-looking Korean woman in her early 50s — NOT glamorous, NOT beautified, believable everyday middle-aged face, "
        "light-brown short bob haircut, glasses, slightly dated old-fashioned styling (not nerdy, just a bit behind the trends), "
        "set in Mueum-dong — a back-alley Seoul neighborhood where the night runs longer than the day; "
        "warm lamplight against deep shadows, a restrained palette with a muted antique-gold (#c9a86b) accent, "
        "no text, no caption, no watermark, no logo, no border. Scene — ")

# 4안 = 표정·소품·안경만 변주(운영자 픽 폭 확보 — 인물 스펙은 고정)
CANDS = [
    ("v1", "in her small second-floor culture classroom, standing proudly in front of a wall crowded with framed two-shot photos with celebrities and autographs, "
           "thin metal round glasses, a silk scarf and a small brooch on a knit cardigan, a modest self-effacing smile that doesn't quite open up."),
    ("v2", "leaning over a cafe table mid-gossip, eyes sparkling behind slightly slid-down glasses, one hand half-covering her mouth as if sharing a secret, "
           "holding a cup of tea, a floral-pattern blouse a decade out of fashion, lively storytelling energy."),
    ("v3", "a calm formal front-facing portrait, square acetate glasses, a neat but old-fashioned jacket with a scarf pinned by a brooch, "
           "hands folded, chin slightly tucked, a faint awkward smile of someone who dodges compliments."),
    ("v4", "caught glancing away shyly while holding a thick folder of poems against her chest, oval glasses, a plain cardigan over a blouse, "
           "warm but tired eyes, standing at the doorway of her classroom with a '애리의 방' vibe (no readable text), wistful mood."),
]

_USAGE = []


def gemini_image(prompt, aspect="2:3"):
    """yeta_map_char.py gemini_image 동형(자립형 규약)."""
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["IMAGE"],
                             "imageConfig": {"aspectRatio": aspect, "imageSize": "1K"}},
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(API + "?key=" + KEY, data=data, headers={"Content-Type": "application/json"})
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                j = json.loads(r.read().decode())
            um = j.get("usageMetadata") or {}
            if isinstance(um, dict):
                _USAGE.append(int(um.get("totalTokenCount") or 0))
            for cand in j.get("candidates", []):
                for p in cand.get("content", {}).get("parts", []):
                    inl = p.get("inlineData") or p.get("inline_data")
                    if inl and inl.get("data"):
                        return base64.b64decode(inl["data"])
            print("  ⚠️ 이미지 파트 없음", flush=True)
            return None
        except urllib.error.HTTPError as e:
            print(f"  ⚠️ HTTP {e.code}: {e.read()[:200]}", flush=True)
            if attempt == 0:
                time.sleep(8); continue
        except Exception as e:
            print(f"  ⚠️ 생성 실패: {e}", flush=True)
            if attempt == 0:
                time.sleep(8); continue
    return None


def webp(path):
    """뷰어 서빙용 webp 사본(768w·q82) — yeta_char_art.py 동형. ffmpeg 없으면 조용히 생략."""
    if not shutil.which("ffmpeg"):
        return
    try:
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", path, "-vf", "scale=768:-2",
                        "-quality", "82", path[:-4] + ".webp"], check=True, timeout=120)
    except Exception as e:
        print(f"  ⚠️ webp 변환 실패(비치명): {e}", flush=True)


def main():
    if not KEY:
        print("GEMINI_API_KEY 없음 — 애리 후보 생성 생략(no-op)"); return 0
    os.makedirs(OUT, exist_ok=True)
    made = 0
    for tag, desc in CANDS:
        path = os.path.join(OUT, f"aeri_{tag}.png")
        if os.path.exists(path) and not FORCE:
            print(f"skip aeri_{tag}(기존)"); continue
        print(f"생성 aeri_{tag} …", flush=True)
        png = gemini_image(BASE + desc)
        if not png:
            continue
        open(path, "wb").write(png)
        webp(path)
        made += 1
        print(f"  ✓ {path} ({len(png)//1024}KB)", flush=True)
        time.sleep(2)
    print(f"완료 — 신규 {made}장 · 토큰 {sum(_USAGE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
