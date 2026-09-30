# -*- coding: utf-8 -*-
"""글자층이 있는 공인중개사 문제지 PDF → 문항 JSON

- 글자 좌표로 줄을 다시 세우고(단 나누기·띄어쓰기 복원), 밑줄 도형으로 강조어(<b>)를 찾는다.
- 줄바꿈 자리의 띄어쓰기는 (1) 전체 문제지 말뭉치에서 붙여 쓴 예/띄어 쓴 예를 세고,
  (2) 근거가 없으면 Kiwi 형태소 분석기의 띄어쓰기 판단을 따른다.
- 표·그림·수식이 들어간 문항은 flags로 표시하고, 문항 영역 이미지를 crops/에 저장한다.
사용: python3 parse_pdf.py <exam_id> <pdf> [<pdf2>]   (2교시 파일이 따로면 두 번째 인자)
"""
import sys, os, re, json, collections
import pymupdf

HANGUL = re.compile(r'[가-힣]')
CIRC = '①②③④⑤'

def load_corpus():
    p = '/home/claude/hx/corpus.txt'
    return open(p, encoding='utf-8').read() if os.path.exists(p) else ''

_kiwi = None
def kiwi():
    global _kiwi
    if _kiwi is None:
        from kiwipiepy import Kiwi
        _kiwi = Kiwi()
    return _kiwi

# ---------------------------------------------------------------- 1. 글자 → 줄
def page_lines(page, gap=0.25):
    W, H = page.rect.width, page.rect.height
    mid = W / 2
    # 밑줄 후보: 얇은 가로선
    ul = []
    for g in page.get_drawings():
        r = g['rect']
        if r.height < 1.6 and 6 < r.width < W * 0.3:
            ul.append(r)
    # 표 격자 후보(가로·세로 선)
    grid = []
    for g in page.get_drawings():
        r = g['rect']
        if (r.height < 1.6 and r.width >= 20) or (r.width < 1.6 and r.height >= 12):
            grid.append(r)
    imgs = [pymupdf.Rect(i['bbox']) for i in page.get_image_info()]
    out = []
    for col, (x0, x1) in enumerate(((0, mid), (mid, W))):
        rd = page.get_text("rawdict", clip=pymupdf.Rect(x0, 0, x1, H))
        chars = []
        for b in rd['blocks']:
            for l in b.get('lines', []):
                for s in l['spans']:
                    for ch in s['chars']:
                        c = ch['c']
                        if not c.strip(): continue
                        bx0, by0, bx1, by1 = ch['bbox']
                        chars.append([(by0 + by1) / 2, bx0, bx1, c, s['size'], by0, by1])
        chars.sort(key=lambda c: (c[0], c[1]))
        rows = []
        for c in chars:
            if rows and abs(c[0] - rows[-1]['yc']) <= 0.45 * c[4]:
                rows[-1]['ch'].append(c)
            else:
                rows.append({'yc': c[0], 'ch': [c]})
        vlines = [g for g in grid if g.width < 1.6 and g.height >= 8 and x0 - 2 <= g.x0 <= x1 + 2]
        for r in rows:
            cs = sorted(r['ch'], key=lambda c: c[1])
            txt, prev, marks, cells = '', None, [], 0
            for c in cs:
                if prev is not None:
                    cut = any(prev - 0.5 <= v.x0 <= c[1] + 0.5 and v.y0 - 1 <= r['yc'] <= v.y1 + 1 for v in vlines)
                    if cut:
                        txt += ' | '; marks += [False, False, False]; cells += 1
                    elif c[1] - prev > gap * c[4]:
                        txt += ' '; marks.append(False)
                # 밑줄: 글자 바로 아래 얇은 선
                u = any(abs(u_.y0 - c[6]) < 3.2 and u_.x0 - 1 <= (c[1] + c[2]) / 2 <= u_.x1 + 1 for u_ in ul)
                txt += c[3]; marks.append(u)
                prev = c[2]
            y0 = min(c[5] for c in cs); y1 = max(c[6] for c in cs)
            out.append({'col': col, 'x0': cs[0][1], 'x1': cs[-1][2], 'y0': y0, 'y1': y1,
                        'size': max(c[4] for c in cs), 't': txt, 'u': marks, 'cells': cells})
    return out, grid, imgs

