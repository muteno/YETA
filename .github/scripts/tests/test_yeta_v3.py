# yeta v3 세션 로직 회귀 테스트 (stdlib unittest — 신규 의존성 0)
# 대상 = yeta_v3.py 순수함수 SSOT: migrate_v3(JS migrateV3 동형)·pick_thread(age 큐)·leave_room(멤버 제거 계약).
# 실행: python3 .github/scripts/tests/test_yeta_v3.py   (또는 python3 -m unittest discover .github/scripts/tests)
# 목적: #3(사망 last_sp 인계 누락)·마이그레이션·스레드 큐 회귀를 커밋 단계에서 고정 — 러너 heredoc 손검증 대체.
import os, sys, unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from yeta_v3 import migrate_v3, pick_thread, leave_room, thread_view, INVITE_TTL_MS


def _th(**kw):
    base = {"turns": [], "state": "idle", "opening": 0, "awaiting_since": 0, "err": "",
            "room": [], "invite": None, "barged": 0, "declined": {}, "pin": 0,
            "updated": 0, "last_sp": "", "char_ver": "", "nudge": None}
    base.update(kw)
    return base


class TestMigrateV3(unittest.TestCase):
    def test_non_dict_returns_empty_skeleton(self):
        s = migrate_v3(None)
        self.assertEqual(s["v"], 3)
        self.assertEqual(s["threads"], {})
        self.assertEqual(s["me"], {"call": "", "about": ""})

    def test_v3_is_idempotent(self):
        s0 = {"v": 3, "cur": "haeun", "threads": {"haeun": _th(room=["haeun"])}}
        s1 = migrate_v3(s0)
        self.assertIs(s1, s0)                       # 멱등 = 동일 객체 반환(랩 없음)
        self.assertEqual(s1["v"], 3)
        self.assertIn("me", s1)                     # me 백필
        self.assertEqual(migrate_v3(s1)["threads"], s1["threads"])  # 2회차도 안정

    def test_threads_key_presence_forces_v3(self):
        s = migrate_v3({"threads": {}})            # v 미표기여도 threads 있으면 v3 취급
        self.assertEqual(s["v"], 3)

    def test_v2_wraps_persona_thread(self):
        s = migrate_v3({"persona": "haeun", "turns": [{"role": "user", "text": "hi", "ts": 100}]})
        self.assertEqual(s["v"], 3)
        self.assertEqual(s["cur"], "haeun")
        self.assertIn("haeun", s["threads"])
        self.assertEqual(s["threads"]["haeun"]["room"], ["haeun"])   # room 백필 = [persona]
        self.assertEqual(s["threads"]["haeun"]["last_sp"], "haeun")

    def test_v2_preserves_explicit_room(self):
        s = migrate_v3({"persona": "haeun", "turns": [{"role": "user", "ts": 1}], "room": ["haeun", "winter"]})
        self.assertEqual(s["threads"]["haeun"]["room"], ["haeun", "winter"])

    def test_v2_empty_turns_no_thread(self):
        s = migrate_v3({"persona": "haeun", "turns": []})
        self.assertEqual(s["threads"], {})          # 턴 없으면 스레드 미생성
        self.assertEqual(s["cur"], "haeun")


