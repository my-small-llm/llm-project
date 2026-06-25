# RTX 4090 (24GB) Qwen2.5-7B VRAM 종합 분석

RTX 4090(24GB VRAM) 단일 GPU 환경에서 Qwen2.5-7B(7.6B 파라미터, Vocab 152,064)를 긴 시퀀스(`max_seq_length=8192`)로 QLoRA SFT 학습할 때 발생한 OOM 문제와 해결 과정을 기록한 기술 문서이다.

학습 시 GPU 내부에서 **어떤 텐서가 어떤 용도로 VRAM을 차지하는지** 분해하고, LoRA와 QLoRA의 차이, 메모리 단편화를 억제하는 allocator 튜닝의 효과를 시퀀스 길이별로 비교 분석한다.

---

## 1. 문제 정의

### 목표

- **모델**: Qwen2.5-7B-Instruct (7.6B params, GQA, Vocab 152,064)
- **GPU**: NVIDIA RTX 4090 24GB, 단일 GPU
- **학습 방식**: QLoRA(NF4) + SFT
- **시퀀스 길이**: `max_seq_length=8192`

### OOM 발생 조건

| 조건                               | 결과                              |
| ---------------------------------- | --------------------------------- |
| LoRA(bf16) + seq=8192              | 모델 로드만으로 14.2GB, 학습 불가 |
| QLoRA + seq=8192, allocator 기본값 | backward 중 OOM 발생              |
| QLoRA + seq=4096, allocator 기본값 | 동작하나 Reserved 낭비 과다       |

QLoRA를 사용하더라도 `seq=8192`에서는 allocator fragmentation으로 인한 OOM이 재현되었다.

---

## 2. 재현 환경

### 하드웨어 및 소프트웨어

| 항목          | 값                           |
| ------------- | ---------------------------- |
| GPU           | NVIDIA GeForce RTX 4090 24GB |
| NVIDIA Driver | 580.126.09                   |
| CUDA / cuDNN  | 사용 환경에 따라 확인 필요   |
| PyTorch       | 사용 환경에 따라 확인 필요   |
| Transformers  | 사용 환경에 따라 확인 필요   |
| PEFT          | 사용 환경에 따라 확인 필요   |
| bitsandbytes  | 사용 환경에 따라 확인 필요   |
| TRL           | 사용 환경에 따라 확인 필요   |

> **주의**: VRAM 사용량은 PyTorch, CUDA, bitsandbytes 버전에 따라 달라질 수 있다.
> 본 문서의 수치를 재현하려면 동일 버전 조합을 사용해야 한다.

### 학습 하이퍼파라미터

`train/config.py` 기준:

| 파라미터                    | 값                         | 비고                             |
| --------------------------- | -------------------------- | -------------------------------- |
| micro batch size            | 1                          | `per_device_train_batch_size`    |
| gradient accumulation steps | 2                          | effective batch = 2              |
| optimizer                   | `paged_adamw_8bit`         | 8-bit paged optimizer            |
| gradient checkpointing      | ✅ 사용                     | activation 메모리 절감           |
| precision                   | bf16                       | `bf16=True`                      |
| QLoRA quant type            | NF4                        | `bnb_4bit_quant_type="nf4"`      |
| double quantization         | ✅ 사용                     | `bnb_4bit_use_double_quant=True` |
| LoRA rank / alpha           | r=8 / α=32                 |                                  |
| LoRA target modules         | q, k, v, o_proj            | GQA 구조                         |
| FlashAttention 2            | 사용 환경에 따라 확인 필요 | attention 메모리에 직접 영향     |
| sequence packing            | 미사용                     | padding to max length            |
| `use_cache`                 | 학습 시 자동 비활성        | Trainer 내부 처리                |

### 메모리 측정 지표 정의

본 문서에서 사용하는 메모리 수치는 다음과 같은 서로 다른 의미를 가진다.

| 지표                                | 의미                                | 측정 도구 | 측정 시점                       |
| ----------------------------------- | ----------------------------------- | --------- | ------------------------------- |
| Theoretical Tensor Size             | dtype·shape 기반 이론 계산치        | 수식      | forward/backward 특정 연산 직후 |
| `torch.cuda.memory_allocated()`     | 실제 활성 tensor가 점유 중인 메모리 | PyTorch   | step 내 특정 지점               |
| `torch.cuda.memory_reserved()`      | allocator cache 포함 예약 메모리    | PyTorch   | step 내 특정 지점               |
| `torch.cuda.max_memory_allocated()` | step 동안 peak allocated            | PyTorch   | step 종료 후                    |
| `torch.cuda.max_memory_reserved()`  | step 동안 peak reserved             | PyTorch   | step 종료 후                    |
| `nvidia-smi`                        | 프로세스 전체 GPU memory usage      | driver    | sampling 시점                   |

