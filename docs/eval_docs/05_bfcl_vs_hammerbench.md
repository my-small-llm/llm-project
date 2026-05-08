> 이 문서는 BFCL과 HammerBench의 역할 차이를 정리한 핵심 근거 문서다.
> 현재 프로젝트용 정리 문서는 [docs/eval/02_eval_metric_report.md](/home/wonjun/llm-project/docs/eval/02_eval_metric_report.md:1) 이다.

# BFCL vs HammerBench

## 1. 전체 구조 한눈에 보기

| 구분 | BFCL Singleton | BFCL Multi-Turn | HammerBench |
| --- | --- | --- | --- |
| 평가 단위 | 단일 턴 | 대화 전체 | 턴 또는 snapshot |
| 핵심 질문 | 구조가 맞는가 | 대화가 완주되었는가 | 어디서 어떻게 틀렸는가 |
| 스키마 검증 | O | O | O |
| 상태 비교 | X | O | 선택적 |
| 경로 검증 | X | O | O |
| 점수 방식 | 0/1 | 0/1 성격이 강함 | 비율/분포 지표 |
| 디버깅 적합성 | 낮음 | 낮음 | 높음 |

## 1.1 지표 비교

| 지표 | 벤치마크 | 무엇을 측정하는가 |
| --- | --- | --- |
| AST Accuracy | BFCL | 함수명·인자·타입·값의 구조적 정확도 |
| Executable Accuracy | BFCL | 실제 실행 결과가 기대 결과와 일치하는지 |
| Relevance / Hallucination | BFCL | 호출 불필요 시 abstain 여부, tool hallucination 억제 |
| State-based Pass | BFCL Multi-Turn | 각 턴 후 backend 상태가 기대 상태와 일치하는지 |
| Func Acc | HammerBench | 함수명 선택 정확도 |
| PHR (Hallucination Rate) | HammerBench | 스키마 외 파라미터 생성 비율 |
| PMR (Missing Rate) | HammerBench | 필수 파라미터 누락 비율 |
| Args Acc | HammerBench | 함수명·파라미터명 모두 맞을 때 값까지 맞춘 비율 |
| PR (Progress Rate) | HammerBench | 첫 오류 전 연속 정답 턴 비율 |
| SR (Success Rate) | HammerBench | 전체 snapshot 중 정답 비율 |

## 2. 세 체계의 포함 관계

```
Singleton Validation
        ↓
Multi-Turn = Singleton + State + Trajectory
        ↓
HammerBench = Multi-Turn을 턴 단위로 분해 + 오류 유형 정량화
```

Multi-Turn은 Singleton 검사를 포함하면서 상태와 경로를 추가로 본다. HammerBench는 같은 대화를 0/1로 채점하지 않고 턴 단위로 쪼개 어디서 무너졌는지를 보여준다.

## 3. 같은 사례, 세 가지 결과

모델이 `prepare_checkout` 단계를 생략한 경우:

| 평가 체계 | 결과 |
| --- | --- |
| BFCL Singleton | 해당 턴 단독으로는 Pass (구조 정확) |
| BFCL Multi-Turn | 0점 (대화 전체 실패) |
| HammerBench | SR=0.67, PR=0.67, PMR>0 (2/3턴은 맞았고 3번째 턴에서 단계 누락) |

BFCL이 "실패"라고만 말하는 곳에서 HammerBench는 "어디서, 어떤 유형으로 실패했는지"를 준다.

## 4. 실무 적용 관점

| 목적 | 가장 적합한 체계 |
| --- | --- |
| 모델 구조 안정성 측정 | BFCL Singleton |
| 에이전트 완주율 평가 | BFCL Multi-Turn |
| 실패 원인 디버깅 | HammerBench |
| 외부 비교 기준 | BFCL |
| 모델 개선 방향 도출 | HammerBench |

## 5. BFCL Singleton의 역할

BFCL Singleton은 함수 호출 구조의 정확성을 평가하는 기준점이었다. 함수명, required 파라미터, 타입, 불필요한 파라미터 같은 구조 항목을 엄격하게 본다.

## 6. BFCL Multi-Turn의 역할

BFCL Multi-Turn은 구조 정확성을 대화 전체 성공 문제로 확장한다. 상태 정확성, minimal trajectory, 종료 조건을 포함한 절차 완주 여부가 중요하다.

## 7. HammerBench의 역할

HammerBench는 멀티턴 대화에서 실패 유형을 더 잘 보여주는 진단 도구로 이해했다. 함수명 오류, parameter hallucination, parameter missing, progress 저하 같은 문제를 turn 수준에서 읽기 쉽다.

## 8. 프로젝트 관점의 정리

이 비교를 통해 정리한 결론은 아래와 같았다.

- BFCL은 표준화된 함수 호출 성능 평가의 틀을 준다
- HammerBench는 실패를 더 세밀하게 분해해 해석할 수 있게 한다
- 현재 프로젝트는 실제 backend state를 재현하지 않았기 때문에 BFCL 멀티턴을 그대로 복제하지 않았다
- 대신 BFCL의 구조 정확성 철학과 HammerBench의 오류 분해 관점을 결합해 프로젝트용 평가 체계를 설계했다

한 줄 요약: **BFCL은 툴콜링 모델의 표준 시험지, HammerBench는 실제 대화에서 왜 툴콜링이 깨지는지 보는 현미경.**
