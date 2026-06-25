## 아규먼트

- `--model_name` : 토크나이저에 사용할 모델 이름
- `--target_dir`  : 분석할 `*.jsonl` 파일이 위치한 디렉토리 (preprocess.py 출력 기준)
- `--output_dir`  : 히스토그램 이미지 및 분석 .txt 파일이 저장될 디렉토리

## 분석 항목

### 기본 분포

- tool 호출 분포 히스토그램
- sequential call 수 분포 히스토그램
- 대화 turn 수 분포 히스토그램
- 대화당 총 토큰 수 분포 히스토그램

### 파라미터 커버리지

- 함수별 optional 파라미터 사용률
  (special_request, min_rating, sort, delivery_note 등)
- 파라미터 값 다양성: 파라미터별 unique value 비율

### 토큰 길이 세분화

- role별 토큰 분포 (user / assistant / tool_response JSON 각각)
- tool_response JSON 크기 분포: 함수별 평균 토큰 수
