# 공인중개사 기출 상세 해설지 — 작업 저장소

제37회(2026.10) 대비 기출 해설지를 만드는 작업입니다. **클라우드 세션(claude.ai/code)에서 배치 단위로 돌리기 위한 저장소**입니다.
무거운 작업(해설 쓰기)만 여기서 하고, PDF 조판·검수는 Cowork 대화에서 합니다.

## 폴더

```
specs/     해설·전사·채점 지시문 (EXPLAIN1=1차, EXPLAIN2=2차)
exams/<회차>/q.json        문항 원문(발문·박스·선지) — 이미 추출해 둔 것
exams/<회차>/ex/*_in.json  배치별 입력 문항
exams/<회차>/ex/*.prompt.md 배치별 지시문 (세션에 이 파일을 읽으라고 시키면 됩니다)
exams/<회차>/crops/        표·그림 문항의 원본 이미지 조각(대조용)
law/       과목별 현행법 정리 노트 (2026.9 기준) — 해설 쓸 때 먼저 참고
scan-src/  글자층이 없는 시험지 원본 PDF를 넣을 자리 (scan-src/README.txt 참고 — 바탕화면 공인중개사 폴더에서 6개 복사)
scripts/   문항 추출·배치 생성·병합·PDF 조판 스크립트
data/corpus.txt  띄어쓰기 복원용 말뭉치
batches.json     남은 배치 목록(기계용)
```

회차 이름: `1-2022` = 1차 제33회(2022년), `2-2014` = 2차 제25회(2014년)

## 한 배치가 하는 일

1. `exams/<회차>/ex/<배치>_in.json` 의 문항을 읽는다 (1차 20문항 / 2차 1교시 16, 2교시 20)
2. 문항마다 해설을 쓴다 — 이해하기 · 용어 풀이 · 정답 근거(조문) · 선지별 O/X · 암기 정리 · 계산 풀이 · 함정 · 한 줄 암기 · 관련 강 · 개정 메모
3. 현행법(2026.9)으로 답이 달라지면 `changed: true` 와 `rev`(고친 문제와 해설)를 넣는다
4. `<배치>_1.json`, `<배치>_2.json` 두 파일로 저장한다

자세한 규칙은 `specs/EXPLAIN2.md`(2차) / `specs/EXPLAIN1.md`(1차)에 있습니다. **이 지시문을 세션이 직접 읽게 하세요.**

## 처음 한 번만

1. 이 폴더를 깃허브 저장소로 올립니다 (`git init && git add -A && git commit -m init && git remote add origin ... && git push -u origin main`).
   비공개 저장소면 [Claude GitHub App](https://github.com/apps/claude/installations/new)을 그 저장소에 설치해야 클라우드 세션이 접근합니다.
2. `scan-src/README.txt` 를 보고 시험지 PDF 6개를 복사해 넣고 커밋합니다(전사 작업을 할 때만 필요).
3. [claude.ai/code](https://claude.ai/code) 에서 이 저장소를 고르고 아래처럼 배치를 하나씩 맡깁니다.

## 진행 방법

`TASKS.md` 의 표에서 배치를 하나 고르고, 거기 적힌 문장을 claude.ai/code 세션에 붙여넣으면 됩니다.
여러 배치를 동시에 돌려도 됩니다(배치마다 파일이 달라 충돌하지 않습니다). 각 세션은 브랜치를 올리고, PR로 합치면 됩니다.

## 결과 합치기 (Cowork 대화에서)

```
python3 scripts/merge_exam.py <회차>          # q.json + ex/*.json → final.json
python3 scripts/build_book2.py exams/<회차>/final.json books/meta-<회차>.json books/<회차>.html dark
node scripts/render.js books/<회차>.html books/<이름>.pdf "<머리말>" "#A9A69A"
python3 scripts/darken.py books/<이름>.pdf "#14140F"
```

## 규칙

- 문항 원문은 바꾸지 않습니다. 원본과 다른 곳을 찾으면 해설 JSON의 `fix` 필드에만 적습니다.
- 정답 `a`는 **시험 당시 법령 기준**입니다. 현행법 기준 답은 `changed`/`rev` 로 따로 씁니다.
- 수험생이 옛 규정을 외우면 안 됩니다. 바뀐 규정은 반드시 `law`에 적고 `rev`에 현행 문제를 만들어 둡니다.
