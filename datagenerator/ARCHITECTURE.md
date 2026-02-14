# datagenerator 아키텍처 설계 문서

---

## 전체 파일 구조

```
datagenerator/
├── __init__.py
├── config.py                  # 상수 및 설정값 중앙 관리
├── _extractor.py              # docs/custom_functions.py에서 함수 스펙 추출
├── client.py                  # OpenAI API 클라이언트 래퍼
│
├── generators/
│   ├── __init__.py
│   ├── base.py                # 추상 BaseGenerator
│   ├── conversation.py        # 멀티턴 대화 생성 + LLM 출력 파서
│   └── rejection.py           # 거절 응답 생성
│
├── prompts/
│   ├── system.txt             # 데이터 생성 전문가 시스템 프롬프트
│   ├── conversation.txt       # 멀티턴 대화 생성 지시문 (플레이스홀더 포함)
│   └── rejection.txt          # 거절 응답 생성 지시문 (플레이스홀더 포함)
│
├── renderer.py                # Jinja2 기반 Qwen3 chat-template 렌더링
├── pipeline.py                # CLI 진입점 및 파이프라인 조율
│
├── README.md                  # 사용 방법 가이드
└── ARCHITECTURE.md            # 이 파일
```

---

## 데이터 흐름

```
pipeline.py (--type, --fns, --n, --output)
    │
    ├─ _extractor.py
    │     └─ docs/custom_functions.py AST 파싱
    │           ├─ function_specs (str)  → 프롬프트 삽입용 텍스트
    │           └─ tools_schema (list)  → Jinja2 렌더링용 OpenAI tool 형식
    │
    ├─ ConversationGenerator / RejectionGenerator
    │     ├─ build_messages(context)    → OpenAI API용 messages 리스트 조립
    │     └─ parse_response(text)       → LLM 출력 텍스트 → messages 배열 변환
    │
    ├─ client.py (OpenAI 호출, 지수 백오프 재시도)
    │     └─ raw_text (str)             → LLM이 생성한 대화 텍스트
    │
    ├─ sample_NNNN.json                 → raw messages 배열 저장
    │
    └─ renderer.py
          └─ docs/qwen3_chat-template.jinja 로 렌더링
                └─ sample_NNNN.txt      → Qwen3 포맷 저장
```

---

## 모듈별 설계 의도

### config.py

모든 상수를 한 곳에 모아 유지보수를 쉽게 합니다.

- `MODEL`, `TEMPERATURE`: OpenAI 호출 파라미터
- `ALL_FUNCTIONS`: 지원 함수 전체 목록 (순서 포함). `--fns all` 처리와 rejection 프롬프트에 공통으로 사용됩니다.
- `CHATBOT_SYSTEM_PROMPT`: 학습 데이터의 첫 번째 system 메시지로 삽입될 AI 상담사 역할 정의. 데이터 생성용 프롬프트와 분리되어 있습니다.
- 파일 경로 상수: `_extractor.py`와 `renderer.py`가 각각 `CUSTOM_FUNCTIONS_PATH`, `JINJA_TEMPLATE_DIR`를 import하여 사용합니다.

### _extractor.py

`docs/custom_functions.py`를 런타임에 `ast.parse`로 파싱합니다. 함수 정의를 직접 import하지 않는 이유는 해당 파일의 async 함수들을 실행하지 않고 **스펙(시그니처 + docstring)만 텍스트로 추출**하기 위해서입니다.

두 가지 출력 형식을 제공합니다.

| 함수 | 반환 타입 | 용도 |
|------|-----------|------|
| `extract_specs_text(fn_names)` | `str` | 프롬프트 `{function_specs}` 플레이스홀더에 삽입 |
| `extract_tools_schema(fn_names)` | `list[dict]` | Jinja2 렌더링의 `tools` 인자 |

`fn_names` 리스트의 **원래 순서를 보존**합니다. 내부적으로 `set`으로 조회 후 `fn_names` 순서대로 재정렬합니다.

파라미터 타입 변환 규칙:

| Python 타입 | JSON Schema 타입 |
|-------------|-----------------|
| `str` | `"string"` |
| `int` | `"integer"` |
| `float` | `"number"` |
| `bool` | `"boolean"` |
| `list[X]` | `{"type": "array", "items": ...}` |
| `Optional[X]` | X의 타입 (required에서 제외) |

### client.py

`openai.OpenAI()`를 래핑합니다. `RateLimitError`, `APIConnectionError`, `APIError` 세 가지 예외를 잡아 **지수 백오프**(2초 → 4초 → 8초)로 최대 3회 재시도합니다. 재시도 소진 시 마지막 예외를 그대로 raise합니다.

### generators/base.py

두 개의 추상 메서드를 정의합니다.

