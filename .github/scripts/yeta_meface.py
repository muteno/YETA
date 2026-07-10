#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""yeta_meface.py — 유저 프로필 이미지 생성 (운영자 260710 · ⚠️ OpenAI 유료 — 트리거 = op meface 일 상한 / 수동 dispatch).

비공개 R2 세션(sess.me)에서 소개(about)·호칭(call)만 읽어 → 로스터 초상과 동일 스타일(BASE = yeta_face.py SSOT 임포트 = "캐릭터들 톤" 정합)
1장 생성 → 공개 R2 `yeta_face/me.png` 업로드 → MEFACE_MODE:
  apply(기본) = sess.me.avatar 에 URL CAS 주입(+ meface.pending 해제) — 뷰어 폴이 집어감.
  sample      = 세션 무기록 · `SAMPLE_URL=` 로그만(개발 검증용).

⚠️ public 레포 = 공개 Actions 로그 → 소개·호칭 원문 print 절대 금지(길이만) · 대화 turns 무접촉.
⚠️ git 폴백 없음(yeta_face와 다름) — 유저 개인화 이미지를 공개 레포에 커밋하지 않는다(공개 R2 미설정 = 명시 에러).
CAS = 러너 r2put 결(ETag if-match · 4회 루프).
"""
import os, sys, json, time, hashlib, subprocess, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from yeta_face import BASE, openai_image, r2_upload, R2_ON   # 스타일·이미지 호출·공개 R2 업로드 SSOT(복제 금지 = 드리프트 차단)

MODE = (os.environ.get("MEFACE_MODE") or "apply").strip() or "apply"
ACC = os.environ.get("R2_ACCOUNT_ID", "").strip()
PRIV = os.environ.get("YETA_R2_BUCKET", "").strip()
EP = "https://{}.r2.cloudflarestorage.com".format(ACC)
KEY = "sessions/main.json"
SESS = "/tmp/yeta_meface_sess.json"


def aws(*args):
    env = dict(os.environ, AWS_ACCESS_KEY_ID=os.environ.get("R2_ACCESS_KEY_ID", ""),
               AWS_SECRET_ACCESS_KEY=os.environ.get("R2_SECRET_ACCESS_KEY", ""), AWS_DEFAULT_REGION="auto")
    return subprocess.run(["aws", *args, "--endpoint-url", EP], env=env, capture_output=True, text=True, timeout=90)


def sess_get():
    """비공개 세션 read + ETag(CAS 짝). 실패 = (None, None)."""
    r = aws("s3api", "get-object", "--bucket", PRIV, "--key", KEY, SESS)
    if r.returncode != 0:
        print("::error::세션 로드 실패"); print((r.stderr or "")[-300:], file=sys.stderr)
        return None, None
    etag = ""
    try:
        etag = (json.loads(r.stdout).get("ETag") or "").strip('"')
    except Exception:
        pass
    try:
        with open(SESS, encoding="utf-8") as f:
            return json.load(f), etag
    except Exception:
        print("::error::세션 파싱 실패"); return None, None


def sess_put(sess, etag):
    """조건부 put(ETag) — 경합 = False(호출부 fresh 재시도 · yeta_chat.sh r2put 동형)."""
    with open(SESS, "w", encoding="utf-8") as f:
        json.dump(sess, f, ensure_ascii=False)
    args = ["s3api", "put-object", "--bucket", PRIV, "--key", KEY, "--body", SESS, "--content-type", "application/json"]
    if etag:
        args += ["--if-match", etag]
    r = aws(*args)
    if r.returncode != 0:
        print("  ⚠️ 세션 put 실패(경합/기타) — 재시도", flush=True)
    return r.returncode == 0


def main():
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY 없음 — 생성 생략(no-op 스캐폴드)"); return 0
    if not (ACC and PRIV):
        print("::error::비공개 R2 미설정(R2_ACCOUNT_ID/YETA_R2_BUCKET)"); return 1
    if not R2_ON:
        print("::error::공개 R2 미설정(R2_BUCKET·R2_PUBLIC_BASE 등 5종) — 유저 아바타는 git 폴백 없음(개인화 이미지 공개 레포 커밋 회피)"); return 1

    sess, etag = sess_get()
    if sess is None:
        return 1
    me = sess.get("me") or {}
    about = str(me.get("about") or "").strip()[:300]
    if not about:
        print("소개(me.about) 비어 있음 — 생성 생략(뷰어가 소개부터 유도)"); return 0
    print("· 소개 {}자 기반 생성(원문 비출력 · 모드 {})".format(len(about), MODE), flush=True)

    # 로스터 톤 정합 = BASE 그대로 + 유저 페르소나 파트(소개 원문 = 이미지 프롬프트 재료 — 텍스트 명령이어도 그림 취향 반영 이상의 권한 없음 · 상한 op가 가드)
    prompt = (BASE + "the player themselves — a regular late-night visitor of this alley who belongs in its world, "
              "an ordinary yet quietly charismatic person. Derive their look, styling, expression and mood from this "
              "self-introduction (personality first, tasteful, any gender that fits it): “" + about + "”. "
              "Warm approachable presence, a subtle lime-green accent glow in the background.")
    png = openai_image(prompt)
    if not png:
        print("::error::이미지 생성 실패"); return 1
    v = hashlib.sha256(png).hexdigest()[:8]
    url = r2_upload(png, "yeta_face/me.png")
    if not url:
        print("::error::공개 R2 업로드 실패"); return 1
    url += "?v=" + v   # 고정 키 + 내용 해시 캐시버스트(재생성 = 파일 교체·URL 갱신)
    print("이미지 URL: " + url)

    if MODE == "sample":
        print("SAMPLE_URL=" + url)   # 세션 무기록 — 개발 세션이 이 줄 파싱
        return 0

    for _ in range(4):   # apply — CAS 루프(러너 결)
        sess.setdefault("me", {})["avatar"] = url
        mf = sess.setdefault("meface", {})
        mf["pending"] = 0; mf["url"] = url; mf["done"] = int(time.time() * 1000)
        if sess_put(sess, etag):
            print("세션 주입 완료 — me.avatar 갱신"); return 0
        time.sleep(1)
        sess, etag = sess_get()
        if sess is None:
            return 1
    print("::error::세션 CAS 4회 경합 — 주입 실패(이미지는 업로드됨 · 재실행으로 주입만 재시도 가능)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
