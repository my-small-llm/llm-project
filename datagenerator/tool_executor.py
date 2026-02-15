"""tool_calls의 응답을 스키마를 준수하는 동적 생성값으로 교체하는 유틸리티.

custom_functions.py의 TypedDict 스키마를 기준으로 삼되,
실제 응답 내용은 tool_call의 인자를 반영하여 동적으로 생성합니다.
"""
from __future__ import annotations

import json
import logging
import random
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 데이터 풀 (음식 배달 도메인)
# ---------------------------------------------------------------------------

_RESTAURANT_POOL: dict[str, dict] = {
    "피자": {
        "names": ["피자나라", "도미노피자", "피자헛", "피자스쿨", "마르게리타하우스"],
        "menus": [
            ("페퍼로니 피자", 21900), ("치즈 피자", 19900), ("고르곤졸라 피자", 24900),
            ("불고기 피자", 22900), ("새우 피자", 23900), ("콤비네이션 피자", 25900),
        ],
    },
    "치킨": {
        "names": ["교촌치킨", "BBQ치킨", "굽네치킨", "처갓집양념치킨", "페리카나"],
        "menus": [
            ("후라이드 치킨", 18000), ("양념 치킨", 19000), ("반반 치킨", 19000),
            ("간장 치킨", 20000), ("파닭", 21000), ("순살 치킨", 19500),
        ],
    },
    "한식": {
        "names": ["한솥도시락", "정통국밥", "돌솥비빔밥집", "삼겹살명가", "청국장마을"],
        "menus": [
            ("된장찌개", 8000), ("김치찌개", 8000), ("비빔밥", 9000),
            ("삼겹살 1인분", 15000), ("순두부찌개", 8500), ("갈비탕", 12000),
        ],
    },
    "중식": {
        "names": ["홍콩반점", "베이징키친", "중화요리장", "차이나하우스", "팬더차이나"],
        "menus": [
            ("짜장면", 7000), ("짬뽕", 8000), ("탕수육(소)", 18000),
            ("볶음밥", 8000), ("마파두부", 10000), ("깐풍기", 22000),
        ],
    },
    "일식": {
        "names": ["스시하루", "라멘본점", "돈부리야", "사쿠라스시", "교토라멘"],
        "menus": [
            ("스시 세트", 22000), ("쇼유라멘", 11000), ("돈가스", 12000),
            ("연어 덮밥", 13000), ("우동", 9000), ("된장라멘", 11500),
        ],
    },
    "분식": {
        "names": ["김밥천국", "분식나라", "떡볶이명가", "엽기떡볶이", "국물떡볶이"],
        "menus": [
            ("참치김밥", 3500), ("떡볶이", 4500), ("순대", 4000),
            ("라면", 3500), ("오뎅탕", 4000), ("치즈볶이", 5000),
        ],
    },
}

_ALL_CATEGORIES = list(_RESTAURANT_POOL.keys())

_RECIPIENT_NAMES = [
    "김민준", "이서연", "박지호", "최수아", "정서준",
    "강도현", "윤지아", "임현우", "오채원", "한지훈",
]
_ADDR_DISTRICTS = [
    "서울특별시 강남구", "서울특별시 마포구", "서울특별시 서초구",
    "경기도 성남시 분당구", "경기도 수원시 영통구",
    "부산광역시 해운대구", "인천광역시 연수구",
]
_ADDR_STREETS = [
    "테헤란로", "강남대로", "종로", "홍대입구로",
    "이태원로", "판교로", "분당로", "광교중앙로",
]
_DELIVERY_NOTES = [
    "문 앞에 두고 문자 주세요", "벨 눌러주세요", "경비실에 맡겨주세요",
    "조심히 올려주세요", None, None,
]
_ORDER_STATUSES = ["pending", "accepted", "preparing", "delivering", "delivered"]
_PAYMENT_STATUSES = ["unpaid", "paid"]


# ---------------------------------------------------------------------------
# 공통 헬퍼
# ---------------------------------------------------------------------------

def _uuid() -> str:
    return str(uuid.uuid4())


def _pick_category(category: Optional[str]) -> str:
    """입력된 카테고리가 있으면 사용, 없으면 랜덤."""
    return category if category in _RESTAURANT_POOL else random.choice(_ALL_CATEGORIES)


def _make_menu_items(category: str, n: int = 3) -> list[dict]:
    pool = _RESTAURANT_POOL[category]["menus"]
    chosen = random.sample(pool, min(n, len(pool)))
    return [
        {
            "menu_item_id": _uuid(),
            "name": name,
            "price": price,
            "is_available": random.choices([True, False], weights=[9, 1])[0],
        }
        for name, price in chosen
    ]


def _make_cart_item(
    menu_item_id: str,
    quantity: int,
    special_request: Optional[str],
    unit_price: int,
) -> dict:
    return {
        "cart_item_id": _uuid(),
        "menu_item_id": menu_item_id,
        "menu_name": "메뉴",  # 실제 이름은 알 수 없으므로 placeholder
        "quantity": quantity,
        "unit_price_snapshot": unit_price,
        "special_request": special_request,
        "line_total": unit_price * quantity,
    }