> 본 문서의 `nvidia-smi` 수치는 **학습 진행 중 관찰된 값**이며, `Allocated` 및 `Reserved` 수치는 **이론 계산치와 nvidia-smi 역산을 혼합**한 근사값이다.
> 향후 정밀 검증 시에는 step별 `max_memory_allocated/reserved`를 직접 기록하는 것을 권장한다.

---

## 3. 메모리 구성 요소 분해

학습 루프가 실행될 때, GPU VRAM에는 크게 5가지 종류의 메모리가 할당된다.

### ① 베이스 모델 가중치 (고정 비용)

모델 파라미터를 GPU에 올리는 기본 공간이다.

- **LoRA (bf16)**: 7.6B × 2 bytes = **약 14.2 GB** 고정. 24GB 중 60%를 모델 로드만으로 소진.
- **QLoRA (NF4 4-bit)**: 7.6B × 0.5 bytes ≈ **약 3.5 GB**로 축소. double quantization 적용 시 추가 절감.

이 차이(10.7GB)가 QLoRA 전환의 핵심 근거이다.

### ② LoRA 어댑터 가중치 & 옵티마이저 상태 (고정 비용)

원본 가중치는 동결(freeze)하고, LoRA adapter의 학습 가능 파라미터만 갱신한다.

- Qwen2.5-7B는 **GQA(Grouped Query Attention)** 구조이므로, `q, k, v, o_proj` 전체를 LoRA 대상으로 열어도 학습 가능 파라미터는 약 **500만 개** 수준으로 적다.
- 파라미터(bf16) + gradient(bf16) + optimizer 상태(8-bit) 합산 ≈ **약 30 MB**.

> LoRA trainable parameter는 전체 VRAM에서 지배적이지 않다.
> 다만 절대 크기는 optimizer 구현(`paged_adamw_8bit`, `adamw_torch`, `fused adamw` 등)에 따라 달라진다.
> 본 실험에서는 `paged_adamw_8bit`를 사용했으며, master weight 복사본은 생성되지 않는다.

### ③ Logits 텐서 및 Gradient (변동 비용 — 핵심 병목)

OOM의 **주된 원인으로 관찰된** 항목이다.

Logits는 모델이 vocab 전체(152,064개)에 대해 다음 토큰 확률을 출력하는 최종 행렬이다.
backward 시 loss를 계산하려면 forward에서 생성된 logits 텐서와 해당 gradient가 **동시에 GPU 메모리에 상주(peak)**해야 한다.

- **계산식**: `B × T × V × dtype_size`
  - B = micro batch size (본 실험: 1)
  - T = sequence length
  - V = vocab size (152,064)
  - dtype_size = loss 계산 시 dtype에 따라 결정

> logits 메모리는 `batch × seq × vocab × dtype_size`에 비례하며,
> 실제 peak는 loss 계산 구현 방식(upcast 여부, fused cross entropy, chunked loss 등)에 따라 달라진다.
> 대형 vocab(152k)에서는 이 항이 전체 peak VRAM의 핵심 병목이 되기 쉽다.

**본 실험 조건에서의 근사치** (float32 기준, logits + gradient 동시 상주 시):

| seq_length | logits 텐서 | gradient | **peak 합산** |
| :--------: | :---------: | :------: | :-----------: |
|    4096    |   ~2.3 GB   | ~2.3 GB  |  **~4.6 GB**  |
|    8192    |   ~4.6 GB   | ~4.6 GB  |  **~9.2 GB**  |

시퀀스가 2배가 되면 logits peak도 정확히 2배가 된다. 이것이 `seq=8192`에서 OOM이 발생하는 구조적 원인이다.

### ④ Activations (활성화 중간값 버퍼) (변동 비용)

backward를 위해 forward 시 각 레이어의 중간 결과를 보존해야 한다.

