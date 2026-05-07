## 제약 조건

- 분석 결과물(이미지, 텍스트)은 `--output_dir`로 지정한 디렉터리에만 저장 — 소스 파일 수정 금지
- HuggingFace 토크나이저 다운로드 필요 — 네트워크 없는 환경에서는 실행 불가

## 이 폴더의 역할

datagen이 생성한 JSONL 파일을 분석해 tool 분포, 토큰 수, 파라미터 커버리지 등 8가지 차트와 텍스트 리포트를 생성한다. 학습 전 데이터 품질을 시각적으로 확인하는 용도다.

## 디렉터리 지도

```
analyze.py     분석 로직 및 main() 진입점
__main__.py    python -m dataanalyzer 실행 위임
```

## 도구

```bash
python -m dataanalyzer \
    --target_dir train_data \
    --output_dir train_data \
    --model_name Qwen/Qwen2.5-7B-Instruct
```

출력물: `tool_distribution.png`, `sequential_calls.png`, `turn_count.png`, `total_tokens.png`, `token_by_role.png`, `tool_response_size.png`, `param_coverage.txt`, `summary.txt`

## 도메인 컨텍스트

- `datagen/config.py`의 `tools` 명세에서 optional 파라미터 목록을 가져온다 — 함수 스키마 변경 시 분석 결과도 자동 반영
- 한글 레이블을 위해 Noto Sans CJK KR 폰트를 자동 감지 (없으면 기본 폰트)
- 헤드리스 환경 대응을 위해 matplotlib Agg 백엔드 사용

## 폴더별 규칙

- `analyze.py`의 분석 함수는 순수 함수 형태 유지 — 파일 I/O는 `main()`에서만 수행
- 새 분석 항목 추가 시 `analyze.py`의 `main()` 실행 순서에 맞게 추가
