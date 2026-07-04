#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""yeta_voice_clone.py — 페르소나 전용 음색 생성(보이스 클로닝 · IVC) → roster 주입 = **프리미엄 승격** (260704).

운영자 흐름(요구 1·2):
  ① 운영자가 1분 내외 음성 샘플을 **비공개** 세션 R2 `voice_samples/<persona>.mp3` 에 업로드
     (목소리 원본 = 민감 데이터 → 공개 버킷·git 커밋 금지 · 대화와 같은 비공개 축)
  ② yeta-voice.yml 수동 dispatch(persona 지정) → 이 스크립트:
     R2에서 샘플 다운로드 → ElevenLabs Instant Voice Clone(POST /v1/voices/add · 1분 샘플로 충분·한국어 OK)
     → voice_id 획득 → roster.json 그 캐릭터에 `"voice": "el:<id>"` 주입(라인 정규식 = 수제 포맷 보존)
  ③ roster 커밋 = 그 캐릭터가 프리미엄(전용 음색) — 이후 전화(yeta_call)·무전기(yeta_chat PTT) TTS가
     yeta_tts.py 에서 이 클론 보이스를 자동 우선 사용.

⚠️ 과금: ElevenLabs = 유료(Starter $5/월 = IVC + TTS 30k자). 자동 트리거 금지 · 수동 dispatch 전용(face/bg 동일 원칙).
멱등: roster voice 가 이미 "el:" 이면 skip(FORCE=1 재클론·기존 voice_id 는 ElevenLabs 대시보드에서 정리).
env: ELEVENLABS_API_KEY(필수) · YETA_VOICE_PERSONA(필수) · YETA_VOICE_SAMPLE(로컬 샘플 경로 — 워크플로가 R2에서 받아 전달) · FORCE.
"""
import json, os, re, sys, urllib.request, urllib.error, uuid

ROSTER = "apps/yeta/characters/roster.json"
API = "https://api.elevenlabs.io/v1/voices/add"


def multipart(fields, file_field, filename, blob, ctype="audio/mpeg"):
    """의존성 0 멀티파트 인코더(urllib 용) — (body, content_type)."""
    b = "----yeta" + uuid.uuid4().hex
    out = []
    for k, v in fields.items():
        out.append("--{}\r\nContent-Disposition: form-data; name=\"{}\"\r\n\r\n{}\r\n".format(b, k, v).encode())
    out.append("--{}\r\nContent-Disposition: form-data; name=\"{}\"; filename=\"{}\"\r\nContent-Type: {}\r\n\r\n"
               .format(b, file_field, filename, ctype).encode())
    out.append(blob)
    out.append("\r\n--{}--\r\n".format(b).encode())
    return b"".join(out), "multipart/form-data; boundary=" + b


def set_voice(text, pid, val):
    """roster 라인 정규식 — "id":"<pid>" 줄에 "voice":"…" 교체, 없으면 줄 끝 `}` 앞에 삽입(yeta_face set_avatar 동형)."""
    out, hit = [], False
    for line in text.splitlines(keepends=True):
        if re.search(r'"id"\s*:\s*"%s"' % re.escape(pid), line):
            line2, n = re.subn(r'"voice"\s*:\s*"[^"]*"', '"voice": "%s"' % val, line, count=1)
            if n:
                line, hit = line2, True
            else:
                line2, n = re.subn(r'\s*\}\s*(,?)\s*$', ', "voice": "%s" }\\1\n' % val, line, count=1)
                if n:
                    line, hit = line2, True
        out.append(line)
    return "".join(out), hit


def main():
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    persona = os.environ.get("YETA_VOICE_PERSONA", "").strip()
    sample = os.environ.get("YETA_VOICE_SAMPLE", "").strip()
    force = os.environ.get("FORCE", "") == "1"
    if not key:
        print("ELEVENLABS_API_KEY 없음 — 클로닝 생략(no-op 스캐폴드)"); return 0
    if not re.fullmatch(r"[a-z0-9_-]{1,24}", persona):
        print("::error::잘못된 persona"); return 1
    try:
        roster = open(ROSTER, encoding="utf-8").read()
    except OSError:
        print("::error::roster.json 없음"); return 1
    if not force and re.search(r'"id"\s*:\s*"%s"[^\n]*"voice"\s*:\s*"el:' % re.escape(persona), roster):
        print("· {} — 이미 클론 보이스 있음, skip(FORCE=1 재클론)".format(persona)); return 0
    if not (sample and os.path.isfile(sample) and os.path.getsize(sample) > 10000):
        print("::error::샘플 파일 없음/너무 작음({}) — 비공개 R2 voice_samples/{}.mp3 업로드 확인".format(sample, persona)); return 1

    blob = open(sample, "rb").read()
    if len(blob) > 10 * 1024 * 1024:
        print("::error::샘플 10MB 초과 — 1분 내외로 잘라줘"); return 1
    body, ctype = multipart({"name": "yeta_" + persona,
                             "description": "yeta persona voice (Korean)",
                             "remove_background_noise": "true"},
                            "files", persona + ".mp3", blob)
    req = urllib.request.Request(API, data=body, headers={"xi-api-key": key, "Content-Type": ctype})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            j = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        print("::error::클로닝 HTTP {} — {}".format(e.code, e.read().decode()[:300])); return 1
    except Exception as e:
        print("::error::클로닝 실패: {}".format(e)); return 1
    vid = (j.get("voice_id") or "").strip()
    if not vid:
        print("::error::voice_id 없음 — 응답: {}".format(str(j)[:200])); return 1

    roster, hit = set_voice(roster, persona, "el:" + vid)
    if not hit:
        print("::error::roster 라인 못 찾음({})".format(persona)); return 1
    open(ROSTER, "w", encoding="utf-8").write(roster)
    print("완료 — {} voice ← el:{} (프리미엄 승격 · roster 커밋은 워크플로)".format(persona, vid))
    return 0


if __name__ == "__main__":
    sys.exit(main())
