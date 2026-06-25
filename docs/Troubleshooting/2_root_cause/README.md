# 2. Root Cause

이 폴더는 `1_eval_discovery`에서 발견한 실패를 보고, 그 실패가 실제로 어디서 생겼는지 판정하는 단계다.

여기서는 실패 사례를 다시 나열하기보다, 원인을 `tool schema`, `datagen 규칙`, `train data 구조` 같은 시스템 구성요소 단위로 잘라서 본다. 수정 규칙과 최종 적용 계획은 `../3_fixes/`에서 다룬다.

## 읽기 순서

| 순서 | 문서 | 답하는 질문 |
| --- | --- | --- |
| 1 | `01_tool_schema_overdesign_review.md` | `argument_value` 실패 중 무엇이 함수 스키마 과설계이고, 무엇이 규칙 재정의 또는 보존 규약 문제인가? |
| 2 | `02_relevance_detection_root_cause.md` | `relevance_detection` 실패 중 datagen 규칙과 함수 설명 부족으로 설명되는 핵심 원인은 무엇인가? |
| 3 | `03_train_data_dataset_defect_report.md` | 개별 규칙 수정 이후에도 남는 문제를 보면, 더 나은 train data는 어떤 구조를 가져야 하는가? |

## 단계 경계

- 이 폴더의 산출물: 원인 판정, 책임 위치 구분, 수정이 필요한 규칙 축 식별
- 다음 단계의 산출물: 실제 규칙 변경, 스키마 단순화 결정, datagen 수정 계획
- 수정 결정 위치: `../3_fixes/`

## 핵심 흐름

- `1_eval_discovery`는 실패를 발견하고 분해했다.
- `2_root_cause`는 그 실패가 왜 생겼는지 판정한다.
- `3_fixes`는 판정된 원인에 대해 무엇을 바꿀지 결정한다.
- 특히 `01_tool_schema_overdesign_review.md`는 `argument_value` 축을 한 문장으로 끝내는 문서가 아니다.
  - `page/page_size/at/is_default`처럼 축소가 필요한 슬롯
  - `query/category`처럼 역할 경계 재정의가 필요한 슬롯
  - `special_request/delivery_note`처럼 원문 보존 규약 보강이 필요한 슬롯
  를 나눠서 본 뒤, 그 결과가 `3_fixes/01*`의 세부 결정 문서로 이어진다.
