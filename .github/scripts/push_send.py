#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 긴급(breaking) 속보 웹푸시 발송 — candidates.json의 새 isBreaking 사건을 구독자에게 pywebpush로.
# dedup = push/sent.json(이미 보낸 키). 죽은 구독(404/410) 자동 정리. 비치명(실패해도 파이프 안 깸).
# env: VAPID_PRIVATE_KEY(raw base64url)·VAPID_PUBLIC_KEY·VAPID_SUBJECT. 인자 --test = 구독자 전원 테스트 1발.
# 정본 설명 = CLAUDE.md §🚨. 푸시 기준(앱푸시긴급) = breaking_judge AND grade≥3(운영자 260622) AND cross≥PUSH_MIN AND 최신(<4h · 뷰어 화면알림 isAlert과 동일 tier · 🚨배지 grade≥2는 별개).
# ⚠️ 푸시는 되돌릴 수 없다(발송=회수 불가) → 뷰어 점등(가역)보다 *더* 보수적: grade 미채점(None)은 푸시 안 함
#    (뷰어는 None도 점등=즉시·가역) · 다매체 검증 cross≥PUSH_MIN_CROSS 필수 · dedup=event_key+제목해시(중복발송 차단).
import json, os, re, sys, time, base64, hashlib, tempfile, datetime as dt
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent.parent
SUBS = ROOT / "push" / "subscriptions.json"
SENT = ROOT / "push" / "sent.json"
CAND = ROOT / "viewer" / "candidates.json"
FAST_MAX_H = 4   # 최신 긴급만 푸시(뷰어 토스트와 동일 단일상수 정신)
PUSH_MIN_CROSS = int(os.environ.get("PUSH_MIN_CROSS", "2"))   # 푸시 최소 교차매체(다매체 검증 = 오발송 가드 · MIN_CROSS 바뀌어도 푸시 하한 고정)

def jload(p, d):
    try: return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception: return d

def is_breaking(c):
    # 푸시용(가역 아님·앱푸시긴급) = grade가 *채점되어* ≥3여야 함(운영자 260622 = 뷰어 화면알림 isAlert[grade≥3]과 동일선상 · None=미채점은 푸시 보류 · 🚨배지[grade≥2]보다 엄격).
    g = c.get("grade")
    return bool(c.get("breaking")) and g is not None and (g or 0) >= 3

def brk_url(c):
    # 긴급 알림 탭 → 루트가 아니라 *해당 건*으로 딥링크(/?brk=키&bl=메이저링크). 뷰어가 탭 *시점*에 '요약 완료?'를
    # 보고 분기: 완료=요약창 / 미완료=스크랩 기사 중 가장 메이저(breaking_pick)로 이동(웹앱 경유). 운영자 260622.
    #  · key = event_key 우선(별칭 점프에도 안정)·url 폴백 → 뷰어가 candidates 에서 해당 후보를 찾는 매칭키.
    #  · bl  = 대표 매체 픽 url(없으면 최초보도) → 후보 조회 실패(랙·만료) 시에도 메이저 원문 보장(client scLinkUrl 의 서버판).
    key = (c.get("event_key") or c.get("url") or "").strip()
    if not key:
        return "/"
    bp = c.get("breaking_pick") or {}
    bl = (bp.get("url") or c.get("url") or "").strip()
    u = "/?brk=" + quote(key, safe="")
    if bl:
        u += "&bl=" + quote(bl, safe="")
    return u

def disp_title(c):
    # 외신 = 한국어 번역 제목 우선(gate_judge 편승 title_ko · 원문 일치 도장만 유효 — 뷰어 scKoTitle 과 동일 술어 · 260703)
    ko = c.get("title_ko")
    return ko if (ko and c.get("title_ko_of") == c.get("title")) else (c.get("title") or "")

def dedup_keys(c):
    # 같은 사건 중복 발송 차단 — event_key(별칭 점프에도 안정) + 제목해시(event_key=url 디폴트라 url 점프 시
    # 갈리는 구멍 보완: 같은 헤드라인이면 url 달라도 같은 키). 둘 중 하나라도 sent에 있으면 스킵.
    ks = []
    ek = c.get("event_key") or c.get("id") or c.get("url")
    if ek: ks.append(str(ek))
    t = re.sub(r"\s+", "", c.get("title") or "")
    if t: ks.append("t:" + hashlib.md5(t.encode("utf-8")).hexdigest()[:16])
    return ks

def age_h(c):
    s = c.get("published") or c.get("first_seen") or ""
    for f in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M"):
        try:
            t = dt.datetime.strptime(s.replace("Z", "+0000")[:25 if "+" in s else 19], f)
            if t.tzinfo is None: t = t.replace(tzinfo=dt.timezone.utc)
            return (time.time() - t.timestamp()) / 3600
        except Exception: pass
    return None

def vapid_pem(raw_b64url):
    # raw 32바이트 스칼라(web-push 표준) → PKCS8 PEM(파일). pywebpush 버전 무관 안전 입력.
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import serialization
    raw = base64.urlsafe_b64decode(raw_b64url + "=" * (-len(raw_b64url) % 4))
    key = ec.derive_private_key(int.from_bytes(raw, "big"), ec.SECP256R1())
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                            serialization.NoEncryption()).decode()
    tf = tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False)
    tf.write(pem); tf.close()
    return tf.name