# ---------------------------------------------------------------------------
# 함수별 동적 응답 생성기
# ---------------------------------------------------------------------------

def _gen_search_restaurants(
    query: Optional[str] = None,
    category: Optional[str] = None,
    min_rating: Optional[float] = None,
    only_open: bool = False,
    sort: str = "relevance",
    page: int = 1,
    page_size: int = 20,
    **_: Any,
) -> dict:
    cat = _pick_category(category)
    names = _RESTAURANT_POOL[cat]["names"]
    min_r = min_rating or 3.0

    items = [
        {
            "restaurant_id": _uuid(),
            "name": name,
            "category": cat,
            "rating_avg": round(random.uniform(max(min_r, 3.0), 5.0), 1),
            "is_open": True if only_open else random.choice([True, False]),
            "min_delivery_fee": random.choice([1000, 2000, 3000, 3500]),
        }
        for name in random.sample(names, min(3, len(names)))
    ]
    total = len(items)
    return {
        "items": items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": max(1, -(-total // page_size)),
        },
        "applied_filters": {
            "query": query,
            "category": category,
            "min_rating": min_rating,
            "only_open": only_open,
            "sort": sort,
        },
    }


def _gen_get_restaurant_detail(
    restaurant_id: str,
    at: Any = None,
    **_: Any,
) -> dict:
    cat = random.choice(_ALL_CATEGORIES)
    checked_at = (
        at.isoformat() if isinstance(at, datetime)
        else datetime.now().isoformat()
    )
    return {
        "restaurant_id": restaurant_id,
        "name": random.choice(_RESTAURANT_POOL[cat]["names"]),
        "category": cat,
        "rating_avg": round(random.uniform(3.5, 5.0), 1),
        "is_open": random.choice([True, False]),
        "checked_at": checked_at,
        "menus": _make_menu_items(cat, n=random.randint(3, 5)),
    }


def _gen_upsert_address(
    user_id: str,
    address_id: Optional[str] = None,
    **_: Any,
) -> str:
    return address_id or _uuid()


def _gen_list_addresses(user_id: str, **_: Any) -> list[dict]:
    n = random.randint(1, 3)
    addresses = []
    for i in range(n):
        district = random.choice(_ADDR_DISTRICTS)
        street = random.choice(_ADDR_STREETS)
        num = random.randint(1, 500)
        addresses.append({
            "address_id": _uuid(),
            "user_id": user_id,
            "recipient_name": random.choice(_RECIPIENT_NAMES),
            "phone": f"010-{random.randint(1000,9999)}-{random.randint(1000,9999)}",
            "line1": f"{district} {street} {num}",
            "line2": f"{random.randint(1,30)}층 {random.randint(101,999)}호" if random.random() > 0.3 else None,
            "is_default": i == 0,
            "gate_password": f"*{random.randint(1000,9999)}#" if random.random() > 0.6 else None,
            "delivery_note": random.choice(_DELIVERY_NOTES),
        })
    return addresses


def _gen_cart_summary(
    user_id: str,
    restaurant_id: str,
    items: list[dict],
) -> dict:
    item_count = sum(i["quantity"] for i in items)
    subtotal = sum(i["line_total"] for i in items)
    return {
        "cart_id": _uuid(),
        "user_id": user_id,
        "restaurant_id": restaurant_id,
        "items": items,
        "item_count": item_count,
        "subtotal": subtotal,
    }


def _gen_get_cart(user_id: str, **_: Any) -> Optional[dict]:
    if random.random() < 0.1:
        return None  # 10% 확률로 빈 장바구니
    cat = random.choice(_ALL_CATEGORIES)
    menu_pool = _RESTAURANT_POOL[cat]["menus"]
    chosen = random.sample(menu_pool, random.randint(1, 3))
    items = [
        {
            "cart_item_id": _uuid(),
            "menu_item_id": _uuid(),
            "menu_name": name,
            "quantity": random.randint(1, 3),
            "unit_price_snapshot": price,
            "special_request": random.choice([None, None, "덜 맵게", "소스 추가"]),
            "line_total": price * random.randint(1, 3),
        }
        for name, price in chosen
    ]
    # line_total 수정 (quantity와 일치)
    for item in items:
        item["line_total"] = item["unit_price_snapshot"] * item["quantity"]
    return _gen_cart_summary(user_id, _uuid(), items)


def _gen_add_to_cart(
    user_id: str,
    restaurant_id: str,
    menu_item_id: str,
    quantity: int,
    special_request: Optional[str] = None,
    **_: Any,
) -> dict:
    unit_price = random.choice([8000, 9000, 11000, 15000, 18000, 21900, 24900])
    new_item = {
        "cart_item_id": _uuid(),
        "menu_item_id": menu_item_id,
        "menu_name": "메뉴",
        "quantity": quantity,
        "unit_price_snapshot": unit_price,
        "special_request": special_request,
        "line_total": unit_price * quantity,
    }
    return _gen_cart_summary(user_id, restaurant_id, [new_item])


