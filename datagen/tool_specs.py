"""Function calling tool specifications and validator stubs.

이 모듈은 프로젝트 전반에서 공유되는 함수 계약의 단일 원본입니다.
- OpenAI/Qwen용 `tools`
- 프롬프트용 `tools_return_format`
- validator가 사용하는 타입 힌트/목업 함수
"""
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
    only_open: Optional[bool]
    sort: Optional[str]


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
    only_open: Optional[bool] = None,
    sort: Optional[str] = None,
) -> SearchRestaurantsResponse:
    page = 1
    page_size = 20
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
    return address_id or "53e17944-5ee3-4783-9a3e-2e39796d6491"


async def list_addresses(
    *,
    user_id: str,
) -> list[Address]:
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
    return "e4b7c689-19a2-4c3f-b9d1-7f5a38e2d104"


async def get_order_status(
    *,
    user_id: str,
    order_id: str,
) -> OrderStatusResponse:
    return {
        "order_id": order_id,
        "status": "pending",
        "payment_status": "pending",
        "paid_at": None,
        "created_at": "2026-02-14T18:55:00+09:00",
    }


tools = [
    {
        "type": "function",
        "name": "search_restaurants",
        "description": "식당 목록을 검색/필터/정렬하여 반환합니다. 식당명이나 메뉴명으로 검색하거나, 카테고리·최소 평점·영업 여부로 필터링할 수 있습니다. 검색 결과는 백엔드 정책에 따라 항상 1페이지부터 정해진 개수만 반환됩니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "자유 검색어. 메뉴명, 요리명, 브랜드명, 식당명, 세부 키워드에 사용합니다 (예: '치킨', '피자', '초밥', '라멘', '짜장면', '미스터피자'). 사용자가 메뉴/브랜드만 말하면 query만 사용하고, category는 자동추론하지 않습니다."
                },
                "category": {
                    "type": "string",
                    "description": "고정 음식 카테고리 필터. 아래 taxonomy 값에만 사용합니다: '한식', '중식', '일식', '분식', '카페', '야식'. 사용자가 cuisine/도메인만 말하면 category만 사용하고 query는 만들지 않습니다. 같은 의미를 query와 category에 동시에 넣지 마세요."
                },
                "min_rating": {
                    "type": "number",
                    "description": "고객이 '4.5 이상', '최소 4.3'처럼 숫자 기준을 명시한 경우에만 사용하는 최소 평점 필터입니다. '평점 높은 곳', '추천해줘'처럼 모호한 표현만 있으면 이 파라미터는 생략합니다. '평점 높은 순', '별점순'은 정렬 기준이므로 sort로 처리하고 min_rating을 임의로 추가하지 않습니다."
                },
                "only_open": {
                    "type": "boolean",
                    "description": "고객이 '영업 중인 곳만', '지금 열려 있는 곳만'처럼 명시적으로 요청한 경우에만 true를 사용합니다. 영업 여부를 특정하지 않으면 이 파라미터는 생략합니다. 필터를 걸지 않는 기본 상태는 false를 명시하는 대신 생략으로 표현합니다."
                },
                "sort": {
                    "type": "string",
                    "description": "고객이 평점순, 관련도순, 배달비 낮은 순처럼 정렬 기준을 명시한 경우에만 사용합니다. 정렬을 특정하지 않으면 이 파라미터는 생략하며, 백엔드는 기본적으로 별점 높은 순으로 반환합니다."
                }
            },
            "required": [],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "get_restaurant_detail",
        "description": "특정 식당의 기본 정보(이름, 카테고리, 평점, 영업 여부)와 메뉴 목록을 반환합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "restaurant_id": {
                    "type": "string",
                    "description": "조회할 식당의 UUID"
                },
                "at": {
                    "type": "string",
                    "description": "영업 여부를 판단할 기준 시각 (ISO 8601 형식, 생략 시 현재 시각)"
                }
            },
            "required": ["restaurant_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "upsert_address",
        "description": "배송지를 새로 등록하거나 기존 배송지를 수정합니다. address_id를 전달하면 수정, 생략하면 신규 생성합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "배송지를 소유한 사용자 UUID"},
                "address_id": {"type": "string", "description": "수정할 배송지 UUID (신규 생성 시 생략)"},
                "recipient_name": {"type": "string", "description": "수령인 이름"},
                "phone": {"type": "string", "description": "수령인 연락처"},
                "line1": {"type": "string", "description": "기본 주소"},
                "line2": {"type": "string", "description": "상세 주소 (동·호수 등)"},
                "is_default": {"type": "boolean", "description": "기본 배송지 여부", "default": False},
                "gate_password": {"type": "string", "description": "공동현관 비밀번호"},
                "delivery_note": {"type": "string", "description": "배달 요청 사항"}
            },
            "required": ["user_id", "recipient_name", "phone", "line1"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "list_addresses",
        "description": "사용자의 저장된 배송지 목록을 반환합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "배송지를 조회할 사용자 UUID"}
            },
            "required": ["user_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "get_cart",
        "description": "사용자의 현재 장바구니를 조회합니다. 담긴 메뉴 항목, 수량, 소계 금액 등을 반환합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "장바구니를 조회할 사용자 UUID"}
            },
            "required": ["user_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "add_to_cart",
        "description": "장바구니에 메뉴 항목을 추가합니다. 1카트=1식당 제약이 있으며, 다른 식당 메뉴 추가 시 기존 카트가 교체될 수 있습니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "장바구니 소유 사용자 UUID"},
                "restaurant_id": {"type": "string", "description": "메뉴가 속한 식당 UUID"},
                "menu_item_id": {"type": "string", "description": "추가할 메뉴 항목 UUID"},
                "quantity": {"type": "integer", "description": "추가 수량 (1 이상)", "minimum": 1},
                "special_request": {"type": "string", "description": "해당 항목에 대한 요청 사항 (예: '소스 추가')"}
            },
            "required": ["user_id", "restaurant_id", "menu_item_id", "quantity"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "update_cart_item",
        "description": "장바구니의 특정 항목 수량 또는 요청 사항을 수정합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "장바구니 소유 사용자 UUID"},
                "cart_item_id": {"type": "string", "description": "수정할 장바구니 항목 UUID"},
                "quantity": {"type": "integer", "description": "변경할 수량 (생략 시 기존 수량 유지)", "minimum": 1},
                "special_request": {"type": "string", "description": "변경할 요청 사항 (생략 시 기존 값 유지)"}
            },
            "required": ["user_id", "cart_item_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "remove_cart_items",
        "description": "장바구니에서 지정한 항목들을 삭제합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "장바구니 소유 사용자 UUID"},
                "cart_item_ids": {"type": "array", "items": {"type": "string"}, "description": "삭제할 장바구니 항목 UUID 목록"}
            },
            "required": ["user_id", "cart_item_ids"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "prepare_checkout",
        "description": "주문 생성 전 최종 금액을 계산하고 스냅샷을 생성합니다. 카트와 배송지를 조회하여 subtotal·total을 계산합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "주문할 사용자 UUID"},
                "address_id": {"type": "string", "description": "배송에 사용할 배송지 UUID"},
                "delivery_note": {"type": "string", "description": "추가 배달 요청 사항"}
            },
            "required": ["user_id", "address_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "place_order",
        "description": "주문을 확정하고 order_items를 생성합니다. prepare_checkout에서 받은 스냅샷을 기반으로 주문을 INSERT하고 카트를 비웁니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "snapshot": {"type": "object", "description": "prepare_checkout이 반환한 CheckoutSnapshot 객체"},
                "payment_method": {"type": "string", "description": "결제 수단 (예: 'card', 'kakao')"},
                "pg_id": {"type": "string", "description": "PG사 거래 ID (선택)"}
            },
            "required": ["snapshot", "payment_method"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "get_order_status",
        "description": "주문 상태와 결제 상태를 조회합니다. 주문 진행 단계(pending/paid/preparing/delivering/delivered/cancelled)와 결제 상태를 반환합니다. 이 함수는 고객이 실제로 주문 상태/결제 상태 조회를 원하고, 조회 가능한 주문 UUID(order_id)가 이미 확보된 경우에만 호출합니다. 첫 대화에서 주문번호가 없으면 호출하지 말고 먼저 주문번호를 요청하는 clarification text를 생성하세요. 고객이 말한 번호가 UUID 형식이 아니거나 시스템에서 조회 가능한 주문 ID가 아니면 바로 호출하지 말고 조회 가능한 주문번호를 다시 요청하세요. 환불 요청, 보상 요청, 버그 신고처럼 정책 처리나 민원 접수가 핵심인 경우에는 주문번호가 함께 있어도 이 함수를 호출하지 말고 정책/안내 text를 우선 생성하세요.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "주문 소유 사용자 UUID"},
                "order_id": {"type": "string", "description": "조회할 주문 UUID"}
            },
            "required": ["user_id", "order_id"],
            "additionalProperties": False
        }
    },
]


