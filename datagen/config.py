"""
Function Calling 학습 데이터 생성을 위한 설정 및 상수.

- user_ids, 시나리오, tools, tools_return_format 등
- 유틸 함수: generate_random_date, pick_random_yn
"""

import random
from datetime import datetime, timedelta


# ================================================================
# 모델 설정
# ================================================================
MODEL = "gpt-5-2025-08-07"


# ================================================================
# 사용자 ID 목록 (학습 데이터용)
# ================================================================
USER_IDS = [
    "a1661d37-87bb-44e9-b2b3-ad951c237ba5",
    "928ef291-19a0-4408-90f0-b130a019c19f",
    "fac75497-7df8-4902-bda6-066e60a1f5ef",
    "47d67a36-584a-4154-8a7c-e9eb74ee1326",
    "af1b5d7a-f9db-479f-9749-226ba884f3ff",
    "531a4da5-92a9-4aa4-a4d2-a2e67ecb838d",
    "dd1fbd52-cd42-4a6e-b943-44a36e4e7f2d",
    "1a461d28-9400-44cf-bcd1-b997488cf20e",
    "83e6d570-ad10-40f0-8aca-0f1cdc63a14f",
    "afe98e1c-9ea2-46ef-bbe1-b7fafc08660f",
]


# ================================================================
# 함수로 처리 가능한 시나리오
# ================================================================
QUESTION_TOPICS = [
    # search_restaurants
    "식당 이름으로 검색",
    "메뉴 키워드로 식당 검색",
    "카테고리별 식당 검색",
    "평점 높은 식당 검색",
    "현재 영업 중인 식당 검색",
    "평점순 식당 정렬 조회",
    "특정 카테고리에서 평점 높은 식당 검색",

    # get_restaurant_detail
    "식당 상세 정보 조회",
    "식당 메뉴 목록 조회",
    "식당 영업 여부 확인",

    # upsert_address
    "새 배송지 등록",
    "기존 배송지 수정",
    "기본 배송지 변경",

    # list_addresses
    "내 배송지 목록 조회",
    "저장된 주소 확인",

    # get_cart
    "장바구니 조회",
    "장바구니 담긴 메뉴 확인",
    "장바구니 금액 확인",

    # add_to_cart
    "장바구니에 메뉴 추가",
    "장바구니에 메뉴 여러 개 추가",
    "특별 요청사항과 함께 메뉴 추가",

    # update_cart_item
    "장바구니 메뉴 수량 변경",
    "장바구니 메뉴 요청사항 수정",

    # remove_cart_items
    "장바구니에서 메뉴 삭제",
    "장바구니에서 여러 메뉴 한번에 삭제",

    # prepare_checkout
    "주문 전 최종 금액 확인",
    "결제 전 주문 요약 조회",

    # place_order
    "카드로 주문 결제",
    "주문 확정",

    # get_order_status
    "주문 상태 조회",
    "결제 상태 확인",
    "주문 진행 상황 확인",
]


# ================================================================
# 함수로 처리 불가능한 시나리오
# ================================================================
UNSUPPORTED_SCENARIOS = [
    # 주문 관련
    "주문 취소 요청",
    "주문 내역 전체 조회",
    "환불 요청",
    "재주문 요청",

    # 결제 관련
    "결제 취소",
    "카드 영수증 발급",

    # 배송지 관련
    "배송지 삭제",

    # 식당/메뉴 관련
    "식당 리뷰 조회",
    "식당 리뷰 작성",
    "식당 찜하기 (즐겨찾기)",
    "즐겨찾기 식당 목록 조회",

    # 사용자 관련
    "사용자 프로필 조회",
    "사용자 프로필 수정",
    "비밀번호 변경",
    "회원 탈퇴",

    # 쿠폰/포인트 관련
    "보유 쿠폰 조회",
    "쿠폰 적용",
    "적립금 조회",

    # 배달 관련
    "실시간 배달 추적",
    "배달 예상 시간 조회",

    # 도메인 외
    "연애 상담",
    "날씨 문의",
    "심리 상담",
    "음식 칼로리 문의",
    "이벤트 응모",
]


# ================================================================
# 잡담 데이터 소스
# ================================================================
CHATBOT_DATA_URL = (
    "https://raw.githubusercontent.com/songys/Chatbot_data/master/ChatbotData.csv"
)


# ================================================================
# 유틸 함수
# ================================================================

def generate_random_date() -> str:
    """2023-01-01 ~ 2025-12-31 사이의 랜덤 날짜를 'YYYY-MM-DD' 형식으로 반환."""
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2025, 12, 31)
    delta_days = (end_date - start_date).days
    random_days = random.randint(0, delta_days)
    random_date = start_date + timedelta(days=random_days)
    return random_date.strftime("%Y-%m-%d")


def pick_random_yn() -> str:
    """'Yes' 또는 'No'를 랜덤으로 반환."""
    return random.choice(["Yes", "No"])


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


# ================================================================
# 평가 전용 골드 데이터셋 카테고리
# ================================================================

