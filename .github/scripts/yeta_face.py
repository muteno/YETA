#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""yeta_face.py — yeta 캐릭터 프로필 얼굴 이미지 생성 (OpenAI GPT Image · 1:1 얼굴중심 · 수동 dispatch 전용).

무음동 10인 각자에 어울리는 초상 프롬프트 하나씩 → OpenAI Images API(gpt-image) → 공개 R2 `yeta_face/<id>.png` 업로드 →
roster.json 의 그 캐릭터 `avatar` 슬롯에 공개 URL 주입(라인 정규식 = 수제 포맷 보존). 뷰어가 avatar 있으면 이니셜 대신 얼굴.

⚠️ 과금: OpenAI 이미지 = **유료 종량제** — 챗(구독 OAuth)과 완전 별개 축.
   자동 트리거 금지 · workflow_dispatch(yeta-face.yml) **수동 1회성만**(운영자 직접 지시 260703).
게이트 = `OPENAI_API_KEY`(없으면 no-op 스캐폴드). 공개 R2 5시크릿 없으면 git 폴백(viewer/assets/yeta_face/ 커밋).
멱등: roster avatar 가 이미 차 있으면 그 캐릭터 skip(FORCE=1 이면 재생성·덮어쓰기).
R2 업로드 = aws cli(러너 기본설치) S3호환 — yeta_chat.sh 세션 저장과 동일 배관(단, 공개 버킷 `R2_BUCKET` ≠ 비공개 `YETA_R2_BUCKET`). fail-soft.
⚠️ 독립 레포(muteno/yeta) 자립형 — nomute `thumb_gen` 의존 제거·R2 업로드 인라인(260703 이식).
"""
import os, re, sys, json, time, base64, hashlib, tempfile, subprocess, urllib.request, urllib.error

ROSTER = "apps/yeta/characters/roster.json"
LOCAL_DIR = "viewer/assets/yeta_face"   # R2 미설정 git 폴백(뷰어 상대경로 서빙)
KEY = os.environ.get("OPENAI_API_KEY", "")
MODEL = (os.environ.get("OPENAI_IMAGE_MODEL") or "gpt-image-2").strip()   # 빈 env(vars 미설정=빈문자열)도 기본값으로 — os.environ.get 기본값은 빈값 안 덮음(260703 버그) · 실제 ID 다르면 vars OPENAI_IMAGE_MODEL로 교체
API = "https://api.openai.com/v1/images/generations"

# ── 공개 R2(얼굴 호스팅) — 챗 세션(YETA_R2_BUCKET·비공개)과 별도 버킷. 계정 키는 공용 재사용(§🔑 인프라). ──
R2_ACCOUNT = os.environ.get("R2_ACCOUNT_ID", "").strip()
R2_BUCKET = os.environ.get("R2_BUCKET", "").strip()                    # 공개 버킷(≠ YETA_R2_BUCKET)
R2_PUBLIC = os.environ.get("R2_PUBLIC_BASE", "").strip().rstrip("/")   # 예: https://pub-xxxx.r2.dev
R2_KEY = os.environ.get("R2_ACCESS_KEY_ID", "").strip()
R2_SECRET = os.environ.get("R2_SECRET_ACCESS_KEY", "").strip()
R2_ON = all([R2_ACCOUNT, R2_BUCKET, R2_PUBLIC, R2_KEY, R2_SECRET])

# 공통 스타일 — 한국 웹툰(manhwa) 프로필 초상(정사각 1:1·얼굴중심·미남미녀·키·글래머러스 존재감·착장 유지 안전가드).
BASE = ("Korean webtoon-style character profile portrait, polished digital manhwa illustration, "
        "clean lineart with soft cel shading, perfectly square 1:1, "
        "face-centered head-and-shoulders close-up (the face fills the frame), "
        "one single original fictional character, very good-looking and attractive, "
        "tall with an elegant glamorous striking presence, refined proportions, flawless skin, "
        "set in the moody night-lit back-alley mood of a quiet Seoul neighborhood, "
        "soft cinematic lighting with a subtle touch of fantasy — faint magical ambient glow, "
        "delicate floating light particles, a dreamlike ethereal atmosphere (still grounded and semi-realistic, not costume fantasy), "
        "gentle color grade, fully clothed and tasteful, "
        "no text, no caption, no watermark, no logo. Character — ")

# 캐릭터 10인 초상(보강 카드 성격·수치·이면·직업 반영 · 미남미녀·매력 각인 · '어울리는 하나씩' · 260703 v2 카드정합)
FACES = [
    ("desk",  "a strikingly handsome man of 48 with a distinguished mature air, a veteran newsroom editor-in-chief, sharp intelligent eyes behind thin steel-rimmed glasses, cool composed almost unreadable expression that hides a lifelong love of the work, neat dark hair greying at the temples, faint stubble, crisp muted grey shirt with sleeves rolled once, a coffee cup nearby; cold late-night newsroom monitor glow with a faint icy-blue holographic shimmer."),
    ("kopi",  "a charming handsome man of 34, a freelance copywriter, playful witty half-smile that's half a mask, stylishly tousled hair, warm expressive eyes quietly hungry for a little praise, a cozy oversized knit, a laptop and teacup at a cafe corner; warm teahouse lamplight with soft golden floating bokeh."),
    ("mudi",  "a serene androgynous beautiful person in their early 40s of gentle ambiguous gender, the owner of a 24-hour teahouse, a soft reassuring half-smile, calm kind knowing eyes, tidy linen apron over a fitted shirt, holding a warm cup; deep amber pendant light with gentle glowing steam wisps curling up."),
    ("sera",  "a beautiful striking young woman of 19, an idol trainee, chic aloof guarded expression with a flicker of loneliness underneath, sleek high ponytail with one earphone in, delicate sharp features, a trendy sporty crop-and-jacket practice outfit; dreamy underground practice-room neon pink-and-blue haze, cool fluorescent shimmer."),
    ("haeun", "a beautiful elegant woman of 32, a high-school Korean-literature teacher, a warm teasing playful smile, soft wavy shoulder-length hair, graceful refined features, a neat stylish blouse, a teacup by a window; soft dusk window glow with drifting warm petals of light."),
    ("gaeul", "a gorgeous commanding woman of 33, a merchants'-association leader, a poised proud almost regal gaze, a glamorous polished look, sleek pulled-back dark hair, an impeccably tailored elegant coat, spine perfectly straight; elegant amethyst-violet aura with refined shopfront neon reflection."),
    ("baek",  "an extremely handsome man of 43, a tall broad-shouldered quiet ex-special-forces bodyguard, chiseled jaw, intense watchful weary eyes that haven't slept well, a faint old scar, a sharp black suit; deep dramatic pre-dawn alley shadow with a faint steel-blue mist."),
    ("ryu",   "a handsome charismatic man of 45, a laid-back kendo master, light stubble, an alluring half-lidded lazy gaze that turns sharp about the blade, dark hair loosely tied back, elegant traditional-modern attire, a folding fan half-raised; silver-teal moonlit veranda haze."),
    ("von",   "a handsome powerfully athletic man of 42, 184cm tall, a disciplined ex-fighter turned boxing-gym owner, short cropped hair, strong composed weathered features, a fit muscular build under a clean fitted jacket, a towel around the neck; cool blue 5am pre-dawn gym light with faint drifting sparks."),
    ("yun",   "a handsome mellow man of 34, a late-night radio DJ, soft introspective half-lit eyes, stylishly tousled hair, headphones resting around his neck, a quiet magnetic warmth kept just at arm's length; dim red ON-AIR booth glow with soft starlight particles."),
]


def r2_upload(png_bytes, key, content_type="image/png"):
    """바이트 → 공개 R2 업로드(aws cli S3호환·러너 기본설치) → 공개 URL. 실패 시 None(fail-soft → git 폴백)."""
    endpoint = "https://{}.r2.cloudflarestorage.com".format(R2_ACCOUNT)
    env = dict(os.environ, AWS_ACCESS_KEY_ID=R2_KEY, AWS_SECRET_ACCESS_KEY=R2_SECRET,
               AWS_DEFAULT_REGION="auto")
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(png_bytes); tmp = f.name
        subprocess.run(["aws", "s3", "cp", tmp, "s3://{}/{}".format(R2_BUCKET, key),
                        "--endpoint-url", endpoint, "--content-type", content_type,
                        "--only-show-errors"], check=True, env=env, timeout=90)
        return "{}/{}".format(R2_PUBLIC, key)
    except Exception as e:
        print("  ⚠️ R2 업로드 실패: {}".format(e), flush=True)
        return None
    finally:
        if tmp and os.path.exists(tmp):
            os.remove(tmp)


def openai_image(prompt):
    """OpenAI Images API 1장 → PNG bytes(실패 시 None · fail-soft). b64_json 우선, url 반환 모델이면 다운로드."""
    payload = {"model": MODEL, "prompt": prompt, "size": "1024x1024", "n": 1}   # 1024²=정확한 1:1
    data = json.dumps(payload).encode()
    req = urllib.request.Request(API, data=data,
                                 headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                j = json.loads(r.read().decode())
            d = (j.get("data") or [{}])[0]
            b = d.get("b64_json")
            if b:
                return base64.b64decode(b)
            u = d.get("url")
            if u:
                with urllib.request.urlopen(u, timeout=120) as ir:
                    return ir.read()
            print("  ⚠️ 이미지 파트 없음(응답에 b64_json/url 부재)", flush=True)
            return None
        except urllib.error.HTTPError as e:
            print("  ⚠️ HTTP {} — {}".format(e.code, e.read().decode()[:250]), flush=True)
            if e.code in (429, 500, 503) and attempt == 0:
                time.sleep(5); continue
            return None
        except Exception as e:
            print("  ⚠️ 호출 실패: {}".format(e), flush=True)
            if attempt == 0:
                time.sleep(5); continue
            return None
    return None


def set_avatar(text, pid, url):
    """roster.json 라인 정규식 — "id":"<pid>" 줄의 "avatar":"…" 만 교체(수제 1줄=1명 포맷 보존)."""
    out, hit = [], False
    for line in text.splitlines(keepends=True):
        if re.search(r'"id"\s*:\s*"%s"' % re.escape(pid), line):
            line, n = re.subn(r'"avatar"\s*:\s*"[^"]*"', '"avatar": "%s"' % url, line, count=1)
            hit = hit or n > 0
        out.append(line)
    return "".join(out), hit


def main():
    if not KEY:
        print("OPENAI_API_KEY 없음 — 얼굴 생성 생략(no-op 스캐폴드)"); return 0
    force = os.environ.get("FORCE", "") == "1"
    try:
        roster = open(ROSTER, encoding="utf-8").read()
    except OSError:
        print("::error::roster.json 없음"); return 1

    only = os.environ.get("YETA_FACE_ONLY", "").strip()   # 특정 id 하나만(연결·모델 테스트용 · 비용 절감)
    faces = [f for f in FACES if not only or f[0] == only]
    if only and not faces:
        print("::warning::YETA_FACE_ONLY={} 가 FACES에 없음".format(only)); return 0
    made, skipped, failed = 0, 0, 0
    for pid, desc in faces:
        if not force and re.search(r'"id"\s*:\s*"%s"[^\n]*"avatar"\s*:\s*"[^"]+"' % re.escape(pid), roster):
            print("· {} — avatar 이미 있음, skip".format(pid)); skipped += 1; continue
        print("· {} 생성 — {}".format(pid, desc[:44]), flush=True)
        png = openai_image(BASE + desc)
        if not png:
            print("  ⚠️ 생성 실패 — 건너뜀(비치명·재실행으로 채움)"); failed += 1; continue
        v = hashlib.sha256(png).hexdigest()[:8]   # 캐시버스트
        r2key = "yeta_face/{}.png".format(pid)
        url = None
        if R2_ON:
            url = r2_upload(png, r2key)
            if url:
                url += "?v=" + v
        if not url:   # git 폴백
            os.makedirs(LOCAL_DIR, exist_ok=True)
            open(os.path.join(LOCAL_DIR, pid + ".png"), "wb").write(png)
            url = "assets/yeta_face/{}.png?v={}".format(pid, v)
            print("  ⚠️ R2 미설정/실패 → git 폴백: {}".format(url))
        roster, hit = set_avatar(roster, pid, url)
        print("  {} avatar ← {}".format(pid, url) if hit else "  ⚠️ {} 라인 못 찾음".format(pid))
        made += 1

    if made:
        open(ROSTER, "w", encoding="utf-8").write(roster)
    print("완료 — 생성 {} · skip {} · 실패 {} (모델 {})".format(made, skipped, failed, MODEL))
    return 0   # 부분 실패 = 비치명(멱등 재실행으로 빈 캐릭터만 채움)


if __name__ == "__main__":
    sys.exit(main())
