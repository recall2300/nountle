# 명사맨틀

명사만 쓰는 꼬맨틀. 오늘의 단어와 무제한 모드가 있고, GitHub Pages(서버 없음)나 NAS(FastAPI 서버)에 올릴 수 있습니다.

```bash
pip install -r requirements.txt
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

## 3. 서버 (NAS에서, 선택)
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

## 5. GitHub Pages 배포 (서버 없이)
`main`에 푸시하면 GitHub Actions가 벡터 다운로드부터 Pages 배포까지 알아서 처리합니다(`.github/workflows/pages.yml`).
Pages에서는 유사도를 브라우저가 직접 계산합니다(`export_static.py`로 PCA와 int8 압축, 약 8MB).

처음 한 번만 설정하면 됩니다.
1. **Settings → General**에서 저장소를 Public으로 바꿉니다(무료 플랜 기준).
2. 국립국어원 누리집 자료실에서 「한국어 학습용 어휘 목록」을 받아 `resources/vocab.xls`로 커밋합니다.
   `.xlsx` 파일이면 워크플로의 `VOCAB_FILE`도 같이 바꿔 주세요.
3. **Settings → Pages → Source**를 `GitHub Actions`로 바꿉니다.
4. (선택) **Settings → Secrets → Actions**에 `DAILY_SALT`를 넣으면 오늘의 단어 순서가 바뀝니다.

첫 배포는 FastText 파일(1.2GB) 다운로드와 명사 추출 때문에 10~20분쯤 걸립니다.
이후에는 스크립트나 어휘 파일이 바뀌지 않는 한 캐시를 써서 금방 끝납니다.
주소는 `https://recall2300.github.io/nountle/`입니다.

Pages 버전의 차이점
- 정답 후보가 공개 파일에 들어 있어서 마음먹으면 볼 수 있습니다.
- 무제한 모드에서 같은 코드를 넣으면 같은 문제가 나오지만, 친구와 추측 목록이 공유되지는 않습니다(NAS 서버 버전은 공유됨).
- 같은 `index.html`이 `data/meta.json`이 있으면 브라우저 계산, 없으면 서버 API를 씁니다.

## 조정 포인트
- `--max-words`: 높이면 희귀 명사까지 받지만 이상한 단어도 늘어남
- `TOP_N`: 순위를 매길 이웃 수 (기본값 1000)
- 워크플로의 `MAX_NOUNS`, `DIMS`: Pages에 올릴 명사 수와 압축 차원. 늘리면 정확해지지만 첫 로딩이 무거워짐
- 세션은 메모리에만 저장되므로 서버를 재시작하면 사라짐