```python
def build_messages(self, context: dict) -> list[dict]: ...
def parse_response(self, text: str) -> list[dict]: ...
```

`__init__`에서 `prompts/system.txt`와 서브클래스가 지정한 `prompt_filename`을 읽어 `self.system_prompt`, `self.prompt_template`에 저장합니다. 파일 읽기를 생성자에서 처리하므로 매 호출마다 I/O가 발생하지 않습니다.

### generators/conversation.py

**`build_messages`**: `prompt_template.format(function_specs=..., target_functions=...)`으로 프롬프트를 조립하고 `[system, user]` 형식의 messages를 반환합니다.

**`parse_response`**: LLM이 반환한 텍스트를 `(role) content` 마커 기준으로 세그먼트로 분리한 뒤, 아래 규칙으로 messages 배열로 변환합니다.

```
(user)          → {"role": "user", "content": "..."}
(assistant)     → {"role": "assistant", "content": "..."}
(tool_call)     → 직전 assistant 메시지의 "tool_calls" 리스트에 병합
(tool_response) → {"role": "tool", "content": "..."}
```

`(tool_call)`을 별도 메시지로 만들지 않고 **직전 assistant 메시지에 병합**하는 것이 핵심입니다. 이는 OpenAI messages 형식에서 tool call은 assistant 메시지의 필드이기 때문입니다.

변환 후 맨 앞에 `config.CHATBOT_SYSTEM_PROMPT`를 system 메시지로 추가합니다.

### generators/rejection.py

`ConversationGenerator`와 동일한 구조이지만 프롬프트 파일이 `rejection.txt`이고, `parse_response`에서 `(tool_call)`과 `(tool_response)` 세그먼트를 무시합니다.

`build_messages`의 context는 `function_specs`만 필요합니다. rejection 생성 시에도 함수 스펙 전체를 주입하는 이유는, LLM이 **어떤 기능이 지원되는지 알아야 정확하게 지원되지 않는 시나리오를 생성**할 수 있기 때문입니다.

### prompts/

프롬프트를 `.py` 파일이 아닌 `.txt` 파일로 분리한 이유는, 프롬프트는 코드가 아닌 텍스트 자산이기 때문입니다. 코드 수정 없이 프롬프트만 편집할 수 있으며, 형식 문자열 `{placeholder}` 방식으로 동적 값을 주입합니다.

| 파일 | 플레이스홀더 | 주입 시점 |
|------|------------|---------|
| `system.txt` | 없음 | `BaseGenerator.__init__` |
| `conversation.txt` | `{function_specs}`, `{target_functions}` | `ConversationGenerator.build_messages` |
| `rejection.txt` | `{function_specs}` | `RejectionGenerator.build_messages` |

### renderer.py

`docs/qwen3_chat-template.jinja`를 `jinja2.FileSystemLoader`로 로드하여 렌더링합니다. `messages`와 `tools`를 받아 Qwen3 모델이 학습에 사용하는 포맷(`<|im_start|>`, `<tool_call>` 등)으로 변환합니다.

렌더링 시 `add_generation_prompt=False`로 설정하여 학습 데이터에 불필요한 프롬프트 suffix가 추가되지 않게 합니다.

### pipeline.py

CLI 진입점입니다. `argparse`로 인자를 파싱하고, 생성 유형에 따라 `ConversationGenerator` 또는 `RejectionGenerator`를 선택하여 N번 반복 실행합니다. 샘플별로 `.json`과 `.txt`를 쌍으로 저장하고, 개별 샘플 실패 시 로그를 남기고 계속 진행합니다.

---

## 설계 결정 사항

### 왜 function_specs를 프롬프트에 텍스트로 삽입하는가?

LLM에게 함수 목록을 system 메시지가 아닌 **user 프롬프트에 텍스트로 주입**합니다. 이는 LLM이 어떤 함수가 있는지 인식하고 적절히 활용하는 대화를 생성하게 하기 위한 데이터 생성 전략입니다. 실제 학습 데이터의 system 메시지에는 `CHATBOT_SYSTEM_PROMPT`가 들어갑니다.

### 왜 출력이 JSON과 TXT 두 가지인가?

- `.json`: messages 배열은 다른 렌더러나 템플릿으로 재처리할 수 있는 중간 결과물입니다.
- `.txt`: 모델 학습에 바로 사용할 수 있는 최종 포맷입니다.

두 파일을 동일한 stem으로 저장함으로써 검증 및 디버깅 시 쌍으로 열어볼 수 있습니다.

### 왜 _extractor.py에서 ast.parse를 사용하는가?

`docs/custom_functions.py`는 async 함수를 포함하며, import 시 외부 의존성이 필요할 수 있습니다. 런타임 실행 없이 **정적 분석만으로 스펙을 추출**하기 위해 AST 파싱을 선택했습니다.
