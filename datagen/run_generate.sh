#!/usr/bin/env bash
# datagen 전체 파이프라인 실행 스크립트
# 사용법 (llm-project 루트에서 실행): bash datagen/run_generate.sh

set -euo pipefail

# 경로
OUTPUT_DIR="synthetic_data"
BATCH_INPUT="${OUTPUT_DIR}/batch_input.jsonl"
STATUS_FILE="${OUTPUT_DIR}/batch_input_status.json"
RESULT_FILE="${OUTPUT_DIR}/result_lst.json"
DATASET_FILE="${OUTPUT_DIR}/dataset.jsonl"
SAMPLES_DIR="${OUTPUT_DIR}/samples"

# 파라미터
COUNT=10
SEED=42
POLL_INTERVAL=60

echo "[1/5] generate_batch → ${BATCH_INPUT}"
python -m datagen.generate_batch \
    --count  "${COUNT}" \
    --seed   "${SEED}" \
    --output "${BATCH_INPUT}"

echo "[2/5] submit_batch → 완료까지 폴링 대기 (${POLL_INTERVAL}초 간격)"
python -m datagen.submit_batch \
    --input         "${BATCH_INPUT}" \
    --output        "${STATUS_FILE}" \
    --wait \
    --poll-interval "${POLL_INTERVAL}"

echo "[3/5] retrieve_batch → ${RESULT_FILE}"
python -m datagen.retrieve_batch \
    --status-file "${STATUS_FILE}" \
    --output      "${RESULT_FILE}"

echo "[4/5] preprocess → ${DATASET_FILE}"
python -m datagen.preprocess \
    --input  "${RESULT_FILE}" \
    --output "${DATASET_FILE}" \
    --seed   "${SEED}"

echo "[5/5] render_txt → ${SAMPLES_DIR}/"
python -m datagen.render_txt \
    --input  "${DATASET_FILE}" \
    --output "${SAMPLES_DIR}"

echo "완료"
