## 제약 조건

- `.env` 파일 읽기 금지 (OPENAI_API_KEY, WANDB_API_KEY 포함)
- 대화 내용·프롬프트·모델 응답 전문을 저장/표시/로그 출력 금지
- `datagen/tool_specs.py`의 함수 계약을 한쪽만 깨는 변경 금지 — datagen, datavalidator, evaluations 세 곳이 이 파일에 의존한다
- 사용자가 명시하지 않은 삭제, 초기화, 대량 포맷팅, 설정 덮어쓰기 금지
- 하위 `CLAUDE.md`가 이 파일보다 우선한다

## 프로젝트 소개

배달 앱 AI 상담사 파인튜닝 파이프라인. OpenAI Batch API로 멀티턴 function calling 데이터를 생성하고, Qwen2.5-7B-Instruct를 QLoRA SFT로 학습한 뒤 GT 히스토리 기반 7단계 메트릭으로 tool calling 정확도를 평가한다. 도구 호출 외 일반 API 서빙이나 프론트엔드는 포함하지 않는다.

## 디렉터리 지도

```
datagen/        데이터 생성 파이프라인 (Batch API → ChatML JSONL) — CLAUDE.md 있음
datavalidator/  생성 데이터 format/schema/content 검증 — CLAUDE.md 있음
dataanalyzer/   데이터셋 품질·분포 분석 및 시각화 — CLAUDE.md 있음
evaluations/    vLLM·API 추론 + 7단계 tool calling 메트릭 평가 — CLAUDE.md 있음
train/          QLoRA SFT 학습 파이프라인 — CLAUDE.md 있음
database/       schema.sql, seed.sql (정적 참조용)
docs/           설계 문서, 메트릭 리포트, 트러블슈팅 기록 (conventions/eval/data/references/Troubleshooting) — CLAUDE.md 있음
eval_data/      평가 기준 gold 데이터셋 (40개 대화, git-tracked)
pyproject.toml  Python 3.10.12, uv 의존성 관리
```

## 작업 흐름

1. 수정 대상 폴더의 `CLAUDE.md` 읽기
2. 관련 소스 파일 읽기 후 계획 수립
3. 구현
4. 해당 폴더의 도구 섹션 명령으로 검증

## 도구

```bash
# 환경 설정
uv python install 3.10.12
uv sync
source .venv/bin/activate

# 전체 lint (flake8, mypy 등 설정돼 있지 않으므로 python -c import로 빠른 확인)
python -c "import datagen, datavalidator, dataanalyzer, evaluations, train"

# 평가 실행 (GPU 필요)
python -m evaluations.runner \
    --model Qwen/Qwen2.5-7B-Instruct \
    --dataset eval_data/dataset.jsonl \
    --output eval_output
```

## 아키텍처

```
datagen (생성)
  └→ datavalidator (검증) → dataanalyzer (분석)
       └→ HuggingFace Hub (업로드)
            └→ train (QLoRA SFT)
                 └→ evaluations (tool calling 평가)
```

`datagen/tool_specs.py`는 함수 계약의 단일 원본(SSoT). 이 파일을 바꾸면 datavalidator(Rule 2·3)와 evaluations(tool_schemas)를 함께 검증해야 한다.

## 도메인 컨텍스트

| 용어 | 설명 |
|------|------|
| tool_call / tool_response | Qwen ChatML의 XML 태그로 감싼 함수 호출·응답 |
| sequential call | 한 user 발화에 assistant가 여러 tool_call을 연속 수행 |
| GT 히스토리 기반 평가 | 이전 턴 정답으로 컨텍스트를 채워 각 턴을 독립 평가 |
| QLoRA | 4-bit NF4 양자화 + LoRA 어댑터로 베이스 모델 미세조정 |
| ChatML | `<\|im_start\|>role\n...<\|im_end\|>` 형식 대화 포맷 |
| 싱글턴 | user 발화 1회 + 이에 대응하는 모든 assistant 출력의 묶음 |

## 개발 원칙

**Karpathy-first**: 코드를 건드리기 전 요구사항·가정·성공 기준을 먼저 확인한다.

TDD 적용 기준:
- 적용: 메트릭 로직, 검증 규칙, 데이터 전처리 변경, 회귀 위험 있는 리팩토링
- 선택적: 프롬프트·설정 튜닝, 분석 스크립트, 단발성 변환 스크립트

완료 기준: TDD 대상이면 테스트 통과, 그 외는 스크립트 직접 실행으로 동작 확인.

## 코딩 컨벤션

- Python 3.10, type hints 사용
- 기존 패턴 우선, 작은 변경 선호
- `tool_specs.py` 변경 시 datavalidator·evaluations 영향 반드시 함께 검토
- 의존성 변경 후 `uv lock` 재실행 → `pyproject.toml`, `uv.lock` 함께 커밋