GOLD_CATEGORIES = {
    "단순/연속 검색": {
        "count": 10,
        "instruction": "고객이 필터나 검색어를 계속 바꿔가며 'search_restaurants'를 여러 번 반복 호출하는 대화를 생성하십시오. 생성할 때마다 [한식, 중식, 일식, 분식, 카페, 야식] 등 다양한 도메인과 상황을 무작위로 설정하세요. 고객의 어투도 다양하게(존댓말, 반말, 급한 어투 등) 변형하고, 검색 조건(최소 평점, 영업 여부, 정렬 기준 등)을 다채롭게 요구하게 하십시오. 검색 이외에 장바구니나 결제는 시도하지 마십시오."
    },
    "메뉴 조회": {
        "count": 10,
        "instruction": "고객이 특정 식당의 상세 정보나 메뉴('get_restaurant_detail')를 요구하는 대화를 다양하게 생성하십시오. 다짜고짜 특정 브랜드의 메뉴를 묻거나, 검색 후 모호하게 지칭('별점 제일 높은 곳 메뉴 알려줘', '두 번째 식당 뭐 팔아?')하는 등 컨텍스트 의존성을 테스트할 수 있는 다양한 방식을 고안하십시오. 음식 종류와 상황을 매번 다르게 설정하십시오."
    },
    "장바구니 조작": {
        "count": 10,
        "instruction": "장바구니 조작('add_to_cart', 'update_cart_item', 'remove_cart_items') 대화를 다양하게 생성하십시오. 주의: add_to_cart 호출에는 menu_item_id가 필수이므로, AI가 고객 요청 후 스스로 get_restaurant_detail을 선행 호출하여 메뉴ID를 알아내는 논리적 흐름이 포함되어야 합니다. 또한 '마라탕 담아' -> '아 고수 빼줘(update)' 처럼 옵션(special_request)과 수량 변경 등을 복합적으로 사용하십시오."
    },
    "주문 이력/상태": {
        "count": 10,
        "instruction": "주문 정보('get_order_status')를 조회하는 시나리오를 생성하십시오. 주의: 현재 도구 명세에는 주문 목록 조회(list_orders) 기능이 없고 get_order_status는 반드시 'order_id'를 요구합니다. 따라서 고객이 '주문번호 12345번 배달 출발했나요?'라고 번호를 명시하거나, '언제 와요?'라고 물어서 AI가 '주문 번호를 알려주세요'라고 되묻는 등 도구의 제약을 훌륭하게 극복하는 대화 흐름을 만드십시오."
    },
    "주문 처리": {
        "count": 10,
        "instruction": "결제 전 확인('prepare_checkout')부터 주문 확정('place_order')까지 이어지는 결제 흐름을 생성하십시오. 주의: prepare_checkout 에는 address_id가 필수이며, place_order에는 prepare_checkout이 반환한 snapshot 데이터가 필수입니다. 이 도구 간의 파라미터 체인이 완벽하게 맞물려 작동하는 대화 (예: 주소 확인/수정 -> 결제 준비 -> 카드 결제 승인)를 다양한 다이내믹스(요청사항 추가 등)와 함께 구성하십시오."
    },
    "멀티턴 복합": {
        "count": 10,
        "instruction": "장기 컨텍스트(Long Context)와 도구 체이닝 능력을 종합적으로 보는 대화를 생성하십시오. 식당 검색(search) -> 메뉴 열람(detail) -> 장바구니 조작(cart) -> 배송지/결제(checkout -> order)로 이어지는 풀사이클 주문 여정을 구현하십시오. 각 턴마다 AI가 필요한 파라미터(restaurant_id, menu_item_id, address_id, snapshot 등)를 정확히 이전 함수에서 따와서 다음 함수로 넘기는 과정을 철저하게 평가할 수 있는 긴 호흡이어야 합니다."
    },
    "비지원 시나리오": {
        "count": 10,
        "instruction": "ai가 절대로 도구를 호출해서는 안 되는(no_call) 시나리오를 생성하십시오. 생성할 때마다 [타사 배달앱 비교], [라이더 사고 및 배상 문의], [앱 오류/버그 신고], [심한 욕설 및 컴플레인], [음식 레시피 문의] 등 완전히 다른 종류의 정책 위반 및 도메인 이탈 상황을 주입하여 거절 및 안내 능력을 다각도로 평가할 수 있게 하십시오."
    },
    "엣지 케이스": {
        "count": 10,
        "instruction": "고객의 입력이 극도로 비정형적인 엣지 케이스 대화를 생성하십시오. 심각한 오타('치긴 벅고십다', '짲장묜 배달'), 중간에 지시 번복('피자 줘... 아 아니 막국수로 변경'), 아주 모호한 지시('제일 싼거 아무거나', '다들 많이 먹는걸로 줘') 등 모델의 추론 능력을 한계까지 시험하는 다양하고 기상천외한 상황을 매번 새롭게 만들어 내십시오."
    }
}
