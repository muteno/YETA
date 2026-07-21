#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""yeta_aeri_cand.py — 신규 주민 '애리쌤' 이미지 일괄 생성·탑재(운영자 260721 "제미나이 말고 지피티로 얼굴 만들고 일반 사람처럼 탑재 · 지도도 · 표정 위주 8장").

Gemini 월 지출 한도 429(260721 실측)로 OpenAI(gpt-image = yeta_char_art.py 10인 초상과 동일 축)로 전환. 3종 일괄:
  ① 초상 1장(2:3) → viewer/assets/yeta_char/aeri.png(+webp 768w) + 상단 정사각 512² 크롭 av/aeri.webp + roster avatar 자동 주입(= 일반 주민 탑재 규약 · yeta_char_art 동형)
  ② 지도 워커 스프라이트 → viewer/assets/yeta_map/char_aeri.png(그린스크린 → 크로마키 → 트림 → 320px = yeta_map_char.py 동형)
  ③ 표정 갤러리 8장(평범한 사무실 배경 · 표정이 분위기 전달 · 클로즈업/상반신/전신 카메라 각도 변주) → viewer/characters/aeri/<표정>_01.webp(용량 = webp만 보존)
수동 dispatch 전용(⚠️ OpenAI 유료 종량제 · 자동 트리거 금지 = 이미지 파이프 공통 규약).
멱등: 있으면 skip(FORCE=1 재생성). 게이트 = OPENAI_API_KEY(없으면 no-op).
"""
import base64, io, json, os, re, shutil, subprocess, sys, time, urllib.request

KEY = os.environ.get("OPENAI_API_KEY", "") or os.environ.get("OPENAI_API_KEY_nomute", "")
MODEL = (os.environ.get("OPENAI_IMAGE_MODEL") or "gpt-image-2").strip()
API = "https://api.openai.com/v1/images/generations"
FORCE = os.environ.get("FORCE", "") == "1"
CHAR_DIR = "viewer/assets/yeta_char"
AVDIR = os.path.join(CHAR_DIR, "av")
MAP_DIR = "viewer/assets/yeta_map"
EXPR_DIR = "viewer/characters/aeri"
ROSTER = "apps/yeta/characters/roster.json"
AV_URL = "assets/yeta_char/av/aeri.webp"

# 인물 스펙 고정(카드 정본 = aeri.md 수치 주석) — 미형 보정 금지가 정체성: 평범한 인상의 52세.
WHO = ("a plain ordinary-looking Korean woman in her early 50s — NOT glamorous, NOT beautified, believable everyday middle-aged face, "
       "light-brown short bob haircut, glasses, slightly dated old-fashioned styling with a knit cardigan, silk scarf and a small brooch "
       "(not nerdy, just a bit behind the trends)")

# ① 초상(주민 표준 · yeta_char_art BASE 결 계승 — 단 '미형' 가드 반전)
PORTRAIT = ("Character portrait, polished Korean manhwa / webtoon key-art illustration, painterly semi-realistic, "
            "half-body (waist-up) shot, vertical 2:3 composition, one single original fictional character, " + WHO + ", "
            "standing in her small second-floor culture classroom in Mueum-dong — a back-alley Seoul neighborhood where the night runs longer than the day — "
            "in front of a wall crowded with framed two-shot photos and autographs, "
            "a modest self-effacing smile that doesn't quite open up, warm lamplight against deep shadows, "
            "a restrained palette with a muted antique-gold (#c9a86b) accent, "
            "no text, no caption, no watermark, no logo, no border.")

# ② 지도 스프라이트(yeta_map_char.py BASE 동형 — 걷는 치비 한 컷 · 그린스크린)
SPRITE = ("tiny cute chibi full-body character sprite for a cozy village map game, 3/4 top-down view, "
          "mid-step walking pose facing slightly left, flat pastel cartoon style with soft outlines, "
          "a plain middle-aged Korean woman with a light-brown short bob and glasses, knit cardigan and scarf, "
          "clutching a folder of papers to her chest while glancing sideways curiously, muted antique-gold color accents, busybody quick walk. "
          "Single character only, centered, whole body visible with margin. "
          "Plain solid pure bright green background color #00FF00 filling the entire frame (chroma key). "
          "No text, no letters, no watermark, no shadow on the ground.")

# ③ 표정 갤러리(운영자 260721 "평범한 사무실 · 표정 위주 · 전신/상반신 · 카메라 각도 다양 · 분위기는 표정이 나타냄")
EXPR_BASE = ("Expressive character study, polished Korean manhwa / webtoon key-art illustration, painterly semi-realistic, "
             "vertical 2:3 composition, one single original fictional character, " + WHO + ", "
             "inside a plain ordinary small office-like culture classroom (beige walls, cluttered desk, bookshelf, framed photos), "
             "THE FACIAL EXPRESSION carries the entire mood of the image, "
             "no text, no caption, no watermark, no logo, no border. Shot — ")
EXPRS = [
    ("gossip_sparkle_01",   "upper-body shot leaning in across the desk toward the camera, eyes sparkling wide behind glasses, one hand half-covering a thrilled conspiratorial grin, mid-whisper of a juicy secret."),
    ("flustered_wave_01",   "upper-body three-quarter angle, flustered and shrinking, waving both hands to deflect a compliment, awkward embarrassed half-smile, shoulders pulled in, gaze slipping sideways."),
    ("proud_wall_01",       "full-body shot standing beside a photo-covered wall, chin slightly lifted, hands clasped in front, a quietly proud contained smile trying not to show."),
    ("frozen_startle_01",   "full-body side-angle shot at the doorway, frozen mid-step, eyes wide and stiff with panic behind glasses, clutching her folder, caught by someone she idolizes."),
    ("brooding_night_01",   "upper-body shot at a dim desk lit by a single lamp at night, glasses held in one hand, staring down deflated, a bitter wounded expression chewing over a slight."),
    ("lecture_confident_01","upper-body front shot mid-lecture, pointing a pen forward, animated confident teaching face, eyebrows raised, the only place she shines directly."),
    ("wistful_drawer_01",   "close-up over-the-shoulder low-angle shot, gazing down at an old manuscript bundle inside a desk drawer, wistful longing eyes, lips slightly pressed."),
    ("cold_smirk_01",       "close-up slightly high-angle shot, a cooled polite smile that doesn't reach the skeptical narrowed eyes, listening to someone else's name-dropping."),
]


def openai_image(prompt, size="1024x1536"):
    """yeta_char_art.py openai_image 동형(자립형 규약)."""
    payload = {"model": MODEL, "prompt": prompt, "size": size, "n": 1}
    req = urllib.request.Request(API, data=json.dumps(payload).encode(),
                                 headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                d = (json.load(r).get("data") or [{}])[0]
            b = d.get("b64_json")
            if b:
                return base64.b64decode(b)
            u = d.get("url")
            if u:
                with urllib.request.urlopen(u, timeout=120) as r2:
                    return r2.read()
            print("  ⚠️ 이미지 파트 없음", flush=True)
            return None
        except Exception as e:
            print(f"  ⚠️ 생성 실패: {e}", flush=True)
            if attempt == 0:
                time.sleep(5); continue
    return None


def webp(path, width=768, q="82"):
    """뷰어 서빙용 webp 사본 — yeta_char_art.py 동형. ffmpeg 없으면 None(png 원본 유지)."""
    if not shutil.which("ffmpeg"):
        return None
    out = path[:-4] + ".webp"
    try:
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", path, "-vf", f"scale={width}:-2",
                        "-quality", q, out], check=True, timeout=120)
        return out
    except Exception as e:
        print(f"  ⚠️ webp 변환 실패(비치명): {e}", flush=True)
        return None


def avatar_crop(png_path):
    """상단·가로중앙 정사각 512² webp = 작은 얼굴(yeta_char_art.py 동형 · 260713 운영자 눈검증 프레이밍)."""
    if not shutil.which("ffmpeg"):
        print("  ⚠️ ffmpeg 없음 — av 크롭 생략", flush=True); return None
    os.makedirs(AVDIR, exist_ok=True)
    out = os.path.join(AVDIR, "aeri.webp")
    try:
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", png_path,
                        "-vf", "crop=iw/2:iw/2:iw/4:0,scale=512:512", "-quality", "86", out],
                       check=True, timeout=120)
        return out
    except Exception as e:
        print(f"  ⚠️ av 크롭 실패(비치명): {e}", flush=True); return None


def set_avatar(text, pid, url):
    """roster.json id 블록 안 avatar 값만 치환(yeta_char_art.py 동형 · 수제 포맷 보존)."""
    m = re.search(r'"id"\s*:\s*"%s"' % re.escape(pid), text)
    if not m:
        return text, False
    nxt = re.search(r'"id"\s*:\s*"', text[m.end():])
    end = m.end() + nxt.start() if nxt else len(text)
    seg, n = re.subn(r'"avatar"\s*:\s*"[^"]*"', '"avatar": "%s"' % url, text[m.end():end], count=1)
    if n == 0:
        return text, False
    return text[:m.end()] + seg + text[end:], True


def chroma_cut(png_bytes, size=320):
    """그린스크린 제거 → 투명 PNG + bbox 트림 + 축소(yeta_map_char.py 동형 · fail-soft)."""
    try:
        from PIL import Image
    except Exception:
        print("  ⚠️ Pillow 없음 — 원본 저장 폴백", flush=True)
        return png_bytes
    try:
        im = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
        px = im.load()
        w, h = im.size
        for y in range(h):
            for x in range(w):
                r, g, b, a = px[x, y]
                if g > 120 and g > r * 1.6 and g > b * 1.6:
                    px[x, y] = (0, 0, 0, 0)
                elif g > 90 and g > r * 1.25 and g > b * 1.25:
                    m = max(r, b)
                    px[x, y] = (r, min(g, int(m * 1.15)), b, a)
        bbox = im.getbbox()
        if bbox:
            im = im.crop(bbox)
        im.thumbnail((size, size), Image.LANCZOS)
        out = io.BytesIO()
        im.save(out, "PNG", optimize=True)
        return out.getvalue()
    except Exception as e:
        print(f"  ⚠️ 크로마키 실패({e}) — 원본 저장 폴백", flush=True)
        return png_bytes


def main():
    if not KEY:
        print("OPENAI_API_KEY 없음 — 애리 이미지 생성 생략(no-op)"); return 0
    made = 0

    # ① 초상 + av 크롭 + roster 배선
    os.makedirs(CHAR_DIR, exist_ok=True)
    portrait = os.path.join(CHAR_DIR, "aeri.png")
    if os.path.exists(portrait) and not FORCE:
        print("skip 초상(기존)")
    else:
        print("생성 초상 …", flush=True)
        png = openai_image(PORTRAIT)
        if png:
            open(portrait, "wb").write(png)
            webp(portrait)
            made += 1
            print(f"  ✓ {portrait} ({len(png)//1024}KB)", flush=True)
    if os.path.exists(portrait):
        if avatar_crop(portrait) and os.path.exists(ROSTER):
            roster = open(ROSTER, encoding="utf-8").read()
            roster, ok = set_avatar(roster, "aeri", AV_URL)
            if ok:
                open(ROSTER, "w", encoding="utf-8").write(roster)
                print("  ✓ roster avatar 배선", flush=True)
            else:
                print("  ⚠️ roster 주입 실패(avatar 키 없음?)", flush=True)

    # ② 지도 워커 스프라이트
    os.makedirs(MAP_DIR, exist_ok=True)
    sprite = os.path.join(MAP_DIR, "char_aeri.png")
    if os.path.exists(sprite) and not FORCE:
        print("skip 스프라이트(기존)")
    else:
        print("생성 지도 스프라이트 …", flush=True)
        png = openai_image(SPRITE, size="1024x1024")
        if png:
            open(sprite, "wb").write(chroma_cut(png))
            made += 1
            print(f"  ✓ {sprite}", flush=True)

    # ③ 표정 갤러리 8장(webp만 보존 — 용량)
    os.makedirs(EXPR_DIR, exist_ok=True)
    for name, desc in EXPRS:
        final = os.path.join(EXPR_DIR, f"{name}.webp")
        tmp_png = os.path.join(EXPR_DIR, f"{name}.png")
        if (os.path.exists(final) or os.path.exists(tmp_png)) and not FORCE:
            print(f"skip {name}(기존)"); continue
        print(f"생성 {name} …", flush=True)
        png = openai_image(EXPR_BASE + desc)
        if not png:
            continue
        open(tmp_png, "wb").write(png)
        if webp(tmp_png):
            os.remove(tmp_png)   # webp 성공 시 png 미보존(갤러리 용량 규약 · 초상만 png 편집 베이스 유지)
        made += 1
        print(f"  ✓ {name}", flush=True)
        time.sleep(2)

    print(f"완료 — 신규 {made}건")
    return 0


if __name__ == "__main__":
    sys.exit(main())
