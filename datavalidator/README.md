# datavalidator

`datagen`으로 생성된 학습 데이터(`.txt`)의 유효성을 자동 검증하는 패키지.

## 실행 방법

### 기본 실행

```bash
python -m datavalidator.validate --target_dir <디렉토리>
```

### 예시

```bash
# synthetic_data/samples 디렉토리의 모든 .txt 파일 검증
python -m datavalidator.validate --target_dir synthetic_data/samples

# 절대 경로도 가능
python -m datavalidator.validate --target_dir /home/khh/workspace/llm-project/synthetic_data/samples
```

### 출력 예시

```
검증 시작: /home/khh/workspace/llm-project/synthetic_data/samples

  [PASS] sample_0002.txt
  [FAIL] sample_0001.txt  (2건)
         [tool_response] block#17: 함수 'list_addresses' 반환 타입은 list이어야 하나 dict 수신
         [tool_response] block#25: 함수 'place_order' 반환 타입은 str이어야 하나 dict 수신

결과: 55개 파일 중 23개 통과, 32개 실패
```

- `[PASS]` — 모든 규칙 통과
- `[FAIL]` — 하나 이상의 규칙 위반, 오류 내용과 블록 번호를 함께 출력
  - `[format]` — Rule 1 오류 (im_start/im_end 짝 불일치)
  - `[tool_call]` — Rule 2 오류 (함수명·파라미터 불일치)
  - `[tool_response]` — Rule 3 오류 (반환 형태 불일치)

---

## 패키지 구조

```
datavalidator/
├── validate.py       # 진입점 — 디렉토리 순회 및 결과 출력
├── utils.py          # 파일 로딩, im 블록 파싱
└── rules/
    ├── format.py     # Rule 1: im_start/im_end 짝 검증
    ├── schema.py     # Rule 2, 3: tool_call/tool_response 스키마 검증
    └── content.py    # (향후 확장용)
```

---

## 데이터 포맷

검증 대상 파일은 ChatML 형식으로 작성된 대화입니다.

```
<|im_start|>system
...시스템 프롬프트 + 툴 정의...
<|im_end|>
<|im_start|>user
...유저 메시지...
<|im_end|>
<|im_start|>assistant
<tool_call>
{"name": "함수명", "arguments": {...}}
</tool_call>
<|im_end|>
<|im_start|>user
<tool_response>
{...}
</tool_response>
<|im_end|>
<|im_start|>assistant
...어시스턴트 응답...
<|im_end|>
```

---

## 검증 로직

### Rule 1 — im_start / im_end 짝 검증 (`rules/format.py`)

`<|im_start|>`와 `<|im_end|>`가 순서대로 정확히 짝을 이루는지 검사한다.

정규식으로 두 토큰을 순서대로 추출한 뒤 depth 카운터로 상태를 추적한다.

```
depth = 0

<|im_start|> 등장 → depth가 0이 아니면 오류 (이전 블록 미닫힘)
               → depth += 1

<|im_end|>   등장 → depth가 0이면 오류 (대응 im_start 없음)
               → depth -= 1

파일 끝       → depth != 0이면 오류 (열린 블록 존재)
```

Rule 1이 실패한 파일은 블록 파싱 자체가 불가하므로 Rule 2, 3을 건너뜁니다.

---

### Rule 2 — tool_call 스키마 검증 (`rules/schema.py`)

`assistant` 블록 내 `<tool_call>` JSON을 `docs/custom_functions.py`의 함수 시그니처와 대조한다.

**검증 순서**

1. `name` 필드가 `custom_functions.py`에 정의된 함수 이름인지 확인
2. `arguments`의 각 key가 해당 함수의 파라미터 목록에 존재하는지 확인
3. 각 value의 Python 타입이 파라미터 타입 힌트와 일치하는지 확인

**구현 방식**

`docs/custom_functions.py`를 `importlib`으로 동적 import한 뒤,
`inspect.signature()` + `typing.get_type_hints()`로 파라미터 이름·타입을 추출한다.

```python
# 예: search_restaurants의 파라미터 힌트
{
    "query":     Optional[str],
    "category":  Optional[str],
    "min_rating": Optional[float],
    "only_open": bool,
    "sort":      str,
    "page":      int,
    "page_size": int,
}
```

---

### Rule 3 — tool_response 스키마 검증 (`rules/schema.py`)

`user` 블록 내 `<tool_response>` JSON을 해당 함수의 반환 타입과 대조한다.

**핵심 과제**: `tool_response` 자체에는 어떤 함수의 응답인지 정보가 없다.
직전 `assistant` 블록의 `tool_call.name`을 추적하여 기대 반환 타입을 결정한다.

```
assistant 블록 처리 시 → last_called_func = "search_restaurants"
user 블록 처리 시      → last_called_func 기준으로 반환 타입 결정
tool_response 소비 후  → last_called_func = None (초기화)
```

**반환 타입별 처리**

| 반환 타입 | 처리 방식 |
|---|---|
| `str` (`upsert_address`, `place_order`) | 값이 문자열인지 확인 |
| `list[X]` (`list_addresses`) | 값이 list인지 확인 |
| `Optional[X]` (`get_cart`) | None 허용, 값이 있으면 내부 타입으로 검증 |
| TypedDict (`SearchRestaurantsResponse` 등) | `get_type_hints()`로 필드 추출 → key 존재 여부 + value 타입 검증 |

---

## 검증 흐름 요약

```
validate.py
  └─ .txt 파일 순회
       └─ 각 파일
            ├─ Rule 1: check_im_pairing(text)
            │     실패 시 → Rule 2, 3 스킵
            └─ Rule 1 통과 시
                 ├─ 블록 파싱 (parse_blocks)
                 └─ 블록 순회
                      ├─ assistant 블록 → Rule 2: check_tool_call()
                      │                    last_called_func 갱신
                      └─ user 블록     → Rule 3: check_tool_response()
                                           last_called_func 초기화
```
