#!/usr/bin/env python3
# yeta_map_trace.py — 지도 도로 재실측·마스크 재생성 도구 v5 (운영자 260716 "픽셀 단위로 길을 쪼개고 레이어 분리")
# 배경(map_day/night.png)은 생성 이미지라 재생성하면 도로 좌표·픽셀 마스크가 전부 실효한다. 이 스크립트가 재실측 정본 경로.
#
# 산출(= 커밋 대상):
#   viewer/assets/yeta_map/road_mask_{night,day}.png — 아스팔트 픽셀 백색 마스크(512², #ymCars SVG mask 짝).
#   $YMT_OUT(기본 /tmp)/ymt_overlay_{tone}.png — 차선 중심선 + 차 가시밴드(초록=보임·빨강=클립) 육안 QA.
#
# 방법(v5 확정 · v4 점선 히스토그램 단독 방식은 창불빛 오검출로 폐기):
#   ① 도로 좌표 SSOT = viewer/index.html YMAP_ROADS_TONE(직선 y=±0.5x+c · 수직 x=c)을 파싱(드리프트 0).
#   ② 각 도로 회랑(중심선 ±2.5u)에서 중심선 위 국소 기준색(롤링 중앙값 · 가림 스테이션 제외)과 도로 전역 기준색을
#      AND 게이트로 아스팔트 픽셀 분류 + 노면 흰 표시(점선·횡단보도)는 무조건 포함.
#   ③ 건물·나무가 회랑을 덮는 픽셀 = 기각 = 마스크 구멍 → 차가 그 뒤로 숨음(z 분리 — 'h' 은폐 플래그 대체).
#   좌표 자체가 어긋났으면: 회랑 ±2.8u 안 흰 표시 픽셀의 수직 오프셋 중앙값만큼 c를 옮겨 재시도(스냅 리포트 출력).
# 마지막에 YMAP_BG_SHA 토큰(check_refs 짝 게이트)용 sha1[:8] 출력.
# 의존: pip install pillow numpy scipy
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.environ.get('YMT_OUT', '/tmp')
HW = 2.5          # 회랑 반폭(u · 실측 도로 전폭 ~4.5-5u)
CARBAND = 1.9     # 차 실렌더 밴드(차선 오프셋 1.2 + 차 반폭 0.62 + 여유)
TUNE = {'night': dict(tol=32, gtol=52, white_lo=100, anchor_lo=112), 'day': dict(tol=36, gtol=62, white_lo=175, anchor_lo=180)}
# white_lo = 마스크 포함용(어두운 점선까지 포섭 — 차가 노면표시 위에서 안 끊기게) · anchor_lo = c 스냅 앵커용(밝은 확실 표시만 — 보도 밝은 픽셀 오염 차단)


def parse_roads(tone):
    """viewer/index.html YMAP_ROADS_TONE → {이름: [[x,y,f?],...]} (좌표 SSOT — 여기서 직접 파싱 = 드리프트 0)."""
    src = open(os.path.join(ROOT, 'viewer/index.html'), encoding='utf-8').read()
    body = re.search(r'const YMAP_ROADS_TONE = \{(.*?)\n\};', src, re.S).group(1)
    tm = re.search(tone + r': \{(.*?)\n  \}', body, re.S)
    return {n: json.loads(p.replace("'", '"')) for n, p in re.findall(r'(\w+):\s*(\[\[.*?\]\])', tm.group(1))}


