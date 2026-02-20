# ================================================================
# 펑션콜링을 위한 함수 작성
# ================================================================
# 이 코드는 노트북의 "1. Init & Load Data" 셀 이후에 배치합니다.
# df_users, df_restaurants, df_menu_items, df_carts, df_cart_items,
# df_orders, df_order_items, df_addresses 가 이미 로드되어 있다고 가정합니다.
# ================================================================

from datetime import datetime, time


# 사용자가 로그인하였다고 가정
user_id = df_users.iloc[0]["id"]


# ----------------------------------------------------------------
# 2-1. 음식점 검색 (search_restaurants)
# ----------------------------------------------------------------

def search_restaurants(query=None, category=None, min_rating=None,
                       only_open=False, sort="relevance",
                       page=1, page_size=20):
    """
    음식점을 검색/필터/정렬하여 페이지 단위로 반환합니다.
    """
    result = df_restaurants.copy()

    # 키워드 검색: 식당명 또는 메뉴명
    if query:
        name_match = result["name"].str.contains(query, case=False, na=False)
        menu_match_ids = df_menu_items[
            df_menu_items["name"].str.contains(query, case=False, na=False)
        ]["restaurant_id"].unique()
        result = result[name_match | result["id"].isin(menu_match_ids)]

    # 카테고리 필터
    if category:
        result = result[result["category"] == category]

    # 최소 평점 필터
    if min_rating is not None:
        result = result[result["rating_avg"] >= min_rating]

    # 영업 여부 필터
    if only_open:
        now = datetime.now()
        is_weekend = now.weekday() >= 5
        if is_weekend:
            result = result[result["is_open_weekend"] == True]
        else:
            result = result[result["is_open_weekday"] == True]

    # 정렬
    if sort == "rating":
        result = result.sort_values("rating_avg", ascending=False)

    # 페이지네이션
    total_items = len(result)
    total_pages = max(1, -(-total_items // page_size))  # ceil division
    start = (page - 1) * page_size
    end = start + page_size
    page_result = result.iloc[start:end]

    items = []
    for _, row in page_result.iterrows():
        items.append({
            "restaurant_id": row["id"],
            "name": row["name"],
            "category": row["category"],
            "rating_avg": float(row["rating_avg"]),
            "is_open": bool(row["is_open_weekday"]),
            "min_order_amount": int(row["min_order_amount"]),
        })

    return {
        "items": items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
        },
        "applied_filters": {
            "query": query,
            "category": category,
            "min_rating": min_rating,
            "only_open": only_open,
            "sort": sort,
        },
    }


# ----------------------------------------------------------------
# 2-2. 음식점 상세 조회 (get_restaurant_detail)
# ----------------------------------------------------------------

def get_restaurant_detail(restaurant_id, at=None):
    """
    특정 음식점의 기본 정보 + 메뉴 목록을 반환합니다.
    """
    rest = df_restaurants[df_restaurants["id"] == restaurant_id]
    if rest.empty:
        return {"error": f"식당 {restaurant_id}을 찾을 수 없습니다."}
    rest = rest.iloc[0]

    check_time = at or datetime.now()
    is_weekend = check_time.weekday() >= 5
    is_open = bool(rest["is_open_weekend"] if is_weekend else rest["is_open_weekday"])

    menus = df_menu_items[df_menu_items["restaurant_id"] == restaurant_id]
    menu_list = []
    for _, m in menus.iterrows():
        menu_list.append({
            "menu_item_id": m["id"],
            "name": m["name"],
            "price": int(m["base_price"]),
            "is_available": True,
        })

    return {
        "restaurant_id": restaurant_id,
        "name": rest["name"],
        "category": rest["category"],
        "rating_avg": float(rest["rating_avg"]),
        "is_open": is_open,
        "checked_at": check_time.isoformat(),
        "menus": menu_list,
    }


# ----------------------------------------------------------------
# 2-3. 배송지 관리 (upsert_address / list_addresses)
# ----------------------------------------------------------------

def upsert_address(user_id, recipient_name, phone, line1,
                   address_id=None, line2=None, is_default=False,
                   gate_password=None, delivery_note=None):
    """
    배송지를 신규 생성 또는 수정합니다.
    """
    global df_addresses
    import uuid as _uuid

    if address_id:
        # 수정
        idx = df_addresses[
            (df_addresses["id"] == address_id) &
            (df_addresses["user_id"] == user_id)
        ].index
        if idx.empty:
            return {"error": f"배송지 {address_id}를 찾을 수 없습니다."}
        df_addresses.loc[idx, "recipient_name"] = recipient_name
        df_addresses.loc[idx, "phone"] = phone
        df_addresses.loc[idx, "line1"] = line1
        df_addresses.loc[idx, "line2"] = line2
        df_addresses.loc[idx, "is_default"] = is_default
        return address_id
    else:
        # 신규 생성
        new_id = str(_uuid.uuid4())
        if is_default:
            df_addresses.loc[
                df_addresses["user_id"] == user_id, "is_default"
            ] = False
        new_row = {
            "id": new_id,
            "user_id": user_id,
            "recipient_name": recipient_name,
            "phone": phone,
            "line1": line1,
            "line2": line2,
            "is_default": is_default,
        }
        df_addresses = pd.concat(
            [df_addresses, pd.DataFrame([new_row])], ignore_index=True
        )
        return new_id


def list_addresses(user_id):
    """
    사용자의 저장된 배송지 목록을 반환합니다.
    """
    addrs = df_addresses[df_addresses["user_id"] == user_id]
    result = []
    for _, row in addrs.iterrows():
        result.append({
            "address_id": row["id"],
            "user_id": row["user_id"],
            "recipient_name": row["recipient_name"],
            "phone": row["phone"],
            "line1": row["line1"],
            "line2": row.get("line2"),
            "is_default": bool(row["is_default"]),
        })
    return result


# ----------------------------------------------------------------
# 2-4. 장바구니 조회 (get_cart)
# ----------------------------------------------------------------

def get_cart(user_id):
    """
    사용자의 현재 장바구니를 조회하고 금액을 계산합니다.
    """
    cart = df_carts[df_carts["user_id"] == user_id]
    if cart.empty:
        return None
    cart = cart.iloc[0]
    cart_id = cart["id"]

    items_df = df_cart_items[df_cart_items["cart_id"] == cart_id]
    items = []
    for _, ci in items_df.iterrows():
        line_total = int(ci["unit_price_snapshot"]) * int(ci["quantity"])
        items.append({
            "cart_item_id": ci["id"],
            "menu_item_id": ci["menu_item_id"],
            "menu_name": ci["name_snapshot"],
            "quantity": int(ci["quantity"]),
            "unit_price_snapshot": int(ci["unit_price_snapshot"]),
            "special_request": ci.get("special_request"),
            "line_total": line_total,
        })

    subtotal = sum(i["line_total"] for i in items)
    return {
        "cart_id": cart_id,
        "user_id": user_id,
        "restaurant_id": cart["restaurant_id"],
        "items": items,
        "item_count": len(items),
        "subtotal": subtotal,
    }


# ----------------------------------------------------------------
# 2-5. 장바구니에 메뉴 추가 (add_to_cart)
# ----------------------------------------------------------------

def add_to_cart(user_id, restaurant_id, menu_item_id,
                quantity, special_request=None):
    """
    카트에 메뉴를 추가합니다 (1카트=1식당 제약).
    """
    global df_carts, df_cart_items
    import uuid as _uuid

    # 메뉴 정보 조회
    menu = df_menu_items[df_menu_items["id"] == menu_item_id]
    if menu.empty:
        return {"error": f"메뉴 {menu_item_id}를 찾을 수 없습니다."}
    menu = menu.iloc[0]

    # 카트 확인/생성
    cart = df_carts[df_carts["user_id"] == user_id]
    if cart.empty:
        cart_id = str(_uuid.uuid4())
        new_cart = {
            "id": cart_id,
            "user_id": user_id,
            "restaurant_id": restaurant_id,
        }
        df_carts = pd.concat(
            [df_carts, pd.DataFrame([new_cart])], ignore_index=True
        )
    else:
        cart_row = cart.iloc[0]
        cart_id = cart_row["id"]
        if cart_row["restaurant_id"] != restaurant_id:
            # 다른 식당이면 기존 카트 비우고 교체
            df_cart_items = df_cart_items[df_cart_items["cart_id"] != cart_id]
            df_carts.loc[
                df_carts["id"] == cart_id, "restaurant_id"
            ] = restaurant_id

    # 아이템 추가
    new_item = {
        "id": str(_uuid.uuid4()),
        "cart_id": cart_id,
        "menu_item_id": menu_item_id,
        "name_snapshot": menu["name"],
        "unit_price_snapshot": int(menu["base_price"]),
        "quantity": quantity,
    }
    if special_request:
        new_item["special_request"] = special_request

    df_cart_items = pd.concat(
        [df_cart_items, pd.DataFrame([new_item])], ignore_index=True
    )

    return get_cart(user_id)


# ----------------------------------------------------------------
# 2-6. 장바구니 아이템 수정 (update_cart_item)
# ----------------------------------------------------------------

def update_cart_item(user_id, cart_item_id, quantity=None,
                     special_request=None):
    """
    장바구니의 특정 항목 수량 또는 요청 사항을 수정합니다.
    """
    global df_cart_items

    # 사용자의 카트 확인
    cart = df_carts[df_carts["user_id"] == user_id]
    if cart.empty:
        return {"error": "장바구니가 없습니다."}
    cart_id = cart.iloc[0]["id"]

    idx = df_cart_items[
        (df_cart_items["id"] == cart_item_id) &
        (df_cart_items["cart_id"] == cart_id)
    ].index
    if idx.empty:
        return {"error": f"장바구니 항목 {cart_item_id}를 찾을 수 없습니다."}

    if quantity is not None:
        df_cart_items.loc[idx, "quantity"] = quantity
    if special_request is not None:
        df_cart_items.loc[idx, "special_request"] = special_request

    return get_cart(user_id)


# ----------------------------------------------------------------
# 2-7. 장바구니에서 아이템 삭제 (remove_cart_items)
# ----------------------------------------------------------------

def remove_cart_items(user_id, cart_item_ids):
    """
    장바구니에서 지정한 항목들을 삭제합니다.
    """
    global df_cart_items

    cart = df_carts[df_carts["user_id"] == user_id]
    if cart.empty:
        return {"error": "장바구니가 없습니다."}
    cart_id = cart.iloc[0]["id"]

    removed = df_cart_items[
        (df_cart_items["id"].isin(cart_item_ids)) &
        (df_cart_items["cart_id"] == cart_id)
    ]["id"].tolist()

    df_cart_items = df_cart_items[~df_cart_items["id"].isin(removed)]

    cart_summary = get_cart(user_id)
    if cart_summary is None:
        cart_summary = {
            "cart_id": cart_id,
            "user_id": user_id,
            "restaurant_id": cart.iloc[0]["restaurant_id"],
            "items": [],
            "item_count": 0,
            "subtotal": 0,
        }
    cart_summary["removed_cart_item_ids"] = removed
    return cart_summary


# ----------------------------------------------------------------
# 2-8. 체크아웃 준비 (prepare_checkout)
# ----------------------------------------------------------------

def prepare_checkout(user_id, address_id, delivery_note=None):
    """
    주문 생성 전 최종 금액 계산 및 스냅샷을 생성합니다.
    """
    cart_summary = get_cart(user_id)
    if cart_summary is None:
        return {"error": "장바구니가 비어 있습니다."}

    addr = df_addresses[
        (df_addresses["id"] == address_id) &
        (df_addresses["user_id"] == user_id)
    ]
    if addr.empty:
        return {"error": f"배송지 {address_id}를 찾을 수 없습니다."}
    addr = addr.iloc[0]

    subtotal = cart_summary["subtotal"]
    return {
        "user_id": user_id,
        "cart_id": cart_summary["cart_id"],
        "restaurant_id": cart_summary["restaurant_id"],
        "address_id": address_id,
        "delivery_recipient_name": addr["recipient_name"],
        "delivery_phone": addr["phone"],
        "delivery_line1": addr["line1"],
        "delivery_line2": addr.get("line2"),
        "delivery_note": delivery_note,
        "items": cart_summary["items"],
        "subtotal": subtotal,
        "total": subtotal,
    }


# ----------------------------------------------------------------
# 2-9. 주문 확정 (place_order)
# ----------------------------------------------------------------

def place_order(snapshot, payment_method, pg_id=None):
    """
    주문을 확정하고 order_items를 생성합니다.
    """
    global df_orders, df_order_items, df_cart_items
    import uuid as _uuid

    order_id = str(_uuid.uuid4())
    now = datetime.now().isoformat()

    new_order = {
        "id": order_id,
        "user_id": snapshot["user_id"],
        "restaurant_id": snapshot["restaurant_id"],
        "status": "pending",
        "delivery_recipient_name": snapshot["delivery_recipient_name"],
        "delivery_phone": snapshot["delivery_phone"],
        "delivery_line1": snapshot["delivery_line1"],
        "delivery_line2": snapshot.get("delivery_line2"),
        "subtotal_amount": snapshot["subtotal"],
        "delivery_fee_amount": 0,
        "discount_amount": 0,
        "total_amount": snapshot["total"],
        "payment_method": payment_method,
        "pg_id": pg_id,
        "payment_status": "pending",
        "paid_at": None,
    }

    df_orders = pd.concat(
        [df_orders, pd.DataFrame([new_order])], ignore_index=True
    )

    # order_items 생성
    new_items = []
    for item in snapshot["items"]:
        new_items.append({
            "id": str(_uuid.uuid4()),
            "order_id": order_id,
            "menu_item_id": item["menu_item_id"],
            "name_snapshot": item["menu_name"],
            "unit_price_snapshot": item["unit_price_snapshot"],
            "quantity": item["quantity"],
        })
    df_order_items = pd.concat(
        [df_order_items, pd.DataFrame(new_items)], ignore_index=True
    )

    # 카트 비우기
    cart_id = snapshot["cart_id"]
    df_cart_items = df_cart_items[df_cart_items["cart_id"] != cart_id]

    return order_id


# ----------------------------------------------------------------
# 2-10. 주문 상태 조회 (get_order_status)
# ----------------------------------------------------------------

def get_order_status(user_id, order_id):
    """
    주문 상태 및 결제 상태를 조회합니다.
    """
    order = df_orders[
        (df_orders["id"] == order_id) &
        (df_orders["user_id"] == user_id)
    ]
    if order.empty:
        return {"error": f"주문 {order_id}을 찾을 수 없습니다."}
    order = order.iloc[0]

    return {
        "order_id": order_id,
        "status": order["status"],
        "payment_status": order["payment_status"],
        "paid_at": order.get("paid_at"),
        "created_at": order.get("paid_at", datetime.now().isoformat()),
    }


# ================================================================
# 함수 호출 예시
# ================================================================

# ── 2-1. 음식점 검색 ──

# 1-1. "피자 파는 곳 좀 찾아줘."
result_sr_1 = search_restaurants(query="피자")
print("질의: 피자 파는 곳 좀 찾아줘.")
print("호출 결과:", result_sr_1)
print("------------------------------------------------")

# 1-2. "평점 4.5 이상인 치킨집 있어?"
result_sr_2 = search_restaurants(query="치킨", min_rating=4.5)
print("질의: 평점 4.5 이상인 치킨집 있어?")
print("호출 결과:", result_sr_2)
print("------------------------------------------------")

# 1-3. "지금 영업 중인 한식집 보여줘."
result_sr_3 = search_restaurants(category="한식", only_open=True)
print("질의: 지금 영업 중인 한식집 보여줘.")
print("호출 결과:", result_sr_3)
print("------------------------------------------------")


# ── 2-2. 음식점 상세 ──

restaurant_id = df_restaurants.iloc[0]["id"]

# 2-1. "이 식당 메뉴 뭐 있어?"
result_rd_1 = get_restaurant_detail(restaurant_id)
print("질의: 이 식당 메뉴 뭐 있어?")
print("호출 결과:", result_rd_1)
print("------------------------------------------------")

# 2-2. "이 가게 지금 영업하고 있어?"
result_rd_2 = get_restaurant_detail(restaurant_id)
print("질의: 이 가게 지금 영업하고 있어?")
print("호출 결과:", result_rd_2)
print("------------------------------------------------")


# ── 2-3. 배송지 관리 ──

# 3-1. "내 배송지 목록 보여줘."
result_la_1 = list_addresses(user_id)
print("질의: 내 배송지 목록 보여줘.")
print("호출 결과:", result_la_1)
print("------------------------------------------------")

# 3-2. "새 배송지 등록해줘."
result_ua_1 = upsert_address(
    user_id=user_id,
    recipient_name="테스트",
    phone="010-0000-0000",
    line1="서울시 강남구 역삼동 123",
    line2="5층",
    is_default=False,
)
print("질의: 새 배송지 등록해줘.")
print("호출 결과:", result_ua_1)
print("------------------------------------------------")


# ── 2-4. 장바구니 조회 ──

# 기존 카트가 있는 사용자 찾기
cart_user_id = df_carts.iloc[0]["user_id"] if not df_carts.empty else user_id

# 4-1. "내 장바구니에 뭐 들어있어?"
result_gc_1 = get_cart(cart_user_id)
print("질의: 내 장바구니에 뭐 들어있어?")
print("호출 결과:", result_gc_1)
print("------------------------------------------------")


# ── 2-5. 장바구니에 메뉴 추가 ──

first_menu = df_menu_items[
    df_menu_items["restaurant_id"] == restaurant_id
].iloc[0]

# 5-1. "이 메뉴 하나 장바구니에 넣어줘."
result_atc_1 = add_to_cart(
    user_id=user_id,
    restaurant_id=restaurant_id,
    menu_item_id=first_menu["id"],
    quantity=1,
)
print(f"질의: {first_menu['name']} 하나 장바구니에 넣어줘.")
print("호출 결과:", result_atc_1)
print("------------------------------------------------")

# 5-2. "같은 메뉴 2개 추가하고 양파 빼달라고 해줘."
result_atc_2 = add_to_cart(
    user_id=user_id,
    restaurant_id=restaurant_id,
    menu_item_id=first_menu["id"],
    quantity=2,
    special_request="양파 빼주세요",
)
print("질의: 같은 메뉴 2개 추가하고 양파 빼달라고 해줘.")
print("호출 결과:", result_atc_2)
print("------------------------------------------------")


# ── 2-6. 장바구니 아이템 수정 ──

my_cart = get_cart(user_id)
if my_cart and my_cart["items"]:
    target_item_id = my_cart["items"][0]["cart_item_id"]

    # 6-1. "수량 3개로 바꿔줘."
    result_uci_1 = update_cart_item(
        user_id=user_id,
        cart_item_id=target_item_id,
        quantity=3,
    )
    print("질의: 수량 3개로 바꿔줘.")
    print("호출 결과:", result_uci_1)
    print("------------------------------------------------")


# ── 2-7. 장바구니 아이템 삭제 ──

my_cart = get_cart(user_id)
if my_cart and my_cart["items"]:
    remove_id = my_cart["items"][-1]["cart_item_id"]

    # 7-1. "장바구니에서 이 메뉴 빼줘."
    result_rci_1 = remove_cart_items(
        user_id=user_id,
        cart_item_ids=[remove_id],
    )
    print("질의: 장바구니에서 이 메뉴 빼줘.")
    print("호출 결과:", result_rci_1)
    print("------------------------------------------------")


# ── 2-8. 체크아웃 준비 ──

# 배송지 하나 가져오기
my_addrs = list_addresses(user_id)
if my_addrs:
    addr_id = my_addrs[0]["address_id"]
else:
    addr_id = upsert_address(
        user_id=user_id,
        recipient_name="기본",
        phone="010-0000-0000",
        line1="서울시 강남구",
        is_default=True,
    )

# 8-1. "결제 전에 최종 금액 확인하고 싶어."
result_pc_1 = prepare_checkout(user_id=user_id, address_id=addr_id)
print("질의: 결제 전에 최종 금액 확인하고 싶어.")
print("호출 결과:", result_pc_1)
print("------------------------------------------------")


# ── 2-9. 주문 확정 ──

if isinstance(result_pc_1, dict) and "error" not in result_pc_1:
    # 9-1. "카드로 결제할게."
    result_po_1 = place_order(
        snapshot=result_pc_1,
        payment_method="card",
    )
    print("질의: 카드로 결제할게.")
    print("호출 결과:", result_po_1)
    print("------------------------------------------------")

    # ── 2-10. 주문 상태 조회 ──

    # 10-1. "내 주문 상태 알려줘."
    result_os_1 = get_order_status(user_id=user_id, order_id=result_po_1)
    print("질의: 내 주문 상태 알려줘.")
    print("호출 결과:", result_os_1)
    print("------------------------------------------------")
else:
    print("카트가 비어있어 주문을 진행할 수 없습니다. 먼저 add_to_cart를 실행하세요.")


# ================================================================
# 3. 함수 명세 (OpenAI Function Calling tools 형식)
# ================================================================

tools = [
    {
        "type": "function",
        "name": "search_restaurants",
        "description": "식당 목록을 검색/필터/정렬하여 페이지 단위로 반환합니다. 식당명이나 메뉴명으로 검색하거나, 카테고리·최소 평점·영업 여부로 필터링할 수 있습니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "식당명 또는 메뉴명 검색 키워드 (예: '피자', '치킨')"
                },
                "category": {
                    "type": "string",
                    "description": "음식 카테고리 필터 (예: '한식', '중식', '피자')"
                },
                "min_rating": {
                    "type": "number",
                    "description": "최소 평점 필터 (0.0 ~ 5.0)"
                },
                "only_open": {
                    "type": "boolean",
                    "description": "true이면 현재 영업 중인 식당만 반환",
                    "default": False
                },
                "sort": {
                    "type": "string",
                    "description": "정렬 기준 ('relevance' | 'rating' | 'delivery_fee')",
                    "default": "relevance"
                },
                "page": {
                    "type": "integer",
                    "description": "페이지 번호 (1부터 시작)",
                    "default": 1
                },
                "page_size": {
                    "type": "integer",
                    "description": "페이지당 항목 수",
                    "default": 20
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
                "user_id": {
                    "type": "string",
                    "description": "배송지를 소유한 사용자 UUID"
                },
                "address_id": {
                    "type": "string",
                    "description": "수정할 배송지 UUID (신규 생성 시 생략)"
                },
                "recipient_name": {
                    "type": "string",
                    "description": "수령인 이름"
                },
                "phone": {
                    "type": "string",
                    "description": "수령인 연락처"
                },
                "line1": {
                    "type": "string",
                    "description": "기본 주소"
                },
                "line2": {
                    "type": "string",
                    "description": "상세 주소 (동·호수 등)"
                },
                "is_default": {
                    "type": "boolean",
                    "description": "기본 배송지 여부",
                    "default": False
                },
                "gate_password": {
                    "type": "string",
                    "description": "공동현관 비밀번호"
                },
                "delivery_note": {
                    "type": "string",
                    "description": "배달 요청 사항"
                }
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
                "user_id": {
                    "type": "string",
                    "description": "배송지를 조회할 사용자 UUID"
                }
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
                "user_id": {
                    "type": "string",
                    "description": "장바구니를 조회할 사용자 UUID"
                }
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
                "user_id": {
                    "type": "string",
                    "description": "장바구니 소유 사용자 UUID"
                },
                "restaurant_id": {
                    "type": "string",
                    "description": "메뉴가 속한 식당 UUID"
                },
                "menu_item_id": {
                    "type": "string",
                    "description": "추가할 메뉴 항목 UUID"
                },
                "quantity": {
                    "type": "integer",
                    "description": "추가 수량 (1 이상)",
                    "minimum": 1
                },
                "special_request": {
                    "type": "string",
                    "description": "해당 항목에 대한 요청 사항 (예: '소스 추가')"
                }
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
                "user_id": {
                    "type": "string",
                    "description": "장바구니 소유 사용자 UUID"
                },
                "cart_item_id": {
                    "type": "string",
                    "description": "수정할 장바구니 항목 UUID"
                },
                "quantity": {
                    "type": "integer",
                    "description": "변경할 수량 (생략 시 기존 수량 유지)",
                    "minimum": 1
                },
                "special_request": {
                    "type": "string",
                    "description": "변경할 요청 사항 (생략 시 기존 값 유지)"
                }
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
                "user_id": {
                    "type": "string",
                    "description": "장바구니 소유 사용자 UUID"
                },
                "cart_item_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "삭제할 장바구니 항목 UUID 목록"
                }
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
                "user_id": {
                    "type": "string",
                    "description": "주문할 사용자 UUID"
                },
                "address_id": {
                    "type": "string",
                    "description": "배송에 사용할 배송지 UUID"
                },
                "delivery_note": {
                    "type": "string",
                    "description": "추가 배달 요청 사항"
                }
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
                "snapshot": {
                    "type": "object",
                    "description": "prepare_checkout이 반환한 CheckoutSnapshot 객체"
                },
                "payment_method": {
                    "type": "string",
                    "description": "결제 수단 (예: 'card', 'kakao')"
                },
                "pg_id": {
                    "type": "string",
                    "description": "PG사 거래 ID (선택)"
                }
            },
            "required": ["snapshot", "payment_method"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "get_order_status",
        "description": "주문 상태와 결제 상태를 조회합니다. 주문 진행 단계(pending/paid/preparing/delivering/delivered/cancelled)와 결제 상태를 반환합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "주문 소유 사용자 UUID"
                },
                "order_id": {
                    "type": "string",
                    "description": "조회할 주문 UUID"
                }
            },
            "required": ["user_id", "order_id"],
            "additionalProperties": False
        }
    },
]


# ================================================================
# 4. 각 함수의 반환 포맷
# ================================================================

tools_return_format = [
    {
        "function_name": "search_restaurants",
        "result_columns_format": {
            "items": "list(dict[restaurant_id: string, name: string, category: string, rating_avg: float, is_open: boolean, min_order_amount: integer])",
            "pagination": "dict[page: integer, page_size: integer, total_items: integer, total_pages: integer]",
            "applied_filters": "dict[query: string|null, category: string|null, min_rating: float|null, only_open: boolean, sort: string]",
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
    {
        "function_name": "upsert_address",
        "result_columns_format": {
            "return": "string (생성/수정된 배송지 UUID)",
        },
    },
    {
        "function_name": "list_addresses",
        "result_columns_format": {
            "return": "list(dict[address_id: string, user_id: string, recipient_name: string, phone: string, line1: string, line2: string|null, is_default: boolean])",
        },
    },
    {
        "function_name": "get_cart",
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
    {
        "function_name": "place_order",
        "result_columns_format": {
            "return": "string (생성된 주문 UUID)",
        },
    },
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