- **Gradient Checkpointing**을 사용하면 모든 중간값을 저장하는 대신 **레이어 입력값만 저장**하고, 필요 시 재계산(recompute)한다. 메모리와 연산 시간의 트레이드오프이다.
- 본 실험에서는 gradient checkpointing을 활성화한 상태이다.

| seq_length | 근사 activation 메모리 |
| :--------: | :--------------------: |
|    4096    |        ~0.9 GB         |
|    8192    |        ~1.9 GB         |

> 긴 시퀀스에서 attention 관련 메모리는 구현체에 따라 크게 달라진다.
> FlashAttention 계열을 사용하면 naive attention 대비 attention score materialization 비용이 줄어든다.
> 따라서 본 문서의 activation 추정치는 **attention backend에 의존**한다.
>
> Activation 메모리의 세부 구성:
> - **Attention scores / softmax 임시 버퍼**: FlashAttention 사용 시 크게 절감
> - **QKV projection intermediate**: 레이어별 고정
> - **MLP intermediate**: 레이어별 고정
> - **Residual stream**: 모든 레이어에 걸쳐 유지
> - **Checkpointing 보존 입력**: 레이어 수(28)에 비례

### ⑤ 역양자화(Dequantize) 임시 버퍼 (QLoRA 전용)

QLoRA는 가중치를 4-bit로 압축 저장하지만, 실제 연산(matmul)은 bf16으로 수행해야 한다.

- **현재 연산 중인 1개 레이어 분량**만 임시로 bf16으로 풀고, 해당 레이어 계산 완료 후 즉시 해제한다.
- 전체 모델 크기와 무관하게 **약 0.45 GB (450 MB)**의 고정 임시 공간만 추가된다.

---

## 4. 이론 메모리 모델

### 근사 수식

학습 시 총 할당 메모리(Allocated)는 다음과 같이 근사할 수 있다:

```
Total_Allocated ≈ W_base + W_adapter + Opt_state + Logits_peak + Act + Dequant + CUDA_ctx
```

여기서:
- `W_base`: 모델 가중치 (QLoRA: ~3.5GB, LoRA bf16: ~14.2GB)
- `W_adapter`: LoRA adapter 가중치 (~10MB)
- `Opt_state`: optimizer 상태 (~38MB, paged_adamw_8bit 기준)
- `Logits_peak`: `B × T × V × dtype_size × 2` (forward + backward 동시 상주)
- `Act`: gradient checkpointing 후 남는 activation
- `Dequant`: 역양자화 임시 버퍼 (QLoRA 시 ~0.45GB)
- `CUDA_ctx`: CUDA context, cuBLAS handle 등 (~1.0GB)

### 4096 vs 8192 비교 (QLoRA, B=1)

| 항목                     | QLoRA (seq=4096) | QLoRA (seq=8192) | LoRA bf16 (seq=8192) |
| :----------------------- | :--------------: | :--------------: | :------------------: |
| ① 가중치                 |    **3.5 GB**    |    **3.5 GB**    |     **14.2 GB**      |
| ② LoRA + Optimizer       |     0.05 GB      |     0.05 GB      |       0.05 GB        |
| ③ Logits & Gradient peak |      4.6 GB      |    **9.2 GB**    |        9.2 GB        |
| ④ Activations            |      0.9 GB      |      1.9 GB      |        1.9 GB        |
| ⑤ Dequantize buffer      |     0.45 GB      |     0.45 GB      |         0 GB         |
| CUDA context 등          |     ~1.0 GB      |     ~1.0 GB      |       ~1.0 GB        |
| **이론 Allocated 합계**  |   **~10.5 GB**   |   **~16.1 GB**   |     **~26.3 GB**     |

- **LoRA bf16 + seq=8192**: 이론 합계 26.3GB로 24GB를 초과하여 물리적으로 불가능.
- **QLoRA + seq=8192**: 이론 합계 16.1GB로 여유가 있어 보이지만, **실제로는 allocator reserved 메모리 때문에 OOM이 발생했다.**

> 위 수치는 본 실험 조건에서의 이론 근사치이다.
> 실제 peak VRAM은 loss 구현, attention backend, optimizer, PyTorch/CUDA 버전에 따라 달라질 수 있다.

---

## 5. 실험 결과

### 5-1. OOM의 원인: Reserved 메모리와 Allocator Fragmentation

이론적 필요량이 16.1GB인데 OOM이 발생하는 이유는, `nvidia-smi`에 표시되는 값이 순수 Allocated가 아니라 **PyTorch allocator의 Reserved 캐시**를 포함하기 때문이다.

