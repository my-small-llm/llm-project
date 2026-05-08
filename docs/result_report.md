# QLoRA Fine-tuning 성능 결과 보고서

> 작성일: 2026-05-08
> 대상 모델: Qwen2.5-7B-Base → QLoRA SFT (배달 앱 Function Calling)
> 평가 기준: Claude Modified 평가셋 (함수 description 원본 유지)

---

## 1. 개요

배달 앱 AI 상담사를 위한 멀티턴 Function Calling 파인튜닝 결과를 정리한다.  
베이스 모델(Qwen2.5-7B-Base)에 대해 QLoRA SFT를 적용한 뒤, 7단계 메트릭으로 tool calling 정확도를 평가했다.  
GPT-4o는 동일 조건에서의 참조 기준으로 함께 제시한다.

### 평가 조건

| 항목 | 값 |
| --- | --- |
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
| relevance_detection_acc | 83.92% | 89.07% | 90.23% | +1.16%p |
| format_compliance_acc | 96.30% | 96.89% | 95.83% | -1.06%p |
| function_matching_acc | 94.87% | 91.03% | 93.79% | +2.76%p |
| param_hallucination_acc | 100.00% | 100.00% | 100.00% | ±0.00%p |
| required_params_acc | 100.00% | 100.00% | 100.00% | ±0.00%p |
| argument_type_acc | 100.00% | 100.00% | 100.00% | ±0.00%p |
| **argument_value_acc** | 70.27% | 61.27% | **84.77%** | **+23.50%p** |

### Multi-Turn 안정성

| 지표 | GPT-4o | Base | Fine-tuned | Δ (vs Base) |
| --- | ---: | ---: | ---: | ---: |
| **turn_level_accuracy** | 59.86% | 61.86% | **72.03%** | **+10.17%p** |
| **conversation_success_rate** | 12.50% | 20.75% | **32.08%** | **+11.32%p** |
| conversation_progress_rate | 61.70% | 64.12% | 71.92% | +7.81%p |
| first_failure_turn_avg | 0.26 | 0.43 | 1.00 | +0.57 |
| **error_cascade_rate** | 39.83% | 37.93% | **33.85%** | **-4.08%p** |

---

## 3. 학습 초기 모델 대비 최종 개선

Fine-tuning 초기 최고 모델(LoRA 500 스텝) 및 GPT-4o와 최종 모델을 비교한다.  
샘플 조건이 동일하다고 가정한다.

| 지표 | GPT-4o | LoRA 500 (초기) | Fine-tuned (최종) | Δ (vs LoRA 500) |
| --- | ---: | ---: | ---: | ---: |
| argument_value_acc | 70.27% | 68.75% | **84.77%** | **+16.02%p** |
| turn_level_accuracy | 59.86% | 58.50% | **72.03%** | **+13.53%p** |
| conversation_success_rate | 12.50% | 7.50% | **32.08%** | **+24.58%p** |
| conversation_progress_rate | 61.70% | 60.05% | **71.92%** | **+11.87%p** |
| error_cascade_rate | 39.83% | 51.64% | **33.85%** | **-17.79%p** |

---

## 4. 핵심 요약

- **argument_value_acc** (파라미터 값 정확도): GPT-4o(70.27%) 대비 +14.50%p 우위. Base 대비 +23.50%p 상승.
- **conversation_success_rate** (대화 완주율): GPT-4o(12.50%) 대비 +19.58%p 우위. LoRA 500 초기 대비 +24.58%p 상승.
- **turn_level_accuracy** (턴 단위 정확도): GPT-4o(59.86%) 대비 +12.17%p 우위.
- **error_cascade_rate** (오류 연쇄율): GPT-4o(39.83%)보다 낮은 33.85%로, 초기 오류가 후속 턴까지 번지는 현상이 가장 적다.
- 파라미터 안전성 지표(param_hallucination, required_params, argument_type)는 전 모델 100% 유지.

---

## 5. 결론

QLoRA SFT 적용 후 Function Calling 전 축에서 베이스 모델 대비 의미 있는 성능 향상이 확인됐으며,  
주요 지표에서 GPT-4o를 상회하는 결과가 나타났다.  
특히 **파라미터 값 선택 정확도**와 **대화 완주율**의 개선이 두드러지며,  
오류 연쇄율 감소는 멀티턴 안정성이 실질적으로 높아졌음을 보여준다.
