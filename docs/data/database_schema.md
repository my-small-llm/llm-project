# Food Delivery Database Schema

이 문서는 8개의 테이블로 구성된 음식 배달 서비스의 데이터베이스 스키마를 정의합니다.
**특징**: JSONB 제거, 메뉴 옵션 제거, Payments 테이블 통합 (Orders에 포함).

---

## 1. Users & Addresses (사용자 및 주소)

### `users`
사용자 기본 정보를 저장합니다.

| 컬럼명       | 타입         | 제약조건         | 설명      |
| :----------- | :----------- | :--------------- | :-------- |
| `id`         | UUID         | PK               | 사용자 ID |
| `email`      | VARCHAR(255) | UNIQUE, NOT NULL | 이메일    |
| `phone`      | VARCHAR(50)  | UNIQUE, NOT NULL | 전화번호  |
| `name`       | VARCHAR(100) | NOT NULL         | 이름      |
| `created_at` | TIMESTAMPTZ  | DEFAULT now()    | 생성일    |

### `addresses`
사용자의 배송지 정보를 저장합니다. 사용자당 기본 배송지는 1개로 제한됩니다.

| 컬럼명           | 타입         | 제약조건                         | 설명                  |
| :--------------- | :----------- | :------------------------------- | :-------------------- |
| `id`             | UUID         | PK                               | 주소 ID               |
| `user_id`        | UUID         | FK (users.id), NOT NULL, CASCADE | 사용자                |
| `recipient_name` | VARCHAR(100) | NOT NULL                         | 수령인                |
| `phone`          | VARCHAR(50)  | NOT NULL                         | 연락처                |
| `line1`          | VARCHAR(255) | NOT NULL                         | 기본 주소             |
| `line2`          | VARCHAR(255) | NULL                             | 상세 주소             |
| `is_default`     | BOOLEAN      | DEFAULT FALSE                    | 기본 배송지 여부      |
| `gate_password`  | VARCHAR(100) | NULL                             | 공동현관 비밀번호     |
| `delivery_note`  | TEXT         | NULL                             | 배송 요청 사항 (기본) |
| `created_at`     | TIMESTAMPTZ  | DEFAULT now()                    | 생성일                |

> **Note**: `addresses(user_id, is_default)`에 대해 Partial Unique Index 권장 (is_default=true인 경우).

---

## 2. Restaurants & Menu (식당 및 메뉴)

### `restaurants`
식당 정보 및 영업 시간을 저장합니다.

| 컬럼명             | 타입         | 설명           |
| :----------------- | :----------- | :------------- |
| `id`               | UUID         | PK             |
| `name`             | VARCHAR(255) | 식당 이름      |
| `category`         | VARCHAR(50)  | 카테고리       |
| `phone`            | VARCHAR(50)  | 전화번호       |
| `min_order_amount` | INTEGER      | 최소 주문 금액 |
| `rating_avg`       | NUMERIC(3,2) | 평균 평점      |
| `rating_count`     | INTEGER      | 평점 수        |
| `is_active`        | BOOLEAN      | 운영 여부      |
| `is_open_weekday`  | BOOLEAN      | 평일 영업 여부 |
| `weekday_open`     | TIME         | 평일 오픈 시간 |
| `weekday_close`    | TIME         | 평일 마감 시간 |
| `is_open_weekend`  | BOOLEAN      | 주말 영업 여부 |
| `weekend_open`     | TIME         | 주말 오픈 시간 |
| `weekend_close`    | TIME         | 주말 마감 시간 |
| `created_at`       | TIMESTAMPTZ  | 생성일         |

### `menu_items`
식당의 메뉴 정보를 저장합니다. 옵션 기능은 제외되었습니다.

| 컬럼명          | 타입         | 제약조건                               | 설명           |
| :-------------- | :----------- | :------------------------------------- | :------------- |
| `id`            | UUID         | PK                                     | 메뉴 ID        |
| `restaurant_id` | UUID         | FK (restaurants.id), NOT NULL, CASCADE | 식당           |
| `name`          | VARCHAR(255) | NOT NULL                               | 메뉴명         |
| `description`   | TEXT         | NULL                                   | 설명           |
| `base_price`    | INTEGER      | NOT NULL                               | 가격           |
| `is_available`  | BOOLEAN      | DEFAULT TRUE                           | 판매 가능 여부 |
| `sort_order`    | INTEGER      | DEFAULT 0                              | 정렬 순서      |
| `created_at`    | TIMESTAMPTZ  | DEFAULT now()                          | 생성일         |

---

## 3. Cart (장바구니)

### `carts`
장바구니는 사용자당 1개, 식당 1곳으로 제한됩니다.

| 컬럼명          | 타입        | 제약조건                                 | 설명        |
| :-------------- | :---------- | :--------------------------------------- | :---------- |
| `id`            | UUID        | PK                                       | 카트 ID     |
| `user_id`       | UUID        | UNIQUE, FK (users.id), NOT NULL, CASCADE | 사용자      |
| `restaurant_id` | UUID        | FK (restaurants.id), NOT NULL            | 식당        |
| `updated_at`    | TIMESTAMPTZ | DEFAULT now()                            | 최종 수정일 |

### `cart_items`
장바구니에 담긴 개별 메뉴 아이템입니다.

