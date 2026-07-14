#!/usr/bin/env python3
# yeta_stream.py — claude -p stream-json 수집 필터 + 문장 스트리밍 부분 박제(대화 속도 260714 한수2)
# 파이프: claude -p --output-format stream-json --include-partial-messages --verbose | 이 필터
#   stdout = 최종 result 이벤트 JSON 1개(= --output-format json 출력과 동형) → claude_meter 기존 파서(.result)·계측·실패판정 그대로 호환.
#   부수효과 = 텍스트 델타를 문장 경계로 모아 R2 draft(sessions/<char>.draft.json)에 발행 → 게이트웨이 watch가 감시 → 뷰어가 생성 중 문장부터 표시.
# 안전:
#   · 대사 밖 유출 0 — 첫 '<<' 이후 전부 보류(출력 계약상 <<NOTE>>/<<MOOD>>는 대사 뒤 = 기억 내용·무드 태그가 draft로 새지 않음) · 꼬리 낱개 '<'도 보류(다음 델타에서 << 가능).
#   · result 이벤트 부재(크래시·비정상) = 원문 라인 그대로 stdout(기존 is_quota/is_transient 폴오버 매칭 보존).
#   · draft 발행 실패 = 전부 무해(check=False·예외 삼킴) — 스트리밍은 가산 축, 본답장 파이프라인 무영향.
#   · 발행 게이트 = 새 문장 경계 + 최소 1.2s 간격(aws 서브프로세스 남발 방지 · R2 Class A ~2-6회/답장).
# env: YETA_DRAFT_KEY/BUCKET/EP(없으면 순수 수집만) · YETA_DRAFT_T(스레드)/YETA_DRAFT_P(페르소나) — 뷰어 스테일 가드용.
#      YETA_PTT_HEAD(선택 · PTT 턴만) = 헤드 TTS 선굽기 경로 프리픽스 — 첫 문장이 확정되는 순간 백그라운드로 yeta_tts.py 발사
#      (한수3 260714: 음성 대기 = 생성+전문TTS → 생성과 헤드TTS 병렬 · ptt_voice가 접두 일치 검증 후 나머지만 굽고 이어붙임 · 불일치 = 전문 폴백).
import json, os, re, subprocess, sys, tempfile, time

KEY = os.environ.get("YETA_DRAFT_KEY", "")
BUCKET = os.environ.get("YETA_DRAFT_BUCKET", "")
EP = os.environ.get("YETA_DRAFT_EP", "")
TH = os.environ.get("YETA_DRAFT_T", "")
PS = os.environ.get("YETA_DRAFT_P", "")
HEAD = os.environ.get("YETA_PTT_HEAD", "")
FIRST = os.environ.get("YETA_STREAM_FIRST", "")   # 첫 발행 시각(epoch ms) 기록 파일 — 계기판 lat.f(첫문장까지) 재료(운영자 260714)
first_done = False
MIN_GAP = 1.2
last_pub = 0.0
pub_len = 0
buf = []
result = None
raw_lines = []
head_fired = False

def clean(t):
    i = t.find("<<")                      # 첫 마커부터 전부 보류 — NOTE 내용·MOOD 태그 유출 원천 차단(대사는 마커 앞)
    if i >= 0: t = t[:i]
    if t.endswith("<"): t = t[:-1]        # 꼬리 낱개 '<' 보류(다음 델타에서 '<<' 완성 가능)
    return t.strip()[:4000]

def publish(force=False):
    global last_pub, pub_len
    if not (KEY and BUCKET and EP): return
    t = clean("".join(buf))
    if not t or (len(t) <= pub_len and not force): return
    now = time.time()
    if not force and now - last_pub < MIN_GAP: return
    if not force and not re.search(r"[.!?…~\n]", t[pub_len:]): return   # 새 문장 경계 없으면 보류(어중간한 단어 절단 노출 감소)
    try:
        body = json.dumps({"t": TH, "p": PS, "ts": int(now * 1000), "text": t}, ensure_ascii=False)
        f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        f.write(body); f.close()
        subprocess.run(["aws", "s3api", "put-object", "--bucket", BUCKET, "--key", KEY, "--body", f.name,
                        "--content-type", "application/json", "--endpoint-url", EP],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15, check=False)
        os.unlink(f.name)
        last_pub = now; pub_len = len(t)
        global first_done
        if FIRST and not first_done:
            first_done = True
            try: open(FIRST, "w").write(str(int(now * 1000)))   # 첫 문장 발행 시각 — 계기판 f 축
            except Exception: pass
    except Exception:
        pass

def spoken_head(t):                       # ptt_voice의 spoken 정제와 동일 연산(접두 일치 계약 — 드리프트 금지: yeta_chat.sh ptt_voice 짝)
    t = re.split(r'^\s*\[[^\]\n]{1,24}\]\s', t, maxsplit=1, flags=re.M)[0]
    t = re.sub(r'\*[^*\n]{1,200}\*', '', t)
    t = re.sub(r'[`*_]', '', t)
    return re.sub(r'\s+', ' ', t).strip()

def try_head():                           # 첫 문장 확정 순간 헤드 TTS 백그라운드 발사(1회) — 실패 전부 무해(ptt_voice 전문 폴백)
    global head_fired
    if head_fired or not (HEAD and PS): return
    raw = clean("".join(buf))
    if not raw or raw.count("*") % 2: return          # 미닫힌 *지문* = 경계 미확정 — 정제 결과가 전문과 어긋날 수 있어 대기
    s2 = spoken_head(raw)
    head = ""
    for m in re.finditer(r'[.!?…~]', s2):             # 첫 '충분히 긴' 머리(≥5자)까지 — 짧은 감탄("안녕!")은 다음 문장까지 흡수
        if m.end() >= 5: head = s2[:m.end()].strip()[:200]; break
    if not head: return
    head_fired = True                                 # 성공/실패 무관 1회(재발사 소음 방지)
    try:
        open(HEAD + ".txt", "w", encoding="utf-8").write(head)
        subprocess.Popen(["bash", "-c",
            'python3 .github/scripts/yeta_tts.py "$1" "$2" "$3.part" >/dev/null 2>&1 && mv -f "$3.part" "$3.mp3"; echo done > "$3.done"',
            "_", PS, head, HEAD], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

for line in sys.stdin:
    raw_lines.append(line)
    s = line.strip()
    if not s: continue
    try: ev = json.loads(s)
    except Exception: continue
    ty = ev.get("type")
    if ty == "stream_event":              # 토큰 델타(--include-partial-messages)
        d = (ev.get("event") or {}).get("delta") or {}
        if d.get("type") == "text_delta":
            buf.append(d.get("text") or ""); try_head(); publish()
    elif ty == "assistant":               # 완결 어시스턴트 메시지 — 파셜 미지원 CLI에서도 메시지 단위 동기
        try:
            txt = "".join(c.get("text", "") for c in (ev.get("message") or {}).get("content") or [] if c.get("type") == "text")
            if len(txt) > len("".join(buf)): buf = [txt]; try_head(); publish()
        except Exception: pass
    elif ty == "result":
        result = ev

if result is not None:
    publish(force=True)                   # 마지막 조각까지 발행(확정 스왑 전 공백 최소화)
    sys.stdout.write(json.dumps(result, ensure_ascii=False))
else:
    sys.stdout.write("".join(raw_lines))  # 비정상 종료 = 원문 그대로(호출부 실패판정·폴오버 경로 보존)
