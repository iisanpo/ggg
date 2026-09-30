# -*- coding: utf-8 -*-
"""공인중개사 1차 기출 상세 해설지 — 인쇄용 A4 책자 HTML 생성
사용법: python3 build_book.py <data.json> <meta.json> <out.html>
data: [{n,stem,box,o[5],a(0-based),diff,type,L,topic,core,opts[5],calc,trap,memo,law}, ...]
"""
import json, sys, re, html, collections

DATA, META, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
DARK = len(sys.argv) > 4 and sys.argv[4] == 'dark'
D = json.load(open(DATA, encoding='utf-8'))
M = json.load(open(META, encoding='utf-8'))


LIGHT = dict(paper='#FFFFFF', ink='#1A1A18', ink2='#45443F', ink3='#6B6960', rule='#D9D5CB',
             ruleSoft='#DFDBD1', ruleSoft2='#E3E0D8', track='#EFEDE7', surface2='#F4F2ED',
             exBg='#FAF9F6', thBg='#E9E6DE', boxLine='#C9C5B9', tableBg='#FFFFFF', calcBg='#FFFFFF',
             onAccent='#FFFFFF', brick='#A4442E', brickLine='#D9A08C', brickSoft='#F9EFEB',
             gold='#8E6310', goldLine='#DCC189', goldSoft='#FAF3E4', teal='#146B5E', tealLine='#8FC3B6',
             tealSoft='#E7F1EE', tealInk='#0E4F45', plum='#5B4B8A', plumLine='#B0A4D4',
             plumSoft='#EFECF7', plumInk='#4A3B78', qn2Bg='#3A3660', c1='#00897B', c2='#6246A8')
DARKP = dict(paper='#14140F', ink='#F0EEE6', ink2='#CBC8BD', ink3='#928F84', rule='#3A3A31',
             ruleSoft='#33332B', ruleSoft2='#2E2E27', track='#2C2C25', surface2='#262620',
             exBg='#1D1D18', thBg='#33332B', boxLine='#4A4A40', tableBg='#1A1A16', calcBg='#14140F',
             onAccent='#14140F', brick='#E08A6F', brickLine='#7A4433', brickSoft='#3A231C',
             gold='#D9AD52', goldLine='#6B5525', goldSoft='#332916', teal='#6FC3B0', tealLine='#2F6659',
             tealSoft='#17332E', tealInk='#9BDACB', plum='#B0A4D4', plumLine='#4C4173',
             plumSoft='#26213A', plumInk='#B0A4D4', qn2Bg='#B0A4D4', c1='#12A991', c2='#8A6FE8')

LSHORT = {1:'토지 특성·용어', 2:'감정평가 이론', 3:'감정평가 계산·가격공시', 4:'부동산 정책론',
          5:'시장론·지대·도시구조', 6:'입지·상권', 7:'경제론(수요·공급)', 8:'투자론',
          9:'개발·관리·금융', 10:'주택·상가 임대차', 11:'명의신탁·가담·집합건물',
          12:'법률행위·의사표시', 13:'대리', 14:'무효·취소·조건·기한', 15:'계약법', 16:'물권법'}
MK = ['①', '②', '③', '④', '⑤']
esc = lambda s: html.escape(s or '', quote=False)

