# ============================================================
# API 호출 명세 (Call Spec)
# ------------------------------------------------------------
# 새 API를 추가할 때 아래 형식에 맞춰 dict를 tools 리스트에 추가하면 됩니다.
#
# {
#     "type": "function",
#     "name": "<함수명>",                    # str — 고유 식별자
#     "description": "<함수 설명>",          # str — 이 함수가 하는 일
#     "parameters": {
#         "type": "object",
#         "properties": {                    # 파라미터 정의
#             "<param_name>": {
#                 "type": "<타입>",           #   "string" | "integer" | "boolean" 등
#                 "description": "<설명>"
#             },
#             ...
#         },
#         "required": ["<필수 파라미터>"],    # 반드시 전달해야 하는 파라미터 목록
#         "additionalProperties": False
#     }
# }
# ============================================================

tools = [
    {
        "type": "function",
        "name": "show_cart",
        "description": "사용자의 장바구니에 담긴 상품 목록을 조회합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "사용자 ID (예: U001)"
                }
            },
            "required": ["user_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "search_product",
        "description": "키워드로 상품을 검색합니다. 선택적으로 카테고리 필터를 적용할 수 있습니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "검색할 상품 키워드 (예: 노트북, 헤드폰)"
                },
                "category": {
                    "type": "string",
                    "description": "필터링할 카테고리 (예: 전자기기, 패션, 식품)"
                }
            },
            "required": ["keyword"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "add_to_cart",
        "description": "사용자의 장바구니에 상품을 추가합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "사용자 ID (예: U001)"
                },
                "product_id": {
                    "type": "string",
                    "description": "추가할 상품 ID (예: P001)"
                },
                "quantity": {
                    "type": "integer",
                    "description": "추가할 수량 (기본값: 1)"
                }
            },
            "required": ["user_id", "product_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "remove_from_cart",
        "description": "사용자의 장바구니에서 상품을 제거합니다. 상품명 키워드 또는 상품 ID로 제거할 수 있습니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "사용자 ID (예: U001)"
                },
                "keyword": {
                    "type": "string",
                    "description": "제거할 상품의 키워드 (예: 헤드폰)"
                },
                "product_id": {
                    "type": "string",
                    "description": "제거할 상품 ID (예: P001)"
                }
            },
            "required": ["user_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "view_order_history",
        "description": "사용자의 전체 주문 내역을 배송 정보 및 주문 상품과 함께 조회합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "사용자 ID (예: U001)"
                }
            },
            "required": ["user_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "view_order_details",
        "description": "특정 주문의 상세 내역(주문 상품, 수량, 가격, 할인 가격 등)을 조회합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "사용자 ID (예: U001)"
                },
                "order_id": {
                    "type": "string",
                    "description": "주문 ID (예: O001)"
                }
            },
            "required": ["user_id", "order_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "view_user_profile",
        "description": "사용자의 프로필 정보(이름, 이메일, 전화번호, 주소, 포인트, 멤버십, 쿠폰 등)를 조회합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "사용자 ID (예: U001)"
                }
            },
            "required": ["user_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "search_policy_info",
        "description": "브라더훈몰의 정책 정보를 키워드로 검색합니다. (예: 주문 취소, 반품, 환불, 배송, 재입고)",
        "parameters": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "검색할 정책 키워드 (예: 주문 취소, 반품, 환불, 배송, 재입고)"
                }
            },
            "required": ["keyword"],
            "additionalProperties": False
        }
    }
]
