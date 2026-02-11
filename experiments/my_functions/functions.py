import pandas as pd
from datetime import datetime

_df_carts = None
_df_products = None
_df_orders = None
_df_deliveries = None
_df_order_items = None
_df_users = None
_df_user_coupons = None
_df_coupons = None
_df_regulations = None


def init(df_carts, df_products, df_orders, df_deliveries,
         df_order_items, df_users, df_user_coupons, df_coupons, df_regulations):
    global _df_carts, _df_products, _df_orders, _df_deliveries
    global _df_order_items, _df_users, _df_user_coupons, _df_coupons, _df_regulations
    _df_carts = df_carts
    _df_products = df_products
    _df_orders = df_orders
    _df_deliveries = df_deliveries
    _df_order_items = df_order_items
    _df_users = df_users
    _df_user_coupons = df_user_coupons
    _df_coupons = df_coupons
    _df_regulations = df_regulations


## 장바구니 상태 조회 함수 정의
def show_cart(user_id):
    global _df_carts
    user_cart = _df_carts[_df_carts['user_id'] == user_id].copy()
    # 제품 정보와 조인 (제품명, 가격, 수량 등)
    user_cart = user_cart.merge(_df_products[['id', 'name', 'price']],
                                left_on='product_id', right_on='id',
                                suffixes=('', '_prod'))
    user_cart = user_cart[['id', 'name', 'price', 'quantity', 'added_at']]
    if user_cart.empty:
        return {
            "success": False,
            "message": f"사용자 {user_id}님의 장바구니에 상품이 없습니다."
        }
    return {
        "success": True,
        "user_id": user_id,
        "item_count": len(user_cart),
        "cart_items": user_cart.to_dict(orient="records")
    }

## 제품 검색 함수
def search_product(keyword, category=None):
    # 기본 키워드로 제품명에 포함하는 항목 검색
    condition = _df_products['name'].str.contains(keyword, case=False, na=False)
    if category:
        condition &= _df_products['category'] == category
    results = _df_products[condition]
    if results.empty:
        return {
            "success": False,
            "message": f"키워드 '{keyword}'에 해당하는 상품을 찾을 수 없습니다."
        }
    # 평점 순 혹은 최신상품 등 다양한 기준을 적용할 수 있음. 여기서는 평점순 정렬을 예로 사용
    results = results.sort_values(by='rating', ascending=False)
    return {
        "success": True,
        "keyword": keyword,
        "category_filter": category,
        "result_count": len(results),
        "products": results.to_dict(orient="records")
    }

## 장바구니에 상품 추가 함수
def add_to_cart(user_id, product_id, quantity=1):
    global _df_carts
    new_id = f"C{str(len(_df_carts) + 1).zfill(3)}"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    new_item = {
        "id": new_id,
        "user_id": user_id,
        "product_id": product_id,
        "quantity": quantity,
        "added_at": now_str
    }

    _df_carts = pd.concat([_df_carts, pd.DataFrame([new_item])], ignore_index=True)

    return {
        "success": True,
        "message": f"상품 {product_id}가 장바구니에 {quantity}개 추가되었습니다.",
        "cart_item": new_item
    }

## 장바구니에서 상품 제거 함수
def remove_from_cart(user_id, keyword=None, product_id=None):
    global _df_carts

    if product_id is not None:
        to_remove = _df_carts[(_df_carts['user_id'] == user_id) & (_df_carts['product_id'] == product_id)]
        if to_remove.empty:
            return {
                "success": False,
                "message": f"장바구니에서 상품 ID {product_id}를 찾을 수 없습니다."
            }
        _df_carts = _df_carts.drop(to_remove.index)
        return {
            "success": True,
            "removed_by": "product_id",
            "product_id": product_id,
            "removed_count": len(to_remove),
            "message": f"장바구니에서 상품 {product_id}를 제거했습니다."
        }

    if keyword is not None:
        user_cart = _df_carts[_df_carts['user_id'] == user_id].merge(
            _df_products[['id', 'name']], left_on='product_id', right_on='id', suffixes=('', '_prod')
        )
        to_remove = user_cart[user_cart['name'].str.contains(keyword, case=False, na=False)]
        if to_remove.empty:
            return {
                "success": False,
                "message": f"장바구니에서 '{keyword}'와 관련된 상품을 찾지 못했습니다."
            }
        _df_carts = _df_carts[~_df_carts['id'].isin(to_remove['id'])]
        return {
            "success": True,
            "removed_by": "keyword",
            "keyword": keyword,
            "removed_count": len(to_remove),
            "message": f"장바구니에서 '{keyword}' 관련 상품 {len(to_remove)}건을 제거했습니다."
        }

    return {
        "success": False,
        "message": "제거할 상품 키워드 또는 product_id를 지정해주세요."
    }


