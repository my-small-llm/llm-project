# Commit Message Convention

## 형식

```
<type>(<scope>): <subject>  # scope 선택
<type>: <subject>

<body> (선택)

<footer> (선택)
```

## Type (필수)

| Type | 설명 |
|------|------|
| `feat` | 새로운 기능 추가 / 기존 기능 변경 |
| `fix` | 버그 수정 |
| `refactor` | 기능 변경 없는 코드 구조 개선 |
| `config` | 설정 파일 변경 (yaml, requirements.txt, .gitignore 등) |
| `docs` | 문서 관련 (README, 주석) |
| `chore` | 빌드, 스크립트 등 기타 잡무 |
| `exp` | 파이프라인과 무관한 탐색/실험 코드 |

## Scope (선택) - 도메인을 scope로 구분

| Scope | 설명 |
|-------|------|
| `data` | 데이터 수집, 전처리, BIO 태깅, schema 관련 |
| `training` | 모델 정의, 학습 루프, 하이퍼파라미터 관련 |
| `eval` | 평가 메트릭, 추론 관련 |
| `pipeline` | main.py, 전체 파이프라인 통합 관련 |
| `experiment` | 레포와 직접 연관 없는 실험/프로토타입 |

## 예시

```
feat(data): Massive 데이터셋 한국어 수집 스크립트 추가
feat(data): BIO 태깅 전처리 로직 구현
feat(training): EXAONE-3.5-7.8B QLoRA 모델 구현
feat(training): early stopping 콜백 추가
feat(eval): slot F1 score 평가 로직 추가
feat(eval): 실시간 추론 데모 스크립트 구현
feat(pipeline): 수집-학습-평가 통합 실행 기능 추가

fix(data): BIO 태깅 시 공백 토큰 누락 수정
fix(training): gradient accumulation 스텝 계산 오류 수정
fix(eval): intent accuracy 계산 시 분모 0 예외 처리

config(training): learning rate 2e-4 → 1e-4로 변경
config(data): schema.json에 새 intent 레이블 추가

refactor(training): dataset 로딩 로직 공통 유틸로 분리
docs: README에 실행 방법 추가
chore: run_train.sh 실행 권한 추가

exp: GLM-4-9B 추론 테스트 스크립트 추가
exp(experiment): Qwen3-8B 응답 비교 실험 스크립트 추가
exp(training): LoRA 파라미터 스윕 실험 스크립트 추가
```

## 규칙

1. subject는 50자 이내, 한국어 또는 영어 통일
2. type과 scope는 소문자로 작성
3. subject 끝에 마침표 금지
4. body가 필요한 경우 빈 줄로 구분하여 상세 내용 기술
5. scope가 명확하면 사용하고, 해당사항이 없으면 생략 가능
6. 파이프라인과 무관한 실험은 `exp` 타입을 사용하고, 레포와 직접 연관이 없으면 scope로 `experiment` 사용을 권장
