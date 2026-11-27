#!/usr/bin/env python3
"""
2단계: 국립국어원 '한국어 학습용 어휘 목록'에서 정답 후보 명사를 만든다.

  python build_answers.py "한국어 학습용 어휘 목록.xls" --data data

- 품사가 '명'인 단어만 사용한다.
- 원본의 '배01', '배02'처럼 번호가 붙은 단어는 동음이의어다.
  같은 표기가 두 번 이상 나오면(품사 무관) 정답 후보에서 뺀다.
  (입력으로는 여전히 받을 수 있다. 정답으로만 안 나올 뿐.)
- 1단계에서 만든 nouns.txt에 있는 단어만 남긴다(벡터가 있어야 하니까).
- 결과는 시드로 섞어서 answers.txt에 저장한다.
"""
import argparse
import random
from collections import Counter
from pathlib import Path

import pandas as pd


def load_table(path):
    p = str(path)
    if p.endswith(".csv"):
        return pd.read_csv(p)
    if p.endswith((".tsv", ".txt")):
        return pd.read_csv(p, sep="\t", dtype=str, keep_default_na=False)
    return pd.read_excel(p, sheet_name=0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("vocab", help="한국어 학습용 어휘 목록 (.tsv/.xls/.xlsx/.csv)")
    ap.add_argument("--data", default="data")
    ap.add_argument("--min-len", type=int, default=2, help="한 글자 정답은 기본 제외")
    ap.add_argument("--seed", type=int, default=20261127)
    ap.add_argument("--exclude", help="정답에서 뺄 단어 목록 파일(선택)")
    args = ap.parse_args()

    df = load_table(args.vocab)
    df["표기"] = df["단어"].astype(str).str.replace(r"\d+", "", regex=True).str.strip()
    df["품사"] = df["품사"].astype(str).str.strip()

    homonyms = {w for w, c in Counter(df["표기"]).items() if c > 1}
    nouns = set((Path(args.data) / "nouns.txt").read_text(encoding="utf-8").split("\n"))
    exclude = set()
    if args.exclude:
        exclude = {w.strip() for w in open(args.exclude, encoding="utf-8") if w.strip()}

    answers = []
    stats = Counter()
    for w, pos in zip(df["표기"], df["품사"]):
        if pos != "명":
            continue
        stats["명사"] += 1
        if w in homonyms:
            stats["동음이의어 제외"] += 1
        elif len(w) < args.min_len:
            stats["짧아서 제외"] += 1
        elif w not in nouns:
            stats["벡터 없음 제외"] += 1
        elif w in exclude:
            stats["수동 제외"] += 1
        elif w not in answers:
            answers.append(w)

    random.Random(args.seed).shuffle(answers)
    (Path(args.data) / "answers.txt").write_text("\n".join(answers), encoding="utf-8")
    print(dict(stats))
    print(f"정답 후보 {len(answers):,}개 → {args.data}/answers.txt")


if __name__ == "__main__":
    main()
