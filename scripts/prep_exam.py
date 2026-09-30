# -*- coding: utf-8 -*-
"""문항 JSON → 해설 배치 입력·지시문 만들기
사용: python3 prep_exam.py <exam> <회차라벨> <시행일> [q파일]
  exam: 1-2022, 2-2023 …   회차라벨: '제34회(2023년)'   시행일: '2023. 10. 28.'
"""
import sys, os, json, re

exam, label, date = sys.argv[1], sys.argv[2], sys.argv[3]
base = '/home/claude/hx/exams/%s' % exam
qfile = sys.argv[4] if len(sys.argv) > 4 else (base + '/q.json' if os.path.exists(base + '/q.json') else base + '/q_raw.json')
Q = json.load(open(qfile, encoding='utf-8'))

def normtxt(s):
    if not s: return s
    return s.replace('ᆞ', 'ㆍ').replace('․', 'ㆍ').replace('‧', 'ㆍ')
for q in Q:
    q['stem'] = normtxt(q['stem']); q['box'] = normtxt(q.get('box') or ''); q['o'] = [normtxt(x) for x in q['o']]
    q.setdefault('flags', []); q.setdefault('crops', [])
json.dump(Q, open(base + '/q.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# 문제은행의 개정 메모(있으면 힌트로)
kind, year = exam.split('-')[0], int(exam.split('-')[1])
hints = {}
try:
    QB = json.load(open('/home/claude/k36/qbank.json', encoding='utf-8'))
    for b in QB:
        if b.get('c') == int(kind) and b.get('y') == year and b.get('law'):
            hints[(b.get('s') or 1, b['n'])] = b['law']
except Exception:
    pass

def batches(Q):
    if kind == '1':
        return [('B%02d' % (i // 20 + 1), Q[i:i + 20]) for i in range(0, len(Q), 20)]
    s1 = [q for q in Q if q['s'] == 1]; s2 = [q for q in Q if q['s'] == 2]
    B = [('P1-%02d' % (i // 16 + 1), s1[i:i + 16]) for i in range(0, len(s1), 16)]
    B += [('P2-01', s2[0:20]), ('P2-02', s2[20:40])]
    return B

os.makedirs(base + '/ex', exist_ok=True)
tmpl = open('/home/claude/hx/EXPLAIN%s.md' % kind, encoding='utf-8').read()
out = []
for bid, qs in batches(Q):
    if os.path.exists(base + '/ex/%s_1.json' % bid) and os.path.exists(base + '/ex/%s_2.json' % bid):
        continue  # 이미 끝난 배치
    rows = []
    for q in qs:
        r = {k: q[k] for k in ('s', 'n', 'stem', 'box', 'o', 'flags', 'crops')}
        key = (q['s'], q['n'] - 80 if (kind == '2' and q['s'] == 2 and q['n'] > 80) else q['n'])
        if key in hints: r['hint'] = hints[key]
        rows.append(r)
    inp = base + '/ex/%s_in.json' % bid
    json.dump(rows, open(inp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    pr = tmpl.replace('{EXAM}', label).replace('{DATE}', date).replace('{IN}', inp).replace('{OUT}', base + '/ex/%s' % bid)
    open(base + '/ex/%s.prompt.md' % bid, 'w', encoding='utf-8').write(pr)
    out.append(bid)
print(exam, '배치', out, '| 힌트', len(hints), '| flags', sum(1 for q in Q if q['flags']))