## 주문 내역 전체 보기 함수
def view_order_history(user_id):
    """
    해당 사용자의 전체 주문 내역과 관련 배송 정보, 그리고 주문에 포함된 상품명을 집계하여 반환합니다.
    반환 형식은 JSON(list of dict)입니다.
    """
    orders = _df_orders[_df_orders["user_id"] == user_id].copy()
    if orders.empty:
        return {"message": f"사용자 {user_id}님의 주문 내역이 없습니다."}

    orders["order_date"] = pd.to_datetime(orders["order_date"])
    orders = orders.sort_values(by="order_date", ascending=False)

    orders = orders.merge(
        _df_deliveries[["order_id", "courier", "tracking_number", "status"]],
        left_on="id", right_on="order_id",
        how="left",
        suffixes=('_order', '_delivery')
    )

    order_items_agg = (
        _df_order_items
        .merge(_df_products[["id", "name"]], left_on="product_id", right_on="id", how="left")
        .groupby("order_id")["name"]
        .apply(lambda x: ", ".join(x.tolist()))
        .reset_index()
        .rename(columns={"name": "products"})
    )

    orders = orders.merge(
        order_items_agg,
        left_on="id", right_on="order_id",
        how="left",
        suffixes=('', '_items')
    )

    orders["order_id"] = orders["id"]

    result_df = orders[
        [
            "order_id",
            "order_date",
            "total",
            "payment_status",
            "delivery_status",
            "courier",
            "tracking_number",
            "status",
            "products"
        ]
    ].copy()

    # 날짜를 문자열로 변환
    result_df["order_date"] = result_df["order_date"].dt.strftime('%Y-%m-%d')

    # JSON 변환
    return result_df.to_dict(orient="records")

## 특정 주문의 상세 내역 보기 함수
def view_order_details(user_id, order_id):
    """
    특정 주문의 상세 내역(주문 상품, 수량, 가격, 할인 가격 등)을 JSON 형식으로 반환합니다.
    """
    order = _df_orders[(_df_orders["id"] == order_id) & (_df_orders["user_id"] == user_id)]
    if order.empty:
        return {"error": f"주문 {order_id}은/는 사용자 {user_id}님의 주문 내역에 없습니다."}

    details = _df_order_items[_df_order_items["order_id"] == order_id].copy()
    details = details.merge(_df_products[["id", "name"]],
                            left_on="product_id", right_on="id", how="left")

    result = details[["order_id", "product_id", "name", "quantity", "price", "discount_price"]]
    return result.to_dict(orient="records")


## 사용자 정보 조회
def view_user_profile(user_id):
    """
    주어진 user_id에 해당하는 사용자의 프로필 정보를 반환합니다.
    - 사용자 기본 정보: 이름, 이메일, 전화번호, 주소, 포인트, 멤버십 등
    - 사용자 쿠폰 정보: 쿠폰 ID, 쿠폰명, 할인 유형/값, 최소 주문 금액, 최대 할인 한도, 유효 기간, 사용 여부, 사용 일자
    """
    # 1) 사용자 기본 정보 조회
    user = _df_users[_df_users["id"] == user_id].copy()
    if user.empty:
        return f"사용자 {user_id}을(를) 찾을 수 없습니다."
    user_info = user.iloc[0].to_dict()

    # 2) 사용자 쿠폰 정보 조회 및 쿠폰 상세 조인
    user_cp = _df_user_coupons[_df_user_coupons["user_id"] == user_id].copy()
    if not user_cp.empty:
        user_cp = user_cp.merge(
            _df_coupons,
            left_on="coupon_id",
            right_on="id",
            how="left",
            suffixes=("", "_coupon")
        )
        # 필요한 컬럼만 선택
        user_cp = user_cp[[
            "coupon_id", "name", "discount_type", "discount_value",
            "min_order", "max_discount", "start_date", "end_date",
            "used", "use_date"
        ]]
        # 리스트 형태로 변환
        user_info["coupons"] = user_cp.to_dict(orient="records")
    else:
        user_info["coupons"] = []

    return user_info

# 8. 약관 조회 함수
def search_policy_info(keyword):
    """
    특정 키워드(예: '주문 취소', '반품')에 해당하는 상준몰 정책 정보를 검색하여 반환합니다.
    """
    results = _df_regulations[_df_regulations["keyword"] == keyword]["content"].tolist()
    if not results:
        return {
            "keyword": keyword,
            "search_result": [f"'{keyword}'에 대한 정책 정보를 찾을 수 없습니다."]
        }
    return {
        "keyword": keyword,
        "search_result": results
    }