def segments(pts):
    """폴리라인 → (kind, c, a0, a1) 구간 목록. kind: d+(y=0.5x+c) · d-(y=-0.5x+c) · v(x=c)."""
    out = []
    for a, b in zip(pts, pts[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        if abs(dx) < 1e-6:
            out.append(('v', a[0], min(a[1], b[1]), max(a[1], b[1])))
        else:
            m = dy / dx
            kind = 'd+' if m > 0 else 'd-'
            out.append((kind, a[1] - m * a[0], min(a[0], b[0]), max(a[0], b[0])))
    return out


def build(tone):
    import numpy as np
    from PIL import Image, ImageFilter
    from scipy import ndimage as ndi
    cfg = TUNE[tone]
    path = os.path.join(ROOT, f'viewer/assets/yeta_map/map_{tone}.png')
    print(f'=== {tone} · sha1[:8] = {hashlib.sha1(open(path, "rb").read()).hexdigest()[:8]} (YMAP_BG_SHA 토큰)')
    im = np.asarray(Image.open(path).convert('RGB')).astype(np.float32)
    H, W = im.shape[:2]; u = W / 100.0
    med = ndi.median_filter(im, size=(5, 5, 1))
    Y, X = np.mgrid[0:H, 0:W]; Xu, Yu = X / u, Y / u
    sat = im.max(2) - im.min(2); mn = im.min(2)
    white = (mn > cfg['white_lo']) & (sat < 55)
    anchor = (mn > cfg['anchor_lo']) & (sat < 50)
    mask = np.zeros((H, W), bool); carband = np.zeros((H, W), bool)
    for name, pts in parse_roads(tone).items():
        for kind, c, a0, a1 in segments(pts):
            if kind == 'v':
                d, nv = np.array([0., 1.]), np.array([1., 0.])
                p0 = np.array([c, 0.]); E = Yu
            else:
                m = 0.5 if kind == 'd+' else -0.5
                d = np.array([1., m]); d /= np.linalg.norm(d)
                nv = np.array([-d[1], d[0]]); p0 = np.array([0., c]); E = Xu
            Pd = (Xu - p0[0]) * nv[0] + (Yu - p0[1]) * nv[1]
            stripe = (np.abs(Pd) <= HW) & (E >= a0) & (E <= a1)
            # 흰 표시 앵커 스냅 리포트(|중앙값|>0.8u = 좌표 어긋남 경고 — viewer 좌표를 고치라는 신호)
            wsel = anchor & (np.abs(Pd) <= 2.8) & (E >= a0) & (E <= a1)
            if wsel.sum() >= 40:
                off = float(np.median(Pd[wsel]))
                if abs(off) > 0.8:
                    print(f'   ⚠️ {name}: 흰 표시 수직 오프셋 {off:+.2f}u — viewer c를 {off * (1.118 if kind != "v" else 1):+.1f} 이동 권고')
            ts = np.arange(a0, a1 + 1e-9, 0.5)
            if kind == 'v':
                sx, sy = np.full_like(ts, c), ts
            else:
                m = 0.5 if kind == 'd+' else -0.5
                sx, sy = ts, m * ts + c
            cols = np.array([med[int(np.clip(y * u, 0, H - 1)), int(np.clip(x * u, 0, W - 1))] for x, y in zip(sx, sy)])
            gref = np.median(cols, 0)
            good = np.max(np.abs(cols - gref), 1) < cfg['gtol']
            ref = np.array([np.median(cols[max(0, i - 10):i + 11][good[max(0, i - 10):i + 11]], 0)
                            if good[max(0, i - 10):i + 11].sum() >= 3 else gref for i in range(len(cols))])
            si = np.clip(((E - a0) / 0.5).astype(int), 0, len(ts) - 1)
            cd_l = np.maximum.reduce([np.abs(med[:, :, ch] - ref[:, ch][si]) for ch in range(3)])
            cd_g = np.maximum.reduce([np.abs(med[:, :, ch] - gref[ch]) for ch in range(3)])
            mask |= stripe & (((cd_l < cfg['tol']) & (cd_g < cfg['gtol'])) | (white & stripe))
            carband |= (np.abs(Pd) <= CARBAND) & (E >= a0) & (E <= a1)
    mask = ndi.binary_closing(mask, np.ones((9, 9)))
    mask = ndi.binary_opening(mask, np.ones((3, 3)))
    # 합성 건물 레이어(성당 등) 구멍 — 뷰어 #ymBld와 동일 배치(500-space 박스 350,42,80,80 · 바닥 앵커 ⚠️ viewer와 짝):
    # 스프라이트 불투명 픽셀을 도로 마스크에서 제거 = 차가 건물 뒤로 자연 은폐(u2·다리가 성당과 겹치는 구간 z 정합 · 운영자 260717)
    bld = os.path.join(ROOT, f'viewer/assets/yeta_map/bld_cathedral_{tone}.png')
    if os.path.exists(bld):
        spr = Image.open(bld).convert('RGBA')
        k = W / 500.0
        bw = int(80 * k)
        s = spr.copy(); s.thumbnail((bw, bw))
        px, py = int(350 * k) + (bw - s.width) // 2, int(42 * k) + (bw - s.height)
        hole = np.zeros((H, W), bool)
        hole[py:py + s.height, px:px + s.width] = np.asarray(s)[:, :, 3] > 60
        cut = int((hole & mask).sum())
        mask &= ~hole
        print(f'   성당 레이어 구멍 — 겹친 도로 픽셀 {cut}개 마스크 제거(차 = 성당 뒤 은폐)')
    mp = Image.fromarray((mask * 255).astype('uint8'), 'L').resize((512, 512), Image.LANCZOS)
    mp = mp.filter(ImageFilter.GaussianBlur(0.8))
    out_mask = os.path.join(ROOT, f'viewer/assets/yeta_map/road_mask_{tone}.png')
    mp.save(out_mask, optimize=True)
    vis = carband & mask
    print(f'   마스크 {mask.mean() * 100:.1f}% · 차 밴드 가시 {vis.sum() / max(carband.sum(), 1) * 100:.1f}% → {out_mask}')
    ov = im.copy()
    ov[vis] = ov[vis] * .45 + np.array([60, 255, 120]) * .55
    clip = carband & ~mask
    ov[clip] = ov[clip] * .45 + np.array([255, 60, 60]) * .55
    qa = os.path.join(OUT, f'ymt_overlay_{tone}.png')
    Image.fromarray(ov.astype('uint8')).save(qa)
    print(f'   QA 오버레이 → {qa} (초록=차 보임 · 빨강=클립[건물·나무 가림 = 정상] — 도로 위인지 눈으로 QA)')


def fg_check(tone):
    """가림체(YMAP_FG) 픽셀 지문 검증(Q.11 한 수) — 폴리곤 내부 중앙값 RGB(/6 양자화) 해시를 viewer YMAP_FG_FP 토큰과 대조.
    배경 재생성으로 폴리곤이 구조물에서 벗어나면 내부 픽셀이 바뀌어 지문이 어긋난다 → 재실측 경고 + 새 토큰 제시."""
    import hashlib as _h
    import numpy as np
    from PIL import Image, ImageDraw
    src = open(os.path.join(ROOT, 'viewer/index.html'), encoding='utf-8').read()
    blk = re.search(r'const YMAP_FG = \{(.*?)\n\};', src, re.S)
    tokm = re.search(r'YMAP_FG_FP: night=([0-9a-f]{8}) day=([0-9a-f]{8})', src)
    if not blk or not tokm:
        print('   ⚠️ 가림체 지문 게이트 — YMAP_FG 블록/YMAP_FG_FP 토큰 미검출(둘 다 viewer/index.html)'); return
    tm = re.search(tone + r': \[(.*?)\n  \]', blk.group(1), re.S)
    polys = [json.loads(p) for p in re.findall(r'pts: (\[\[.*?\]\])', tm.group(1))]
    im = np.asarray(Image.open(os.path.join(ROOT, f'viewer/assets/yeta_map/map_{tone}.png')).convert('RGB')).astype(np.float32)
    H, W = im.shape[:2]; u = W / 100.0
    meds = []
    for pts in polys:
        pm = Image.new('L', (W, H), 0)
        ImageDraw.Draw(pm).polygon([(x * u, y * u) for x, y in pts], fill=255)
        med = np.median(im[np.asarray(pm) > 0], 0)
        meds.append([int(v) // 6 for v in med])
    fp = _h.sha1(json.dumps(meds).encode()).hexdigest()[:8]
    want = tokm.group(1) if tone == 'night' else tokm.group(2)
    if fp != want:
        print(f'   ⚠️ 가림체 지문 불일치({tone}: {fp} ≠ 토큰 {want}) — 배경이 바뀌어 YMAP_FG 폴리곤이 구조물에서 벗어났을 수 있음: 폴리곤 재실측 후 토큰을 {fp}로 갱신')
    else:
        print(f'   ✅ 가림체 지문 일치({tone}: {fp}) — YMAP_FG 폴리곤 ↔ 배경 정합')


def main():
    try:
        import numpy, scipy, PIL  # noqa: F401
    except ImportError as e:
        print(f'의존 누락({e.name}): pip install pillow numpy scipy'); return 1
    for tone in ['night', 'day']:
        build(tone)
        fg_check(tone)
    return 0


if __name__ == '__main__':
    sys.exit(main())