tools_return_format = [
    {
        "function_name": "search_restaurants",
        "result_columns_format": {
            "items": "list(dict[restaurant_id: string, name: string, category: string, rating_avg: float, is_open: boolean, min_order_amount: integer])",
            "pagination": "dict[page: integer, page_size: integer, total_items: integer, total_pages: integer]",
            "applied_filters": "dict[query: string|null, category: string|null, min_rating: float|null, only_open: boolean|null, sort: string|null]",
        },
    },
    {
        "function_name": "get_restaurant_detail",
        "result_columns_format": {
            "restaurant_id": "string",
            "name": "string",
            "category": "string",
            "rating_avg": "float",
            "is_open": "boolean",
            "checked_at": "string (ISO 8601)",
            "menus": "list(dict[menu_item_id: string, name: string, price: integer, is_available: boolean])",
        },
    },
    {"function_name": "upsert_address", "result_columns_format": {"return": "string (생성/수정된 배송지 UUID)"}},
    {
        "function_name": "list_addresses",
        "result_columns_format": {
            "return": "list(dict[address_id: string, user_id: string, recipient_name: string, phone: string, line1: string, line2: string|null, is_default: boolean])",
        },
    },
    {
        "function_name": "get_cart",
        "result_columns_format": {
            "return": "dict[cart_id: string, user_id: string, restaurant_id: string, items: list(dict[cart_item_id: string, menu_item_id: string, menu_name: string, quantity: integer, unit_price_snapshot: integer, special_request: string|null, line_total: integer]), item_count: integer, subtotal: integer] | null (장바구니가 없으면 null 반환)",
        },
    },
    {
        "function_name": "add_to_cart",
        "result_columns_format": {
            "cart_id": "string",
            "user_id": "string",
            "restaurant_id": "string",
            "items": "list(dict[cart_item_id: string, menu_item_id: string, menu_name: string, quantity: integer, unit_price_snapshot: integer, special_request: string|null, line_total: integer])",
            "item_count": "integer",
            "subtotal": "integer",
        },
    },
    {
        "function_name": "update_cart_item",
        "result_columns_format": {
            "cart_id": "string",
            "user_id": "string",
            "restaurant_id": "string",
            "items": "list(dict[cart_item_id: string, menu_item_id: string, menu_name: string, quantity: integer, unit_price_snapshot: integer, special_request: string|null, line_total: integer])",
            "item_count": "integer",
            "subtotal": "integer",
        },
    },
    {
        "function_name": "remove_cart_items",
        "result_columns_format": {
            "cart_id": "string",
            "user_id": "string",
            "restaurant_id": "string",
            "removed_cart_item_ids": "list(string)",
            "items": "list(dict[cart_item_id: string, menu_item_id: string, menu_name: string, quantity: integer, unit_price_snapshot: integer, special_request: string|null, line_total: integer])",
            "item_count": "integer",
            "subtotal": "integer",
        },
    },
    {
        "function_name": "prepare_checkout",
        "result_columns_format": {
            "user_id": "string",
            "cart_id": "string",
            "restaurant_id": "string",
            "address_id": "string",
            "delivery_recipient_name": "string",
            "delivery_phone": "string",
            "delivery_line1": "string",
            "delivery_line2": "string|null",
            "delivery_note": "string|null",
            "items": "list(dict[cart_item_id: string, menu_item_id: string, menu_name: string, quantity: integer, unit_price_snapshot: integer, special_request: string|null, line_total: integer])",
            "subtotal": "integer",
            "total": "integer",
        },
    },
    {"function_name": "place_order", "result_columns_format": {"return": "string (생성된 주문 UUID)"}},
    {
        "function_name": "get_order_status",
        "result_columns_format": {
            "order_id": "string",
            "status": "string (pending|paid|preparing|delivering|delivered|cancelled)",
            "payment_status": "string (pending|paid|failed|cancelled|refunded)",
            "paid_at": "string (ISO 8601)|null",
            "created_at": "string (ISO 8601)",
        },
    },
]
