# dataanalyzer

학습 데이터셋의 품질과 분포를 시각적으로 분석하는 모듈이다.
`datagen/preprocess.py`가 생성한 `*.jsonl` 파일을 입력으로 받아 8가지 분석을 수행하고, 차트 이미지와 텍스트 리포트를 출력한다.

## 파일 구성

```
dataanalyzer/
├── analyze.py     # 분석 로직 및 main() 진입점
├── __main__.py    # python -m dataanalyzer 실행 지원
└── output/        # 생성된 분석 결과물 (이미지·텍스트)
```

### `analyze.py`

모듈의 핵심 파일. 파싱 유틸, 분석 함수, 플롯 함수, 텍스트 리포트 함수, `main()`으로 구성된다.

#### 파싱 유틸

| 함수 | 설명 |
|------|------|
| `load_records(target_dir)` | 디렉토리 내 모든 `*.jsonl`을 읽어 `messages` 키가 있는 레코드만 반환 |
| `_parse_tool_call(content)` | `<tool_call>...</tool_call>` 블록을 파싱해 dict 반환 |
| `_parse_tool_response_raw(content)` | `<tool_response>...</tool_response>` 블록의 원문 문자열 반환 |
| `_get_optional_params()` | `datagen/config.py`의 `tools` 명세에서 함수별 optional 파라미터 목록 추출 |

#### 분석 함수

| 함수 | 설명 | 출력 |
|------|------|------|
| `analyze_tool_distribution(records)` | 함수별 총 호출 횟수 집계 | `dict[str, int]` |
| `analyze_sequential_calls(records)` | 대화당 `tool_call → tool_response` 연속 쌍의 최대 체인 길이 | `list[int]` |
| `analyze_turn_counts(records)` | 대화당 사용자 일반 발화 수 (`tool_response` 포함 user 메시지는 제외) | `list[int]` |
| `analyze_total_tokens(records, tokenizer)` | 대화당 전체 토큰 수 (`system_prompt` + 모든 메시지 합산) | `list[int]` |
| `analyze_param_coverage(records)` | 함수별 optional 파라미터의 사용률과 unique value 비율 | `(usage_rate, unique_ratio)` |
| `analyze_token_by_role(records, tokenizer)` | `user_plain` / `assistant_plain` / `tool_call` / `tool_response` 4가지 역할별 토큰 수 분포 | `dict[str, list[int]]` |
| `analyze_tool_response_size(records, tokenizer)` | 함수별 `tool_response` 토큰 수 분포 | `dict[str, list[int]]` |

#### 플롯 함수

| 함수 | 차트 유형 | 용도 |
|------|----------|------|
| `_save_bar(data, ...)` | 막대 그래프 | 함수별 호출 횟수 등 카테고리형 데이터 |
| `_save_hist(values, ...)` | 히스토그램 | 연속값 분포 (토큰 수 등) |
| `_save_int_bar(values, ...)` | 정수 전용 막대 그래프 | turn 수, sequential call 수처럼 값 종류가 적은 정수 분포 |
| `_save_bar_role(buckets, ...)` | 역할별 평균 토큰 막대 그래프 | role별 평균 토큰 수 비교 |
| `_save_boxplot(data, ...)` | 박스 플롯 | 함수별 tool_response 크기의 분포 및 이상치 |

#### 텍스트 리포트 함수

| 함수 | 출력 파일 | 내용 |
|------|----------|------|
| `write_param_coverage_txt(usage_rate, unique_ratio, path)` | `param_coverage.txt` | 함수별 optional 파라미터의 사용률(%) 및 unique값 비율(%) |
| `write_summary_txt(n_records, token_counts, path)` | `summary.txt` | 대화 수, 총/평균/최소/최대 토큰 수 |

### `__main__.py`

```python
from dataanalyzer.analyze import main
main()
```

`python -m dataanalyzer` 형태로 실행할 수 있도록 `analyze.main()`을 위임한다.

## 실행 방법

```bash
python -m dataanalyzer.analyze \
    --target_dir eval_data \
    --output_dir dataanalyzer/output \
    --model_name Qwen/Qwen2.5-7B-Instruct
```

또는

```bash
python -m dataanalyzer \
    --target_dir eval_data \
    --output_dir dataanalyzer/output \
    --model_name Qwen/Qwen2.5-7B-Instruct
```

### 인수

| 인수 | 필수 | 설명 |
|------|------|------|
| `--target_dir` | O | 분석할 `*.jsonl` 파일이 위치한 디렉토리 |
| `--output_dir` | O | 차트 이미지 및 텍스트 리포트가 저장될 디렉토리 |
| `--model_name` | O | 토큰 수 계산에 사용할 HuggingFace 토크나이저 모델 이름 |

## 출력 결과물

| 파일 | 유형 | 설명 |
|------|------|------|
| `tool_distribution.png` | 막대 그래프 | 11개 함수별 호출 횟수 분포 |
| `sequential_calls.png` | 막대 그래프 | 대화당 최대 sequential tool_call 체인 길이 분포 |
| `turn_count.png` | 막대 그래프 | 대화당 사용자 발화 turn 수 분포 |
| `total_tokens.png` | 히스토그램 | 대화당 총 토큰 수 분포 (평균값 빨간 점선 표시) |
| `token_by_role.png` | 막대 그래프 | user_plain / assistant_plain / tool_call / tool_response 역할별 평균 토큰 수 |
| `tool_response_size.png` | 박스 플롯 | 함수별 tool_response JSON의 토큰 수 분포 및 이상치 |
| `param_coverage.txt` | 텍스트 | 함수별 optional 파라미터 사용률 및 unique값 비율 |
| `summary.txt` | 텍스트 | 전체 데이터셋 토큰 통계 요약 |

## 의존성

- `datagen/config.py`: `tools` 명세에서 optional 파라미터 정보를 가져온다. 함수 스키마가 변경되면 분석 결과도 자동으로 반영된다.
- `transformers.AutoTokenizer`: 토큰 수 계산에 사용. `transformers` 패키지가 없으면 실행 불가.
- `matplotlib`: 차트 생성. 헤드리스 환경을 위해 `Agg` 백엔드를 사용하며, 한글 레이블을 위해 Noto Sans CJK KR 폰트를 자동 감지한다.

## 분석 흐름

```
1. JSONL 로드          load_records()
2. 토크나이저 로드      AutoTokenizer.from_pretrained()
3. tool 분포           analyze_tool_distribution() → tool_distribution.png
4. sequential call    analyze_sequential_calls()  → sequential_calls.png
5. turn 수             analyze_turn_counts()       → turn_count.png
6. 총 토큰 수          analyze_total_tokens()      → total_tokens.png, summary.txt
7. 파라미터 커버리지   analyze_param_coverage()    → param_coverage.txt
8. 토큰 세분화         analyze_token_by_role()     → token_by_role.png
                       analyze_tool_response_size() → tool_response_size.png
```
