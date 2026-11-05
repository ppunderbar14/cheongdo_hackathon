# 청도 한입 앱

RATE에서 반응형 스타일, 선택적 위치 조회, 메뉴 경험 기록 흐름을 골라 새 앱에 맞게 분리한 해커톤용 기반입니다. 원본 RATE 폴더와 그 Supabase 연결 설정은 사용하지 않습니다.

## 로컬 실행

Python 3.11 이상을 권장합니다.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

브라우저에서 `http://127.0.0.1:8000`을 엽니다. 이 앱은 아직 검증된 청도 식당 데이터가 없어 빈 상태를 표시합니다. 임의의 식당·메뉴·평점을 실제 정보처럼 채우지 마세요. 데이터 항목에는 원문 출처와 확인일을 추가해야 합니다.

## AI 취향 요약 설정

Copilot SDK는 서버에서만 실행합니다. Microsoft Foundry/Azure OpenAI BYOK를 사용할 때 앱 프로세스 환경에 아래 값을 설정하세요.

```text
COPILOT_AZURE_ENDPOINT=https://<resource>.openai.azure.com
COPILOT_AZURE_API_KEY=<server-secret>
COPILOT_MODEL=<deployment-name>
```

비밀값을 코드, `.env` 커밋, 브라우저, 공개 이슈에 넣지 마세요. 모델 호출은 선택적 취향 요약에만 사용하며 평점이나 월간 Best를 만들지 않습니다. 현재 SDK 통합은 로컬 런타임/실제 인증 및 Azure 배포 확인이 필요합니다.

## 데이터 계약

`data/catalog.json`은 공개 카탈로그의 입력 형식입니다.

- 식당: `id`, `name`, 청도 `area`, `address`, `latitude`, `longitude`, 좌표 출처/확인일, `status`
- 메뉴: `id`, `restaurant_id`, `name`
- 공개 리뷰: `restaurant_id`, `menu_id`, `reviewer_id`, `score`, `created_at`, `status`

실제 주소/좌표/영업 정보는 원자료를 검증한 뒤에만 입력하세요. 위치 권한은 버튼을 누른 경우에만 요청하며 위경도는 저장하지 않습니다. 현재 개인 테스트 평가는 브라우저 localStorage에 저장되므로 커뮤니티 공개 리뷰로 집계되지 않습니다.

## Azure

Azure Container Apps 배포 전 `COPILOT_*` 비밀을 환경의 secret으로 설정하고 실제 런타임 인증을 확인하세요. `Dockerfile`은 Copilot SDK 런타임을 이미지 빌드 단계에서 준비하도록 되어 있습니다. Azure 배포는 계정/구독과 예산 승인을 확인한 뒤 수행합니다.
