# 이 파일은 docs/functioncalling_sections.py의 스키마(반환 필드명, 구조)를 기준으로
# 작성된 목업(mock) 구현체입니다. 실제 DB 대신 하드코딩된 더미 데이터를 반환합니다.
from __future__ import annotations

from datetime import datetime
from typing import Optional, TypedDict


class RestaurantSummary(TypedDict):
    restaurant_id: str
    name: str
    category: str
    rating_avg: float
    is_open: bool
    min_order_amount: int


class Pagination(TypedDict):
    page: int
    page_size: int
    total_items: int
    total_pages: int


class SearchFilters(TypedDict):
    query: Optional[str]
    category: Optional[str]
    min_rating: Optional[float]
    only_open: bool
    sort: str


class SearchRestaurantsResponse(TypedDict):
    items: list[RestaurantSummary]
    pagination: Pagination
    applied_filters: SearchFilters


class MenuItem(TypedDict):
    menu_item_id: str
    name: str
    price: int
    is_available: bool


class RestaurantDetailResponse(TypedDict):
    restaurant_id: str
    name: str
    category: str
    rating_avg: float
    is_open: bool
    checked_at: str
    menus: list[MenuItem]


class Address(TypedDict):
    address_id: str
    user_id: str
    recipient_name: str
    phone: str
    line1: str
    line2: Optional[str]
    is_default: bool


class CartItem(TypedDict):
    cart_item_id: str
    menu_item_id: str
    menu_name: str
    quantity: int
    unit_price_snapshot: int
    special_request: Optional[str]
    line_total: int


class CartSummary(TypedDict):
    cart_id: str
    user_id: str
    restaurant_id: str
    items: list[CartItem]
    item_count: int
    subtotal: int


class RemoveCartItemsResponse(CartSummary):
    removed_cart_item_ids: list[str]


class CheckoutSnapshot(TypedDict):
    user_id: str
    cart_id: str
    restaurant_id: str
    address_id: str
    delivery_recipient_name: str
    delivery_phone: str
    delivery_line1: str
    delivery_line2: Optional[str]
    delivery_note: Optional[str]
    items: list[CartItem]
    subtotal: int
    total: int


class OrderStatusResponse(TypedDict):
    order_id: str
    status: str
    payment_status: str
    paid_at: Optional[str]
    created_at: str


async def search_restaurants(
    *,
    query: Optional[str] = None,
    category: Optional[str] = None,
    min_rating: Optional[float] = None,
    only_open: bool = False,
    sort: str = "relevance",
    page: int = 1,
    page_size: int = 20,
) -> SearchRestaurantsResponse:
    """음식점을 검색/필터/정렬하여 페이지 단위로 반환합니다.

    Args:
        query: 음식점 이름 또는 메뉴 키워드
        category: 음식 카테고리 필터 (예: "피자", "한식")
        min_rating: 최소 평점 필터 (0.0 ~ 5.0)
        only_open: True이면 현재 영업 중인 음식점만 반환
        sort: 정렬 기준 ("relevance" | "rating" | "delivery_fee")
        page: 페이지 번호 (1부터 시작)
        page_size: 페이지당 항목 수

    Returns:
        items: 음식점 요약 목록 (restaurant_id, name, category, rating_avg, is_open, min_order_amount)
        pagination: 페이지 정보 (page, page_size, total_items, total_pages)
        applied_filters: 실제 적용된 필터 조건
    """
    items = [
        {
            "restaurant_id": "76a2d649-8a13-49fb-8b61-d63fbcaec5ea",
            "name": "미스터피자",
            "category": "피자",
            "rating_avg": 4.7,
            "is_open": True,
            "min_order_amount": 15000,
        },
        {
            "restaurant_id": "f0e692f8-381d-46ff-b3b1-1cef9674ab55",
            "name": "도미노피자",
            "category": "피자",
            "rating_avg": 4.5,
            "is_open": False,
            "min_order_amount": 12000,
        },
    ]
    return {
        "items": items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": len(items),
            "total_pages": 1,
        },
        "applied_filters": {
            "query": query,
            "category": category,
            "min_rating": min_rating,
            "only_open": only_open,
            "sort": sort,
        },
    }


