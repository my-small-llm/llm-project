## 제약 조건

- 실제 대화 내용(프롬프트 전문, 모델 응답 전문) 문서에 포함 금지
- 현재 코드와 불일치하는 오래된 설계 문서는 파일 상단에 `> ⚠ 이 문서는 구버전입니다.` 표시 또는 삭제

## 이 폴더의 역할

프로젝트 설계 문서, 평가 계획, 메트릭 리포트, 트러블슈팅 기록을 담는다. 코드 변경의 근거와 이력을 보존하고, 코드만으로 파악하기 어려운 의사결정 맥락을 제공한다.

## 디렉터리 지도

```
conventions/
  branch_naming_convention.md   브랜치 네이밍 규칙
  commit_message_convention.md  커밋 메시지 규칙
eval/
  01_eval_problem_definition.md    왜 평가를 다시 설계했는지 설명하는 문제 정의 문서
  02_eval_metric_report.md         BFCL·HammerBench 조사와 평가 축 학습 정리
  03_eval_plan.md                  현재 프로젝트용 평가 프레임워크 설계 기준
  04_metric_issue_resolution_workflow.md  평가 결과를 수정 루프로 연결하는 절차
eval_docs/
  01_bfcl_overview.md              BFCL 전체 평가 축 개요
  02_bfcl_single_turn.md           BFCL single-turn 구조 정확성 평가 정리
  03_bfcl_multi_turn.md            BFCL multi-turn 상태·경로 평가 정리
  04_hammerbench_overview.md       HammerBench의 snapshot 기반 오류 분석 정리
  05_bfcl_vs_hammerbench.md        BFCL과 HammerBench의 역할 차이 비교
data/
  api_functions.md              배달 앱 함수 API 명세
  data_change_log.md            데이터셋 버전 변경 이력
references/
  harness_engineering_problem_definition.md  하네스 문제 정의
  qwen3_chat-template.jinja     Qwen3 chat template 참조용
result_report.md                QLoRA 파인튜닝 최종 성능 결과 보고서
Troubleshooting/                이슈 분석 및 의사결정 기록 (README.md에 읽기 순서 정리)
  1_eval_discovery/             평가 지표 하락 발견 및 실패 케이스 분석
    README.md                   1단계 문서 읽기 순서와 단계 경계
    01_multiturn_100_vs_500_discovery.md
                                LoRA 100 대비 LoRA 500 멀티턴 지표 하락 최초 발견
    02_hyperparameter_model_comparison_unmodified_eval.md
                                하이퍼파라미터별 성능 비교와 실패 축 분리 판단
    03_relevance_detection_failure_report.md
                                tool/no-tool 경계 실패 분석
    04_function_matching_failure_report.md
                                함수 선택 실패와 데이터셋 라벨 문제 분리
    05_argument_value_failure_report.md
                                인자값 보존/슬롯 복원 실패 지도
    hypothesis_notes_from_multiturn_100_vs_500.md
                                01번에서 분리한 가설 보관용 메모
  2_root_cause/                 데이터·스키마 결함 원인 분석 및 결정
  3_fixes/                      파라미터별 수정 결정 및 적용
```

## 작업 흐름

- 코드 변경 시 관련 문서(특히 `03_eval_plan.md`, `api_functions.md`)와 불일치 발생 여부 확인
- 새 트러블슈팅 사례는 `Troubleshooting/`에 파일로 추가
- 문서 수정 시 코드와 동기화 여부를 먼저 확인한 뒤 작성
- `1_eval_discovery/` 문서를 정리할 때는 발견 → 하이퍼파라미터 확인 → 실제 실패 데이터 확인 순서를 유지
- `1_eval_discovery/`에서는 원인 확정이나 수정 결정을 하지 않고, 실패 유형·대표 샘플·다음 질문까지만 정리
- 원인 판단은 `2_root_cause/`, 수정 결정과 적용 내역은 `3_fixes/`에 둔다
- `Troubleshooting/README.md`는 상위 읽기 순서와 단계 연결 기준 문서로 유지한다
- `2_root_cause/01_tool_schema_overdesign_review.md`는 `argument_value` 전체를 단일 원인으로 환원하는 문서가 아니다
  - 이 문서는 무엇이 스키마 축소 대상인지, 무엇이 규칙 재정의 대상인지, 무엇이 학습/보존 규약 문제인지를 가르는 역할을 맡는다
  - 특히 `search_restaurants`는 `3_fixes/01*`로 이어지며, 여기서 보조 제어 슬롯 단순화와 `query/category` 경계 재정의를 나눠 다룬다

## 폴더별 규칙

- `Troubleshooting/`의 파일은 의사결정 근거를 담는다 — 현재 코드에서 이미 해결된 내용이라도 삭제하지 않고 유지
- `Troubleshooting/1_eval_discovery/`의 메인 문서는 `01_`, `02_`처럼 읽기 순서 번호를 붙인다
- 메인 흐름에서 분리한 가설·메모는 `hypothesis_` 또는 `notes_` 접두어를 사용하고, README의 메인 순서에는 넣지 않는다
- `Troubleshooting/2_root_cause/` 문서는 원인 분류 문서다
  - "축소 대상", "규칙 재정의 대상", "학습/평가 규약 보강 대상"을 구분해서 쓴다
- `Troubleshooting/3_fixes/` 문서는 실제 변경 결정을 담는다
  - 하나의 실패 축이라도 필요하면 여러 문서로 쪼개고, 상위 문서에서 하위 결정 문서로 왜 갈라지는지 설명한다
- `03_eval_plan.md`는 `evaluations/`의 설계 기준 문서 — 평가 로직 변경 시 함께 업데이트
- 문서에 코드 경로를 언급할 때는 모듈 경로(예: `datagen/tool_specs.py`) 형식 사용