| 컬럼명                | 타입         | 제약조건                         | 설명           |
| :-------------------- | :----------- | :------------------------------- | :------------- |
| `id`                  | UUID         | PK                               | 카트 아이템 ID |
| `cart_id`             | UUID         | FK (carts.id), NOT NULL, CASCADE | 카트           |
| `menu_item_id`        | UUID         | FK (menu_items.id), NOT NULL     | 메뉴           |
| `name_snapshot`       | VARCHAR(255) | NOT NULL                         | 메뉴명 스냅샷  |
| `unit_price_snapshot` | INTEGER      | NOT NULL                         | 단가 스냅샷    |
| `quantity`            | INTEGER      | NOT NULL (CHECK > 0)             | 수량           |
| `special_request`     | TEXT         | NULL                             | 요청사항       |
| `created_at`          | TIMESTAMPTZ  | DEFAULT now()                    | 생성일         |
| `updated_at`          | TIMESTAMPTZ  | DEFAULT now()                    | 수정일         |

> **합계 계산**: `SUM(unit_price_snapshot * quantity)`

---

## 4. Orders (주문 및 결제)

### `orders`
주문 정보와 결제 정보, 배송지 스냅샷을 포함합니다.

| 컬럼명          | 타입        | 제약조건                       | 설명                                                       |
| :-------------- | :---------- | :----------------------------- | :--------------------------------------------------------- |
| `id`            | UUID        | PK                             | 주문 ID                                                    |
| `user_id`       | UUID        | FK (users.id), NULL 허용       | 사용자 (탈퇴 대비)                                         |
| `restaurant_id` | UUID        | FK (restaurants.id), NULL 허용 | 식당 (삭제 대비)                                           |
| `status`        | VARCHAR(50) | NOT NULL                       | pending, paid, preparing, delivering, delivered, cancelled |
| `created_at`    | TIMESTAMPTZ | DEFAULT now()                  | 생성일                                                     |

#### 배송지 스냅샷 (고정 컬럼)
| 컬럼명                    | 타입         | 설명          |
| :------------------------ | :----------- | :------------ |
| `delivery_recipient_name` | VARCHAR(100) | 수령인        |
| `delivery_phone`          | VARCHAR(50)  | 연락처        |
| `delivery_line1`          | VARCHAR(255) | 기본 주소     |
| `delivery_line2`          | VARCHAR(255) | 상세 주소     |
| `delivery_gate_password`  | VARCHAR(100) | 공동현관 비번 |
| `delivery_note`           | TEXT         | 주문 메모     |

#### 금액 정보
| 컬럼명                | 타입    | 설명                    |
| :-------------------- | :------ | :---------------------- |
| `subtotal_amount`     | INTEGER | 주문 총액 (배달팁 제외) |
| `discount_amount`     | INTEGER | 할인 금액               |
| `delivery_fee_amount` | INTEGER | 배달팁                  |
| `total_amount`        | INTEGER | 최종 결제 금액          |

#### 결제 정보 (통합)
| 컬럼명           | 타입         | 설명                                       |
| :--------------- | :----------- | :----------------------------------------- |
| `payment_method` | VARCHAR(20)  | card, kakao 등                             |
| `pg_id`          | VARCHAR(100) | PG사 거래 ID                               |
| `payment_status` | VARCHAR(20)  | pending, paid, failed, cancelled, refunded |
| `paid_at`        | TIMESTAMPTZ  | 결제 완료 시각                             |

### `order_items`
주문 당시의 메뉴 정보 스냅샷입니다.

| 컬럼명                | 타입         | 설명                              |
| :-------------------- | :----------- | :-------------------------------- |
| `id`                  | UUID         | PK                                |
| `order_id`            | UUID         | FK (orders.id), NOT NULL, CASCADE |
| `menu_item_id`        | UUID         | FK (menu_items.id), NULL 허용     |
| `name_snapshot`       | VARCHAR(255) | 메뉴명 스냅샷                     |
| `unit_price_snapshot` | INTEGER      | 단가 스냅샷                       |
| `quantity`            | INTEGER      | 수량 (1 이상)                     |
| `special_request`     | TEXT         | 요청사항                          |

---

## 설계 요약

| 포인트            | 설명                                                                 |
| :---------------- | :------------------------------------------------------------------- |
| **JSONB 제거**    | 데이터 구조의 단순화 및 운영 용이성 확보                             |
| **옵션 제거**     | 메뉴를 단일 가격으로 단순화하여 카트/주문 로직 간소화                |
| **결제 통합**     | 별도의 `payments` 테이블 없이 `orders` 테이블 내 컬럼으로 관리       |
| **스냅샷 저장**   | 주문 시점의 가격, 이름, 주소 정보를 별도 컬럼으로 저장하여 이력 보존 |
| **단순 영업시간** | 평일/주말 구분으로 스키마 단순화                                     |

## 권장 인덱스

- `addresses(user_id)`: 사용자별 주소 조회
- `addresses(user_id, is_default) WHERE is_default = TRUE`: 기본 배송지 유니크 보장
- `menu_items(restaurant_id, is_available)`: 식당별 판매 중인 메뉴 조회
- `cart_items(cart_id)`: 카트 아이템 조회
- `orders(user_id, created_at)`: 사용자별 주문 내역 조회 (최신순)
- `orders(status)`: 주문 상태별 조회
- `order_items(order_id)`: 주문 상세 품목 조회
