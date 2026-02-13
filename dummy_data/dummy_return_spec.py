# ============================================================
# API 응답 명세 (Return Spec)
# ------------------------------------------------------------
# 새 API의 응답 형식을 추가할 때 아래 형식에 맞춰 dict를 리스트에 추가하면 됩니다.
#
# {
#     'function_name': '<함수명>',           # str — dummy_call_spec.py의 name과 일치해야 함
#     'result_columns_format': {             # 응답 JSON의 key-type 쌍
#         '<key>': '<타입>',
#         ...
#     }
# }
#
# 타입 표기 규칙:
#   기본형   — 'string', 'integer', 'float', 'boolean'
#   nullable — 'string or null', 'string (nullable)'
#   enum     — 'string(value_a or value_b)'
#   날짜형   — 'string(%Y-%m-%d)', 'string(%Y-%m-%d %H:%M)'
#   리스트   — 'list(string)', 'list(dict[key1: type1, key2: type2, ...])'
#   딕셔너리 — 'dict[key1: type1, key2: type2, ...]'
# ============================================================

tools_return_format = [
    {
        'function_name': 'show_cart',
        'result_columns_format': {
            'success': 'boolean',
            'user_id': 'string',
            'item_count': 'integer',
            'cart_items': 'list(dict[id: string, name: string, price: integer, quantity: integer, added_at: string(%Y-%m-%d %H:%M)])'
        }
    },
    {
        'function_name': 'search_product',
        'result_columns_format': {
            'success': 'boolean',
            'keyword': 'string',
            'category_filter': 'string or null',
            'result_count': 'integer',
            'products': 'list(dict[id: string, name: string, price: integer, category: string, rating: float, stock: integer])'
        }
    },
    {
        'function_name': 'add_to_cart',
        'result_columns_format': {
            'success': 'boolean',
            'message': 'string',
            'cart_item': 'dict[id: string, user_id: string, product_id: string, quantity: integer, added_at: string(%Y-%m-%d %H:%M)]'
        }
    },
    {
        'function_name': 'remove_from_cart',
        'result_columns_format': {
            'success': 'boolean',
            'removed_by': 'string(product_id or keyword)',
            'product_id': 'string (nullable)',
            'keyword': 'string (nullable)',
            'removed_count': 'integer',
            'message': 'string'
        }
    },
    {
        'function_name': 'view_order_history',
        'result_columns_format': {
            'order_id': 'string',
            'order_date': 'string(%Y-%m-%d)',
            'total': 'integer',
            'payment_status': 'string',
            'delivery_status': 'string',
            'courier': 'string',
            'tracking_number': 'string',
            'status': 'string',
            'products': 'string'
        }
    },
    {
        'function_name': 'view_order_details',
        'result_columns_format': {
            'order_id': 'string',
            'product_id': 'string',
            'name': 'string',
            'quantity': 'integer',
            'price': 'integer',
            'discount_price': 'integer'
        }
    },
    {
        'function_name': 'view_user_profile',
        'result_columns_format': {
            'id': 'string',
            'name': 'string',
            'email': 'string',
            'phone': 'string',
            'address': 'string',
            'points': 'integer',
            'membership': 'string',
            'coupons': 'list(dict[coupon_id: string, name: string, discount_type: string, discount_value: integer, min_order: integer, max_discount: integer, start_date: string, end_date: string, used: boolean, use_date: string or null])'
        }
    },
    {
        'function_name': 'search_policy_info',
        'result_columns_format': {
            'keyword': 'string',
            'search_result': 'list(string)'
        }
    }
]