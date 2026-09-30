# -*- coding: utf-8 -*-
"""문제은행 텍스트의 띄어쓰기를 원본 문제지(PDF) 기준으로 복원한다.

- 줄 안의 띄어쓰기는 PDF(pdftotext -layout)를 그대로 따른다.
- PDF에서 줄이 바뀐 자리는 원본에서 알 수 없으므로, 같은 문제지 안의 다른 줄에서
  그 낱말이 붙어 쓰였는지/띄어 쓰였는지를 보고 정한다. 근거가 없으면 문제은행을 따른다.
- 수식·그림 글자가 빠진 문항은 겹치는 구간만 고치고 나머지는 문제은행 그대로 둔다.
"""
import re, subprocess, difflib

MAP = {'−': '-', '–': '-', '—': '-', '～': '~', '∼': '~', 'ㆍ': '·', '‧': '·', '・': '·',
       '“': '"', '”': '"', '‘': "'", '’': "'", '％': '%', '（': '(', '）': ')', '，': ',', '．': '.'}
DROP = set('｢｣「」')
WS = set(' \t　')

def _prep(s):
    s = re.sub(r'm\s*2(?![0-9])', '㎡', s)
    s = re.sub(r'([0-9])\s+%', r'\1%', s)
    return ''.join(MAP.get(c, c) for c in s)

def norm(s):
    return ''.join(c for c in _prep(s) if c not in DROP and c not in WS and not c.isspace())

class Book:
    def __init__(self, pdf, page_w=728.0, gap=0.25):
        """글자 좌표를 보고 띄어쓰기를 되살린다(pdftotext는 이 문제지에서 글자를 흩뜨린다)."""
        import pymupdf
        doc = pymupdf.open(pdf)
        lines = []
        for p in doc:
            mid = p.rect.width / 2
            for x0, x1 in ((0, mid), (mid, p.rect.width)):
                rd = p.get_text("rawdict", clip=pymupdf.Rect(x0, 0, x1, p.rect.height))
                rows = []
                for blk in rd['blocks']:
                    for ln in blk.get('lines', []):
                        chars = []
                        for sp in ln['spans']:
                            for ch in sp['chars']:
                                chars.append((ch['bbox'][0], ch['bbox'][2], ch['c'], sp['size']))
                        if not chars: continue
                        chars.sort(key=lambda c: c[0])
                        txt, prev = '', None
                        for cx0, cx1, c, size in chars:
                            if prev is not None and cx0 - prev > gap * size: txt += ' '
                            txt += c; prev = cx1
                        rows.append((round(ln['bbox'][1], 1), ln['bbox'][0], txt.strip()))
                rows.sort(key=lambda t: (t[0], t[1]))
                lines += [t[2] for t in rows if t[2]]
        self.lines = [_prep(ln) for ln in lines]
        self.ref = '\n'.join(self.lines)          # 줄 안 띄어쓰기가 살아 있는 참고 말뭉치
        chars, seps, pend = [], [], ''
        for ln in self.lines:
            for c in ln:
                if c in DROP: continue
                if c.isspace():
                    if pend != '\n': pend = ' '
                    continue
                if chars: seps.append(pend)
                chars.append(c); pend = ''
            pend = '\n'
        self.s = ''.join(chars); self.seps = seps + ['']
        self.cursor = 0

    def add_corpus(self, text):
        self.corpus = getattr(self, 'corpus', '') + '\n' + text

    def _tok_back(self, p, maxlen=8):
        out, i = [], p
        while i >= 0 and len(out) < maxlen:
            out.append(self.s[i])
            if i == 0 or self.seps[i - 1] in (' ', '\n'): break
            i -= 1
        return ''.join(reversed(out))

    def _tok_fwd(self, p, maxlen=8):
        out, i = [], p
        while i < len(self.s) and len(out) < maxlen:
            out.append(self.s[i])
            if self.seps[i] in (' ', '\n'): break
            i += 1
        return ''.join(out)

    def _join_at_break(self, p, bank_space):
        """줄바꿈 자리: 같은 문제지·문제은행에서 붙여 쓴 예가 있으면 붙이고, 띄어 쓴 예가 있으면 띄운다."""
        w1 = self._tok_back(p)
        w2 = self._tok_fwd(p + 1)
        if not w1 or not w2: return bank_space
        corp = self.ref + getattr(self, 'corpus', '')
        joined = corp.count(w1 + w2)
        spaced = corp.count(w1 + ' ' + w2)
        if joined and joined >= spaced: return False
        if spaced and spaced > joined: return True
        return bank_space

    def fix(self, text, ordered=True):
        """문제은행 문자열을 원본 문제지 띄어쓰기로 다시 쓴다. (결과, 맞춘 비율)"""
        if not text or not text.strip(): return text, 1.0
        plain = re.sub(r'</?b>', '', text)
        prepped = _prep(plain)
        raw = plain if len(prepped) == len(plain) else prepped   # 길이가 달라지면(㎡ 축약 등) 정규화본 사용
        bchars, bspace, bnorm, pend = [], [], [], False
        for c0, c1 in zip(raw, prepped):
            if c1 in DROP: continue
            if c1.isspace():
                pend = True; continue
            if bchars: bspace.append(pend)
            bchars.append(c0); bnorm.append(c1); pend = False
        bspace.append(False)
        bn = ''.join(bnorm)
        if not bn: return text, 1.0
        # 1) 시작 위치 찾기 (앞머리 일부로 닻 내리기)
        anchor = -1
        for L in (24, 16, 12, 8, len(bn)):
            if len(bn) < L or L < 2: continue
            anchor = self.s.find(bn[:L], self.cursor)
            if anchor < 0: anchor = self.s.find(bn[:L])
            if anchor >= 0: break
        if anchor < 0: return text, 0.0
        win = self.s[anchor: anchor + int(len(bn) * 1.7) + 60]
        sm = difflib.SequenceMatcher(None, bn, win, autojunk=False)
        m2p = {}
        for a, b, size in sm.get_matching_blocks():
            for k in range(size): m2p[a + k] = anchor + b + k
        if m2p: self.cursor = max(m2p.values())
        out = []
        for k, c in enumerate(bchars):
            out.append(c)
            if k == len(bchars) - 1: break
            p, q = m2p.get(k), m2p.get(k + 1)
            if p is not None and q == p + 1:
                sep = self.seps[p]
                if sep == ' ': out.append(' ')
                elif sep == '\n':
                    if self._join_at_break(p, bspace[k]):
                        out.append(' ')
            elif bspace[k]:
                out.append(' ')
        res = ''.join(out)
        m = re.search(r'<b>(.*?)</b>', text)
        if m:
            key = re.sub(r'\s+', '', m.group(1))
            flat = re.sub(r'\s+', '', res)
            p = flat.find(key)
            if p >= 0:
                cnt, st, en = 0, None, None
                for idx, ch in enumerate(res):
                    if ch.isspace(): continue
                    if cnt == p: st = idx
                    if cnt == p + len(key) - 1: en = idx + 1; break
                    cnt += 1
                if st is not None and en is not None:
                    res = res[:st] + '<b>' + res[st:en] + '</b>' + res[en:]
        cov = len(m2p) / len(bn)
        return res, cov

    def fix_block(self, text):
        """여러 줄(박스)은 줄 단위로 처리한다."""
        if not text: return text, 1.0
        outs, covs = [], []
        for ln in text.split('\n'):
            r, c = self.fix(ln)
            outs.append(r); covs.append(c)
        return '\n'.join(outs), min(covs) if covs else 1.0
