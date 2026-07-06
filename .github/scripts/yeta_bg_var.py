#!/usr/bin/env python3
"""yeta_bg_var.py — 무음동 배경 배리에이션 생성(운영자 260707 "openai 프롬프팅해서 무음동 배경 — 날씨·분위기·시간대·편의점 등 다양하게").

수동 dispatch 전용(⚠️ OpenAI 유료 종량제 · 자동 트리거 금지 = 기존 이미지 파이프 규약).
OpenAI Images API(gpt-image) → `viewer/assets/yeta_bg/var_<slug>.png` 커밋(git 정본 — R2 불요·yeta_face git 폴백 결).
멱등: 이미 있는 slug는 skip(FORCE=1 재생성). 게이트 = OPENAI_API_KEY(없으면 no-op).
활용: 뷰어 무드/장면 배경 후보 — roster `bg` 교체나 씬 연출은 운영자 선택 후 별도 배선.
"""
import base64, json, os, sys, time, urllib.request

KEY = os.environ.get("OPENAI_API_KEY", "") or os.environ.get("OPENAI_API_KEY_nomute", "")
MODEL = (os.environ.get("OPENAI_IMAGE_MODEL") or "gpt-image-2").strip()
API = "https://api.openai.com/v1/images/generations"
FORCE = os.environ.get("FORCE", "") == "1"
OUT = "viewer/assets/yeta_bg"

BASE = ("Moody atmospheric background art for a Korean urban-fantasy chat app, no people, no text or letters, "
        "a quiet back-alley neighborhood in Seoul called Mueum-dong where the night feels longer than the day; "
        "cinematic vertical 9:16 composition, painterly semi-realistic style, deep spotify-black shadows with a "
        "restrained neon lime (#CFFF40) accent glow and occasional cobalt hints, consistent with a dark glassmorphism app. Scene: ")

# 장소 × 시간대 × 날씨(운영자 축: 편의점·다양)
SCENES = [
    ("cvs_dawn",      "a small Korean convenience store glowing alone at 4am, wet asphalt after rain reflecting the signage, one lime-green neon strip, empty street, steam from a hot-food counter"),
    ("alley_rain",    "the alley entrance during a heavy summer night rain, umbrellas' silhouettes absent, rain streaks lit by a single lime signboard, puddles rippling"),
    ("tea_sunset",    "the 24-hour teahouse 'Mueum' window seat at golden sunset, warm amber light spilling onto the alley, steam rising from a teacup on the windowsill, cozy and quiet"),
    ("rooftop_mid",   "a rooftop view over Mueum-dong at exactly midnight, dense low rooftops, one distant radio tower with a blinking light, thin moon, the boundary hour feeling"),
    ("busstop_fog",   "an old bus stop in thick night fog, its lightbox the only light source, a faint lime hue in the fog, benches empty, streetlamp halos"),
    ("playground_3am","an empty neighborhood playground at 3am when the boundary grows thin, swings perfectly still, pale blue otherworldly glow seeping from beyond the fence"),
    ("radio_neon",    "the narrow lane outside the late-night radio booth 'Frequency', rain-slick pavement, warm booth light and cool neon reflections mixing, cables and antennas overhead"),
    ("snow_night",    "the alley under the first snow of winter at night, snowflakes catching the lime signage glow, footprints of a single cat, hushed and tender"),
]


def openai_image(prompt):
    payload = {"model": MODEL, "prompt": prompt, "size": "1024x1536", "n": 1}   # 세로 9:16 근사(모델 지원 세로 사이즈)
    req = urllib.request.Request(API, data=json.dumps(payload).encode(),
                                 headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
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
    except Exception as e:
        print(f"  ⚠️ 생성 실패: {e}", flush=True)
    return None


def main():
    if not KEY:
        print("OPENAI_API_KEY 없음 — 배경 생성 생략(no-op)"); return 0
    os.makedirs(OUT, exist_ok=True)
    made = 0
    for slug, desc in SCENES:
        path = os.path.join(OUT, f"var_{slug}.png")
        if os.path.exists(path) and not FORCE:
            print(f"skip {slug}(기존)"); continue
        print(f"생성 {slug} …", flush=True)
        png = openai_image(BASE + desc)
        if not png:
            continue
        open(path, "wb").write(png)
        made += 1
        print(f"  ✓ {path} ({len(png)//1024}KB)", flush=True)
        time.sleep(2)
    print(f"완료 — 신규 {made}장")
    return 0


if __name__ == "__main__":
    sys.exit(main())