def mark_text(t, u):
    """밑줄 친 글자 구간을 <b>…</b>로 감싼다(공백 하나는 사이에 있어도 잇는다)."""
    res, on = [], False
    for i, (ch, m) in enumerate(zip(t, u)):
        if ch == ' ' and on:
            nxt = u[i + 1] if i + 1 < len(u) else False
            if not nxt: res.append('</b>'); on = False
            res.append(ch); continue
        if m and not on: res.append('<b>'); on = True
        if not m and on and ch != ' ': res.append('</b>'); on = False
        res.append(ch)
    if on: res.append('</b>')
    return ''.join(res)

# ---------------------------------------------------------------- 2. 줄 잇기
class Joiner:
    def __init__(self, corpus):
        self.corpus = corpus

    def _tok(self, w):
        """w가 말뭉치에서 하나의 온전한 어절로 쓰인 횟수"""
        key = ('T', w)
        if key not in self.cache:
            self.cache[key] = len(re.findall(r'(?:^|[\s(“‘｢「])' + re.escape(w) + r'(?=[\s,.)”’｣」?:;]|$)', self.corpus, re.M))
        return self.cache[key]

    def _cnt(self, s):
        key = ('C', s)
        if key not in self.cache: self.cache[key] = self.corpus.count(s)
        return self.cache[key]

    def decide(self, a, b):
        """a 줄 끝과 b 줄 앞을 이을 때 공백을 넣을지."""
        if not hasattr(self, 'cache'): self.cache = {}
        a_plain = re.sub(r'</?b>', '', a).rstrip(); b_plain = re.sub(r'</?b>', '', b).lstrip()
        if not a_plain or not b_plain: return ''
        la, fb = a_plain[-1], b_plain[0]
        if la in '(［[｢「“‘/-~∼' or fb in ')］]｣」”’,.·ㆍ/%~∼:;?!': return ''
        if fb in CIRC or re.match(r'^(ㄱ|ㄴ|ㄷ|ㄹ|ㅁ|ㅂ|ㅅ|ㅇ)[.)]', b_plain): return ' '
        if not (HANGUL.match(la) or la.isalnum() or la in ')｣」%'): return ' '
        w1 = re.split(r'[\s]', a_plain)[-1]; w2 = re.split(r'[\s]', b_plain)[0]
        w2 = re.sub(r'[,.)”’｣」?:;]+$', '', w2)
        w1 = re.sub(r'^[(“‘｢「]+', '', w1)
        if not w1 or not w2: return ' '
        J = self._cnt(w1 + w2); S = self._cnt(w1 + ' ' + w2)
        if J != S: return '' if J > S else ' '
        PART = {'는','은','을','를','의','으로','로','에','에서','에게','와','과','도','만','이','가','부터','까지','보다','으로서','으로써','로서','로써','이나','나','이며','이고','라','이라','이다','임','인','들'}
        ENDV = {'할','한','하는','하여','하고','된','될','되는','되어','함','됨','해야','하며','하면','하지','하거나','하였다','한다','된다','하게','시킨다','시켜'}
        w1_ends_part = bool(re.search(r'(을|를|이|가|은|는|도|만|의|에|로|와|과|며|고|면|서|여|게|지|야|하여야|해야)$', w1))
        if w2 in PART: return ''
        if w2 in ENDV and not w1_ends_part: return ''
        A = self._tok(w1)
        J1 = self._cnt(w1 + w2[0]); S1 = self._cnt(w1 + ' ' + w2[0])
        if J1 and not A: return ''
        if A and not J1: return ' '
        if J1 or S1:
            if J1 != S1: return '' if J1 > S1 else ' '
        sp = kiwi().space(w1 + w2, reset_whitespace=False)
        return ' ' if sp.startswith(w1 + ' ') else ''

    def join(self, lines):
        s = ''
        for ln in lines:
            if not s: s = ln; continue
            s = s.rstrip() + self.decide(s, ln) + ln.lstrip()
        return s

# ---------------------------------------------------------------- 3. 머리말·꼬리말 제거
FOOT = re.compile(r'(A형\s*-\s*\d+\s*-\s*\d+|A\s*-\s*\d+\s*-\s*\d+|-\s*\d+\s*-$|^\(\s*[12]\s*차?\s*\)$|^차\)?$|^\(?[12]$)')
HEAD = re.compile(r'^(제\s*[1-3]\s*과목|※|수험번호|성\s*명|공인중개사\s*[12]차|\d{4}년도?\s*제\s*\d+\s*회|관련되는\s*규정$|중개에\s*관련되는\s*규정$)')

