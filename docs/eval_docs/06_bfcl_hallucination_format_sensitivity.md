> 이 문서는 BFCL hallucination 측정과 format sensitivity 평가를 정리한 핵심 근거 문서다.
> 현재 프로젝트용 정리 문서는 [docs/eval/02_eval_metric_report.md](/home/wonjun/llm-project/docs/eval/02_eval_metric_report.md:1) 이다.

# BFCL Hallucination & Format Sensitivity

## 1. Hallucination 측정

### 1.1 정의

BFCL 공식 문서에 따르면 hallucination은 두 가지 경우에 판정된다.

- **존재하지 않는 함수 호출**: tool list에 없는 함수를 호출할 때
- **스키마에 없는 파라미터 생성**: 함수 문서에 정의되지 않은 argument를 생성할 때

```
If API_call ∉ Valid_API_List → Hallucination
If parameter ∉ Function_Documentation → Hallucination
```

### 1.2 판정 방식

모델 출력을 AST로 파싱한 뒤, valid API call 목록과 AST subtree matching으로 비교한다. 일치하지 않으면 hallucination으로 flag한다.

### 1.3 점수 반영

공식 문서는 hallucination을 별도 rate 산식으로 고정하지 않고, 리더보드 성능의 구성 요소로 반영한다. relevance detection(호출 불필요 시 abstain)과 연결되어 측정된다.

---

## 2. Format Sensitivity (BFCL V4)

### 2.1 정의

프롬프트 형식, 함수 문서 형식, 출력 형식이 변경될 때 모델 정확도가 얼마나 달라지는지를 측정한다. 구조는 맞아도 형식 변화에 취약한 모델을 잡아낸다.

### 2.2 실험 설계

- 기존 싱글턴 데이터에서 200개 엔트리 선택
- 동일한 문제에 대해 다양한 형식 variation 생성
- 각 variation에서 accuracy 측정

variation 표기:

```
{function_doc_format} -> {return_format}, {has_tool_call_tag}
```

### 2.3 측정 축

| 축 | 설명 |
| --- | --- |
| return format | 출력 형식(JSON, XML 등)을 바꿨을 때 정확도 변화 |
| function doc format | 함수 문서 서술 방식을 바꿨을 때 정확도 변화 |
| toolcall tag | tool call 태그 유무에 따른 정확도 변화 |

### 2.4 점수 계산

```
Accuracy(variation) = Correct / 200

Average Accuracy(return_format=r)
  = mean(variations with r, markdown/experimental 제외)
```

doc_format, toolcall_tag도 동일 방식으로 평균을 낸다.

---

## 3. 이 문서에서 얻은 결론

hallucination 측정은 현재 프로젝트의 `param_hallucination` 지표와 직접 연결된다. format sensitivity는 현재 프로젝트에서 직접 구현하지 않았지만, Qwen ChatML 포맷과 tool call 태그 구조를 고정해야 하는 이유를 설명하는 근거가 된다.
