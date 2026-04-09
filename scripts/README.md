# 스크립트 모음

워크숍 실습 및 확장용 Python 스크립트입니다.

## 사전 설치

```
pip install -r requirements.txt
```

## 스크립트 목록

### fetch_dart_financials.py

OpenDart API로 기업의 연결 재무제표를 조회하여 마크다운 보고서를 생성합니다.

```
python scripts/fetch_dart_financials.py 316140
```

환경변수 `OPENDART_API_KEY` 필수.

**캐싱:** 첫 실행 시 corpCode.xml(약 2MB)을 `.cache/` 폴더에 저장하고, 이후 24시간 동안 캐시를 재사용합니다. 두 번째 실행부터는 즉시 시작합니다.

### fetch_naver_consensus.py

네이버금융에서 증권사 투자의견을 가져옵니다.

```
python scripts/fetch_naver_consensus.py 316140
```

웹 스크래핑 방식이므로 네이버 HTML 구조 변경 시 수정이 필요할 수 있습니다.
