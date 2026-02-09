# 디렉토리 구조

```
llm-project/
├── configs/
│   └── train_config.yaml        # 학습 하이퍼파라미터, 모델 경로 등
├── data/
│   ├── raw/                     # 원본 데이터 (크롤링/수집 결과)
│   ├── processed/               # 전처리 완료된 학습용 데이터
│   └── schema.json              # intent 목록, slot 목록 정의
├── src/
│   ├── data_collection/
│   │   ├── collector.py         # 데이터 수집 스크립트
│   │   └── preprocessor.py      # 전처리 및 BIO 태깅 변환
│   ├── training/
│   │   ├── dataset.py           # Dataset 클래스
│   │   ├── model.py             # 모델 정의 (LoRA 설정 포함)
│   │   └── trainer.py           # 학습 루프
│   └── evaluation/
│       ├── evaluator.py         # 정량 평가 (F1, Accuracy)
│       └── inference.py         # 추론 및 데모
├── outputs/
│   ├── checkpoints/             # 학습 체크포인트
│   └── logs/                    # 학습 로그, 평가 결과
├── scripts/
│   ├── run_collect.sh           # 데이터 수집 실행
│   ├── run_train.sh             # 학습 실행
│   └── run_eval.sh              # 평가 실행
├── experiments/                   # 별도 실험용 스크립트 및 노트북
├── requirements.txt
└── main.py                      # 전체 파이프라인 통합 실행
```

## 핵심 설계 포인트

- **configs/**: 하이퍼파라미터를 코드에서 분리하여 실험 재현성 확보
- **data/schema.json**: intent/slot 레이블을 한 곳에서 관리하여 수집-학습-평가 간 일관성 유지
- **src/ 3분할**: 수집/학습/평가가 독립적으로 실행 가능하면서, main.py에서 통합 실행도 가능
- **outputs/**: git에서 제외 (.gitignore)하여 체크포인트가 저장소를 오염시키지 않도록 처리
- **experiments/**: 본 파이프라인과 분리된 별도 실험용 공간
