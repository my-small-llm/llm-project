> 이 문서는 평가 프레임워크 조사를 위한 핵심 근거 문서다.
> 현재 프로젝트용 정리 문서는 [docs/eval/02_eval_metric_report.md](/home/wonjun/llm-project/docs/eval/02_eval_metric_report.md:1) 이다.

# BFCL 개요

BFCL은 function calling 모델의 성능을 표준화된 방식으로 비교하기 위한 벤치마크다. 이 문서는 BFCL이 어떤 평가 축으로 구성되어 있는지 빠르게 정리하기 위한 조사 노트다.

## 공식적으로 중요하게 본 평가 축

조사 시점 기준으로 BFCL에서 반복적으로 등장한 핵심 축은 아래와 같았다.

- Singleton Metrics
- Multi-Turn Metrics
- Format Sensitivity
- Hallucination / Accuracy Stability

이 중 현재 프로젝트 평가 설계에 가장 직접적으로 영향을 준 것은 singleton과 multi-turn이다.

## 관련 세부 문서

- [02_bfcl_single_turn.md](/home/wonjun/llm-project/docs/eval_docs/02_bfcl_single_turn.md:1)
- [03_bfcl_multi_turn.md](/home/wonjun/llm-project/docs/eval_docs/03_bfcl_multi_turn.md:1)
- [06_bfcl_hallucination_format_sensitivity.md](/home/wonjun/llm-project/docs/eval_docs/06_bfcl_hallucination_format_sensitivity.md:1)

## 이 문서의 의미

초기 조사 흐름에서 BFCL은 가장 먼저 접한 대표 벤치마크였다. 이후 singleton과 multi-turn을 따로 정리하면서, `구조 정확성`과 `대화 전체 성공`을 분리해서 봐야 한다는 감각을 얻게 되었다.
