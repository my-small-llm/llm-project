# llm-project

## Python Version

- Python `3.10.11`

프로젝트 설정의 최소 요구 버전은 `>=3.10`이지만, 현재 `requirements.txt` 검증은 Python `3.10.11`에서 완료했다.

## Environment Setup

`uv`로 가상환경을 만들고 `requirements.txt` 기준으로 설치한다.

```bash
uv venv --python 3.10.11
source venv/bin/activate
uv pip install -r requirements.txt
```

## Evaluation Run Example

```bash
python -m evaluations.runner \
    --model Qwen/Qwen2.5-7B-Instruct \
    --dataset eval_data/dataset.jsonl \
    --output eval_output
```

## Notes

- `evaluations.runner`는 `vllm`을 사용하므로 GPU 환경과 CUDA 런타임이 필요하다.
- `requirements.txt` 기준으로 새 `uv` 가상환경에서 import 및 `python -m evaluations.runner --help` 실행을 확인했다.
