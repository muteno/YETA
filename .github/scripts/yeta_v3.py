# yeta v3 세션 어댑터 SSOT (260707 다중 채팅방 · 5인 기틀검증 반영)
# — migrate_v3: functions/api/yeta.js migrateV3와 **동형**(멱등 순수 랩 · 시뮬 대조 게이트 대상 · 마이그 감사①)
# — pick_thread: 통합 age 큐(신선 invite / pending 최고령 / opening nonce — 가장 오래된 것 우선 · 러너 감사①A·레이스 감사②)
# — thread_view: 스레드 dict + 공유 필드 오버레이(기존 단일 세션 로직 재사용용 읽기 뷰)
import time

INVITE_TTL_MS = 600000

def migrate_v3(s):
    """v>=3 or threads 존재 = no-op(멱등). v2 = threads[persona] 랩 · updated = 마지막 턴 ts 백필."""
    if not isinstance(s, dict):
        return {"v": 3, "cur": "", "barge_day": "", "call": None, "threads": {},
                "note_pub": "", "notes": {}, "tunes": {}, "policy": {}, "pref": {},
                "me": {"call": "", "about": ""}}
    if s.get("v", 0) >= 3 or "threads" in s:
        s.setdefault("threads", {}); s.setdefault("me", {"call": "", "about": ""}); s["v"] = 3   # me = 유저 프로필(호칭+소개 · 260708) 상시 존재(JS migrateV3 동형)
        return s
    t = str(s.get("persona") or "")
    th = {}
    turns = s.get("turns") or []
    if t and turns:
        room = [r for r in (s.get("room") or []) if isinstance(r, str) and r] or [t]
        th[t] = {"turns": turns, "state": s.get("state") or "idle", "opening": s.get("opening") or 0,
                 "awaiting_since": s.get("awaiting_since") or 0, "err": s.get("err") or "",
                 "room": room, "invite": s.get("invite") or None, "barged": s.get("barged") or 0,
                 "declined": s.get("declined") or {}, "pin": 0,
                 "updated": (turns[-1].get("ts") if isinstance(turns[-1], dict) else 0) or int(time.time() * 1000),
                 "last_sp": t, "char_ver": s.get("char_ver") or "", "nudge": s.get("nudge") or None}
    return {"v": 3, "cur": t or "", "barge_day": s.get("barge_day") or "", "call": s.get("call") or None,
            "threads": th, "note_pub": s.get("note_pub") or s.get("note") or "",
            "notes": s.get("notes") or {}, "tunes": s.get("tunes") or {},
            "policy": s.get("policy") or {}, "pref": s.get("pref") or {},
            "me": s.get("me") if isinstance(s.get("me"), dict) else {"call": "", "about": ""}}

def _age(th, now_ms):
    """스레드의 일감 나이(ts) — 없으면 None. invite(신선)·pending(최고령)·opening(assistant 0) 통합."""
    turns = th.get("turns") or []
    la = max([i for i, t in enumerate(turns) if t.get("role") == "assistant"], default=-1)
    pend = [t for t in turns[la + 1:] if t.get("role") == "user"]
    cands = []
    inv = th.get("invite") or {}
    room = [r for r in (th.get("room") or []) if r][:2]
    if inv.get("to") and now_ms - (inv.get("ts") or 0) < INVITE_TTL_MS and inv["to"] not in room and len(room) < 2:
        cands.append(inv.get("ts") or 0)
    if pend:
        cands.append(pend[0].get("ts") or 0)
    if th.get("opening") and not any(t.get("role") == "assistant" for t in turns):
        cands.append(th.get("opening") or 0)
    return min(cands) if cands else None

def pick_thread(S, now_ms=None):
    """가장 오래된 일감 스레드 id 반환(없으면 None) — 스레드 간 FIFO(기아 방지)."""
    now = now_ms or time.time() * 1000
    best = None
    for tid, th in (S.get("threads") or {}).items():
        a = _age(th, now)
        if a is not None and (best is None or a < best[0]):
            best = (a, tid)
    return best[1] if best else None

def leave_room(S, persona):
    """persona를 2명+ 방 전부에서 제거 + last_sp/barged를 생존자로 인계(1:1 room[1명]은 유지 = 잠금은 게이트가).
    사망 이탈(yeta_chat.sh)·강퇴(JS op kick) 공통 '멤버 제거 계약'의 러너측 SSOT. 멱등.
    ⚠️ #3 회귀원: room만 필터하고 last_sp 인계를 빠뜨리면 뷰어 헤더가 죽은/나간 인물을 계속 가리킴(260714)."""
    if not persona:
        return S
    for th in (S.get("threads") or {}).values():
        rm = [r for r in (th.get("room") or []) if r]
        if persona in rm and len(rm) > 1:
            th["room"] = [r for r in rm if r != persona]
            if th.get("last_sp") == persona:
                th["last_sp"] = th["room"][0]           # 나간/죽은 화자가 마지막 화자면 생존자가 이어받음
            if (th.get("barged") or {}).get("id") == persona:
                th["barged"] = 0                         # 데뷔 전 이탈 = 내보내기 pill 스테일 회수
    return S

def thread_view(S, tid):
    """기존 단일 세션 로직 호환 읽기 뷰 — 스레드 필드 + 공유 필드 오버레이 + 타 스레드 메타(_others · 턴 텍스트 접근 금지 = 비밀 누수 차단)."""
    th = (S.get("threads") or {}).get(tid) or {}
    v = dict(th)
    v["persona"] = th.get("last_sp") or tid
    for k in ("note_pub", "note", "notes", "tunes", "policy", "pref"):
        v[k] = S.get(k)
    v["_others"] = [{"id": o, "updated": (S["threads"][o] or {}).get("updated") or 0,
                     "n": len((S["threads"][o] or {}).get("turns") or [])}
                    for o in (S.get("threads") or {}) if o != tid]
    return v
