#!/usr/bin/env python3
"""
1단계: FastText .vec 파일에서 '일반명사'만 골라 정규화된 벡터로 저장한다.

  python build_vocab.py cc.ko.300.vec.gz --out data --max-words 400000

- .vec는 빈도순으로 정렬돼 있으므로 --max-words로 상위 N개만 훑는다.
- Kiwi로 단어 하나를 분석했을 때 토큰 1개, 원형 그대로, 품사 NNG인 것만 남긴다.
  → '사과를'(조사 붙음), '서울'(고유명사), '것'(의존명사), '먹다'(동사)는 빠진다.
- --whitelist: 사전에서 뽑은 명사 목록(한 줄에 하나)이 있으면 Kiwi가 놓친 명사도 살린다.
- 7GB짜리 .bin을 메모리에 올리지 않고 한 줄씩 읽으므로 PC에서 돌리면 되고,
  NAS에는 결과물(nouns.txt, vectors.npy)만 올리면 된다.
"""
import argparse
import gzip
import re
from pathlib import Path

import numpy as np
from kiwipiepy import Kiwi

HANGUL = re.compile(r"^[가-힣]+$")


def open_text(path):
    if str(path).endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="ignore")
    return open(path, encoding="utf-8", errors="ignore")


def iter_vec(path, max_words):
    with open_text(path) as f:
        header = f.readline().split()
        dim = int(header[1])
        for n, line in enumerate(f):
            if n >= max_words:
                break
            parts = line.rstrip().split(" ")
            if len(parts) != dim + 1:
                continue
            yield parts[0], parts[1:], dim


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("vec", help="cc.ko.300.vec 또는 .vec.gz")
    ap.add_argument("--out", default="data")
    ap.add_argument("--max-words", type=int, default=400_000)
    ap.add_argument("--min-len", type=int, default=1)
    ap.add_argument("--max-len", type=int, default=6)
    ap.add_argument("--whitelist", help="추가로 허용할 명사 목록 파일(선택)")
    ap.add_argument("--batch", type=int, default=5000)
    args = ap.parse_args()

    whitelist = set()
    if args.whitelist:
        whitelist = {w.strip() for w in open(args.whitelist, encoding="utf-8") if w.strip()}

    kiwi = Kiwi()
    words, vecs = [], []
    seen = set()
    buf = []

    def flush():
        cand = [w for w, _ in buf]
        for (w, v), toks in zip(buf, kiwi.tokenize(cand)):
            ok = len(toks) == 1 and toks[0].form == w and toks[0].tag == "NNG"
            if ok or w in whitelist:
                words.append(w)
                vecs.append(np.asarray(v, dtype=np.float32))
        buf.clear()

    for w, v, dim in iter_vec(args.vec, args.max_words):
        if w in seen or not HANGUL.match(w) or not (args.min_len <= len(w) <= args.max_len):
            continue
        seen.add(w)
        buf.append((w, v))
        if len(buf) >= args.batch:
            flush()
    if buf:
        flush()

    mat = np.vstack(vecs)
    mat /= np.linalg.norm(mat, axis=1, keepdims=True) + 1e-12  # 코사인 = 내적

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "nouns.txt").write_text("\n".join(words), encoding="utf-8")
    np.save(out / "vectors.npy", mat)
    print(f"명사 {len(words):,}개 저장 → {out}/nouns.txt, vectors.npy "
          f"({mat.nbytes / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
