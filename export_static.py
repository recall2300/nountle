#!/usr/bin/env python3
"""
4단계(정적 배포용): 서버 없이 브라우저에서 유사도를 계산할 수 있게 데이터를 압축한다.

  python export_static.py --data data --out site/data --max-nouns 60000 --dims 300

- 입력 허용 명사를 빈도 상위 --max-nouns개로 줄인다(정답 후보는 항상 포함).
- PCA로 --dims 차원까지 줄이고, 행마다 정규화한 뒤 int8로 양자화한다.
  실측(명사 41,934개): 300차원 12.6MB, 상위 1000위 96.6% 일치 / 128차원 5.4MB, 62.7% 일치.
- 결과물
    words.txt    명사 목록 (줄바꿈 구분, vectors.bin 행 순서와 같음)
    vectors.bin  int8, 행 우선 (N × dims)
    meta.json    {"n", "dims", "answers": [정답 후보의 행 번호], "salt"}
- 공개 사이트라 정답 후보는 파일에서 볼 수 있다. 캐주얼 게임 용도로만 쓰는 전제.
"""
import argparse
import json
import secrets
from pathlib import Path

import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--out", default="site/data")
    ap.add_argument("--max-nouns", type=int, default=60_000)
    ap.add_argument("--dims", type=int, default=300, help="300이면 PCA를 건너뜀(권장)")
    ap.add_argument("--salt", default=None, help="오늘의 단어 순서를 정하는 값(기본: 무작위)")
    args = ap.parse_args()

    data = Path(args.data)
    words = (data / "nouns.txt").read_text(encoding="utf-8").split("\n")
    vecs = np.load(data / "vectors.npy").astype(np.float32)
    answers = [w for w in (data / "answers.txt").read_text(encoding="utf-8").split("\n") if w]

    index = {w: i for i, w in enumerate(words)}
    keep = list(range(min(args.max_nouns, len(words))))
    kept = set(keep)
    keep += [index[a] for a in answers if a in index and index[a] not in kept]
    words = [words[i] for i in keep]
    vecs = vecs[keep]

    if args.dims < vecs.shape[1]:
        centered = vecs - vecs.mean(axis=0)
        _, s, vt = np.linalg.svd(centered, full_matrices=False)
        vecs = centered @ vt[: args.dims].T
        kept_var = (s[: args.dims] ** 2).sum() / (s ** 2).sum()
        print(f"PCA {centered.shape[1]} → {args.dims}차원, 분산 {kept_var:.1%} 유지")

    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-12
    q = np.clip(np.round(vecs * 127), -127, 127).astype(np.int8)

    pos = {w: i for i, w in enumerate(words)}
    meta = {
        "n": len(words),
        "dims": int(q.shape[1]),
        "answers": [pos[a] for a in answers if a in pos],
        "salt": args.salt or secrets.token_hex(8),
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "words.txt").write_text("\n".join(words), encoding="utf-8")
    q.tofile(out / "vectors.bin")
    (out / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    print(f"명사 {meta['n']:,}개, 정답 후보 {len(meta['answers']):,}개 → {out} "
          f"(vectors.bin {q.nbytes / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
