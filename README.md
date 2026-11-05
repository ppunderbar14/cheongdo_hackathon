# 청도 한입

2026청도해커톤

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

## Azure Container Apps 배포

GitHub Actions는 `app/`의 Dockerfile을 빌드해 `ghcr.io/ppunderbar14/cheongdo-hackathon:latest`에 게시합니다. Azure Container Apps에서 이 이미지를 사용하려면 첫 게시 후 GitHub Packages의 패키지 설정에서 이미지 공개 범위를 `Public`으로 바꾸세요. 공개 이미지를 사용하면 Azure 배포에 별도 레지스트리 자격 증명이 필요하지 않습니다.

이 프로젝트의 Azure 구독에서는 Azure Container Registry Tasks가 허용되지 않아 `az containerapp up --source .` 빌드 방식을 사용할 수 없습니다. GitHub Actions로 이미지를 만든 뒤 Azure Container Apps에서 해당 GHCR 이미지를 배포하세요.
