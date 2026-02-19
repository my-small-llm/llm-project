# generated_data_validator 구현 계획

## 목적

`datagenerator` 패키지로 생성된 학습 데이터(`.txt` 파일)의 유효성을 자동으로 검증한다.

## 실행 방식

```bash
python -m generated_data_validator.validate --target_dir mini_samples_n55
```

## 패키지 구조

```
generated_data_validator/
├── __init__.py
├── validate.py          # python -m generated_data_validator.validate 진입점
├── report.py            # python -m generated_data_validator.report 진입점
├── rules/
│   ├── __init__.py
│   ├── format.py        # 파일 형식·구조 검증 규칙
│   ├── schema.py        # 함수 콜 스키마 검증 규칙
│   └── content.py       # 값·내용 검증 규칙
└── utils.py             # 공통 유틸 (파일 로딩 등)
```

## 데이터 포맷 (sample_0001.txt 기준)

```
<|im_start|>system
...시스템 프롬프트 + 툴 정의...
<|im_end|>
<|im_start|>user
...유저 메시지...
<|im_end|>
<|im_start|>assistant
<tool_call>
{"name": "...", "arguments": {...}}
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

## 검증 규칙 목록

### Rule 1: im_start / im_end 짝 검증

- **위치**: `rules/format.py`
- **방식**: depth 카운터 방식 — 정규식으로 토큰을 순서대로 추출하여 순서 검사
- **오류 케이스**:
  - `<|im_start|>` 열린 상태에서 다시 `<|im_start|>` 등장
  - `<|im_start|>` 없이 `<|im_end|>` 등장
  - 파일 끝에 닫히지 않은 블록 존재

### Rule 2: tool_call의 name/arguments 검증 (deep)

- **위치**: `rules/schema.py`
- **대상**: `<|im_start|>assistant` 블록 내 `<tool_call>` JSON
- **검증 내용**:
  - `name`이 `docs/custom_functions.py`에 정의된 함수 중 하나인지 확인
  - `arguments`의 각 key가 해당 함수의 파라미터에 존재하는지 확인
  - 각 value의 Python 타입(`str`, `int`, `float`, `bool`, `list` 등)이 파라미터 타입 힌트와 일치하는지 확인
- **구현 방법**: `docs/custom_functions.py`를 import하고 `inspect.signature()` + `get_type_hints()`로 파라미터 정보 추출

### Rule 3: tool_response의 return 형태 검증 (deep)

- **위치**: `rules/schema.py`
- **대상**: `<|im_start|>user` 블록 내 `<tool_response>` JSON
- **검증 내용**:
  - 직전 `tool_call.name`을 추적하여 기대 반환 타입 결정
  - 반환 타입의 key 존재 여부 확인
  - 각 value의 Python 타입이 TypedDict 필드 타입과 일치하는지 확인
- **구현 방법**: `get_type_hints(ReturnTypeClass)`로 TypedDict 필드 타입 추출
- **특이 케이스**:
  - `upsert_address`, `place_order` → 반환값이 `str` (dict 아님)
  - `get_cart` → `Optional[CartSummary]` (None 허용)
  - `list_addresses` → `list[Address]` (list 타입)

## 검증 흐름

```
validate.py
  └─ 대상 디렉토리의 .txt 파일 순회
       └─ 각 파일에 rules/ 의 규칙 적용
            └─ 결과 수집 → report.py 에서 출력
```
