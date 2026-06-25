# QLoRA Fine-tuning 성능 결과 보고서

> 작성일: 2026-05-08
> 대상 모델: Qwen2.5-7B-Base → QLoRA SFT (배달 앱 Function Calling)
> 평가 기준: Codex Modified `eval_data/dataset.jsonl` (현재 eval 데이터셋)

---

## 1. 개요

배달 앱 AI 상담사를 위한 멀티턴 Function Calling 파인튜닝 결과를 정리한다.  
베이스 모델(Qwen2.5-7B-Base)에 대해 QLoRA SFT를 적용한 뒤, 7단계 메트릭으로 tool calling 정확도를 평가했다.  
GPT-4o는 동일 조건에서의 참조 기준으로 함께 제시한다.

### 평가 조건

| 항목 | 값 |
| --- | --- |
| 평가 데이터셋 | Codex Modified `eval_data/dataset.jsonl` (최종 수정: 2026-04-02, commit `5d14715`) |
| 총 샘플 | 430 |
| Tool call 샘플 | 194 |
| Non-tool 샘플 | 236 |
| 대화(conversation) | 53 |
| 평가 턴 | 236 |

---

## 2. 모델별 성능 비교

### Tool Call 품질

| 지표 | GPT-4o | Base | Fine-tuned | Δ (vs Base) |
| --- | ---: | ---: | ---: | ---: |
| relevance_detection_acc | 79.07% | 86.28% | 90.23% | +3.95%p |
| format_compliance_acc | 97.20% | 95.14% | 96.97% | +1.83%p |
| function_matching_acc | 99.04% | 90.51% | 93.75% | +3.24%p |
| param_hallucination_acc | 100.00% | 99.19% | 100.00% | +0.81%p |
| required_params_acc | 100.00% | 100.00% | 100.00% | ±0.00%p |
| argument_type_acc | 100.00% | 100.00% | 100.00% | ±0.00%p |
| **argument_value_acc** | 64.08% | 56.91% | **82.00%** | **+25.09%p** |

### Multi-Turn 안정성

| 지표 | GPT-4o | Base | Fine-tuned | Δ (vs Base) |
| --- | ---: | ---: | ---: | ---: |
| **turn_level_accuracy** | 59.32% | 57.63% | **72.03%** | **+14.40%p** |
| **conversation_success_rate** | 26.42% | 32.08% | **33.96%** | **+1.89%p** |
| conversation_progress_rate | 62.01% | 60.35% | 72.27% | +11.92%p |
| first_failure_turn_avg | 0.26 | 0.31 | 1.09 | +0.78 |
| **error_cascade_rate** | 43.01% | 54.08% | **36.51%** | **-17.57%p** |

---

## 3. 학습 초기 모델 대비 방향성 비교

Fine-tuning 초기 최고 모델(LoRA 500 스텝)과 최종 모델의 방향성 변화를 정리한다.

> **한계**: LoRA 500 초기 수치는 `before_eval_dataset`(40개 대화, 2026-04-01 이전) 기준,
> Fine-tuned 최종 수치는 Codex Modified eval 데이터셋(53개 대화, commit `5d14715`) 기준이다.
> 평가셋 규모와 gold label이 달라 Δ 값의 산술적 의미가 없으므로 수치 차이가 아닌 방향성으로만 해석한다.

| 지표 | LoRA 500 초기 (`before_eval_dataset`) | Fine-tuned 최종 (Codex Modified) | 방향 |
| --- | ---: | ---: | :---: |
| argument_value_acc | 68.75% | **82.00%** | ↑ |
| turn_level_accuracy | 58.50% | **72.03%** | ↑ |
| conversation_success_rate | 7.50% | **33.96%** | ↑ |
| conversation_progress_rate | 60.05% | **72.27%** | ↑ |
| error_cascade_rate | 51.64% | **36.51%** | ↓ (개선) |

---

## 4. 핵심 요약

- **argument_value_acc** (파라미터 값 정확도): GPT-4o(64.08%) 대비 +17.92%p 우위. Base 대비 +25.09%p 상승.
- **turn_level_accuracy** (턴 단위 정확도): GPT-4o(59.32%) 대비 +12.71%p 우위. Base 대비 +14.40%p 상승.
- **conversation_success_rate** (대화 완주율): Base(32.08%) 대비 +1.89%p 상승. GPT-4o(26.42%) 대비 +7.54%p 우위. LoRA 500 초기(7.50%) 대비 큰 폭 상승 (평가셋 조건 상이, 방향성만 유효).
- **error_cascade_rate** (오류 연쇄율): GPT-4o(43.01%), Base(54.08%) 대비 모두 낮은 36.51%. 멀티턴에서 초기 오류가 연쇄되는 현상이 가장 적다.
- param_hallucination_acc, required_params_acc, argument_type_acc는 Fine-tuned와 GPT-4o에서 100%. Base는 param_hallucination_acc 99.19%.

---

## 5. 결론

QLoRA SFT 적용 후 Function Calling 전 축에서 베이스 모델 대비 의미 있는 성능 향상이 확인됐으며,  
주요 지표에서 GPT-4o를 상회하는 결과가 나타났다.  
특히 **파라미터 값 선택 정확도**와 **턴 단위 정확도**의 개선이 두드러지며,  
오류 연쇄율의 대폭 감소(-17.57%p)는 멀티턴 안정성이 실질적으로 높아졌음을 보여준다.
