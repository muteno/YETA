#!/usr/bin/env python3
# main.png(운영자 포스터) → 텍스트/화살표 제거한 캐릭터 전용 배경(yeta-hero.webp) 생성.
# 로그인 텍스트(PLAY a Episode / YETA / 라벨)는 뷰어에서 애니메이션 오버레이로 재구성(첨부1/2·260704).
# 재생성: python3 shared/clean_hero.py
import numpy as np
from PIL import Image, ImageFilter
im=Image.open('main.png').convert('RGB'); arr=np.array(im); BG=np.array((1,3,2),'uint8')
g=np.array(im.convert('L')).astype(int)
arr[430:952,:,:]=BG                                   # 헤어 크라운 위 = PLAY라인+라벨+YETA상단(순흑 밴드)
for y in range(952,1122):                             # 헤어 겹침대 = 좌우 흑채움(브래킷 틱 포함) + 중앙 밝은글자 제거
    arr[y,:880]=BG; arr[y,1240:]=BG
    thr=165 if y<1012 else 185                        # 상단 = 브래킷 틱(밝음)까지 정리
    seg=arr[y,880:1240]; br=g[y,880:1240]>thr; seg[br]=BG; arr[y,880:1240]=seg
im2=Image.fromarray(arr)
ab=(1540,1555,1835,1878); asub=im2.crop(ab); ag=np.array(asub.convert('L'))  # 우측 화살표 = 미디언 인페인트
am=Image.fromarray(((ag>150)*255).astype('uint8')).filter(ImageFilter.MaxFilter(13))
asub=Image.composite(asub.filter(ImageFilter.MedianFilter(23)),asub,am); im2.paste(asub,ab)
im2.resize((1200,2133)).save('viewer/assets/brand/yeta-hero.webp','WEBP',quality=88,method=6)
print('yeta-hero.webp regenerated')
