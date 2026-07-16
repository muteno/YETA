#!/usr/bin/env python3
# yeta_map_trace.py — 지도 도로 재실측 도구(운영자 260716 Q.08 · 평의회9 "고쳐도 그대로" 반복 절단)
# 배경(map_day/night.png)은 생성 이미지라 재생성하면 viewer/index.html YMAP_ROADS_TONE 좌표가 전부 실효한다.
# 이 스크립트가 재실측의 정본 경로: ① 차선 흰 점선 픽셀 블롭 검출 → ② ±0.5 아이소메트릭(2:1) 기울기 가족의
# c값 히스토그램(도로 중심선 후보) 출력 → ③ 현행 코드 좌표를 배경 위에 렌더한 오버레이 PNG 산출(육안 QA).
# 마지막에 YMAP_BG_SHA 토큰(check_refs 짝 게이트)용 sha1[:8]을 출력한다.
# 사용: python3 shared/yeta_map_trace.py  → /tmp 아래 overlay_{night,day}.png 를 눈으로 보고 좌표를 맞춘 뒤 토큰 갱신.
import hashlib
import json
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.environ.get('YMT_OUT', '/tmp')


def detect_dashes(im, night):
    """차선 흰 점선(밝은 소형 블롭) 중심점 목록 — % 좌표. 크로스워크·간판 일부 섞임 = 히스토그램에서 걸러냄."""
    W, H = im.size
    px = im.load()
    lo = 118 if night else 175            # 밤 점선은 어두운 톤 위 회백(실측 260716)
    vis = [[False] * W for _ in range(H)]

    def bright(x, y):
        r, g, b = px[x, y][:3]
        return min(r, g, b) > lo and max(r, g, b) - min(r, g, b) < (40 if night else 45)

    blobs = []
    for y0 in range(0, H, 2):
        for x0 in range(0, W, 2):
            if vis[y0][x0] or not bright(x0, y0):
                continue
            stack, pts = [(x0, y0)], []
            while stack:
                x, y = stack.pop()
                if x < 0 or y < 0 or x >= W or y >= H or vis[y][x] or not bright(x, y):
                    continue
                vis[y][x] = True
                pts.append((x, y))
                stack += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
            if 15 <= len(pts) <= 1500:
                xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
                if max(max(xs) - min(xs), max(ys) - min(ys)) <= 60:
                    blobs.append((sum(xs) / len(xs) / W * 100, sum(ys) / len(ys) / H * 100))
    return blobs


def histogram(blobs):
    """±0.5 기울기 가족별 c값 분포 — c = y ∓ 0.5x. 피크(n 큰 c) = 도로 중심선 후보."""
    for fam, sign in [('A ↘ y=0.5x+c', -0.5), ('B ↗ y=-0.5x+c', +0.5)]:
        h = defaultdict(list)
        for x, y in blobs:
            h[round(y + sign * x)].append(x)
        print(f'-- {fam}')
        for c in sorted(h):
            xs = h[c]
            if len(xs) >= 3:
                print(f'   c={c:4d} n={len(xs):3d} x=[{min(xs):5.1f}~{max(xs):5.1f}]')


def parse_roads(tone):
    src = open(os.path.join(ROOT, 'viewer/index.html'), encoding='utf-8').read()
    body = re.search(r'const YMAP_ROADS_TONE = \{(.*?)\n\};', src, re.S).group(1)
    tm = re.search(tone + r': \{(.*?)\n  \}', body, re.S)
    return {n: json.loads(p.replace("'", '"')) for n, p in re.findall(r'(\w+): (\[\[.*?\]\])', tm.group(1))}


def main():
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print('Pillow 필요: pip install pillow'); return 1
    for tone in ['night', 'day']:
        path = os.path.join(ROOT, f'viewer/assets/yeta_map/map_{tone}.png')
        im = Image.open(path).convert('RGB')
        print(f'=== {tone} · sha1[:8] = {hashlib.sha1(open(path, "rb").read()).hexdigest()[:8]} (YMAP_BG_SHA 토큰)')
        histogram(detect_dashes(im, tone == 'night'))
        W, H = im.size
        d = ImageDraw.Draw(im)
        for i in range(0, 101, 10):
            x = i / 100 * W
            d.line([(x, 0), (x, H)], fill=(255, 0, 255), width=1)
            d.line([(0, x), (W, x)], fill=(255, 0, 255), width=1)
            for j in range(0, 101, 10):
                d.text((i / 100 * W + 3, j / 100 * H + 2), f'{i},{j}', fill=(255, 255, 0))
        for name, pts in parse_roads(tone).items():
            for a, b in zip(pts, pts[1:]):
                hid = len(a) > 2 and a[2] == 'h'
                d.line([(a[0] / 100 * W, a[1] / 100 * H), (b[0] / 100 * W, b[1] / 100 * H)],
                       fill=(255, 150, 0) if hid else (0, 255, 80), width=4)
            d.text((pts[0][0] / 100 * W + 4, pts[0][1] / 100 * H), name, fill=(255, 255, 0))
        out = os.path.join(OUT, f'overlay_{tone}.png')
        im.save(out)
        print(f'   오버레이 → {out} (초록=가시 · 주황=은폐 h — 도로 회랑 위인지 눈으로 QA)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
