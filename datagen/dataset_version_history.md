# Dataset Version History

이 문서는 배달앱 학습 데이터셋의 **실제 데이터 내용 변화**만 기록한다.
배치 제출, 재다운로드, 병합 같은 운영 절차는 적지 않는다.

기록 원칙:
- 기준은 "데이터셋 샘플 1건의 내용이 이전 버전 대비 어떻게 달라졌는가"이다.
- 학습 설정, 모델 결과, 실험 메모는 여기 쓰지 않는다.
- 각 버전에는 Hugging Face 데이터셋 ID와 핵심 데이터 변경점만 남긴다.

## `deliveryapp-traindata-500`

- Hugging Face: `jjun123/deliveryapp-traindata-500`
- 설명: 초기 500개 학습 데이터셋

데이터 특성:
- `search_restaurants` 호출 인자에 `page`, `page_size`가 포함된 샘플이 존재했다.
- `search_restaurants` 응답의 `pagination.page_size` 값이 샘플마다 다를 수 있었다.

## `deliveryapp-traindata-500-v2`

- Hugging Face: `jjun123/deliveryapp-traindata-500-v2`
- 설명: `deliveryapp-traindata-500`의 스키마 정합성 보정 버전

이 버전에서 실제 데이터셋에 반영한 변경:
- 모든 `search_restaurants` tool call에서 `arguments.page` 제거
- 모든 `search_restaurants` tool call에서 `arguments.page_size` 제거
- 모든 `search_restaurants` tool response에서 `pagination.page_size`를 `20`으로 통일

의도:
- 현재 함수 스키마와 맞지 않는 호출 인자를 제거한다.
- 검색 응답 메타데이터를 일관된 형태로 맞춘다.
- validator 기준에서 `search_restaurants` 관련 스키마 불일치를 줄인다.
