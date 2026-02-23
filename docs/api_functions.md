# 🍽️ AI Agent Tool Calling 함수 명세

> **기준 스키마**: 8개 테이블, JSONB 없음, 메뉴 옵션 없음, 쿠폰 없음, Payments 테이블 없음
> 
> **특이사항**: 외부 인터페이스(함수 인자)에서는 `UUID` 대신 `str` 타입을 사용합니다.

---

## 1️⃣ `search_restaurants`

### 기능
식당 목록을 검색/필터/정렬하여 페이지 단위로 반환합니다.

### 시그니처
```python
async def search_restaurants(
    *,
    query: Optional[str] = None,       # 식당명 또는 메뉴명 검색
    category: Optional[str] = None,    # restaurants.category 문자열 필터
    min_rating: Optional[float] = None,# 최소 평점 (restaurants.rating_avg)
    only_open: bool = False,           # 현재 영업 중인 식당만 필터
    sort: str = "relevance",           # 정렬 기준 ('relevance' | 'rating' | 'delivery_fee')
    page: int = 1,
    page_size: int = 20,
) -> dict  # Page 구조 반환
```

### 사용 예시

**1-A. “치킨” 카테고리에서 평점 4.5 이상 (평점순)**
```python
await search_restaurants(
    query=None,
    category="치킨",
    min_rating=4.5,
    only_open=False,
    sort="rating",
    page=1,
    page_size=20,
)
```

**1-B. 메뉴명 키워드로 검색 (“콜라” 포함 메뉴 있는 식당)**
```python
await search_restaurants(
    query="콜라",
    category=None,
    min_rating=None,
    only_open=False,
    sort="relevance",
    page=1,
    page_size=20,
)
```

---

## 2️⃣ `get_restaurant_detail`

### 기능
식당 기본 정보와 메뉴 목록을 조회합니다.

### 시그니처
```python
async def get_restaurant_detail(
    *,
    restaurant_id: str,
    at: Optional[datetime] = None,   # 영업 여부 판단용 (기본값: 현재시간)
) -> dict
```

### 사용 예시
**2-A. “미스터피자” 메뉴/영업 정보 조회**
```python
from datetime import datetime

await get_restaurant_detail(
    restaurant_id="76a2d649-8a13-49fb-8b61-d63fbcaec5ea",
    at=datetime.now(),
)
```

---

## 3️⃣ `upsert_address`

### 기능
주소를 신규 생성하거나 기존 주소를 수정합니다.

### 시그니처
```python
async def upsert_address(
    *,
    user_id: str,
    address_id: Optional[str] = None,
    recipient_name: str,
    phone: str,
    line1: str,
    line2: Optional[str] = None,
    is_default: bool = False,
    gate_password: Optional[str] = None,
    delivery_note: Optional[str] = None,
) -> str  # address_id 반환
```

### 사용 예시

**3-A. 기존 기본 주소 수정 (배송메모 추가)**
```python
await upsert_address(
    user_id="531a4da5-92a9-4aa4-a4d2-a2e67ecb838d",
    address_id="53e17944-5ee3-4783-9a3e-2e39796d6491",
    recipient_name="정서준",
    phone="010-3861-6707",
    line1="서울시 송파구 테헤란로 355",
    line2="322호",
    is_default=True,
    gate_password=None,
    delivery_note="문 앞에 두고 문자 주세요",
)
```

**3-B. 새 주소 추가 (기본배송지 아님)**
```python
await upsert_address(
    user_id="a1661d37-87bb-44e9-b2b3-ad951c237ba5",
    address_id=None,
    recipient_name="박민수",
    phone="010-3263-5473",
    line1="서울시 송파구 올림픽로 300",
    line2="1층 로비",
    is_default=False,
    gate_password="1234",
    delivery_note="경비실에 맡겨주세요",
)
```

---

## 4️⃣ `list_addresses`

### 기능
사용자의 배송지 목록을 조회합니다.

### 시그니처
```python
async def list_addresses(
    *,
    user_id: str,
) -> list[dict]
```

### 사용 예시
```python
await list_addresses(
    user_id="928ef291-19a0-4408-90f0-b130a019c19f",
)
```

---

## 5️⃣ `get_cart`

### 기능
사용자의 장바구니 상태와 금액 합계를 조회합니다.
*금액 계산: `SUM(unit_price_snapshot * quantity)`*

### 시그니처
```python
async def get_cart(
    *,
    user_id: str,
) -> Optional[dict]
```

### 사용 예시
```python
await get_cart(
    user_id="531a4da5-92a9-4aa4-a4d2-a2e67ecb838d",
)
```

---

## 6️⃣ `add_to_cart`

### 기능
카트에 메뉴를 추가합니다. (1카트=1식당 정책)
- 카트가 없으면 생성
- 식당이 다르면 정책에 따라 에러 처리 또는 교체
- `cart_items` INSERT 및 스냅샷 저장

### 시그니처
```python
async def add_to_cart(
    *,
    user_id: str,
    restaurant_id: str,
    menu_item_id: str,
    quantity: int,
    special_request: Optional[str] = None,
) -> dict  # CartSummary
```

