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

## OpenAI 취향 요약 연결

Copilot SDK가 서버에서 OpenAI API를 호출합니다. 앱을 실행하는 서버 환경에 다음 값을 설정하세요. `OPENAI_MODEL`은 OpenAI API Playground에서 실제 호출 권한이 확인된 모델 ID를 사용합니다.

```text
OPENAI_API_KEY=<server-secret>
OPENAI_MODEL=gpt-6-luna
```

`OPENAI_API_KEY`는 OpenAI API Platform에서 발급한 API 키입니다. ChatGPT 구독과 API 결제는 별도이며, 계정에 API 결제/크레딧과 모델 사용 권한이 있어야 합니다. 이 설정은 Azure OpenAI 배포 이름이나 Azure endpoint가 아니라 OpenAI API를 직접 사용합니다. 키는 로컬 실행 셸의 환경 변수 또는 Azure Container Apps secret으로 주입하세요. Container Apps에서는 `OPENAI_API_KEY` secret을 만든 뒤 같은 이름의 환경 변수에 secret reference를 연결하고, `OPENAI_MODEL`은 일반 환경 변수로 지정해 새 revision을 배포합니다. 키를 코드, `.env`, 브라우저, 로그, 공개 이슈에 넣지 마세요.

OpenAI API는 별도 모델 배포 없이 토큰 사용량에 따라 과금됩니다. 실제 요금은 [OpenAI API 가격표](https://openai.com/api/pricing/)와 계정 사용량에서 확인하세요. 호출은 선택적 취향 요약에만 사용하며 평점이나 월간 Best를 만들지 않습니다. 키가 설정되지 않으면 API는 `503 AI 연결 설정이 없어요.`를 반환합니다. 공개 배포를 변경한 뒤 메뉴 경험을 기록하고 취향 요약을 눌러 실제 API 연결을 확인하세요.

## 데이터 계약

`data/catalog.json`은 공개 카탈로그의 입력 형식입니다.

- 식당: `id`, `name`, 청도 `area`, `address`, `source_url`, `source_label`, `source_published_at`, `source_checked_at`, `status`
- 위치 기반 거리순 검색에 포함하려면 `latitude`, `longitude`와 좌표 출처/확인일을 검증해서 추가합니다. 확인되지 않은 좌표는 추정해 넣지 않습니다.
- 메뉴: `id`, `restaurant_id`, `name`
- 공개 리뷰: `restaurant_id`, `menu_id`, `reviewer_id`, `score`, `created_at`, `status`

현재 메뉴명과 주소의 출처는 [청도관광 공식블로그 게시물](https://m.blog.naver.com/cheongdotour/224164326469)입니다. 실제 주소/좌표/영업 정보는 원자료를 검증한 뒤에만 입력하세요. 위치 권한은 버튼을 누른 경우에만 요청하며 위경도는 저장하지 않습니다. 현재 개인 테스트 평가는 브라우저 localStorage에 저장되므로 커뮤니티 공개 리뷰로 집계되지 않습니다.

## Azure 앱 배포

웹 앱은 Azure Container Apps에서 실행하고, AI 요청은 서버에서 OpenAI API로 보냅니다. 코드를 반영한 새 컨테이너 이미지를 배포한 뒤 Azure Portal에서 다음과 같이 설정합니다.

1. 해당 Container App의 **Secrets**에서 새 secret을 추가합니다. 이름은 `openai-api-key`, 값은 OpenAI API 키입니다.
2. **Containers** 설정의 환경 변수에 `OPENAI_API_KEY`를 추가하고, 값으로 직접 키를 붙여 넣지 말고 `openai-api-key` secret reference를 선택합니다.
3. 일반 환경 변수 `OPENAI_MODEL`에 `gpt-6-luna`를 지정합니다.
4. 설정을 저장해 새 revision을 배포합니다. 해당 revision에서 메뉴 경험을 기록한 뒤 취향 요약을 눌러 확인합니다.

`Dockerfile`은 Copilot SDK 런타임을 이미지 빌드 단계에서 준비합니다. Container App secret과 일반 환경 변수는 기존 revision에 즉시 적용되지 않을 수 있으므로 새 revision이 활성화됐는지 확인하세요. 컨테이너 revision의 AI 설정을 바꾸기 전에 사용량 예산과 OpenAI API 결제를 확인하세요.
