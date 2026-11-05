# 청도 한입

청도에서 식당과 메뉴를 발견하고, 메뉴별 평가를 통해 내 취향을 기록하는 해커톤 웹 앱입니다.

## 실행

```bash
cd app
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

브라우저에서 `http://127.0.0.1:8000`을 엽니다. 현재 검증된 청도 식당 데이터가 연결되기 전이라 카탈로그가 비어 있습니다. 실제 장소·메뉴 정보는 출처와 확인일을 확인한 뒤에만 등록합니다.

## 문서

- [제품 요구사항](./PRD.md)
- [기술 설계](./TRD.md)

## 테스트

```bash
cd app
python test_main.py
```
