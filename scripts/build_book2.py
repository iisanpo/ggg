# -*- coding: utf-8 -*-
"""공인중개사 기출 상세 해설지(1차·2차) — 인쇄용 A4 책자 HTML
사용: python3 build_book2.py <final.json> <meta.json> <out.html> [dark|light]
final.json 레코드: s, n, stem, box, o[5], a(0-based), diff, type, L, topic, explain, terms[], core, opts[5],
                   calc, study, trap, memo, law, changed, rev{}, allcorrect, note
meta.json: kind(1|2), kick, title, date, lede, note, foot, header
"""
import json, sys, re, html, collections
from string import Template

DATA, META, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
DARK = (sys.argv[4] if len(sys.argv) > 4 else 'dark') == 'dark'
D = json.load(open(DATA, encoding='utf-8'))
M = json.load(open(META, encoding='utf-8'))
KIND = int(M.get('kind', 1))

# ---- 1차 책 스크립트에서 CSS·색 가져오기(두 책의 모양을 같게 유지)
_src = open('/home/claude/book/build_book.py', encoding='utf-8').read()
BASE_CSS = _src[_src.index("CSS = '''") + 9:_src.index("'''\n\nfrom string import Template")]
_ns = {}
exec(_src[_src.index('LIGHT = dict('):_src.index('LSHORT = {')], _ns)
LIGHT, DARKP = _ns['LIGHT'], _ns['DARKP']

LS1 = {1: '토지 특성·용어', 2: '감정평가 이론', 3: '감정평가 계산·가격공시', 4: '부동산 정책론',
       5: '시장론·지대·도시구조', 6: '입지·상권', 7: '경제론(수요·공급)', 8: '투자론',
       9: '개발·관리·금융', 10: '주택·상가 임대차', 11: '명의신탁·가담·집합건물',
       12: '법률행위·의사표시', 13: '대리', 14: '무효·취소·조건·기한', 15: '계약법', 16: '물권법'}
LS2 = {1: '총칙·자격·개설등록', 2: '중개사무소 운영', 3: '중개계약·확인설명·보수', 4: '협회·교육·제재',
       5: '부동산거래신고법', 6: '중개실무', 7: '국토계획법①(계획·용도)', 8: '국토계획법②(개발행위·시설)',
       9: '도시개발법', 10: '도시정비법', 11: '주택법', 12: '건축법·농지법',
       13: '지적①(등록·공부)', 14: '지적②(이동·측량)', 15: '등기①(총칙·절차)', 16: '등기②(각종 등기)',
       17: '세법①(총론·취득·재산)', 18: '세법②(종부·양도)'}
LS = LS1 if KIND == 1 else LS2
MK = ['①', '②', '③', '④', '⑤']
esc = lambda s: html.escape(s or '', quote=False)