def md(s):
    """**굵게** 와 줄바꿈만 처리한다. 입력은 평문."""
    s = esc(s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
    return s.replace('\n', '<br>')

NEG = re.compile(r'(옳지 ?않은|틀린|해당하지 ?않는|않는|않은|아닌)')

def stem_html(s):
    """발문의 <b>…</b>(밑줄 강조)를 살리고, 표시가 없으면 부정어에 밑줄을 넣는다."""
    s = s or ''
    if '<b>' not in s:
        m = NEG.search(s)
        if m: s = s[:m.start()] + '<b>' + m.group(0) + '</b>' + s[m.end():]
    s = html.escape(s, quote=False)
    return s.replace('&lt;b&gt;', '<u class="k">').replace('&lt;/b&gt;', '</u>')

def box_html(box):
    if not box: return ''
    out, buf = [], []
    def flush():
        if not buf: return
        rows = [[c.strip() for c in ln.split('|')] for ln in buf]
        w = max(len(r) for r in rows)
        t = ['<table class="bt">']
        for i, r in enumerate(rows):
            r = r + [''] * (w - len(r))
            tag = 'th' if i == 0 else 'td'
            t.append('<tr>' + ''.join('<%s>%s</%s>' % (tag, esc(c), tag) for c in r) + '</tr>')
        t.append('</table>')
        out.append(''.join(t)); buf.clear()
    for ln in box.split('\n'):
        (buf.append(ln) if '|' in ln else (flush(), out.append('<div class="bl">%s</div>' % esc(ln))))
    flush()
    return '<div class="box">' + ''.join(out) + '</div>'

def opt_rows(q):
    h = []
    for i, o in enumerate(q['o']):
        on = (i == q['a']) and not q.get('allcorrect')
        h.append('<li class="%s"><span class="k">%s</span><span>%s</span></li>' % ('on' if on else '', MK[i], esc(o)))
    return '<ol class="opts">' + ''.join(h) + '</ol>'

def ox_rows(q):
    h = []
    for i, t in enumerate(q['opts']):
        t = (t or '').strip()
        m = re.match(r'^([OX])[.:、,]?\s*', t)
        ox = m.group(1) if m else ''
        body = t[m.end():] if m else t
        h.append('<li class="%s"><span class="k">%s</span><span class="ox %s">%s</span><span>%s</span></li>'
                 % ('is-ans' if (i == q['a'] and not q.get('allcorrect')) else '', MK[i], ox.lower(), ox or '·', md(body)))
    return '<ul class="od">' + ''.join(h) + '</ul>'

def question(q):
    subj = '학개론' if q['n'] <= 40 else '민법'
    tags = ['<span class="tag d%s">난이도 %s</span>' % (q['diff'], q['diff']),
            '<span class="tag">%s</span>' % esc(q['type']),
            '<span class="tag L">%d강 %s</span>' % (q['L'], esc(LSHORT.get(q['L'], '')))]
    h = ['<article class="q %s">' % ('s1' if subj == '학개론' else 's2')]
    h.append('<div class="qh"><span class="qn">%d</span><div class="qb"><p class="qs">%s</p><div class="tags">%s</div></div></div>'
             % (q['n'], stem_html(q['stem']), ''.join(tags)))
    h.append(box_html(q.get('box')))
    h.append(opt_rows(q))
    h.append('<div class="ex">')
    lab = '전항 정답' if q.get('allcorrect') else '정답 %s' % MK[q['a']]
    h.append('<div class="ans"><span class="a%s">%s</span><span class="topic">%s</span></div>'
             % (' all' if q.get('allcorrect') else '', lab, esc(q['topic'])))
    if q.get('note'): h.append('<div class="qnote">%s</div>' % md(q['note']))
    h.append('<p class="core">%s</p>' % md(q['core']))
    if q.get('calc'): h.append('<div class="calc">%s</div>' % md(q['calc']))
    h.append(ox_rows(q))
    h.append('<div class="pts"><div class="pt trap"><span class="h">함정</span>%s</div>'
             '<div class="pt memo"><span class="h">한 줄 암기</span>%s</div></div>' % (md(q['trap']), md(q['memo'])))
    if q.get('law'): h.append('<div class="law">%s</div>' % md(q['law']))
    h.append('</div></article>')
    return ''.join(h)

# ---------- 표지 ----------
cnt = collections.Counter(q['L'] for q in D)
mx = max(cnt.values())
def bars(rng, cls):
    return ''.join('<div class="bar %s"><span class="l">%d강 %s</span><span class="t"><i style="width:%.1f%%"></i></span>'
                   '<span class="v">%d</span></div>' % (cls, L, esc(LSHORT[L]), cnt.get(L, 0) / mx * 100, cnt.get(L, 0))
                   for L in rng)
dif = collections.Counter(q['diff'] for q in D)
typ = collections.Counter(q['type'] for q in D)
ansrows = []
for r in range(0, 80, 10):
    ansrows.append('<tr><th>%d~%d</th>%s</tr>' % (r + 1, r + 10,
                   ''.join('<td>%s</td>' % ('전항' if D[i].get('allcorrect') else MK[D[i]['a']])
                           for i in range(r, r + 10))))

cover = f'''<section class="cover">
  <div class="kick">{esc(M['kick'])}</div>
  <h1>{esc(M['title'])}</h1>
  <p class="lede">{esc(M['lede'])}</p>
  <div class="meta"><span>시행 <b>{esc(M['date'])}</b></span><span>부동산학개론 <b>1~40번</b></span>
    <span>민법 및 민사특별법 <b>41~80번</b></span><span>합격 기준 <b>과목별 40점 · 평균 60점</b></span>
    <span>문항당 <b>2.5점</b></span></div>
  <div class="how"><b>이 책의 보는 법</b>
    <ol><li>문제를 먼저 풀고, 바로 아래 <b>정답 · 핵심 근거</b>로 맞춰 봅니다.</li>
    <li><b>선지별 O/X</b>는 틀린 선지가 어디를 어떻게 바꿔 틀렸는지를 짚습니다. 여기가 다음 시험에 다시 나옵니다.</li>
    <li><b>함정</b>과 <b>한 줄 암기</b>만 따로 훑으면 시험 직전 복습이 됩니다.</li>
    <li>문항마다 붙은 <b>N강</b>은 단기합격 강의실의 강 번호입니다. 많이 틀린 강으로 돌아가세요.</li></ol></div>
  <p class="note">{esc(M['note'])}</p>
</section>
<section class="ana">
  <h2>출제 분석</h2>
  <div class="anar">
    <div class="panel">
      <h3>어느 강에서 나왔나 <span class="lg"><i class="c1"></i>부동산학개론 <i class="c2"></i>민법</span></h3>
      <div class="bars">{bars(range(1, 10), 's1')}{bars(range(10, 17), 's2')}</div>
    </div>
    <div class="panel">
      <h3>난이도</h3>
      <div class="kpis"><div class="kpi h"><div class="k">상</div><div class="v">{dif.get('상',0)}</div></div>
        <div class="kpi m"><div class="k">중</div><div class="v">{dif.get('중',0)}</div></div>
        <div class="kpi e"><div class="k">하</div><div class="v">{dif.get('하',0)}</div></div></div>
      <h3 class="mt">유형</h3>
      <div class="tlist">{''.join('<span>%s<b>%d</b></span>' % (esc(k), v) for k, v in typ.most_common())}</div>
      <h3 class="mt">정답 한눈에 보기</h3>
      <table class="at">{''.join(ansrows)}</table>
    </div>
  </div>
</section>'''

body = [cover]
body.append('<section class="subj"><h2>제1과목 부동산학개론</h2><span>1~40번 · 40문항</span></section>')
for q in D:
    if q['n'] == 41:
        body.append('<section class="subj brk"><h2>제2과목 민법 및 민사특별법</h2><span>41~80번 · 40문항</span></section>')
    body.append(question(q))
body.append('<footer class="end">%s</footer>' % esc(M.get('foot', '')))

CSS = '''
@page{size:A4;margin:15mm 13mm 16mm}
*{box-sizing:border-box}
html{background:$paper}
html,body{margin:0;padding:0}
body{background:$paper;font-family:"Noto Sans CJK KR","Noto Sans KR",sans-serif;font-size:10.2pt;line-height:1.62;color:$ink;
  word-break:keep-all;overflow-wrap:anywhere;-webkit-print-color-adjust:exact;print-color-adjust:exact}
h1,h2,h3{font-family:"Noto Serif CJK KR",serif;margin:0;font-weight:700;letter-spacing:-.01em}
b,strong{font-weight:700}
.num,.qn,.v,.k{font-variant-numeric:tabular-nums}

/* 표지 */
.cover{padding:4mm 0 0}
.cover .kick{font-size:9.5pt;font-weight:700;color:$brick;letter-spacing:.02em}
.cover h1{font-size:30pt;line-height:1.15;margin:2mm 0 3mm}
.cover .lede{font-size:11pt;color:$ink2;margin:0;max-width:62ch}
.meta{display:flex;flex-wrap:wrap;gap:2mm 6mm;margin-top:5mm;padding:3mm 0;border-top:1.5pt solid $ink;
  border-bottom:.5pt solid $rule;font-size:9pt;color:$ink3}
.meta b{color:$ink}
.how{margin-top:6mm;background:$surface2;border-radius:3mm;padding:4mm 5mm;font-size:9.6pt}
.how ol{margin:2mm 0 0;padding-left:5mm}
.how li{margin:1mm 0}
.note{margin-top:5mm;font-size:8.8pt;color:$ink3;line-height:1.6}

/* 분석 */
.ana{break-before:page;padding-top:2mm}
.ana h2{font-size:16pt;margin-bottom:4mm}
.anar{display:grid;grid-template-columns:1.15fr 1fr;gap:5mm}
.panel{border:.5pt solid $ruleSoft;border-radius:3mm;padding:4mm}
.panel h3{font-family:"Noto Sans CJK KR",sans-serif;font-size:9.4pt;color:$ink2;margin-bottom:3mm;
  display:flex;justify-content:space-between;align-items:center;gap:3mm}
.panel h3.mt{margin-top:5mm}
.lg{font-weight:400;font-size:8.2pt;color:$ink3}
.lg i{display:inline-block;width:7px;height:7px;border-radius:2px;margin:0 1mm 0 2mm;vertical-align:baseline}
.lg i.c1{background:$c1}.lg i.c2{background:$c2}
.bars{display:flex;flex-direction:column;gap:1.4mm}
.bar{display:grid;grid-template-columns:36mm 1fr 6mm;gap:2mm;align-items:center;font-size:8.6pt}
.bar .l{color:$ink2;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bar .t{height:3.4mm;background:$track;border-radius:1.2mm;overflow:hidden}
.bar .t i{display:block;height:3.4mm;border-radius:1.2mm}
.bar.s1 .t i{background:$c1}.bar.s2 .t i{background:$c2}
.bar .v{text-align:right;font-weight:600}
.kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:2mm}
.kpi{background:$surface2;border-radius:2mm;padding:2.5mm;text-align:center}
.kpi .k{font-size:8.4pt;color:$ink3}
.kpi .v{font-size:15pt;font-weight:700}
.kpi.h .v{color:$brick}.kpi.m .v{color:$gold}.kpi.e .v{color:$teal}
.tlist{display:flex;flex-wrap:wrap;gap:1.6mm}
.tlist span{font-size:8.4pt;padding:.8mm 2.4mm;border-radius:6mm;background:$surface2;color:$ink2}
.tlist b{margin-left:1mm}
.at{width:100%;border-collapse:collapse;font-size:8.6pt;margin-top:1mm}
.at th{background:$surface2;color:$ink3;font-weight:600;width:12mm}
.at th,.at td{border:.4pt solid $ruleSoft2;text-align:center;padding:.9mm 0}

/* 과목 표지 */
.subj{break-before:page;display:flex;align-items:baseline;gap:3mm;border-bottom:1.5pt solid $ink;
  padding-bottom:2mm;margin:0 0 5mm}
.subj h2{font-size:17pt}
.subj span{font-size:9pt;color:$ink3}

/* 문항 */
.q{margin:0 0 6mm;padding-bottom:4mm;border-bottom:.4pt dashed $rule;orphans:2;widows:2}
.qh,.box,.opts,.calc,.pts,.pt,.law,.ans,.bt tr,.od li,.bar{break-inside:avoid}
.qh{break-after:avoid}
.ans{break-after:avoid}
.qh{display:flex;gap:3mm;align-items:flex-start}
.qn{flex:none;width:8mm;height:8mm;border-radius:2mm;background:$ink;color:$paper;font-size:10pt;font-weight:700;
  text-align:center;line-height:8mm}
.q.s2 .qn{background:$qn2Bg}
.qb{flex:1;min-width:0}
.qs{margin:0;font-size:10.6pt;line-height:1.6;font-weight:500}
.qs u.k{text-decoration:underline;text-underline-offset:2px;font-weight:700}
.tags{display:flex;flex-wrap:wrap;gap:1.4mm;margin-top:1.6mm}
.tag{font-size:7.8pt;padding:.4mm 2mm;border-radius:5mm;border:.4pt solid $ruleSoft;color:$ink3}
.tag.d상{color:$brick;border-color:$brickLine;background:$brickSoft}
.tag.d중{color:$gold;border-color:$goldLine;background:$goldSoft}
.tag.d하{color:$teal;border-color:$tealLine;background:$tealSoft}
.tag.L{color:$plum;border-color:$plumLine;background:$plumSoft}
.box{margin:2.5mm 0 0 11mm;background:$surface2;border-left:1pt solid $boxLine;border-radius:0 2mm 2mm 0;
  padding:2.5mm 3mm;font-size:9.4pt;line-height:1.7}
.bl{white-space:pre-wrap;padding-left:4.6mm;text-indent:-4.6mm}
.bt{border-collapse:collapse;font-size:8.8pt;margin:1mm 0;background:$tableBg}
.bt th,.bt td{border:.4pt solid $boxLine;padding:.8mm 2mm;text-align:center}
.bt th{background:$thBg;font-weight:600}
.opts{list-style:none;margin:2.5mm 0 0 11mm;padding:0}
.opts li{display:flex;gap:2mm;padding:.8mm 2mm;border-radius:1.5mm;font-size:9.9pt;line-height:1.55}
.opts li .k{flex:none;color:$ink3}
.opts li.on{background:$tealSoft}
.opts li.on .k{color:$tealInk;font-weight:700}
.q.s2 .opts li.on{background:$plumSoft}
.q.s2 .opts li.on .k{color:$plumInk}

/* 해설 */
.ex{margin:3mm 0 0 11mm;background:$exBg;border:.4pt solid $ruleSoft2;border-radius:2mm;padding:3mm 3.5mm}
.ans{display:flex;align-items:center;gap:2.5mm;font-size:9.4pt}
.ans .a{font-weight:700;color:$onAccent;background:$teal;border-radius:1.5mm;padding:.4mm 2.4mm}
.q.s2 .ans .a{background:$plumInk}
.ans .a.all{background:$brick}
.qnote{margin:2mm 0 0;background:$brickSoft;border-radius:1.5mm;padding:2mm 2.5mm;font-size:8.8pt;line-height:1.6;color:$ink2}
.ans .topic{font-weight:700}
.core{margin:2mm 0 0;font-size:9.5pt;line-height:1.7}
.calc{margin:2mm 0 0;background:$calcBg;border-left:1pt solid $tealLine;border-radius:0 1.5mm 1.5mm 0;padding:2mm 2.5mm;
  font-size:9pt;line-height:1.75}
.calc::before{content:"풀이";display:block;font-size:7.8pt;font-weight:700;color:$teal}
.od{list-style:none;margin:2.5mm 0 0;padding:0}
.od li{display:grid;grid-template-columns:5mm 4mm 1fr;gap:1.5mm;font-size:9pt;line-height:1.6;color:$ink2;
  margin-bottom:.8mm}
.od .k{color:$ink3}
.od .ox{font-weight:700;text-align:center}
.od .ox.o{color:$teal}.od .ox.x{color:$brick}
.od li.is-ans{color:$ink}
.pts{display:grid;grid-template-columns:1fr 1fr;gap:2mm;margin-top:2.5mm}
.pt{border-radius:1.5mm;padding:2mm 2.5mm;font-size:8.8pt;line-height:1.55}
.pt .h{display:block;font-size:7.8pt;font-weight:700;margin-bottom:.3mm}
.pt.trap{background:$brickSoft}.pt.trap .h{color:$brick}
.pt.memo{background:$goldSoft}.pt.memo .h{color:$gold}
.law{margin-top:2mm;font-size:8.6pt;padding:1.8mm 2.5mm;border:.4pt solid $goldLine;border-radius:1.5mm;color:$ink2}
.law::before{content:"개정 메모 · ";font-weight:700;color:$gold}
.end{margin-top:6mm;padding-top:3mm;border-top:.5pt solid $rule;font-size:8.4pt;color:$ink3;line-height:1.6}
'''

from string import Template
CSS = Template(CSS).substitute(DARKP if DARK else LIGHT)
html_doc = ('<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>%s</title><style>%s</style></head>'
            '<body>%s</body></html>' % (esc(M['title']), CSS, ''.join(body)))
open(OUT, 'w', encoding='utf-8').write(html_doc)
print('문항', len(D), '| HTML', len(html_doc), 'bytes →', OUT)