**Reserved 메모리의 본질**:

> Reserved 메모리는 PyTorch allocator의 **재사용 캐시**다.
> PyTorch는 텐서 연산 완료 후 해당 메모리를 OS에 즉시 반환하지 않고, 이후 재사용을 위해 예약(reserve) 상태로 유지한다.
> 이는 성능 최적화 목적이지만, 특정 할당/해제 패턴에서 **단편화(fragmentation)**가 발생하면, 총 여유량이 충분해도 큰 연속 블록 할당에 실패할 수 있다.

**핵심 추론**: `seq=8192`에서 logits gradient는 이론상 ~4.6GB 연속 블록을 요구한다. `max_split_size_mb:128` 적용으로 OOM이 해결된 실험 결과로부터 역추론한 것으로, Reserved 영역에 총량은 충분하더라도 단편화로 인해 4.6GB 연속 공간이 확보되지 않아 OOM이 발생했다고 판단된다.

### 5-2. Allocator 튜닝 결과

fragmentation을 억제하기 위해 다음 환경변수를 적용했다:

```bash
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128
```

이 설정은 allocator에게 **128 MB를 초과하는 캐시 블록은 분할하지 말고 통째로 유지**하도록 지시한다. 대형 텐서(logits gradient 등)를 위한 연속 공간이 보존된다.

#### seq=4096: allocator 튜닝 효과

이론 Allocated ≈ 10.5 GB. logits gradient 크기: ~2.3 GB.

| 설정                    | nvidia-smi 관찰값 |    Reserved (역산)    |         결과         |
| :---------------------- | :---------------: | :-------------------: | :------------------: |
| 기본값 (tuning 없음)    |    **17.1 GB**    | ~6.6 GB (단편화 포함) |  동작하나 낭비 과다  |
| `max_split_size_mb:128` |    **12.5 GB**    |   ~2.0 GB (정리됨)    | 안정 동작, 대폭 절약 |

동일 조건에서 **약 4.6 GB의 단편화된 캐시가 제거**되었다.

#### seq=8192: allocator 튜닝이 OOM을 해결

이론 Allocated ≈ 16.1 GB. logits gradient 크기: ~4.6 GB.

| 설정                    | nvidia-smi 관찰값 |                              Reserved (역산)                              |     결과      |
| :---------------------- | :---------------: | :-----------------------------------------------------------------------: | :-----------: |
| 기본값 (tuning 없음)    | 22~24 GB 벽 충돌  | Allocated 17.4 GB + 단편화 Reserved 4.0 GB에서 4.6 GB 연속 블록 할당 실패 | **OOM 발생**  |
| `max_split_size_mb:128` |    **23.8 GB**    |                        ~7.7 GB (4.6 GB 블록 유지)                         | **안정 동작** |

> **OOM 원인**: Allocated 17.4 GB 상태에서 단편화된 Reserved 영역(4.0 GB)에 4.6 GB 연속 블록을 할당할 수 없었다.
> **해결 원인**: 분할을 억제하자 Reserved 7.7 GB 내부에 4.6 GB 연속 공간이 유지되어 24 GB 안에서 23.8 GB까지 활용할 수 있었다.

#### Reserved 확장의 구조적 이유

`seq=4096` → `8192`로 가면 logits 텐서가 2.3 GB → 4.6 GB로 커진다.
allocator가 이 대형 텐서를 캐싱하려면 Reserved 영역 자체도 비례하여 커져야 한다.
따라서 `seq=8192`에서 Reserved가 2.0 GB → 7.7 GB로 확장된 것은 구조적으로 예상되는 동작이다.

---

## 6. 원인 분석

본 실험 조건에서 OOM의 주요 원인을 정리하면 다음과 같다.

### 6-1. 대형 Vocab의 Logits 병목

Qwen2.5의 vocab size(152,064)는 일반적인 LLM(32k~64k)에 비해 2~5배 크다.
logits 메모리는 `B × T × V`에 비례하므로, 동일 seq_length에서도 vocab이 크면 peak가 크게 증가한다.
backward 시 logits + gradient 동시 상주로 peak가 2배가 되므로, **대형 vocab은 OOM의 지배적 병목**이 되기 쉽다.

### 6-2. 긴 시퀀스의 Activation Peak

