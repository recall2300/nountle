#!/usr/bin/env python3
"""
3단계: 게임 API 서버. 이웃 순위는 정답마다 처음 요청될 때 계산해서 캐시한다.
(명사 5만 개 × 300차원 내적은 수 ms라 미리 파일로 만들 필요가 없다.)

  DATA_DIR=data DAILY_SALT=아무비밀문자열 uvicorn server:app --host 0.0.0.0 --port 8000

모드
- 오늘의 단어:  GET  /api/daily/guess?word=사과
                GET  /api/daily/hint        (1위/10위/1000위 유사도)
                GET  /api/daily/giveup
- 무제한(꼬오맨틀식): POST /api/session  → {"session_id": ...}
                GET  /api/session/{sid}/guess?word=사과
                GET  /api/session/{sid}/hint
                GET  /api/session/{sid}/giveup
                GET  /api/session/{sid}/guesses  (같은 세션 친구들의 추측 목록)
- 웹 화면: static/index.html 을 / 에서 제공
"""
import datetime as dt
import hashlib
import os
import random
import secrets
import time
from functools import lru_cache
from pathlib import Path

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

DATA = Path(os.environ.get("DATA_DIR", "data"))
SALT = os.environ.get("DAILY_SALT", "change-me")
TOP_N = int(os.environ.get("TOP_N", "1000"))
SESSION_TTL = int(os.environ.get("SESSION_TTL", str(12 * 3600)))
KST = dt.timezone(dt.timedelta(hours=9))

WORDS = (DATA / "nouns.txt").read_text(encoding="utf-8").split("\n")
VECS = np.load(DATA / "vectors.npy")
INDEX = {w: i for i, w in enumerate(WORDS)}
ANSWERS = [w for w in (DATA / "answers.txt").read_text(encoding="utf-8").split("\n") if w in INDEX]

app = FastAPI(title="명사맨틀")
# sid -> {"answer": str, "created": float, "guesses": {word: result}}
sessions: dict[str, dict] = {}


@lru_cache(maxsize=128)
def ranking(answer: str):
    sims = VECS @ VECS[INDEX[answer]]
    top = np.argsort(-sims)[: TOP_N + 1]  # 0번은 정답 자신
    ranks = {WORDS[i]: r for r, i in enumerate(top)}
    return sims, ranks, top


def score(sim: float) -> float:
    return round(float(sim) * 100, 2)  # 꼬맨틀처럼 코사인 × 100


def daily_answer() -> str:
    today = dt.datetime.now(KST).date().isoformat()
    h = int(hashlib.sha256(f"{SALT}:{today}".encode()).hexdigest(), 16)
    return ANSWERS[h % len(ANSWERS)]


def judge(answer: str, word: str):
    word = word.strip()
    if word not in INDEX:
        raise HTTPException(400, f"'{word}'은(는) 명사 목록에 없어요.")
    sims, ranks, _ = ranking(answer)
    r = ranks.get(word)
    return {
        "word": word,
        "similarity": score(sims[INDEX[word]]),
        "rank": None if r is None or r == 0 else r,  # 1~1000위, 밖이면 null
        "correct": word == answer,
    }


def hint(answer: str):
    sims, _, top = ranking(answer)
    pick = lambda r: score(sims[top[min(r, len(top) - 1)]])
    return {"rank1": pick(1), "rank10": pick(10), f"rank{TOP_N}": pick(TOP_N)}


def giveup(answer: str, n: int = 100):
    sims, _, top = ranking(answer)
    return {
        "answer": answer,
        "top": [{"rank": r, "word": WORDS[i], "similarity": score(sims[i])}
                for r, i in enumerate(top[1 : n + 1], start=1)],
    }


def get_session(sid: str) -> dict:
    now = time.time()
    for k in [k for k, v in sessions.items() if now - v["created"] > SESSION_TTL]:
        del sessions[k]
    if sid not in sessions:
        raise HTTPException(404, "없거나 만료된 코드예요. 새 문제를 시작해 주세요.")
    return sessions[sid]


@app.get("/api/daily/guess")
def daily_guess(word: str):
    return judge(daily_answer(), word)


@app.get("/api/daily/hint")
def daily_hint():
    return {"date": dt.datetime.now(KST).date().isoformat(), **hint(daily_answer())}


@app.get("/api/daily/giveup")
def daily_giveup():
    return giveup(daily_answer())


@app.post("/api/session")
def new_session():
    sid = secrets.token_urlsafe(8)
    sessions[sid] = {"answer": random.choice(ANSWERS), "created": time.time(), "guesses": {}}
    return {"session_id": sid, "expires_in": SESSION_TTL}


@app.get("/api/session/{sid}/guess")
def session_guess(sid: str, word: str):
    s = get_session(sid)
    result = judge(s["answer"], word)
    if result["word"] not in s["guesses"]:
        s["guesses"][result["word"]] = {**result, "order": len(s["guesses"]) + 1}
    return s["guesses"][result["word"]]


@app.get("/api/session/{sid}/guesses")
def session_guesses(sid: str):
    s = get_session(sid)
    return {"guesses": list(s["guesses"].values()),
            "expires_in": int(SESSION_TTL - (time.time() - s["created"]))}


@app.get("/api/session/{sid}/hint")
def session_hint(sid: str):
    return hint(get_session(sid)["answer"])


@app.get("/api/session/{sid}/giveup")
def session_giveup(sid: str):
    return giveup(get_session(sid)["answer"])


STATIC = Path(__file__).parent / "static"
if STATIC.is_dir():
    app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