def _gen_update_cart_item(
    user_id: str,
    cart_item_id: str,
    quantity: Optional[int] = None,
    special_request: Optional[str] = None,
    **_: Any,
) -> dict:
    final_qty = quantity if quantity is not None else random.randint(1, 3)
    unit_price = random.choice([8000, 9000, 11000, 15000, 18000, 21900])
    item = {
        "cart_item_id": cart_item_id,
        "menu_item_id": _uuid(),
        "menu_name": "메뉴",
        "quantity": final_qty,
        "unit_price_snapshot": unit_price,
        "special_request": special_request,
        "line_total": unit_price * final_qty,
    }
    return _gen_cart_summary(user_id, _uuid(), [item])


def _gen_remove_cart_items(
    user_id: str,
    cart_item_ids: list[str],
    **_: Any,
) -> dict:
    base = _gen_cart_summary(user_id, _uuid(), [])
    base["removed_cart_item_ids"] = cart_item_ids
    return base


def _gen_prepare_checkout(
    user_id: str,
    address_id: str,
    delivery_note: Optional[str] = None,
    **_: Any,
) -> dict:
    cat = random.choice(_ALL_CATEGORIES)
    menu_pool = _RESTAURANT_POOL[cat]["menus"]
    chosen = random.sample(menu_pool, random.randint(1, 3))
    items = [
        {
            "cart_item_id": _uuid(),
            "menu_item_id": _uuid(),
            "menu_name": name,
            "quantity": random.randint(1, 2),
            "unit_price_snapshot": price,
            "special_request": None,
            "line_total": price * random.randint(1, 2),
        }
        for name, price in chosen
    ]
    for item in items:
        item["line_total"] = item["unit_price_snapshot"] * item["quantity"]
    subtotal = sum(i["line_total"] for i in items)
    delivery_fee = random.choice([1000, 2000, 3000, 3500])
    return {
        "user_id": user_id,
        "address_id": address_id,
        "delivery_note": delivery_note,
        "items": items,
        "subtotal": subtotal,
        "delivery_fee": delivery_fee,
        "total": subtotal + delivery_fee,
    }


def _gen_place_order(**_: Any) -> str:
    return _uuid()


def _gen_get_order_status(
    user_id: str,
    order_id: str,
    **_: Any,
) -> dict:
    created = datetime.now() - timedelta(minutes=random.randint(5, 120))
    return {
        "order_id": order_id,
        "user_id": user_id,
        "status": random.choice(_ORDER_STATUSES),
        "payment_status": random.choice(_PAYMENT_STATUSES),
        "total": random.choice([12000, 18000, 22000, 25000, 32000, 45000]),
        "created_at": created.isoformat(),
    }


# ---------------------------------------------------------------------------
# 함수명 → 생성기 매핑
# ---------------------------------------------------------------------------

_GENERATORS: dict[str, Any] = {
    "search_restaurants": _gen_search_restaurants,
    "get_restaurant_detail": _gen_get_restaurant_detail,
    "upsert_address": _gen_upsert_address,
    "list_addresses": _gen_list_addresses,
    "get_cart": _gen_get_cart,
    "add_to_cart": _gen_add_to_cart,
    "update_cart_item": _gen_update_cart_item,
    "remove_cart_items": _gen_remove_cart_items,
    "prepare_checkout": _gen_prepare_checkout,
    "place_order": _gen_place_order,
    "get_order_status": _gen_get_order_status,
}


def _call_generator(name: str, arguments: dict) -> Any:
    gen = _GENERATORS.get(name)
    if gen is None:
        raise ValueError(f"알 수 없는 함수: {name}")
    return gen(**arguments)


# ---------------------------------------------------------------------------
# 공개 API
# ---------------------------------------------------------------------------

def replace_tool_responses(messages: list[dict]) -> list[dict]:
    """messages 리스트에서 tool 응답을 동적 생성값으로 교체.

    assistant 메시지의 tool_calls를 보고 직후에 오는 role=tool 메시지의 content를
    스키마를 준수하는 동적 생성 응답으로 덮어씁니다.
    생성에 실패하면 원본을 유지합니다.

    Args:
        messages: role/content/(tool_calls) 구조의 메시지 리스트.

    Returns:
        tool 응답이 교체된 새 메시지 리스트.
    """
    result: list[dict] = []
    pending_calls: list[dict] = []

    for msg in messages:
        role = msg.get("role")

        if role == "assistant" and msg.get("tool_calls"):
            pending_calls = list(msg["tool_calls"])
            result.append(msg)

        elif role == "tool" and pending_calls:
            tool_call = pending_calls.pop(0)
            fn_name = tool_call["function"]["name"]
            fn_args = tool_call["function"].get("arguments", {})

            try:
                ret = _call_generator(fn_name, fn_args)
                new_content = json.dumps(ret, ensure_ascii=False)
                result.append({**msg, "content": new_content})
            except Exception as exc:
                logger.warning("응답 생성 실패 (%s): %s — 원본 tool 응답 유지", fn_name, exc)
                result.append(msg)

        else:
            if role != "tool":
                pending_calls = []
            result.append(msg)

    return result
