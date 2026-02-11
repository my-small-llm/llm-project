# Branch Naming Convention

이 문서는 브랜치 이름 규칙을 정리합니다. 커밋 컨벤션(`docs/commit_message_convention.md`)의 `type`/`scope` 개념을 브랜치에도 동일하게 적용합니다.

## 형식

```
<type>/<scope>-<subject>
<type>/<subject>                 # scope 생략 가능
```

- 모든 요소는 소문자 사용
- 공백 금지, 단어 구분은 `-` 사용
- 의미 없는 중복 금지 (예: `exp/experiments` 지양)

## Type (필수)

커밋 메시지의 `type`과 동일합니다.

| Type | 설명 |
|------|------|
| `feat` | 새로운 기능 추가 / 기존 기능 변경 |
| `fix` | 버그 수정 |
| `refactor` | 기능 변경 없는 코드 구조 개선 |
| `config` | 설정 파일 변경 |
| `docs` | 문서 관련 |
| `chore` | 빌드, 스크립트 등 기타 잡무 |
| `exp` | 파이프라인과 무관한 탐색/실험 |

## Scope (선택)

커밋 메시지의 `scope`와 동일합니다.

| Scope | 설명 |
|-------|------|
| `data` | 데이터 수집, 전처리, BIO 태깅, schema 관련 |
| `training` | 모델 정의, 학습 루프, 하이퍼파라미터 관련 |
| `eval` | 평가 메트릭, 추론 관련 |
| `pipeline` | main.py, 전체 파이프라인 통합 관련 |
| `experiment` | 레포와 직접 연관 없는 실험/프로토타입 |

## Subject 작성 규칙

- 작업 내용을 2~4개 단어로 요약
- 동사 대신 명사/구문 권장 (예: `lora-sweep`, `schema-update`)
- 지나치게 광범위한 단어는 지양 (`misc`, `temp`, `test` 등)

## 예시

```
feat/data-collector
feat/training-lora
fix/eval-f1-zero
refactor/training-dataloader
config/training-lr-1e-4
docs/branch-convention
chore/run-scripts
exp/experiment-qwen3-compare
exp/training-lora-sweep
```

## 권장 분기 기준

- 기본 작업 브랜치는 `dev`에서 분기
- 파이프라인과 무관한 실험은 `exp/` + 필요 시 `experiment` scope 사용

