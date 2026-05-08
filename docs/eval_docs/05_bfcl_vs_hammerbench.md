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

## 2. BFCL Singleton의 역할

BFCL Singleton은 함수 호출 구조의 정확성을 평가하는 기준점이었다. 함수명, required 파라미터, 타입, 불필요한 파라미터 같은 구조 항목을 엄격하게 본다.

## 3. BFCL Multi-Turn의 역할

BFCL Multi-Turn은 구조 정확성을 대화 전체 성공 문제로 확장한다. 상태 정확성, minimal trajectory, 종료 조건을 포함한 절차 완주 여부가 중요하다.

## 4. HammerBench의 역할

HammerBench는 멀티턴 대화에서 실패 유형을 더 잘 보여주는 진단 도구로 이해했다. 함수명 오류, parameter hallucination, parameter missing, progress 저하 같은 문제를 turn 수준에서 읽기 쉽다.

## 5. 프로젝트 관점의 정리

이 비교를 통해 정리한 결론은 아래와 같았다.

- BFCL은 표준화된 함수 호출 성능 평가의 틀을 준다
- HammerBench는 실패를 더 세밀하게 분해해 해석할 수 있게 한다
- 현재 프로젝트는 실제 backend state를 재현하지 않았기 때문에 BFCL 멀티턴을 그대로 복제하지 않았다
- 대신 BFCL의 구조 정확성 철학과 HammerBench의 오류 분해 관점을 결합해 프로젝트용 평가 체계를 설계했다
