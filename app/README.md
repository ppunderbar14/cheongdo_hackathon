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

브라우저에서 `http://127.0.0.1:8000`을 엽니다. 현재 카탈로그에는 청도관광 공식블로그가 2026년 1월 30일 소개한 식당 3곳과 메뉴 9개가 들어 있습니다. 각 식당 카드에서 원문과 게시일을 확인할 수 있습니다. 출처에 없는 평점은 추가하지 않았고, 영업 여부와 영업시간은 방문 전 확인해야 합니다. 좌표를 검증한 식당만 주변 거리순 검색에 포함해야 합니다.

## AI 취향 요약 설정

Copilot SDK는 서버에서만 실행합니다. Microsoft Foundry/Azure OpenAI BYOK를 사용할 때 앱 프로세스 환경에 아래 값을 설정하세요.

```text
COPILOT_AZURE_ENDPOINT=https://<resource>.openai.azure.com
COPILOT_AZURE_API_KEY=<server-secret>
COPILOT_MODEL=<deployment-name>
```

`COPILOT_MODEL`에는 카탈로그 모델 ID가 아니라 Azure에 만든 **배포 이름**을 입력합니다. 현재 코드는 Copilot SDK의 `azure` provider를 사용하므로 `COPILOT_AZURE_ENDPOINT`에는 리소스 호스트까지만 넣습니다. Foundry의 프로젝트 endpoint(`*.services.ai.azure.com/api/projects/...`)나 `/openai/v1` 경로를 넣지 마세요. 비밀값은 로컬 실행 셸의 환경 변수 또는 Azure Container Apps secret으로 주입하고, 코드·커밋되는 `.env`·브라우저·공개 이슈에 넣지 마세요. Container Apps에서는 API 키를 secret으로 만든 뒤 `COPILOT_AZURE_API_KEY` 환경 변수에 secret reference를 연결합니다. `COPILOT_AZURE_ENDPOINT`와 `COPILOT_MODEL`은 일반 환경 변수로 설정한 다음 새 revision을 배포합니다.

먼저 Foundry에서 모델 배포를 완료해야 합니다. “내 프로젝트에서 사용 가능” 표시는 배포 쿼터가 있다는 보장이 아닙니다. 배포 전에 지역/SKU의 사용 가능 여부와 종량제 가격을 확인하세요. 호출은 선택적 취향 요약에만 사용하며 평점이나 월간 Best를 만들지 않습니다. 키가 설정되지 않으면 API는 `503 AI 연결 설정이 없어요.`를 반환합니다. 배포 이름, 리소스 endpoint, 키가 서로 맞는지 확인한 뒤 실제 Azure 배포에서 테스트해야 합니다.

## 데이터 계약

`data/catalog.json`은 공개 카탈로그의 입력 형식입니다.

- 식당: `id`, `name`, 청도 `area`, `address`, `source_url`, `source_label`, `source_published_at`, `source_checked_at`, `status`
- 위치 기반 거리순 검색에 포함하려면 `latitude`, `longitude`와 좌표 출처/확인일을 검증해서 추가합니다. 확인되지 않은 좌표는 추정해 넣지 않습니다.
- 메뉴: `id`, `restaurant_id`, `name`
- 공개 리뷰: `restaurant_id`, `menu_id`, `reviewer_id`, `score`, `created_at`, `status`

현재 메뉴명과 주소의 출처는 [청도관광 공식블로그 게시물](https://m.blog.naver.com/cheongdotour/224164326469)입니다. 실제 주소/좌표/영업 정보는 원자료를 검증한 뒤에만 입력하세요. 위치 권한은 버튼을 누른 경우에만 요청하며 위경도는 저장하지 않습니다. 현재 개인 테스트 평가는 브라우저 localStorage에 저장되므로 커뮤니티 공개 리뷰로 집계되지 않습니다.

## Azure

Azure Container Apps 배포 전 `COPILOT_*` 비밀을 환경의 secret으로 설정하고 실제 런타임 인증을 확인하세요. `Dockerfile`은 Copilot SDK 런타임을 이미지 빌드 단계에서 준비하도록 되어 있습니다. Azure 배포는 계정/구독과 예산 승인을 확인한 뒤 수행합니다.