class TestPickThread(unittest.TestCase):
    def test_empty(self):
        self.assertIsNone(pick_thread({"threads": {}}, now_ms=1000))

    def test_pending_user_turn_picked(self):
        S = {"threads": {"haeun": _th(turns=[{"role": "user", "ts": 500}])}}
        self.assertEqual(pick_thread(S, now_ms=1000), "haeun")

    def test_answered_thread_not_picked(self):
        S = {"threads": {"haeun": _th(turns=[{"role": "user", "ts": 100}, {"role": "assistant", "ts": 200}])}}
        self.assertIsNone(pick_thread(S, now_ms=1000))   # 답장 뒤 pending 없음 = 일감 아님

    def test_fifo_oldest_pending_wins(self):
        S = {"threads": {
            "a": _th(turns=[{"role": "user", "ts": 800}]),
            "b": _th(turns=[{"role": "user", "ts": 300}]),   # 더 오래된 대기 = 우선(기아 방지)
        }}
        self.assertEqual(pick_thread(S, now_ms=1000), "b")

    def test_opening_flag_picked(self):
        S = {"threads": {"haeun": _th(opening=400, turns=[])}}
        self.assertEqual(pick_thread(S, now_ms=1000), "haeun")

    def test_fresh_invite_picked_stale_not(self):
        fresh = {"threads": {"g1": _th(room=["haeun"], invite={"to": "winter", "ts": 900})}}
        self.assertEqual(pick_thread(fresh, now_ms=1000), "g1")
        stale = {"threads": {"g1": _th(room=["haeun"], invite={"to": "winter", "ts": 1000 - INVITE_TTL_MS - 1})}}
        self.assertIsNone(pick_thread(stale, now_ms=1000))   # TTL 초과 초대 = 일감 아님


class TestLeaveRoom(unittest.TestCase):
    def test_removes_from_two_room_and_reassigns_last_sp(self):
        # #3 회귀 고정: 죽은/나간 화자가 last_sp면 생존자가 이어받아야(안 그러면 헤더가 죽은 인물 표시)
        S = {"threads": {"g1": _th(room=["haeun", "winter"], last_sp="haeun")}}
        leave_room(S, "haeun")
        self.assertEqual(S["threads"]["g1"]["room"], ["winter"])
        self.assertEqual(S["threads"]["g1"]["last_sp"], "winter")   # ← 핵심 단언

    def test_clears_barged_marker(self):
        S = {"threads": {"g1": _th(room=["haeun", "winter"], last_sp="winter", barged={"id": "haeun", "ts": 1})}}
        leave_room(S, "haeun")
        self.assertEqual(S["threads"]["g1"]["barged"], 0)

    def test_preserves_last_sp_when_not_leaver(self):
        S = {"threads": {"g1": _th(room=["haeun", "winter"], last_sp="winter")}}
        leave_room(S, "haeun")
        self.assertEqual(S["threads"]["g1"]["room"], ["winter"])
        self.assertEqual(S["threads"]["g1"]["last_sp"], "winter")   # 나간 사람이 아니면 무변경

    def test_one_to_one_room_preserved(self):
        # 1:1(room 1명)은 유지 — 사망 잠금은 게이트가, 방 자체는 남음
        S = {"threads": {"haeun": _th(room=["haeun"], last_sp="haeun")}}
        leave_room(S, "haeun")
        self.assertEqual(S["threads"]["haeun"]["room"], ["haeun"])

    def test_removes_from_all_rooms(self):
        S = {"threads": {
            "g1": _th(room=["haeun", "winter"], last_sp="haeun"),
            "g2": _th(room=["kopi", "haeun"], last_sp="kopi"),
            "haeun": _th(room=["haeun"], last_sp="haeun"),   # 1:1 = 유지
        }}
        leave_room(S, "haeun")
        self.assertEqual(S["threads"]["g1"]["room"], ["winter"])
        self.assertEqual(S["threads"]["g2"]["room"], ["kopi"])
        self.assertEqual(S["threads"]["haeun"]["room"], ["haeun"])

    def test_empty_persona_noop(self):
        S = {"threads": {"g1": _th(room=["haeun", "winter"], last_sp="haeun")}}
        leave_room(S, "")
        self.assertEqual(S["threads"]["g1"]["room"], ["haeun", "winter"])

    def test_idempotent(self):
        S = {"threads": {"g1": _th(room=["haeun", "winter"], last_sp="haeun")}}
        leave_room(S, "haeun")
        leave_room(S, "haeun")                       # 2회차 = 무변경
        self.assertEqual(S["threads"]["g1"]["room"], ["winter"])
        self.assertEqual(S["threads"]["g1"]["last_sp"], "winter")


if __name__ == "__main__":
    unittest.main(verbosity=2)