async def get_restaurant_detail(
    *,
    restaurant_id: str,
    at: Optional[datetime] = None,
) -> RestaurantDetailResponse:
    """특정 음식점의 기본 정보와 메뉴 목록을 반환합니다.

    Args:
        restaurant_id: 조회할 음식점 UUID
        at: 영업 여부 판단 기준 시각 (None이면 현재 시각)

    Returns:
        restaurant_id, name, category, rating_avg, is_open: 음식점 기본 정보
        checked_at: 영업 여부 확인 시각 (ISO 8601)
        menus: 메뉴 목록 (menu_item_id, name, price, is_available)
    """
    return {
        "restaurant_id": restaurant_id,
        "name": "미스터피자",
        "category": "피자",
        "rating_avg": 4.7,
        "is_open": True,
        "checked_at": (at or datetime.now()).isoformat(),
        "menus": [
            {
                "menu_item_id": "210b0ddf-b1f7-4820-8f6b-de770ffc7440",
                "name": "페퍼로니 피자",
                "price": 21900,
                "is_available": True,
            },
            {
                "menu_item_id": "b0a35e41-abd0-4d81-9a21-e6ad5dd44e3a",
                "name": "치즈오븐스파게티",
                "price": 8900,
                "is_available": True,
            },
        ],
    }


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
) -> str:
    """배송지를 신규 생성하거나 기존 배송지를 수정합니다.

    Args:
        user_id: 배송지 소유 사용자 UUID
        address_id: 수정할 배송지 UUID (None이면 신규 생성)
        recipient_name: 수령인 이름
        phone: 수령인 연락처
        line1: 기본 주소
        line2: 상세 주소 (동·호수 등)
        is_default: True이면 기본 배송지로 설정
        gate_password: 공동현관 비밀번호
        delivery_note: 배달 요청 사항

    Returns:
        생성 또는 수정된 배송지 UUID
    """
    return address_id or "53e17944-5ee3-4783-9a3e-2e39796d6491"


async def list_addresses(
    *,
    user_id: str,
) -> list[Address]:
    """사용자의 저장된 배송지 목록을 반환합니다.

    Args:
        user_id: 조회할 사용자 UUID

    Returns:
        배송지 목록 (address_id, user_id, recipient_name, phone, line1, line2, is_default)
    """
    return [
        {
            "address_id": "53e17944-5ee3-4783-9a3e-2e39796d6491",
            "user_id": user_id,
            "recipient_name": "정서준",
            "phone": "010-3861-6707",
            "line1": "서울시 송파구 테헤란로 355",
            "line2": "322호",
            "is_default": True,
        }
    ]


async def get_cart(
    *,
    user_id: str,
) -> Optional[CartSummary]:
    """사용자의 현재 장바구니를 반환합니다.

    Args:
        user_id: 조회할 사용자 UUID

    Returns:
        cart_id, user_id, restaurant_id, items, item_count, subtotal.
        장바구니가 없으면 None.
    """
    items = [
        {
            "cart_item_id": "1b132098-ef57-4ddb-adda-e85606bc2e66",
            "menu_item_id": "210b0ddf-b1f7-4820-8f6b-de770ffc7440",
            "menu_name": "페퍼로니 피자",
            "quantity": 1,
            "unit_price_snapshot": 21900,
            "special_request": "치즈 많이",
            "line_total": 21900,
        }
    ]
    return {
        "cart_id": "40cd0076-306b-41ce-9caf-fe8f5782ef4e",
        "user_id": user_id,
        "restaurant_id": "76a2d649-8a13-49fb-8b61-d63fbcaec5ea",
        "items": items,
        "item_count": len(items),
        "subtotal": sum(item["line_total"] for item in items),
    }


async def add_to_cart(
    *,
    user_id: str,
    restaurant_id: str,
    menu_item_id: str,
    quantity: int,
    special_request: Optional[str] = None,
) -> CartSummary:
    """장바구니에 메뉴 항목을 추가하고 갱신된 장바구니를 반환합니다.

    1카트=1식당 제약이 있으며, 다른 식당 메뉴 추가 시 기존 카트가 교체됩니다.

    Args:
        user_id: 장바구니 소유 사용자 UUID
        restaurant_id: 메뉴가 속한 음식점 UUID
        menu_item_id: 추가할 메뉴 항목 UUID
        quantity: 추가 수량 (1 이상)
        special_request: 항목별 요청 사항

    Returns:
        추가 후 장바구니 전체 상태 (CartSummary)
    """
    return {
        "cart_id": "40cd0076-306b-41ce-9caf-fe8f5782ef4e",
        "user_id": user_id,
        "restaurant_id": restaurant_id,
        "items": [
            {
                "cart_item_id": "new-cart-item-001",
                "menu_item_id": menu_item_id,
                "menu_name": "페퍼로니 피자",
                "quantity": quantity,
                "unit_price_snapshot": 21900,
                "special_request": special_request,
                "line_total": 21900 * quantity,
            }
        ],
        "item_count": quantity,
        "subtotal": 21900 * quantity,
    }


