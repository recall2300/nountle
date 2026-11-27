# 명사맨틀 — 명사 전용 꼬맨틀

```bash
pip install kiwipiepy numpy pandas xlrd openpyxl fastapi uvicorn
```

## 1. 명사 벡터 만들기 (PC에서)
FastText 한국어 벡터 `cc.ko.300.vec.gz`(약 1.2GB)를 내려받은 뒤 실행합니다.
```bash
python build_vocab.py cc.ko.300.vec.gz --out data --max-words 400000
```
Kiwi로 분석했을 때 단어 하나가 그대로 일반명사(NNG)로 나오는 것만 남깁니다.
`사과를`, `서울`, `것`, `먹다` 같은 단어는 빠집니다.
사전에서 뽑은 명사 목록이 있으면 `--whitelist nouns_dict.txt`로 추가하세요.

## 2. 정답 후보 만들기
국립국어원 「한국어 학습용 어휘 목록」(.xls)을 사용합니다.
```bash
python build_answers.py "한국어 학습용 어휘 목록.xls" --data data
```
명사만 남기고 동음이의어(`배01`/`배02`)와 한 글자 단어는 뺍니다. 정답으로 쓰기 싫은 단어는 `--exclude`로 넘기면 됩니다.

## 3. 서버 (NAS에서)
`data/` 폴더(`nouns.txt`, `vectors.npy`, `answers.txt`)만 옮기면 됩니다.
```bash
DATA_DIR=data DAILY_SALT=비밀문자열 uvicorn server:app --host 0.0.0.0 --port 8000
```
- 오늘의 단어: `/api/daily/guess?word=`, `/api/daily/hint`, `/api/daily/giveup`
- 무제한 모드(꼬오맨틀식): `POST /api/session`을 호출한 뒤 `/api/session/{id}/guess?word=` 사용. 세션은 기본 12시간 뒤 만료됩니다.

## 4. 웹 화면
`static/index.html`이 `server.py` 옆에 있으면 `http://NAS주소:8000/`에서 바로 열립니다.
- 오늘의 단어: 추측 기록이 브라우저에 날짜별로 저장돼서 새로고침해도 유지됩니다.
- 무제한: 참여 코드를 친구에게 보내면 같은 문제를 같이 풀 수 있습니다. 서로의 추측이 4초마다 공유됩니다.

## 조정 포인트
- `--max-words`: 높이면 희귀 명사까지 받지만 이상한 단어도 늘어남
- `TOP_N`: 순위를 매길 이웃 수 (기본값 1000)
- 세션은 메모리에만 저장되므로 서버를 재시작하면 사라짐