def main():
    test = "--test" in sys.argv
    notify = None
    notify_url = "/"
    notify_tag = "nomute-make"
    if "--url" in sys.argv:                           # 알림 탭 시 이동할 경로(제작완료=제작 화면으로) · 미지정이면 "/"
        j = sys.argv.index("--url")
        if len(sys.argv) > j + 1:
            notify_url = sys.argv[j + 1] or "/"
    if "--tag" in sys.argv:                            # 알림 tag — 같은 tag=교체. 건별 고유 tag면 여러 알림 쌓임(요약완료=건별 누적)
        k = sys.argv.index("--tag")
        if len(sys.argv) > k + 1 and sys.argv[k + 1]:
            notify_tag = sys.argv[k + 1]
    if "--notify" in sys.argv:                       # 임의 알림(제작완료 등) — 구독자 전원(=프로필 ON) · dedup 미기록
        i = sys.argv.index("--notify")
        notify = (sys.argv[i + 1] if len(sys.argv) > i + 1 else "🖼 News",
                  sys.argv[i + 2] if len(sys.argv) > i + 2 else "")
    subs = jload(SUBS, [])
    if not isinstance(subs, list) or not subs:
        print("구독자 없음 — 발송 생략"); return
    priv = os.environ.get("VAPID_PRIVATE_KEY", "").strip()
    subj = os.environ.get("VAPID_SUBJECT", "mailto:muteno@pm.me").strip()
    if not priv:
        print("VAPID_PRIVATE_KEY 없음 — 생략"); return
    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        print("pywebpush 미설치 — 생략"); return

    if test:
        msgs = [{"keys": [f"test-{int(time.time())}"], "title": "🔔 노뮤트 테스트",
                 "body": "웹푸시 연결 정상! 긴급 속보가 이렇게 와.", "url": "/", "tag": "nomute-breaking"}]
    elif notify:
        # 제작완료/요약완료 등 = 전용 tag(긴급 속보와 안 덮어씀) · url=대상 화면(notify_url) · tag=notify_tag(건별 고유면 누적)
        msgs = [{"keys": [f"notify-{int(time.time())}"], "title": notify[0], "body": notify[1], "url": notify_url, "tag": notify_tag}]
    else:
        cands = jload(CAND, [])
        sent = set(jload(SENT, []))
        msgs = []
        for c in cands:
            if not is_breaking(c):
                continue
            if (c.get("cross") or 0) < PUSH_MIN_CROSS:   # 다매체 검증 미달 = 오발송 가드(푸시는 회수 불가)
                continue
            a = age_h(c)
            if a is None or a < 0 or a >= FAST_MAX_H:   # a<0 = 미래발행(소스 TZ 오기록) → 음수나이가 4h창 통과해 비가역 오발송하던 구멍 차단(뷰어 scTs 미래가드와 짝)
                continue
            ks = dedup_keys(c)
            if not ks or any(k in sent for k in ks):     # event_key·제목해시 중 하나라도 보냄 = 스킵(중복 차단)
                continue
            msgs.append({"keys": ks, "title": "News", "body": ("(긴급) " + disp_title(c))[:120], "url": brk_url(c), "tag": "nomute-breaking"})   # 제목="News"(고정·OS 볼드) · 본문="(긴급) 헤드라인"(외신=번역 제목) · url=해당 건 딥링크(요약완료=요약창/미완료=메이저링크 · 운영자 260622)
        if not msgs:
            print("새 긴급 없음 — 발송 생략"); return

    pem_path = vapid_pem(priv)
    dead, sent_keys = set(), []
    for m in msgs:
        payload = json.dumps({"title": m["title"], "body": m["body"], "url": m["url"], "tag": m.get("tag", "nomute-breaking")},
                             ensure_ascii=False)
        ok_any = False
        for s in subs:
            ep = (s or {}).get("endpoint")
            if not ep:
                continue
            try:
                webpush(subscription_info=s, data=payload, vapid_private_key=pem_path, vapid_claims={"sub": subj})
                ok_any = True
            except WebPushException as e:
                code = getattr(getattr(e, "response", None), "status_code", None)
                if code in (404, 410):
                    dead.add(ep)
                print(f"push 실패({code}): {ep[:60]}", file=sys.stderr)
            except Exception as e:
                print(f"push 오류: {e}", file=sys.stderr)
        if ok_any:
            sent_keys.extend(m["keys"])   # event_key+제목해시 둘 다 기록 = 다음 런에 어느 쪽으로 와도 dedup

    if dead:   # 죽은 구독 정리
        subs2 = [s for s in subs if (s or {}).get("endpoint") not in dead]
        SUBS.write_text(json.dumps(subs2, ensure_ascii=False), encoding="utf-8")
        print(f"죽은 구독 {len(dead)} 정리")
    if not test and not notify and sent_keys:   # 발송 원장 갱신(테스트·임의알림은 미기록)
        ledger = list(jload(SENT, [])); ledger.extend(sent_keys)
        SENT.parent.mkdir(parents=True, exist_ok=True)
        SENT.write_text(json.dumps(ledger[-500:], ensure_ascii=False), encoding="utf-8")
    print(f"발송: {len(sent_keys)}/{len(msgs)} 사건 · 구독 {len(subs)}{' [TEST]' if test else ''}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"push_send 경고(무시·비치명): {e}", file=sys.stderr)
