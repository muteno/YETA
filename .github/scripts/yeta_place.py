# yeta_place.py — 무음동 위치 판정(260707 마주침 이벤트 · 정본 데이터 = apps/yeta/places.json)
# place_of = 동선표(routine) 기본 + 결정적 시드(sha256)로 가끔(1/4) 인접 장소 외출 — 같은 날·같은 슬롯 = 같은 위치(무저장·재현 가능).
# 러너(extract_mat·barge_check·초대 판정)와 향후 지도 UI가 이 함수 하나만 쓴다(사본 금지 — 드리프트 씨앗).
import hashlib
import json


def load_places(path="apps/yeta/places.json"):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return {"places": {}, "routine": {}}


def world_dh(now_ts=None):
    """무음동 세계 (날짜열 'w<일련일>', 시각 0~23) — 6배 가속(운영자 260716 지도 싱크: 동선·지도·근처·원거리 시간축을 세계 시각으로 통일).
    공식 짝 3점(드리프트 금지): 뷰어 window.yWorldDH · 러너 state_block wmin(yeta_chat.sh) · 여기."""
    import time as _t
    wt = (now_ts if now_ts is not None else _t.time()) / 60 * 6
    return f"w{int(wt // 1440)}", int(wt % 1440 // 60)


def slot_of(hour):
    """state_block 시간대와 동일 경계 — late(0~3)·dawn(3~7)·morning(7~11)·day(11~17)·evening(17~21)·night(21~24)."""
    if hour < 3: return "late"
    if hour < 7: return "dawn"
    if hour < 11: return "morning"
    if hour < 17: return "day"
    if hour < 21: return "evening"
    return "night"


def place_of(pl, char_id, date_str, hour):
    """캐릭터의 지금 장소 id — 동선표 기본 · 시드 1/4로 인접 외출(집(private)은 변주 없음 — 사생활). 미등재 캐릭터 = ""(위치 축 비활성)."""
    slot = slot_of(hour)
    base = ((pl.get("routine") or {}).get(char_id) or {}).get(slot) or ""
    if not base:
        return ""
    info = (pl.get("places") or {}).get(base) or {}
    if info.get("private"):
        return base
    nb = [n for n in (info.get("neighbors") or []) if not ((pl.get("places") or {}).get(n) or {}).get("private")]
    if nb:
        # 이동 빈도 상향(운영자 260709 "장소 이동 많이 — 소통이 자유롭지 않게"): 1/4→1/2 + 2시간 입도(같은 슬롯에도 h//2 단위 재판정 = 결정적 유지) · 뷰어 ymPlaceOf와 시드 문자열 완전 동일(드리프트 금지)
        seed = int(hashlib.sha256(f"{char_id}:{date_str}:{slot}:{hour // 2}:go".encode()).hexdigest(), 16)
        if seed % 2 == 0:
            return nb[seed % len(nb)]
    return base


def place_name(pl, place_id):
    return (((pl.get("places") or {}).get(place_id) or {}).get("name")) or ""
