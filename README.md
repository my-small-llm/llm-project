# llm-project

## Python Version

- Python `3.10.12`

이 저장소는 Python `3.10.x`를 기준으로 관리하며, 현재 작업 환경은 Python `3.10.12`다.

## Environment Setup

기본 설치는 커밋된 `uv.lock`을 사용하는 `uv sync` 기준이다.

```bash
uv python install 3.10.12
uv sync
source .venv/bin/activate
```

`requirements.txt`는 보조 설치 경로로 유지하지만, 새 환경을 재현할 때는 `uv.lock`과 `pyproject.toml`을 함께 사용하는 방법을 우선 권장한다.

## Evaluation Run Example

```bash
python -m evaluations.runner \
    --model Qwen/Qwen2.5-7B-Instruct \
    --dataset eval_data/dataset.jsonl \
    --output eval_output
```

## Notes

- `evaluations.runner`는 `vllm`을 사용하므로 GPU 환경과 CUDA 런타임이 필요하다.
- 의존성 변경 후에는 `uv lock`을 다시 실행한 뒤 `pyproject.toml`, `uv.lock`, `requirements.txt`를 함께 커밋하는 것을 권장한다.
