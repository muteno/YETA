#!/usr/bin/env python3
"""시즌 감정 미디어 manifest 생성기 — viewer/characters/season/<id>/media.json 재생성 (260717 Q.25)

운영 흐름(운영자 260717 "수집은 많이 해줄 수 있는데 감정 명시가 비효율"):
  사진을 모드 폴더(android/·dokkaebi/)에 **아무 이름으로** 던져넣고 이 스크립트를 돌리면 끝.
  파일명에 감정을 쓸 필요 없음 — 감정(무드) 버킷은 폴더→버킷 매핑(SEASONS)이 담당.

규약:
  · 버킷 = base/warm/tense/blue (viewer yStage · 러너 <<MOOD>> 화이트리스트와 짝 — 불변)
  · mode_dir = 변신 모드 전용 폴더명 — viewer yStage 모드 게이트(yModeOn)가 이 폴더 경로로 필터
  · 클립(mp4/webm · 캐릭터 루트) = base 선두(대화 시작 배경 계약 — media.json _comment 정본)
  · 산출물 media.json = 기계 산출물(CLAUDE.md [0] ⚙) — 손편집 금지, 값 바꾸려면 이 스크립트를 고쳐라.

사용: python3 shared/build_season_media.py            # 전 시즌 캐릭터 재생성
      python3 shared/build_season_media.py --check    # 재생성 없이 드리프트 검사(rc=1)
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEASON_DIR = ROOT / "viewer" / "characters" / "season"
IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"}
CLIP_EXT = {".mp4", ".webm"}

# 캐릭터별 폴더→버킷 매핑(모드↔무드 정본 — 루시: 안드로이드=낮 시크(base·blue) / 도깨비=밤 고에너지(warm·tense))
SEASONS = {
    "lucy": {
        "buckets": {"base": ["_clips", "android"], "blue": ["android"], "warm": ["dokkaebi"], "tense": ["dokkaebi"]},
        "mode_dir": "dokkaebi",
        "comment": ("시즌 감정 미디어 manifest(루시) — 기계 산출물(shared/build_season_media.py · 손편집 금지). "
                    "yStage 답장수 n 결정적 로테이션 pool[n%len]. base 선두 클립=대화 시작배경(muted 비디오). "
                    "모드↔무드: 안드로이드(낮 시크 자동인형)=base·blue / 도깨비(밤 레베카 고에너지)=warm·tense. "
                    "mode_dir=도깨비 폴더 — viewer 모드 게이트(yModeOn)가 활성 시 이 폴더만, 평시 이 폴더 제외로 필터. "
                    "정본=viewer/characters/season/lucy/{android,dokkaebi}/ — 사진은 아무 이름으로 폴더에만 넣으면 됨."),
    },
}


def rel(p: Path) -> str:
    return p.relative_to(ROOT / "viewer").as_posix()  # viewer 서빙 루트 기준(로스터 bg 경로 규약과 동일)


def build_one(cid: str, cfg: dict) -> dict:
    cdir = SEASON_DIR / cid
    if not cdir.is_dir():
        raise SystemExit(f"캐릭터 폴더 없음: {cdir}")
    clips = sorted(p for p in cdir.iterdir() if p.suffix.lower() in CLIP_EXT)
    folders = {"_clips": clips}
    for sub in sorted(d for d in cdir.iterdir() if d.is_dir()):
        folders[sub.name] = sorted(p for p in sub.iterdir() if p.suffix.lower() in IMG_EXT)
    out = {"_comment": cfg["comment"]}
    for bucket, srcs in cfg["buckets"].items():
        files = []
        for s in srcs:
            files.extend(folders.get(s, []))
        out[bucket] = [rel(p) for p in files]
    if cfg.get("mode_dir"):
        out["mode_dir"] = cfg["mode_dir"]
    return out


def main() -> int:
    check = "--check" in sys.argv
    rc = 0
    for cid, cfg in SEASONS.items():
        mpath = SEASON_DIR / cid / "media.json"
        fresh = build_one(cid, cfg)
        cur = None
        if mpath.exists():
            try:
                cur = json.loads(mpath.read_text(encoding="utf-8"))
            except Exception:
                cur = None
        if cur == fresh:
            print(f"OK {cid}: media.json 최신 (base {len(fresh['base'])} · warm {len(fresh['warm'])} · tense {len(fresh['tense'])} · blue {len(fresh['blue'])})")
            continue
        if check:
            print(f"DRIFT {cid}: media.json ≠ 폴더 실측 — python3 shared/build_season_media.py 로 재생성")
            rc = 1
            continue
        mpath.write_text(json.dumps(fresh, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"WROTE {cid}: media.json 재생성 (base {len(fresh['base'])} · warm {len(fresh['warm'])} · tense {len(fresh['tense'])} · blue {len(fresh['blue'])} · mode_dir {fresh.get('mode_dir', '-')})")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