def md(s):
    s = esc(s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
    return s.replace('\n', '<br>')

NEG = re.compile(r'(옳지 ?않은|틀린|해당하지 ?않는|않는|않은|아닌)')
def stem_html(s):
    s = s or ''
    if '<b>' not in s:
        m = NEG.search(s)
        if m: s = s[:m.start()] + '<b>' + m.group(0) + '</b>' + s[m.end():]
    s = html.escape(s, quote=False)
    return s.replace('&lt;b&gt;', '<u class="k">').replace('&lt;/b&gt;', '</u>')

def table_html(rows, cls='bt'):
    rows = [[c.strip() for c in r.split('|')] for r in rows]
    w = max(len(r) for r in rows)
    t = ['<table class="%s">' % cls]
    for i, r in enumerate(rows):
        r = r + [''] * (w - len(r))
        tag = 'th' if i == 0 else 'td'
        t.append('<tr>' + ''.join('<%s>%s</%s>' % (tag, md(c), tag) for c in r) + '</tr>')
    return ''.join(t) + '</table>'

def box_html(box):
    if not box: return ''
    out, buf = [], []
    def flush():
        if buf: out.append(table_html(buf)); buf.clear()
    for ln in box.split('\n'):
        if '|' in ln: buf.append(ln)
        else:
            flush(); out.append('<div class="bl">%s</div>' % esc(ln))
    flush()
    return '<div class="box">' + ''.join(out) + '</div>'

def study_html(st):
    """암기 정리: '■ 제목', '- 항목', '칸 | 칸' 표를 렌더링"""
    if not st: return ''
    out, buf, items = [], [], []
    def flush_t():
        if buf: out.append(table_html(buf, 'st-t')); buf.clear()
    def flush_l():
        if items: out.append('<ul>' + ''.join('<li>%s</li>' % md(x) for x in items) + '</ul>'); items.clear()
    for ln in st.split('\n'):
        t = ln.strip()
        if not t: continue
        if '|' in t:
            flush_l(); buf.append(t); continue
        flush_t()
        if t.startswith('■'):
            flush_l(); out.append('<div class="st-h">%s</div>' % md(t.lstrip('■ ').strip()))
        else:
            items.append(re.sub(r'^[-•·]\s*', '', t))
    flush_t(); flush_l()
    return '<div class="study"><span class="h">암기 정리</span>' + ''.join(out) + '</div>'

def terms_html(terms):
    if not terms: return ''
    rows = ''.join('<div class="tm"><dt>%s</dt><dd>%s</dd></div>' % (md(t.get('t', '')), md(t.get('d', ''))) for t in terms)
    return '<dl class="terms"><span class="h">용어 풀이</span>%s</dl>' % rows

def ox_rows(opts, a, allc=False):
    h = []
    for i, t in enumerate(opts):
        t = (t or '').strip()
        m = re.match(r'^([OX])(\s*\(정답\))?[.:、,]?\s*', t)
        ox = m.group(1) if m else ''
        body = t[m.end():] if m else t
        h.append('<li class="%s"><span class="k">%s</span><span class="ox %s">%s</span><span>%s</span></li>'
                 % ('is-ans' if (i == a and not allc) else '', MK[i], ox.lower(), ox or '·', md(body)))
    return '<ul class="od">' + ''.join(h) + '</ul>'

def opt_rows(o, a, allc=False):
    return '<ol class="opts">' + ''.join('<li class="%s"><span class="k">%s</span><span>%s</span></li>'
        % ('on' if (i == a and not allc) else '', MK[i], esc(x)) for i, x in enumerate(o)) + '</ol>'

def subj_of(q):
    if KIND == 1: return 's1' if q['n'] <= 40 else 's2'
    return 's1' if q['s'] == 1 else 's2'

def qlabel(q):
    return ('%d교시 %d번' % (q['s'], q['n'])) if KIND == 2 else ('%d번' % q['n'])

def question(q):
    allc = q.get('allcorrect')
    tags = ['<span class="tag d%s">난이도 %s</span>' % (q.get('diff', '중'), q.get('diff', '중')),
            '<span class="tag">%s</span>' % esc(q.get('type', '')),
            '<span class="tag L">%d강 %s</span>' % (q.get('L', 0), esc(LS.get(q.get('L'), '')))]
    if q.get('changed'): tags.append('<span class="tag chg">현행법으로 답이 달라짐 · 부록</span>')
    h = ['<article class="q %s" id="q%d-%d">' % (subj_of(q), q.get('s', 1), q['n'])]
    h.append('<div class="qh"><span class="qn">%d</span><div class="qb"><p class="qs">%s</p><div class="tags">%s</div></div></div>'
             % (q['n'], stem_html(q['stem']), ''.join(tags)))
    h.append(box_html(q.get('box')))
    h.append(opt_rows(q['o'], q['a'], allc))
    h.append('<div class="ex">')
    lab = '전항 정답' if allc else '정답 %s' % MK[q['a']]
    h.append('<div class="ans"><span class="a%s">%s</span><span class="topic">%s</span></div>'
             % (' all' if allc else '', lab, esc(q.get('topic'))))
    if q.get('changed'):
        ra = (q.get('rev') or {}).get('a')
        h.append('<div class="chgnote">이 문항은 시험 이후 법이 바뀌어 <b>현행법으로 풀면 답이 달라집니다</b>'
                 + (' (현행 기준 정답 %s)' % MK[ra - 1] if isinstance(ra, int) and 1 <= ra <= 5 else '')
                 + '. 아래 해설은 시험 당시 기준이니 <b>규정은 부록의 현행 문제로 외우세요</b>.</div>')
    if q.get('note'): h.append('<div class="qnote">%s</div>' % md(q['note']))
    if q.get('explain'): h.append('<div class="explain"><span class="h">이해하기</span>%s</div>' % md(q['explain']))
    h.append(terms_html(q.get('terms')))
    h.append('<div class="core"><span class="h">정답 근거</span>%s</div>' % md(q.get('core')))
    if q.get('calc'): h.append('<div class="calc">%s</div>' % md(q['calc']))
    h.append(ox_rows(q.get('opts') or [], q['a'], allc))
    h.append(study_html(q.get('study')))
    h.append('<div class="pts"><div class="pt trap"><span class="h">함정</span>%s</div>'
             '<div class="pt memo"><span class="h">한 줄 암기</span>%s</div></div>' % (md(q.get('trap')), md(q.get('memo'))))
    if q.get('law'): h.append('<div class="law">%s</div>' % md(q['law']))
    h.append('</div></article>')
    return ''.join(h)

def appendix_item(q):
    r = q['rev']; a = (r.get('a') or 1) - 1
    h = ['<article class="q rev %s">' % subj_of(q)]
    h.append('<div class="qh"><span class="qn">%d</span><div class="qb"><div class="revk">원래 %s · 현행법(2026.9 기준)으로 고친 문제</div>'
             '<p class="qs">%s</p></div></div>' % (q['n'], qlabel(q), stem_html(r.get('stem'))))
    h.append(box_html(r.get('box')))
    h.append(opt_rows(r.get('o') or [], a))
    h.append('<div class="ex"><div class="ans"><span class="a">정답 %s</span><span class="topic">%s</span></div>'
             % (MK[a], esc(q.get('topic'))))
    if q.get('law'): h.append('<div class="law">%s</div>' % md(q['law']))
    h.append('<div class="core"><span class="h">정답 근거</span>%s</div>' % md(r.get('core')))
    if r.get('calc'): h.append('<div class="calc">%s</div>' % md(r['calc']))
    if r.get('opts'): h.append(ox_rows(r['opts'], a))
    h.append(study_html(r.get('study')))
    if r.get('memo'): h.append('<div class="pts one"><div class="pt memo"><span class="h">한 줄 암기</span>%s</div></div>' % md(r['memo']))
    h.append('</div></article>')
    return ''.join(h)

# ---------------- 표지·분석
changed = [q for q in D if q.get('changed') and q.get('rev')]
def skip_box():
    if not changed:
        return '<div class="skip none"><b>현행법 기준으로 답이 달라진 문항: 없음</b> — 모든 문항을 그대로 풀어도 됩니다.</div>'
    by = collections.OrderedDict()
    for q in changed: by.setdefault(q.get('s', 1), []).append(q['n'])
    parts = []
    for s, ns in by.items():
        lab = ('%d교시 ' % s) if KIND == 2 else ''
        parts.append('<span class="sk">%s<b>%s</b></span>' % (lab, ' · '.join('%d번' % n for n in ns)))
    return ('<div class="skip"><div class="sh">현행법 기준으로 답이 달라진 문항 — 풀 때 빼세요</div>'
            '<div class="sl">%s</div><div class="sn">시험 이후 법이 바뀌어 지금 기준으로는 답이 다르거나 성립하지 않는 문항입니다. '
            '책 끝 <b>부록</b>에 현행법에 맞게 고친 문제와 해설을 실었으니, 규정은 부록으로 외우세요.</div></div>') % ' '.join(parts)

cnt = collections.Counter(q.get('L') for q in D)
mx = max(cnt.values()) if cnt else 1
def bars(rng, cls):
    return ''.join('<div class="bar %s"><span class="l">%d강 %s</span><span class="t"><i style="width:%.1f%%"></i></span>'
                   '<span class="v">%d</span></div>' % (cls, L, esc(LS[L]), cnt.get(L, 0) / mx * 100, cnt.get(L, 0)) for L in rng)
dif = collections.Counter(q.get('diff') for q in D)
typ = collections.Counter(q.get('type') for q in D)

def ans_table(qs, label=''):
    rows = []
    for r in range(0, len(qs), 10):
        chunk = qs[r:r + 10]
        rows.append('<tr><th>%d~%d</th>%s</tr>' % (chunk[0]['n'], chunk[-1]['n'],
                    ''.join('<td class="%s">%s</td>' % ('c' if q.get('changed') else '', '전항' if q.get('allcorrect') else MK[q['a']]) for q in chunk)))
    return ('<div class="atl">%s</div>' % label if label else '') + '<table class="at">%s</table>' % ''.join(rows)

if KIND == 1:
    meta_line = ('<span>시행 <b>%s</b></span><span>부동산학개론 <b>1~40번</b></span><span>민법 및 민사특별법 <b>41~80번</b></span>'
                 '<span>합격 기준 <b>과목별 40점 · 평균 60점</b></span>' % esc(M['date']))
    legend = '<i class="c1"></i>부동산학개론 <i class="c2"></i>민법'
    barhtml = bars(range(1, 10), 's1') + bars(range(10, 17), 's2')
    tables = ans_table(D)
else:
    s2 = [q for q in D if q['s'] == 2]
    n2 = '%d~%d번' % (s2[0]['n'], s2[-1]['n']) if s2 else ''
    meta_line = ('<span>시행 <b>%s</b></span><span>1교시 <b>중개사법·중개실무 40 · 부동산공법 40</b></span>'
                 '<span>2교시 <b>공시법 24 · 세법 16 (%s)</b></span><span>합격 기준 <b>과목별 40점 · 평균 60점</b></span>' % (esc(M['date']), n2))
    legend = '<i class="c1"></i>1교시 <i class="c2"></i>2교시'
    barhtml = bars(range(1, 13), 's1') + bars(range(13, 19), 's2')
    tables = ans_table([q for q in D if q['s'] == 1], '1교시') + ans_table(s2, '2교시')

how2 = ('<li><b>이해하기</b>로 제도의 취지와 흐름을 먼저 잡고, <b>용어 풀이</b>로 낯선 말을 정리합니다.</li>'
        '<li><b>정답 근거</b>와 <b>선지별 O/X</b>에서 틀린 선지가 무엇을 어떻게 바꿨는지, 올바른 규정은 무엇인지 확인합니다.</li>'
        '<li><b>암기 정리</b> 상자는 그 논점의 수치·기간·요건을 통째로 모은 것입니다. 여기만 반복해서 읽어도 복습이 됩니다.</li>'
        '<li><b>함정</b>과 <b>한 줄 암기</b>는 시험 직전용입니다. 문항마다 붙은 <b>N강</b>은 단기합격 강의실의 강 번호입니다.</li>')
cover = f'''<section class="cover">
  <div class="kick">{esc(M['kick'])}</div>
  <h1>{esc(M['title'])}</h1>
  <p class="lede">{esc(M['lede'])}</p>
  <div class="meta">{meta_line}</div>
  {skip_box()}
  <div class="how"><b>이 책의 보는 법</b><ol>{how2}</ol></div>
  <p class="note">{esc(M['note'])}</p>
</section>
<section class="ana">
  <h2>출제 분석</h2>
  <div class="anar">
    <div class="panel"><h3>어느 강에서 나왔나 <span class="lg">{legend}</span></h3><div class="bars">{barhtml}</div></div>
    <div class="panel">
      <h3>난이도</h3>
      <div class="kpis"><div class="kpi h"><div class="k">상</div><div class="v">{dif.get('상',0)}</div></div>
        <div class="kpi m"><div class="k">중</div><div class="v">{dif.get('중',0)}</div></div>
        <div class="kpi e"><div class="k">하</div><div class="v">{dif.get('하',0)}</div></div></div>
      <h3 class="mt">유형</h3>
      <div class="tlist">{''.join('<span>%s<b>%d</b></span>' % (esc(k), v) for k, v in typ.most_common() if k)}</div>
      <h3 class="mt">정답 한눈에 보기</h3>{tables}
      {'<p class="atn">색이 다른 칸은 현행법으로 답이 달라진 문항입니다.</p>' if changed else ''}
    </div>
  </div>
</section>'''

body = [cover]
if KIND == 1:
    for q in D:
        if q['n'] == 1: body.append('<section class="subj"><h2>제1과목 부동산학개론</h2><span>1~40번 · 40문항</span></section>')
        if q['n'] == 41: body.append('<section class="subj"><h2>제2과목 민법 및 민사특별법</h2><span>41~80번 · 40문항</span></section>')
        body.append(question(q))
else:
    s1 = [q for q in D if q['s'] == 1]; s2 = [q for q in D if q['s'] == 2]
    for i, q in enumerate(s1):
        if i == 0: body.append('<section class="subj"><h2>1교시 · 제1과목 공인중개사법령 및 중개실무</h2><span>%d~%d번</span></section>' % (s1[0]['n'], s1[min(39, len(s1)-1)]['n']))
        if i == 40: body.append('<section class="subj"><h2>1교시 · 제2과목 부동산공법</h2><span>%d~%d번</span></section>' % (q['n'], s1[-1]['n']))
        body.append(question(q))
    for i, q in enumerate(s2):
        if i == 0: body.append('<section class="subj"><h2>2교시 · 제1과목 부동산공시에 관한 법령</h2><span>%d~%d번</span></section>' % (q['n'], s2[min(23, len(s2)-1)]['n']))
        if i == 24: body.append('<section class="subj"><h2>2교시 · 제2과목 부동산 관련 세법</h2><span>%d~%d번</span></section>' % (q['n'], s2[-1]['n']))
        body.append(question(q))
if changed:
    body.append('<section class="subj appx"><h2>부록 · 현행법으로 고친 문항</h2><span>%d문항 · 2026년 9월 법령 기준</span></section>' % len(changed))
    body.append('<p class="appx-lede">시험 이후 법이 바뀌어 원래 문제로는 답이 달라진 문항을, 문제의 틀은 살리고 달라진 부분만 현행 규정에 맞게 고쳤습니다. '
                '규정 암기는 이 부록을 기준으로 하세요.</p>')
    for q in changed: body.append(appendix_item(q))
body.append('<footer class="end">%s</footer>' % esc(M.get('foot', '')))

EXTRA = '''
.skip{margin-top:5mm;border:1pt solid $brick;border-radius:3mm;padding:3.5mm 4.5mm;background:$brickSoft}
.skip .sh{font-weight:700;color:$brick;font-size:10.5pt}
.skip .sl{margin-top:1.5mm;font-size:11pt;display:flex;flex-wrap:wrap;gap:2mm 6mm}
.skip .sk b{color:$ink}
.skip .sn{margin-top:1.5mm;font-size:8.8pt;color:$ink2;line-height:1.6}
.skip.none{border-color:$tealLine;background:$tealSoft;font-size:9.4pt;color:$ink2}
.skip.none b{color:$teal}
.atl{font-size:8.6pt;font-weight:700;color:$ink2;margin:2.5mm 0 1mm}
.at td.c{background:$brickSoft;color:$brick;font-weight:700}
.atn{font-size:8pt;color:$ink3;margin:1.5mm 0 0}
.tag.chg{color:$brick;border-color:$brickLine;background:$brickSoft;font-weight:700}
.chgnote{margin:2mm 0 0;background:$brickSoft;border-left:1.2pt solid $brick;border-radius:0 1.5mm 1.5mm 0;
  padding:2mm 2.5mm;font-size:8.9pt;line-height:1.6;color:$ink}
.explain{margin:2.2mm 0 0;font-size:9.5pt;line-height:1.75}
.explain .h,.core .h{display:block;font-size:7.8pt;font-weight:700;color:$teal;margin-bottom:.4mm}
.q.s2 .explain .h,.q.s2 .core .h{color:$plumInk}
.core{margin-top:2.2mm}
.terms{margin:2.2mm 0 0;padding:2mm 2.5mm;background:$surface2;border-radius:1.5mm;font-size:8.8pt;line-height:1.6}
.terms .h{display:block;font-size:7.8pt;font-weight:700;color:$ink3;margin-bottom:.6mm}
.terms .tm{display:grid;grid-template-columns:24mm 1fr;gap:2mm;margin:.5mm 0;break-inside:avoid}
.terms dt{font-weight:700;color:$ink}
.terms dd{margin:0;color:$ink2}
.study{margin-top:2.5mm;border:.6pt solid $tealLine;border-radius:2mm;padding:2.2mm 3mm;background:$tealSoft;font-size:9pt;line-height:1.65}
.q.s2 .study{border-color:$plumLine;background:$plumSoft}
.study .h{display:block;font-size:7.8pt;font-weight:700;color:$teal;margin-bottom:.6mm}
.q.s2 .study .h{color:$plumInk}
.study ul{margin:0;padding-left:4.2mm}
.study li{margin:.4mm 0;break-inside:avoid}
.study .st-h{font-weight:700;margin:1.2mm 0 .4mm;color:$ink}
.st-t{border-collapse:collapse;font-size:8.5pt;margin:1mm 0;width:100%;background:$tableBg}
.st-t th,.st-t td{border:.4pt solid $boxLine;padding:.7mm 1.6mm;text-align:left;vertical-align:top}
.st-t th{background:$thBg;font-weight:700}
.pts.one{grid-template-columns:1fr}
.appx{break-before:page}
.appx-lede{font-size:9.2pt;color:$ink2;margin:0 0 5mm;line-height:1.6}
.q.rev .revk{font-size:8pt;font-weight:700;color:$brick;margin-bottom:.6mm}
'''
CSS = Template(BASE_CSS + EXTRA).substitute(DARKP if DARK else LIGHT)
doc = ('<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>%s</title><style>%s</style></head><body>%s</body></html>'
       % (esc(M['title']), CSS, ''.join(body)))
open(OUT, 'w', encoding='utf-8').write(doc)
print('문항', len(D), '| 개정 부록', len(changed), '| HTML', len(doc), '→', OUT)