### 사용 예시

**6-A. 카트(미스터피자)에 “페퍼로니” 1개 추가**
```python
await add_to_cart(
    user_id="531a4da5-92a9-4aa4-a4d2-a2e67ecb838d",
    restaurant_id="76a2d649-8a13-49fb-8b61-d63fbcaec5ea",
    menu_item_id="210b0ddf-b1f7-4820-8f6b-de770ffc7440",
    quantity=1,
    special_request="치즈 많이",
)
```

**6-B. 다른 식당 메뉴 담기 시도 (에러 발생 가정)**
```python
# 기존 카트가 있는 상태에서 다른 식당 호출 시 409 Conflict 발생 가능
await add_to_cart(
    user_id="47d67a36-584a-4154-8a7c-e9eb74ee1326",
    restaurant_id="f0e692f8-381d-46ff-b3b1-1cef9674ab55", # 도미노피자
    menu_item_id="c81bee64-dc7a-471f-95b5-b8e160adafb7",
    quantity=1,
    special_request=None,
)
```

---

## 7️⃣ `update_cart_item`

### 기능
카트 내 특정 아이템의 수량이나 요청사항을 수정합니다.

### 시그니처
```python
async def update_cart_item(
    *,
    user_id: str,
    cart_item_id: str,
    quantity: Optional[int] = None,
    special_request: Optional[str] = None,
) -> dict  # CartSummary
```

### 사용 예시
**7-A. 수량 변경 (2개 -> 1개)**
```python
await update_cart_item(
    user_id="531a4da5-92a9-4aa4-a4d2-a2e67ecb838d",
    cart_item_id="1b132098-ef57-4ddb-adda-e85606bc2e66",
    quantity=1,
    special_request=None,
)
```

---

## 8️⃣ `remove_cart_items`

### 기능
카트에서 특정 아이템을 삭제합니다.

### 시그니처
```python
async def remove_cart_items(
    *,
    user_id: str,
    cart_item_ids: list[str],
) -> dict  # CartSummary
```

### 사용 예시
```python
await remove_cart_items(
    user_id="531a4da5-92a9-4aa4-a4d2-a2e67ecb838d",
    cart_item_ids=["74910c0c-ba25-4955-b547-c097b01db58b"],
)
```

---

## 9️⃣ `prepare_checkout`

### 기능
주문 생성 전 최종 금액을 계산하고 주문 스냅샷을 생성합니다.
(현재 스키마에는 쿠폰, 팁, ETA 기능 없음)

### 시그니처
```python
async def prepare_checkout(
    *,
    user_id: str,
    address_id: str,
    delivery_note: Optional[str] = None,
) -> dict  # CheckoutSnapshot
```

### 사용 예시
```python
snapshot = await prepare_checkout(
    user_id="531a4da5-92a9-4aa4-a4d2-a2e67ecb838d",
    address_id="53e17944-5ee3-4783-9a3e-2e39796d6491",
    delivery_note="문 앞에 두고 전화주세요",
)
```

---

## 🔟 `place_order`

### 기능
주문을 확정하고 `order_items`를 생성합니다. 결제 정보는 `orders` 테이블 컬럼에 저장됩니다.

### 시그니처
```python
async def place_order(
    *,
    snapshot: dict,  # CheckoutSnapshot
    payment_method: str,
    pg_id: Optional[str] = None,
) -> str  # order_id (UUID 문자열)
```

### 사용 예시
```python
order_id = await place_order(
    snapshot=snapshot,
    payment_method="card",
    pg_id="imp_demo_123456",
)
```

---

## 1️⃣1️⃣ `get_order_status`

### 기능
주문 상태 및 결제 상태를 조회합니다.

### 시그니처
```python
async def get_order_status(
    *,
    user_id: str,
    order_id: str,
) -> dict
```

### 사용 예시
**11-A. 주문 상태 조회**
```python
await get_order_status(
    user_id="1a461d28-9400-44cf-bcd1-b997488cf20e",
    order_id="067d0c41-02d6-47c3-b60f-757d2a72713a",
)
```

**11-B. 다른 사용자의 주문 조회**
```python
# 반환값 예시: { "status": "delivered", "payment_status": "paid", ... }
await get_order_status(
    user_id="fac75497-7df8-4902-bda6-066e60a1f5ef",
    order_id="63e3c093-0636-46e5-8b45-862907eae1a5",
)
```

---

## 📌 참고: 제거된 기능 (현재 스키마 기준)

| 기능                    | 이유                                    |
| :---------------------- | :-------------------------------------- |
| **옵션 선택**           | `menu_items` 옵션 구조 제거 (단일 가격) |
| **쿠폰**                | 쿠폰 관련 테이블 제거                   |
| **ETA / 배달비 계산**   | 정책 데이터 부재                        |
| **Order Type (Pickup)** | 지원 컬럼 없음                          |
| **Tip**                 | 지원 컬럼 없음                          |
| **Payments 테이블**     | `orders` 테이블 컬럼으로 통합           |
