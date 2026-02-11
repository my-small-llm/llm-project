import torch
from datasets import load_dataset, Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig
from trl import SFTConfig, SFTTrainer


# ============================================================
# 1. 데이터 전처리
# ============================================================
dataset = load_dataset("iamjoon/ecommerce-function-calling-datasets-korean", split="train")

# 테스트 비율 설정
test_ratio = 0.2
total_len = len(dataset)
test_size = int(total_len * test_ratio)

# 앞에서부터 테스트 데이터, 나머지는 학습 데이터
test_indices = list(range(test_size))
train_indices = list(range(test_size, total_len))


# OpenAI 포맷으로 변환 함수
def format_conversations(sample):
    return {
        "messages": [
            {"role": "system", "content": sample["system_prompt"]},
            *sample["messages"]
        ]
    }


# 분할 및 변환
train_dataset = Dataset.from_list([format_conversations(dataset[i]) for i in train_indices])
test_dataset = Dataset.from_list([format_conversations(dataset[i]) for i in test_indices])
print(f"데이터 분할 결과: Train {len(train_dataset)}개, Test {len(test_dataset)}개")


# ============================================================
# 2. 모델 로드
# ============================================================
model_id = "Qwen/Qwen2.5-7B-Instruct"

model = AutoModelForCausalLM.from_pretrained(
    model_id,
    device_map="auto",
    torch_dtype=torch.bfloat16,
)
tokenizer = AutoTokenizer.from_pretrained(model_id)


# ============================================================
# 3. LoRA / SFT 설정
# ============================================================
peft_config = LoraConfig(
    lora_alpha=32,
    lora_dropout=0.1,
    r=8,
    bias="none",
    target_modules=["q_proj", "v_proj"],
    task_type="CAUSAL_LM",
)

args = SFTConfig(
    output_dir="qwen-2.5-7b-function-calling",
    num_train_epochs=3,
    per_device_train_batch_size=2,
    gradient_accumulation_steps=2,
    gradient_checkpointing=True,
    optim="adamw_torch_fused",
    logging_steps=10,
    save_strategy="steps",
    save_steps=50,
    bf16=True,
    learning_rate=1e-4,
    max_grad_norm=0.3,
    warmup_ratio=0.03,
    lr_scheduler_type="constant",
    push_to_hub=False,
    remove_unused_columns=False,
    dataset_kwargs={"skip_prepare_dataset": True},
    report_to=None,
)


# ============================================================
# 4. collate_fn (assistant 응답만 레이블링)
# ============================================================
max_seq_length = 8192

# Qwen ChatML 토큰 정의
START_TOKEN = "<|im_start|>"
END_TOKEN = "<|im_end|>"
ASSISTANT_TOKENS = tokenizer.encode(f"{START_TOKEN}assistant\n", add_special_tokens=False)
END_TOKENS = tokenizer.encode(END_TOKEN, add_special_tokens=False)


def collate_fn(batch):
    new_batch = {"input_ids": [], "attention_mask": [], "labels": []}

    for example in batch:
        messages = example["messages"]

        # ChatML 형식으로 prompt 조합
        prompt = ""
        for msg in messages:
            role = msg["role"]
            content = msg["content"].strip()
            prompt += f"{START_TOKEN}{role}\n{content}{END_TOKEN}"

        # 토크나이징
        tokenized = tokenizer(
            prompt,
            truncation=True,
            max_length=max_seq_length,
            padding=False,
            return_tensors=None,
        )
        input_ids = tokenized["input_ids"]
        attention_mask = tokenized["attention_mask"]
        labels = [-100] * len(input_ids)

        # assistant 세그먼트만 레이블에 복사 (종료 토큰 포함)
        i = 0
        n = len(input_ids)
        while i <= n - len(ASSISTANT_TOKENS):
            if input_ids[i:i + len(ASSISTANT_TOKENS)] == ASSISTANT_TOKENS:
                start_idx = i + len(ASSISTANT_TOKENS)
                end_idx = start_idx
                while end_idx <= n - len(END_TOKENS):
                    if input_ids[end_idx:end_idx + len(END_TOKENS)] == END_TOKENS:
                        end_idx += len(END_TOKENS)
                        break
                    end_idx += 1
                for j in range(start_idx, end_idx):
                    labels[j] = input_ids[j]
                i = end_idx
            else:
                i += 1

        new_batch["input_ids"].append(input_ids)
        new_batch["attention_mask"].append(attention_mask)
        new_batch["labels"].append(labels)

    # 패딩 및 Tensor 변환
    max_len = max(len(ids) for ids in new_batch["input_ids"])
    for idx in range(len(new_batch["input_ids"])):
        pad_len = max_len - len(new_batch["input_ids"][idx])
        new_batch["input_ids"][idx].extend([tokenizer.pad_token_id] * pad_len)
        new_batch["attention_mask"][idx].extend([0] * pad_len)
        new_batch["labels"][idx].extend([-100] * pad_len)

    for k in new_batch:
        new_batch[k] = torch.tensor(new_batch[k])

    return new_batch


# ============================================================
# 5. 학습
# ============================================================
trainer = SFTTrainer(
    model=model,
    args=args,
    max_seq_length=max_seq_length,
    train_dataset=train_dataset,
    data_collator=collate_fn,
    peft_config=peft_config,
)

trainer.train()
trainer.save_model()
