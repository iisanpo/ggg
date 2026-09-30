# -*- coding: utf-8 -*-
"""문항 + 해설(+보강) → final.json
사용: python3 merge_exam.py <exam>
- 해설 에이전트의 fix(원문 교정)는 공백을 뺀 글자가 90% 이상 같거나, 표·그림 표시 문항이면 받아들인다.
- a는 0부터 세는 번호로 바꿔 저장한다.
"""
import sys, os, json, glob, re, difflib

exam = sys.argv[1]
ROOT = os.environ.get('HX_ROOT') or os.getcwd()
base = os.path.join(ROOT, 'exams', exam)
Q = json.load(open(base + '/q.json', encoding='utf-8'))
R = {}
for f in sorted(glob.glob(base + '/ex/*_[12].json')):
    for r in json.load(open(f, encoding='utf-8')):
        R[(r.get('s', 1), r['n'])] = r
EN = {}
for f in sorted(glob.glob(base + '/en/E*.json')):
    if f.endswith('_q.json') or f.endswith('_ex.json'): continue
    for r in json.load(open(f, encoding='utf-8')):
        EN[(r.get('s', 1), r['n'])] = r

def flat(s): return re.sub(r'<[^>]+>|\s', '', s or '')
def close(a, b): return difflib.SequenceMatcher(None, flat(a), flat(b), autojunk=False).ratio()

out, missing, rejected, applied = [], [], [], 0
for q in Q:
    k = (q.get('s', 1), q['n'])
    r = R.get(k)
    if not r:
        missing.append(k); continue
    rec = dict(q)
    fx = r.get('fix') or {}
    for fld in ('stem', 'box'):
        if fld in fx and fx[fld] is not None and fx[fld] != q.get(fld):
            if q.get('flags') or close(q.get(fld), fx[fld]) >= 0.9 or not q.get(fld):
                rec[fld] = fx[fld]; applied += 1
            else:
                rejected.append((k, fld))
    if fx.get('o') and len(fx['o']) == 5:
        no = []
        for i in range(5):
            if fx['o'][i] != q['o'][i] and not (q.get('flags') or close(q['o'][i], fx['o'][i]) >= 0.9 or not q['o'][i]):
                rejected.append((k, 'o%d' % (i + 1))); no.append(q['o'][i])
            else:
                if fx['o'][i] != q['o'][i]: applied += 1
                no.append(fx['o'][i])
        rec['o'] = no
    for fld in ('diff', 'type', 'L', 'topic', 'explain', 'terms', 'core', 'opts', 'calc', 'study', 'trap', 'memo',
                'law', 'changed', 'rev', 'conf', 'note', 'allcorrect'):
        if fld in r: rec[fld] = r[fld]
    e = EN.get(k)
    if e:
        if e.get('explain'): rec['explain'] = e['explain']
        if e.get('terms'): rec['terms'] = e['terms']
    rec['a'] = int(r['a']) - 1
    rec.pop('crops', None); rec.pop('flags', None)
    out.append(rec)
json.dump(out, open(base + '/final.json', 'w', encoding='utf-8'), ensure_ascii=False)
print(exam, 'final', len(out), '| 누락', missing, '| 교정 적용', applied, '| 교정 보류', rejected[:10],
      '| changed', [(r.get('s', 1), r['n']) for r in out if r.get('changed')])
