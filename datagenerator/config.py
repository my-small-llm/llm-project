"""datagenerator 설정값 모음."""

# OpenAI 모델 설정
MODEL = "gpt-4o"
TEMPERATURE = 0.4
BATCH_SIZE = 10

# 지원 함수 전체 목록
ALL_FUNCTIONS: list[str] = [
    "search_restaurants",
    "get_restaurant_detail",
    "upsert_address",
    "list_addresses",
    "get_cart",
    "add_to_cart",
    "update_cart_item",
    "remove_cart_items",
    "prepare_checkout",
    "place_order",
    "get_order_status",
]

# 파일 경로
CUSTOM_FUNCTIONS_PATH = "docs/custom_functions.py"
JINJA_TEMPLATE_DIR = "docs"
JINJA_TEMPLATE_NAME = "qwen3_chat-template.jinja"
PROMPTS_DIR = "datagenerator/prompts"

# 학습 데이터에 삽입될 AI 상담사 시스템 프롬프트
CHATBOT_SYSTEM_PROMPT = (
    "당신은 음식 배달 서비스 AI 상담사입니다. "
    "고객의 음식점 검색, 메뉴 확인, 장바구니 관리, 배송지 관리, 주문 및 주문 상태 조회를 도와드립니다. "
    "반드시 제공된 도구(tool)만 사용하여 고객을 응대하세요. "
    "도구로 처리할 수 없는 요청은 정중하게 안내하세요."
)