def clean(lines, H):
    keep = []
    for L in lines:
        t = L['t'].strip()
        if L['y0'] > H * 0.955: continue
        if FOOT.search(t) and L['y0'] > H * 0.9: continue
        keep.append(L)
    return keep

# ---------------------------------------------------------------- 4. 문항 나누기
QNUM = re.compile(r'^(\d{1,3})\s*\.\s*')
BOXMARK = re.compile(r'^(ㄱ|ㄴ|ㄷ|ㄹ|ㅁ|ㅂ|ㅅ|ㅇ|ㅈ|ㅊ)\s*[.)]|^[○•◦▪■□◎●\-–]\s*|^\(\s*[가-힣0-9]\s*\)|^[가-하]\s*[.)]|^\d+\)|^<|^\[|^※')

def parse(exam, pdfs, corpus):
    J = Joiner(corpus)
    seq = []            # (교시, 줄)
    regions = []
    for si, pdf in enumerate(pdfs, start=1):
        d = pymupdf.open(pdf)
        for pno, page in enumerate(d):
            lines, grid, imgs = page_lines(page)
            lines = clean(lines, page.rect.height)
            for col in (0, 1):
                for L in sorted([l for l in lines if l['col'] == col], key=lambda l: l['y0']):
                    L['page'] = pno; L['pdf'] = pdf; L['sfile'] = si
                    seq.append(L)
            regions.append((pdf, pno, grid, imgs, page.rect))
    # 문항 경계
    qs, cur, s, expect = [], None, 1, 1
    multi_file = len(pdfs) > 1
    for L in seq:
        t = L['t'].strip()
        if multi_file and L['sfile'] != s:
            s = L['sfile']; expect = 1
        m = QNUM.match(t)
        if m and int(m.group(1)) == expect and L['x0'] < (L['x1']) and not HEAD.match(t):
            # 2차 한 파일에 1·2교시가 같이 있으면 81번 대신 1번이 다시 나온다
            ss = 2 if (exam.startswith('2-') and not multi_file and expect > 80) else s
            cur = {'s': ss, 'n': expect, 'lines': [dict(L, t=t[m.end():], u=L['u'][m.end():])]}
            qs.append(cur); expect += 1
            continue
        if (not multi_file) and exam.startswith('2-') and m and int(m.group(1)) == 1 and expect == 81:
            s += 1; expect = 1
            cur = {'s': s, 'n': expect, 'lines': [dict(L, t=t[m.end():], u=L['u'][m.end():])]}
            qs.append(cur); expect += 1
            continue
        if cur is None or HEAD.match(t): continue
        cur['lines'].append(L)
    out = []
    for q in qs:
        out.append(build_q(exam, q, J, regions))
    return out

def split_opts(text):
    """①~⑤ 표시를 뒤에서부터 찾아 선지를 떼어 낸다."""
    pos, end = [], len(text)
    for mk in reversed(CIRC):
        i = text.rfind(mk, 0, end)
        if i < 0: return text, None
        pos.append(i); end = i
    pos = pos[::-1]
    head = text[:pos[0]]
    opts = [text[pos[k] + 1:(pos[k + 1] if k < 4 else len(text))].strip() for k in range(5)]
    return head, opts

