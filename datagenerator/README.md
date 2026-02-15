# datagenerator

음식 배달 서비스 AI 상담사를 위한 **function calling 파인튜닝용 합성 대화 데이터**를 생성하는 패키지입니다.
OpenAI API를 사용해 멀티턴 대화를 생성하고, Qwen3 chat-template 형식으로 렌더링하여 저장합니다.

---

## 설치 / 환경 준비

```bash
# 프로젝트 루트에서 실행
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# OpenAI API 키 설정
export OPENAI_API_KEY="sk-..."
```

---

## 빠른 시작

```bash
# 프로젝트 루트에서 실행해야 합니다 (상대 경로 기준)
cd /path/to/llm-project

# 단일 샘플 생성 (기본값: --n 1, --output data/raw)
python -m datagenerator.pipeline --fns search_restaurants,add_to_cart
```

---

## CLI 사용법

```
python -m datagenerator.pipeline [옵션]
```

### 옵션

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--type` | `conversation` | 생성 유형: `conversation` 또는 `rejection` |
| `--fns` | `all` | 사용할 함수 목록 (쉼표 구분). `all`이면 전체 함수. `--type rejection`일 때 무시됨 |
| `--n` | `1` | 생성할 샘플 수 |
| `--output` | `data/raw` | 출력 디렉토리 경로 |

### 사용 가능한 함수 목록 (`--fns` 값)

```
search_restaurants      # 음식점 검색
get_restaurant_detail   # 음식점 상세 조회
upsert_address          # 배송지 생성/수정
list_addresses          # 배송지 목록 조회
get_cart                # 장바구니 조회
add_to_cart             # 장바구니에 메뉴 추가
update_cart_item        # 장바구니 항목 수정
remove_cart_items       # 장바구니 항목 삭제
prepare_checkout        # 결제 전 금액 확인
place_order             # 주문 확정
get_order_status        # 주문 상태 조회
```

---

## 사용 예시

### 1. 멀티턴 대화 — 특정 함수 지정

```bash
python -m datagenerator.pipeline \
    --type conversation \
    --fns add_to_cart,get_cart \
    --n 100 \
    --output data/raw/
```

`add_to_cart`와 `get_cart`를 반드시 사용하는 멀티턴 대화 100건을 생성합니다.

### 2. 멀티턴 대화 — 전체 함수 허용

```bash
python -m datagenerator.pipeline \
    --type conversation \
    --fns all \
    --n 200 \
    --output data/raw/
```

11개 함수 전체를 활용할 수 있는 대화 200건을 생성합니다.

### 3. 주문 완결 흐름 (검색 → 장바구니 → 주문)

```bash
python -m datagenerator.pipeline \
    --type conversation \
    --fns search_restaurants,get_restaurant_detail,add_to_cart,prepare_checkout,place_order \
    --n 50 \
    --output data/raw/
```

### 4. 지원 불가 쿼리 (거절 응답)

```bash
python -m datagenerator.pipeline \
    --type rejection \
    --n 50 \
    --output data/raw/
```

도구로 처리할 수 없는 요청에 정중히 거절하는 대화를 생성합니다. `--fns`는 무시됩니다.

---

## 출력 파일 형식

샘플 하나당 동일한 stem으로 두 파일이 쌍으로 저장됩니다.

```
data/raw/
├── sample_0001.json   ← raw messages 배열 (렌더링 전)
├── sample_0001.txt    ← Qwen3 chat-template 포맷 (렌더링 후)
├── sample_0002.json
├── sample_0002.txt
└── ...
```

### sample_NNNN.json (raw messages)

```json
[
  {"role": "system", "content": "당신은 음식 배달 서비스 AI 상담사입니다..."},
  {"role": "user", "content": "피자 음식점 찾아줘"},
  {
    "role": "assistant",
    "content": "네, 검색해 드리겠습니다.",
    "tool_calls": [
      {"function": {"name": "search_restaurants", "arguments": {"category": "피자"}}}
    ]
  },
  {"role": "tool", "content": "{\"items\": [...]}"},
  {"role": "assistant", "content": "검색 결과입니다..."}
]
```

### sample_NNNN.txt (Qwen3 포맷)

```
<|im_start|>system
당신은 음식 배달 서비스 AI 상담사입니다...

# Tools
...
<|im_end|>
<|im_start|>user
피자 음식점 찾아줘<|im_end|>
<|im_start|>assistant
네, 검색해 드리겠습니다.
<tool_call>
{"name": "search_restaurants", "arguments": {"category": "피자"}}
</tool_call><|im_end|>
...
```

---

## 설정 변경

`datagenerator/config.py`에서 주요 설정을 변경할 수 있습니다.

```python
MODEL = "gpt-4o"       # 사용할 OpenAI 모델
TEMPERATURE = 0.4      # 생성 다양성 (0.0 ~ 1.0)
BATCH_SIZE = 10        # (향후 배치 처리용 예약)
```

---

## 주의사항

- **실행 위치**: 프로젝트 루트(`llm-project/`)에서 실행해야 `docs/` 경로가 올바르게 참조됩니다.
- **API 비용**: `--n` 값이 클수록 OpenAI API 호출 횟수가 늘어납니다. 먼저 `--n 1`로 출력을 확인하세요.
- **파싱 실패**: LLM이 지시한 형식을 따르지 않으면 해당 샘플은 건너뛰고 경고를 출력합니다.
