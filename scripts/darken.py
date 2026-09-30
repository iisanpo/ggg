# -*- coding: utf-8 -*-
"""렌더된 PDF의 여백까지 배경색으로 채운다(크로미움은 페이지 여백을 칠하지 않는다)."""
import sys, pymupdf
f, hexcol = sys.argv[1], sys.argv[2]
c = tuple(int(hexcol[i:i+2], 16) / 255 for i in (1, 3, 5))
d = pymupdf.open(f)
for p in d:
    p.draw_rect(p.rect, color=c, fill=c, overlay=False)
d.saveIncr() if d.can_save_incrementally() else d.save(f + '.tmp')
import os
if os.path.exists(f + '.tmp'): os.replace(f + '.tmp', f)
print('배경 채움', f, d.page_count, '쪽')
