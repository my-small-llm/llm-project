"""데이터셋 로드 및 전처리를 담당합니다."""

from typing import Tuple

from datasets import Dataset, load_dataset


def format_conversations(sample: dict) -> dict:
    """원본 데이터를 OpenAI messages 포맷으로 변환합니다.

    system_prompt를 messages 리스트의 첫 번째 system 메시지로 삽입합니다.
    """
    return {
        "messages": [
            {"role": "system", "content": sample["system_prompt"]},
            *sample["messages"],
        ]
    }


def load_and_split(
    dataset_id: str,
    test_ratio: float = 0.2,
) -> Tuple[Dataset, Dataset]:
    """HuggingFace Hub에서 데이터셋을 로드하고 train/test로 분할합니다.

    앞부분을 test, 뒷부분을 train으로 분할합니다.

    Args:
        dataset_id: HuggingFace 데이터셋 ID
        test_ratio: 테스트 데이터 비율

    Returns:
        (train_dataset, test_dataset) 튜플
    """
    dataset = load_dataset(dataset_id, split="train")

    total_len = len(dataset)
    test_size = int(total_len * test_ratio)

    test_indices = list(range(test_size))
    train_indices = list(range(test_size, total_len))

    train_dataset = Dataset.from_list(
        [format_conversations(dataset[i]) for i in train_indices]
    )
    test_dataset = Dataset.from_list(
        [format_conversations(dataset[i]) for i in test_indices]
    )

    print(f"데이터 분할 결과: Train {len(train_dataset)}개, Test {len(test_dataset)}개")
    return train_dataset, test_dataset