`seq=8192`에서는 activation과 logits 모두 선형적으로 증가한다.
gradient checkpointing으로 activation 증가분은 억제할 수 있으나, logits peak는 이 기법으로 줄일 수 없다.

### 6-3. Allocator Fragmentation

PyTorch CUDA allocator의 기본 동작은 캐시 블록을 필요 시 분할(split)하여 재사용한다.
학습 루프에서 다양한 크기의 텐서가 반복적으로 할당/해제되면, 캐시 내부에 작은 조각(fragment)만 남아 대형 텐서 할당이 실패할 수 있다.

### 6-4. 구현 의존성

다음 항목들은 실제 peak VRAM에 영향을 주지만, 본 문서에서는 고정 조건으로 다루었다:

- **Loss 계산 구현**: 기본 cross entropy vs fused CE vs chunked CE
- **Attention backend**: FlashAttention 2 사용 여부
- **Autocast / mixed precision 동작**: bf16/fp16/tf32 혼합 상태
- **PyTorch/CUDA 버전**: allocator 동작의 버전별 차이
- **bitsandbytes 버전**: dequantize 구현의 차이

---

## 7. 해결 전략

### 7-1. 전략 비교표

`seq=8192`, 단일 RTX 4090 24GB 기준:

| 방법                                       |        메모리 절감        |        속도 영향        | 품질 영향 | 비고                        |
| ------------------------------------------ | :-----------------------: | :---------------------: | :-------: | --------------------------- |
| **QLoRA (NF4)**                            |       큼 (~10.7 GB)       | 중간 (dequant 오버헤드) |   낮음    | 필수급                      |
| **Gradient Checkpointing**                 |            큼             |     느려짐 (재계산)     |   없음    | 필수급                      |
| **Allocator tuning** (`max_split_size_mb`) | 간접 (fragmentation 제거) |          없음           |   없음    | 본 실험에서 OOM 해결의 핵심 |
| **FlashAttention 2**                       |          중간~큼          |        보통 개선        |   없음    | 긴 시퀀스에서 중요          |
| micro-batch 1 유지                         |            큼             | 느림 (grad accum 필요)  |   없음    | 이미 적용됨                 |
| Sequence packing 최적화                    |           중간            |        개선 가능        |   없음    | padding 낭비 감소           |
| Fused / Chunked CE loss                    |            큼             |        구현 의존        |   없음    | large vocab에 특히 유효     |
| Completion-only loss                       |           중간            |          동일           | task 의존 | SFT에서 유용                |
| ZeRO / Offload                             |            큼             |         느려짐          |   없음    | 단일 GPU에서는 타협책       |

### 7-2. 단일 GPU 한계 경계

| 조건                                                  | 기대 결과                           |
| ----------------------------------------------------- | ----------------------------------- |
| 24GB / seq=8192 / B=1 / QLoRA / GC / allocator tuning | ✅ 가능 (23.8 GB 사용으로 관찰됨)    |
| 24GB / seq=8192 / B=1 / LoRA bf16                     | ❌ 불가 (이론 26.3 GB 필요)          |
| 24GB / seq=8192 / B=2 / QLoRA / GC / allocator tuning | ⚠️ 매우 위험 (logits peak 2배)       |
| 24GB / seq=16384 / B=1 / QLoRA                        | ❌ 비현실적 (logits peak만 ~18.4 GB) |
| 24GB / seq=4096 / B=1 / QLoRA / allocator tuning      | ✅ 쾌적 (12.5 GB 사용으로 관찰됨)    |

### 7-3. Logits 경로 최적화 (추가 탐색 가능)

본 문서에서 logits가 핵심 병목으로 관찰되었으므로, logits 메모리를 직접 줄이는 추가 기법들을 정리한다:

- **Fused Cross Entropy**: logits을 full materialization 없이 loss 계산. large vocab에서 효과적.
- **Chunked / Streaming Loss**: logits를 seq 차원에서 분할 계산하여 peak 감소.
- **Vocab-parallel / Blockwise Loss**: vocab 차원을 분할하여 동시 상주 크기 감소.
- **`use_cache=False` 확인**: 학습 시 KV cache를 비활성화하여 불필요한 메모리 사용 방지.
- **불필요한 full logits 보관 방지**: loss 계산 후 즉시 해제되는지 확인.

이 기법들은 allocator tuning과 독립적으로 적용 가능하며, 특히 `seq=8192` 이상에서 추가 여유를 확보하는 데 유효하다.