def build_q(exam, q, J, regions):
    # 줄 단위 텍스트(밑줄 표시 포함)
    lines = [mark_text(L['t'], L['u']) if any(L['u']) else L['t'] for L in q['lines']]
    # 선지가 시작되는 줄 찾기
    flat_all = '\n'.join(lines)
    head_part, opts = None, None
    first_opt_line = next((i for i, l in enumerate(lines) if '①' in re.sub(r'</?b>', '', l)), None)
    flags = []
    if first_opt_line is None:
        flags.append('no-options')
        head_lines, opt_lines = lines, []
    else:
        head_lines = lines[:first_opt_line]
        k = lines[first_opt_line].find('①')
        if k > 0:
            head_lines = head_lines + [lines[first_opt_line][:k]]
            opt_lines = [lines[first_opt_line][k:]] + lines[first_opt_line + 1:]
        else:
            opt_lines = lines[first_opt_line:]
    # 선지: 줄을 이은 뒤 ①~⑤로 자르기(한 줄에 여러 선지가 있어도 됨)
    o = None
    if opt_lines:
        ot = J.join(opt_lines)
        _, o = split_opts(ot)
        if o is None: flags.append('opt-split')
    # 발문 / 박스
    stem_lines, box_lines = [], []
    in_box = False
    for i, ln in enumerate(head_lines):
        plain = re.sub(r'</?b>', '', ln).strip()
        if not in_box:
            stem_lines.append(ln)
            joined = re.sub(r'</?b>', '', J.join(stem_lines))
            if re.search(r'\?\s*(\([^)]*\)|［[^］]*］|\[[^\]]*\])?\s*$', joined):
                in_box = True
        else:
            box_lines.append(ln)
    while box_lines:
        pl = re.sub(r'</?b>', '', box_lines[0]).strip()
        if pl.startswith('(') and re.search(r'단,|다툼|특약|고려|판례|주어진|이하|전제', pl) and not BOXMARK.match(pl.lstrip('(')):
            stem_lines.append(box_lines.pop(0))
            # 괄호가 다음 줄로 이어지는 경우
            while box_lines and J.join(stem_lines).count('(') > J.join(stem_lines).count(')'):
                stem_lines.append(box_lines.pop(0))
        else:
            break
    stem = J.join(stem_lines).strip()
    # 박스: 표시로 시작하는 줄은 새 항목, 아니면 이어 붙임
    items = []
    for ln in box_lines:
        plain = re.sub(r'</?b>', '', ln).strip()
        if not plain: continue
        if BOXMARK.match(plain) or not items or ' | ' in plain or ' | ' in re.sub(r'</?b>', '', items[-1]):
            items.append(ln.strip())
        else:
            items[-1] = J.join([items[-1], ln.strip()])
    box = '\n'.join(items)
    # 표·그림 표시
    pages = {(L['pdf'], L['page'], L['col']) for L in q['lines']}
    y_by = collections.defaultdict(list)
    for L in q['lines']: y_by[(L['pdf'], L['page'], L['col'])].append((L['y0'], L['y1'], L['x0'], L['x1']))
    grid_n, big_img = 0, 0
    crops = []
    for (pdf, pno, grid, imgs, rect) in regions:
        for col in (0, 1):
            key = (pdf, pno, col)
            if key not in y_by: continue
            ys = y_by[key]
            x0 = 0 if col == 0 else rect.width / 2; x1 = rect.width / 2 if col == 0 else rect.width
            R = pymupdf.Rect(x0, min(a for a, _, _, _ in ys) - 6, x1, max(b for _, b, _, _ in ys) + 6)
            crops.append((pdf, pno, R))
            grid_n += sum(1 for g in grid if R.contains(g) or R.intersects(g))
            big_img += sum(1 for im in imgs if R.intersects(im) and (im.width > 22 or im.height > 22))
    if any(L.get('cells') for L in q['lines']): flags.append('table')
    if big_img: flags.append('image')
    if o and any(not x for x in o): flags.append('empty-opt')
    if len(re.sub(r'<[^>]+>', '', stem)) < 8: flags.append('short-stem')
    if re.search(r'(는|은|이|가|을|를)\s*[,.)]', re.sub(r'<[^>]+>', '', stem)) and re.search(r'함수|식|계산', stem):
        flags.append('formula?')
    return {'s': q['s'], 'n': q['n'], 'stem': stem, 'box': box, 'o': o or [], 'flags': flags,
            'crops': [(p, n, [round(v, 1) for v in (R.x0, R.y0, R.x1, R.y1)]) for p, n, R in crops]}

def save_crops(qs, outdir, dpi=150):
    os.makedirs(outdir, exist_ok=True)
    docs = {}
    for q in qs:
        names = []
        for k, (pdf, pno, R) in enumerate(q['crops']):
            d = docs.setdefault(pdf, pymupdf.open(pdf))
            fn = os.path.join(outdir, '%d-%02d-%d.png' % (q['s'], q['n'], k))
            d[pno].get_pixmap(dpi=dpi, clip=pymupdf.Rect(*R)).save(fn)
            names.append(fn)
        q['crops'] = names

if __name__ == '__main__':
    exam = sys.argv[1]; pdfs = sys.argv[2:]
    corpus = load_corpus()
    qs = parse(exam, pdfs, corpus)
    base = '/home/claude/hx/exams/%s' % exam
    os.makedirs(base, exist_ok=True)
    save_crops(qs, base + '/crops')
    json.dump(qs, open(base + '/q_raw.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    cnt = collections.Counter(q['s'] for q in qs)
    fl = [(q['s'], q['n'], q['flags']) for q in qs if q['flags']]
    print(exam, '문항', dict(cnt), '| 표시', len(fl))
    for f in fl[:40]:
        try: print('   ', f)
        except BrokenPipeError: break