async def update_cart_item(
    *,
    user_id: str,
    cart_item_id: str,
    quantity: Optional[int] = None,
    special_request: Optional[str] = None,
) -> CartSummary:
    """장바구니의 특정 항목 수량 또는 요청 사항을 수정합니다.

    Args:
        user_id: 장바구니 소유 사용자 UUID
        cart_item_id: 수정할 장바구니 항목 UUID
        quantity: 변경할 수량 (None이면 기존 수량 유지)
        special_request: 변경할 요청 사항 (None이면 기존 값 유지)

    Returns:
        수정 후 장바구니 전체 상태 (CartSummary)
    """
    final_quantity = quantity if quantity is not None else 1
    return {
        "cart_id": "40cd0076-306b-41ce-9caf-fe8f5782ef4e",
        "user_id": user_id,
        "restaurant_id": "76a2d649-8a13-49fb-8b61-d63fbcaec5ea",
        "items": [
            {
                "cart_item_id": cart_item_id,
                "menu_item_id": "210b0ddf-b1f7-4820-8f6b-de770ffc7440",
                "menu_name": "페퍼로니 피자",
                "quantity": final_quantity,
                "unit_price_snapshot": 21900,
                "special_request": special_request,
                "line_total": 21900 * final_quantity,
            }
        ],
        "item_count": final_quantity,
        "subtotal": 21900 * final_quantity,
    }


async def remove_cart_items(
    *,
    user_id: str,
    cart_item_ids: list[str],
) -> RemoveCartItemsResponse:
    """장바구니에서 지정한 항목들을 삭제합니다.

    Args:
        user_id: 장바구니 소유 사용자 UUID
        cart_item_ids: 삭제할 장바구니 항목 UUID 목록

    Returns:
        삭제 후 장바구니 상태 + removed_cart_item_ids (실제 삭제된 항목 UUID 목록)
    """
    return {
        "cart_id": "40cd0076-306b-41ce-9caf-fe8f5782ef4e",
        "user_id": user_id,
        "restaurant_id": "76a2d649-8a13-49fb-8b61-d63fbcaec5ea",
        "removed_cart_item_ids": cart_item_ids,
        "items": [],
        "item_count": 0,
        "subtotal": 0,
    }


async def prepare_checkout(
    *,
    user_id: str,
    address_id: str,
    delivery_note: Optional[str] = None,
) -> CheckoutSnapshot:
    """주문 생성 전 최종 금액을 계산하고 스냅샷을 생성합니다.

    카트와 배송지를 조회하여 subtotal·total을 계산하고,
    place_order에 전달할 CheckoutSnapshot을 반환합니다.

    Args:
        user_id: 주문할 사용자 UUID
        address_id: 배송에 사용할 배송지 UUID
        delivery_note: 추가 배달 요청 사항

    Returns:
        user_id, cart_id, restaurant_id, address_id: 주문 주체 정보
        delivery_recipient_name, delivery_phone, delivery_line1, delivery_line2, delivery_note: 배송지 스냅샷
        items: 카트 아이템 목록 (CartItem)
        subtotal, total: 금액 정보
    """
    items: list[CartItem] = [
        {
            "cart_item_id": "1b132098-ef57-4ddb-adda-e85606bc2e66",
            "menu_item_id": "210b0ddf-b1f7-4820-8f6b-de770ffc7440",
            "menu_name": "페퍼로니 피자",
            "quantity": 1,
            "unit_price_snapshot": 21900,
            "special_request": "치즈 많이",
            "line_total": 21900,
        }
    ]
    subtotal = sum(i["line_total"] for i in items)
    return {
        "user_id": user_id,
        "cart_id": "40cd0076-306b-41ce-9caf-fe8f5782ef4e",
        "restaurant_id": "76a2d649-8a13-49fb-8b61-d63fbcaec5ea",
        "address_id": address_id,
        "delivery_recipient_name": "정서준",
        "delivery_phone": "010-3861-6707",
        "delivery_line1": "서울시 송파구 테헤란로 355",
        "delivery_line2": "322호",
        "delivery_note": delivery_note,
        "items": items,
        "subtotal": subtotal,
        "total": subtotal,
    }


async def place_order(
    *,
    snapshot: CheckoutSnapshot,
    payment_method: str,
    pg_id: Optional[str] = None,
) -> str:
    """주문을 확정하고 생성된 주문 UUID를 반환합니다.

    prepare_checkout의 스냅샷을 기반으로 주문을 생성하고 카트를 비웁니다.

    Args:
        snapshot: prepare_checkout이 반환한 CheckoutSnapshot
        payment_method: 결제 수단 (예: "card", "kakao")
        pg_id: PG사 거래 ID (선택)

    Returns:
        생성된 주문 UUID
    """
    return "e4b7c689-19a2-4c3f-b9d1-7f5a38e2d104"


async def get_order_status(
    *,
    user_id: str,
    order_id: str,
) -> OrderStatusResponse:
    """주문 상태와 결제 상태를 조회합니다.

    Args:
        user_id: 주문 소유 사용자 UUID
        order_id: 조회할 주문 UUID

    Returns:
        order_id, status, payment_status, paid_at, created_at.
        status: pending | paid | preparing | delivering | delivered | cancelled
        payment_status: pending | paid | failed | cancelled | refunded
    """
    return {
        "order_id": order_id,
        "status": "pending",
        "payment_status": "pending",
        "paid_at": None,
        "created_at": "2026-02-14T18:55:00+09:00",
    }
