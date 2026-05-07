## 제약 조건

- `datagen/tool_specs.py` 함수 시그니처 변경 시 Rule 2·3 자동 반영 — 별도 수정 불필요하지만 검증 통과 여부는 반드시 확인
- `--purge` 실행은 .txt와 dataset.jsonl 레코드를 영구 삭제 — 사용자 명시 요청 시만 실행

## 이 폴더의 역할

datagen이 생성한 ChatML `.txt` 샘플을 4가지 규칙(format, schema, content)으로 검증한다. `datagen/tool_specs.py`를 직접 import해 함수 계약을 참조하므로 별도 스키마 파일이 없다.

## 디렉터리 지도

```
validate.py         진입점 — 디렉터리 순회 및 결과 출력
utils.py            파일 로딩, im 블록 파싱
rules/
  format.py         Rule 1: im_start/im_end 짝 검증
  schema.py         Rule 2·3: tool_call/tool_response 스키마 검증
  content.py        Rule 4: 사용자 발화 기반 추론 불가 파라미터(환각) 탐지
```

## 작업 흐름

규칙 수정 시:
1. `rules/` 대상 파일 읽기
2. 수정 후 샘플 디렉터리로 실행해 통과/실패 확인
3. 의도하지 않은 PASS/FAIL 변화 없는지 검증

## 도구

```bash
# 검증만
python -m datavalidator.validate --target_dir train_data/samples/

# 검증 + 실패 샘플 삭제 (명시적 요청 시만)
python -m datavalidator.validate \
    --target_dir train_data/samples/ \
    --purge \
    --dataset train_data/dataset.jsonl
```

## 도메인 컨텍스트

| 규칙 | 담당 파일 | 설명 |
|------|----------|------|
| Rule 1 | format.py | im_start/im_end depth 카운터로 짝 검증 |
| Rule 2 | schema.py | tool_call의 함수명·파라미터·타입을 tool_specs.py와 대조 |
| Rule 3 | schema.py | tool_response 반환값 타입을 직전 tool_call 함수 기준으로 검증 |
| Rule 4 | content.py | arguments 값이 사용자 발화에서 추론 가능한지 검증 |

Rule 1 실패 시 Rule 2·3은 스킵된다.

## 폴더별 규칙

- `rules/schema.py`는 `datagen/tool_specs.py`를 inspect.signature + get_type_hints로 파싱 — 함수 시그니처 변경 시 자동 반영
- 새 검증 규칙 추가 시 `validate.py`의 순회 루프에도 호출 추가 필요