---

## 8. 최종 레시피 및 부록

### 8-1. 최종 권장 설정

본 실험 조건에서 가장 안정적으로 동작한 조합:

```bash
# 1. 단편화 방지 환경변수 설정
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128

# 2. 학습 실행
python -m train.run
```

학습 설정 핵심 (`config.py`):

```python
use_qlora = True               # NF4 4-bit 양자화
max_seq_length = 8192           # 긴 시퀀스
batch_size = 1                  # micro batch
gradient_accumulation_steps = 2 # effective batch = 2
gradient_checkpointing = True   # activation 메모리 절감
optim = "paged_adamw_8bit"      # 8-bit paged optimizer
bf16 = True                    # bfloat16 학습
```

기대 메모리:
- nvidia-smi 관찰값: **~23.8 GB / 24 GB**
- 이론 Allocated: ~16.1 GB
- Reserved (allocator cache): ~7.7 GB

### 8-2. 검증 실험 프로토콜 (향후 수행용 템플릿)

본 문서의 분석을 가설에서 검증 결과로 발전시키려면, 다음 실험들을 수행할 수 있다.

#### 실험 A — Vocab 크기가 Logits 병목의 원인인지 검증

- 동일 모델, 동일 seq_length, 동일 micro-batch
- loss 계산 방식만 변경: 기본 CE vs fused CE vs chunked CE
- 측정: `max_memory_allocated()`, `max_memory_reserved()`, step time

#### 실험 B — Seq Length가 Peak에 미치는 영향 검증

- seq_length를 `2048 / 4096 / 8192`로 변경
- 나머지 조건 고정
- 측정: step별 `max_memory_allocated`, `max_memory_reserved`, step time

#### 실험 C — LoRA vs QLoRA 메모리 차이 검증

- 동일 LoRA adapter config (r=8, α=32, target q/k/v/o)
- base dtype만 변경: bf16 (LoRA) vs NF4 (QLoRA)
- 측정: 모델 로드 직후 + step 1 완료 후 peak 비교

#### 실험 D — Fragmentation 패턴 검증

- `PYTORCH_CUDA_ALLOC_CONF` 설정 on/off
- step 1 vs step 50의 peak 비교
- `torch.cuda.memory_summary()` 저장하여 fragmentation 패턴 분석

### 8-3. OOM 디버깅 체크리스트

OOM 발생 시 순차적으로 확인해야 할 항목:

**측정 기반 진단**:
- [ ] `torch.cuda.reset_peak_memory_stats()` 호출 후 step 실행
- [ ] step 단위 `max_memory_allocated()` / `max_memory_reserved()` 기록
- [ ] `torch.cuda.memory_summary()` 출력 저장 및 분석

**모델/학습 설정 확인**:
- [ ] `model.config.use_cache = False` 여부
- [ ] gradient checkpointing 실제 적용 여부 (trainer log에서 확인)
- [ ] FlashAttention backend 사용 여부
- [ ] bf16/fp16/autocast 혼합 상태 확인
- [ ] optimizer가 paged 8-bit인지 확인

**데이터/Loss 경로 확인**:
- [ ] padding으로 인해 실효 seq_length가 불필요하게 커지지 않았는지 확인
- [ ] loss 구현이 full logits materialization을 강제하는지 확인
- [ ] `torch.compile` 사용 시 peak 변화 확인
- [ ] DataLoader pinned memory / prefetch 영향 분리

**환경 확인**:
- [ ] `PYTORCH_CUDA_ALLOC_CONF` 환경변수 적용 여부
- [ ] 다른 GPU 프로세스가 VRAM을 점유하고 있지 않은지 확인

---

## 결론

RTX 4090 24GB 단일 GPU에서 Qwen2.5-7B를 `seq=8192`로 학습할 때, 본 실험 조건에서는 base weight 자체보다도 **large vocab logits**와 backward 시점의 peak memory, 그리고 **allocator fragmentation**이 주요 병목으로 관찰되었다.

QLoRA, gradient checkpointing, 그리고 `PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128` 조합은 해당 환경에서 가장 안정적으로 동작했다.

다만 실제 peak VRAM은 loss 구현, attention backend, optimizer, PyTorch/CUDA 버전에 따라 달라질 수 있으므로, **본 문서의 수치는 절대값이 아니라 재현 가능한 근사치와 분석 프레임**으로 이해하는 것이 적절하다.
