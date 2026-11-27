#!/usr/bin/env python3
"""
압축(PCA + int8)이 순위를 얼마나 바꾸는지 확인한다. 배포 로그에서 결과를 볼 수 있다.

  python eval_compression.py --data data --max-nouns 60000 --dims 128 200 300

- 정답 후보 중 무작위 100개에 대해 원본 300차원 기준 상위 1000개와
  압축본 상위 1000개가 얼마나 겹치는지(%)와 상위 10개 겹침을 출력한다.
- 몇몇 단어는 상위 10개 이웃을 나란히 보여 준다.
"""
import argparse
import random

import numpy as np


def compress(vecs, dims):
    if dims < vecs.shape[1]:
        c = vecs - vecs.mean(axis=0)
        _, _, vt = np.linalg.svd(c, full_matrices=False)
        vecs = c @ vt[:dims].T
    vecs = vecs / (np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-12)
    q = np.clip(np.round(vecs * 127), -127, 127).astype(np.float32)
    return q / (np.linalg.norm(q, axis=1, keepdims=True) + 1e-12)


def topk(mat, i, k):
    return np.argsort(-(mat @ mat[i]))[1 : k + 1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--max-nouns", type=int, default=60_000)
    ap.add_argument("--dims", type=int, nargs="+", default=[128, 200, 300])
    ap.add_argument("--samples", type=int, default=100)
    ap.add_argument("--show", nargs="*", default=["사과", "학교", "바다", "음악", "친구"])
    args = ap.parse_args()

    words = open(f"{args.data}/nouns.txt", encoding="utf-8").read().split("\n")
    vecs = np.load(f"{args.data}/vectors.npy").astype(np.float32)
    answers = [w for w in open(f"{args.data}/answers.txt", encoding="utf-8").read().split("\n") if w]
    index = {w: i for i, w in enumerate(words)}
    keep = list(range(min(args.max_nouns, len(words))))
    ks = set(keep)
    keep += [index[a] for a in answers if a in index and index[a] not in ks]
    words = [words[i] for i in keep]
    full = vecs[keep]
    full /= np.linalg.norm(full, axis=1, keepdims=True) + 1e-12
    pos = {w: i for i, w in enumerate(words)}

    pool = [pos[a] for a in answers if a in pos]
    sample = random.Random(0).sample(pool, min(args.samples, len(pool)))
    ref1000 = {i: set(topk(full, i, 1000)) for i in sample}
    ref10 = {i: set(topk(full, i, 10)) for i in sample}

    print(f"명사 {len(words):,}개, 표본 {len(sample)}개")
    comp = {}
    for d in args.dims:
        m = compress(full, d)
        comp[d] = m
        o1000 = np.mean([len(ref1000[i] & set(topk(m, i, 1000))) / 1000 for i in sample])
        o10 = np.mean([len(ref10[i] & set(topk(m, i, 10))) / 10 for i in sample])
        mb = len(words) * d / 1e6
        print(f"dims={d:>3}  상위1000 겹침 {o1000:.1%}  상위10 겹침 {o10:.1%}  vectors.bin {mb:.1f}MB")

    for w in args.show:
        if w not in pos:
            continue
        i = pos[w]
        print(f"\n[{w}]")
        print("  원본 :", " ".join(words[j] for j in topk(full, i, 10)))
        for d, m in comp.items():
            print(f"  {d:>3}차원:", " ".join(words[j] for j in topk(m, i, 10)))


if __name__ == "__main__":
    main()
