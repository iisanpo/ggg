# -*- coding: utf-8 -*-
"""이미지형 시험지 PDF → 단 이미지 + 한글 OCR 초벌 + 문항 번호 위치표
사용: python3 render_scan.py <exam_id> <교시> <pdf>
결과: exams/<exam>/scan/s<교시>/cols/p01L.png …, ocr/p01L.txt …, qmap.json
"""
import sys, os, re, json, subprocess
import pymupdf
from PIL import Image, ImageOps

exam, sess, pdf = sys.argv[1], int(sys.argv[2]), sys.argv[3]
base = '/home/claude/hx/exams/%s/scan/s%d' % (exam, sess)
for d in ('pages', 'cols', 'ocr'): os.makedirs(os.path.join(base, d), exist_ok=True)
doc = pymupdf.open(pdf)

def split_x(img):
    g = ImageOps.grayscale(img); w, h = g.size; px = g.load()
    y0, y1 = int(h * 0.10), int(h * 0.93)
    cols = range(int(w * 0.40), int(w * 0.60))
    ink = {}
    for x in cols:
        ink[x] = sum(1 for y in range(y0, y1, 2) if px[x, y] < 140)
    # 세로 구분선이 있으면(거의 전 구간이 검은 열) 그 열, 없으면 잉크가 가장 적은 열
    tall = max(ink.values())
    if tall > (y1 - y0) / 2 * 0.6:
        return max(ink, key=ink.get)
    return min(ink, key=ink.get)

qmap = {}
for i, page in enumerate(doc):
    n = i + 1
    pix = page.get_pixmap(dpi=220)
    pp = os.path.join(base, 'pages', 'p%02d.png' % n); pix.save(pp)
    img = Image.open(pp).convert('RGB'); w, h = img.size
    gx = split_x(img)
    top, bot = int(h * 0.03), int(h * 0.965)
    parts = {'L': img.crop((int(w * 0.025), top, gx - 5, bot)), 'R': img.crop((gx + 6, top, int(w * 0.975), bot))}
    for side, im in parts.items():
        cp = os.path.join(base, 'cols', 'p%02d%s.png' % (n, side)); im.save(cp)
        txt = subprocess.run(['tesseract', cp, '-', '-l', 'kor+eng', '--psm', '4'],
                             capture_output=True, text=True).stdout
        open(os.path.join(base, 'ocr', 'p%02d%s.txt' % (n, side)), 'w', encoding='utf-8').write(txt)
        nums = [int(m.group(1)) for m in re.finditer(r'(?m)^\s*(\d{1,3})\s*[.,]\s*\S', txt)]
        qmap['p%02d%s' % (n, side)] = nums
    print('p%02d gutter=%d/%d' % (n, gx, w), qmap['p%02dL' % n][:8], qmap['p%02dR' % n][:8])
json.dump(qmap, open(os.path.join(base, 'qmap.json'), 'w'), ensure_ascii=False)
