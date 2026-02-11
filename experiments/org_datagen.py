

# ============================================================
# 1. Imports
# ============================================================
import re
import json
import ast
import os
import pandas as pd
import random
from tqdm import tqdm
from datetime import datetime, timedelta
import openai
import datasets
from huggingface_hub import login


# ============================================================
# 2. 더미 데이터 (10개 테이블)
# ============================================================
# 테이블 1: 상품 데이터 (전자기기와 컴퓨터 카테고리 통합)
products = [
    {"id": "P001", "name": "프리미엄 헤드폰", "category": "전자기기", "brand": "사운드마스터", "price": 129000, "stock": 45, "rating": 4.7, "discount": 10},
    {"id": "P002", "name": "유기농 바나나", "category": "식품", "brand": "자연마을", "price": 8900, "stock": 120, "rating": 4.8, "discount": 0},
    {"id": "P003", "name": "울트라 슬림 노트북", "category": "전자기기", "brand": "테크노바", "price": 1290000, "stock": 10, "rating": 4.8, "discount": 5},
    {"id": "P004", "name": "프리미엄 가죽 지갑", "category": "패션", "brand": "럭셔리스타일", "price": 89000, "stock": 30, "rating": 4.6, "discount": 0},
    {"id": "P005", "name": "캐주얼 스니커즈", "category": "신발", "brand": "스포츠플러스", "price": 79000, "stock": 25, "rating": 4.4, "discount": 20},
    {"id": "P006", "name": "실내 자전거", "category": "스포츠", "brand": "피트니스마스터", "price": 350000, "stock": 8, "rating": 4.9, "discount": 8},
    {"id": "P007", "name": "아로마 테라피 세트", "category": "뷰티", "brand": "힐링라이프", "price": 35000, "stock": 15, "rating": 4.6, "discount": 12},
    {"id": "P008", "name": "무선 블루투스 이어폰", "category": "전자기기", "brand": "사운드마스터", "price": 159000, "stock": 35, "rating": 4.5, "discount": 15},
    {"id": "P009", "name": "프로틴 파우더", "category": "건강식품", "brand": "헬시라이프", "price": 45000, "stock": 18, "rating": 4.7, "discount": 10},
    {"id": "P010", "name": "프로그래밍 책 세트", "category": "도서", "brand": "지식출판", "price": 120000, "stock": 22, "rating": 4.8, "discount": 5},
    {"id": "P011", "name": "유아 교구 세트", "category": "유아용품", "brand": "키즈랜드", "price": 85000, "stock": 15, "rating": 4.9, "discount": 7},
    {"id": "P012", "name": "스테인리스 냄비세트", "category": "주방용품", "brand": "홈쿠킹", "price": 159000, "stock": 12, "rating": 4.6, "discount": 15},
    {"id": "P013", "name": "면세점 향수 세트", "category": "화장품", "brand": "프랑스향수", "price": 210000, "stock": 20, "rating": 4.7, "discount": 8},
    {"id": "P014", "name": "고급 침대 프레임", "category": "가구", "brand": "슬립웰", "price": 890000, "stock": 5, "rating": 4.5, "discount": 10},
    {"id": "P015", "name": "게이밍 마우스", "category": "전자기기", "brand": "게이머프로", "price": 89000, "stock": 30, "rating": 4.8, "discount": 5},
    {"id": "P016", "name": "대형 선인장 화분", "category": "원예", "brand": "그린가든", "price": 35000, "stock": 25, "rating": 4.4, "discount": 0},
    {"id": "P017", "name": "레트로 턴테이블", "category": "음향기기", "brand": "올드스쿨", "price": 320000, "stock": 8, "rating": 4.9, "discount": 5},
    {"id": "P018", "name": "스마트 TV", "category": "전자기기", "brand": "디지털라이프", "price": 750000, "stock": 15, "rating": 4.6, "discount": 12},
    {"id": "P019", "name": "강아지 장난감 세트", "category": "반려동물", "brand": "펫라이프", "price": 28000, "stock": 40, "rating": 4.3, "discount": 5},
    {"id": "P020", "name": "캠핑 텐트", "category": "아웃도어", "brand": "네이처하이킹", "price": 180000, "stock": 18, "rating": 4.7, "discount": 10}
]

# 테이블 2: 사용자 데이터
users = [
    {"id": "U001", "name": "김철수", "email": "kim@example.com", "phone": "010-1234-5678", "address": "서울시 강남구 테헤란로 123", "points": 5000, "membership": "골드"},
    {"id": "U002", "name": "이영희", "email": "lee@example.com", "phone": "010-2345-6789", "address": "서울시 서초구 서초대로 456", "points": 2500, "membership": "실버"},
    {"id": "U003", "name": "박지민", "email": "park@example.com", "phone": "010-3456-7890", "address": "서울시 송파구 올림픽로 789", "points": 1000, "membership": "브론즈"},
    {"id": "U004", "name": "정수민", "email": "jung@example.com", "phone": "010-4567-8901", "address": "서울시 마포구 홍대로 101", "points": 4800, "membership": "골드"},
    {"id": "U005", "name": "최유진", "email": "choi@example.com", "phone": "010-5678-9012", "address": "서울시 영등포구 여의도로 202", "points": 12000, "membership": "플래티넘"},
    {"id": "U006", "name": "강민수", "email": "kang@example.com", "phone": "010-6789-0123", "address": "서울시 종로구 종로 333", "points": 800, "membership": "브론즈"},
    {"id": "U007", "name": "윤서연", "email": "yoon@example.com", "phone": "010-7890-1234", "address": "서울시 용산구 이태원로 444", "points": 3200, "membership": "실버"},
    {"id": "U008", "name": "장준호", "email": "jang@example.com", "phone": "010-8901-2345", "address": "서울시 강서구 공항대로 555", "points": 7500, "membership": "골드"},
    {"id": "U009", "name": "한지원", "email": "han@example.com", "phone": "010-9012-3456", "address": "서울시 강동구 천호대로 666", "points": 1500, "membership": "브론즈"},
    {"id": "U010", "name": "오민지", "email": "oh@example.com", "phone": "010-0123-4567", "address": "서울시 성북구 성북로 777", "points": 6400, "membership": "골드"}
]

# 테이블 3: 장바구니 데이터
carts = [
    {"id": "C001", "user_id": "U001", "product_id": "P001", "quantity": 1, "added_at": "2025-04-10 14:30"},
    {"id": "C002", "user_id": "U001", "product_id": "P003", "quantity": 1, "added_at": "2025-04-10 14:35"},
    {"id": "C003", "user_id": "U002", "product_id": "P002", "quantity": 2, "added_at": "2025-04-12 10:15"},
    {"id": "C004", "user_id": "U003", "product_id": "P005", "quantity": 2, "added_at": "2025-04-13 16:45"},
    {"id": "C005", "user_id": "U004", "product_id": "P004", "quantity": 1, "added_at": "2025-04-14 09:20"},
    {"id": "C006", "user_id": "U005", "product_id": "P007", "quantity": 1, "added_at": "2025-04-14 11:30"},
    {"id": "C007", "user_id": "U006", "product_id": "P009", "quantity": 3, "added_at": "2025-04-15 13:45"},
    {"id": "C008", "user_id": "U007", "product_id": "P012", "quantity": 1, "added_at": "2025-04-15 14:20"},
    {"id": "C009", "user_id": "U008", "product_id": "P015", "quantity": 2, "added_at": "2025-04-15 15:10"},
    {"id": "C010", "user_id": "U009", "product_id": "P016", "quantity": 1, "added_at": "2025-04-15 16:30"}
]

# 테이블 4: 주문 데이터
orders = [
    {"id": "O001", "user_id": "U001", "order_date": "2025-04-01 15:30", "total": 1419000, "payment_method": "신용카드", "payment_status": "완료", "delivery_status": "배송완료"},
    {"id": "O002", "user_id": "U002", "order_date": "2025-04-05 11:20", "total": 17800, "payment_method": "무통장입금", "payment_status": "완료", "delivery_status": "배송중"},
    {"id": "O003", "user_id": "U003", "order_date": "2025-04-08 09:45", "total": 126400, "payment_method": "간편결제", "payment_status": "완료", "delivery_status": "배송준비중"},
    {"id": "O004", "user_id": "U001", "order_date": "2025-03-20 16:00", "total": 89000, "payment_method": "신용카드", "payment_status": "완료", "delivery_status": "배송완료"},
    {"id": "O005", "user_id": "U004", "order_date": "2025-04-10 13:15", "total": 89000, "payment_method": "간편결제", "payment_status": "취소", "delivery_status": "취소됨"},
    {"id": "O006", "user_id": "U005", "order_date": "2025-04-11 10:30", "total": 35000, "payment_method": "신용카드", "payment_status": "완료", "delivery_status": "배송완료"},
    {"id": "O007", "user_id": "U006", "order_date": "2025-04-12 14:45", "total": 135000, "payment_method": "간편결제", "payment_status": "완료", "delivery_status": "배송중"},
    {"id": "O008", "user_id": "U007", "order_date": "2025-04-13 09:20", "total": 159000, "payment_method": "신용카드", "payment_status": "완료", "delivery_status": "배송준비중"},
    {"id": "O009", "user_id": "U008", "order_date": "2025-04-14 11:15", "total": 178000, "payment_method": "무통장입금", "payment_status": "완료", "delivery_status": "배송준비중"},
    {"id": "O010", "user_id": "U009", "order_date": "2025-04-15 15:40", "total": 35000, "payment_method": "간편결제", "payment_status": "대기중", "delivery_status": "주문접수"}
]

# 테이블 5: 주문 상세 데이터
order_items = [
    {"id": "OI001", "order_id": "O001", "product_id": "P001", "quantity": 1, "price": 129000, "discount_price": 116100},
    {"id": "OI002", "order_id": "O001", "product_id": "P003", "quantity": 1, "price": 1290000, "discount_price": 1225500},
    {"id": "OI003", "order_id": "O002", "product_id": "P002", "quantity": 2, "price": 8900, "discount_price": 8900},
    {"id": "OI004", "order_id": "O003", "product_id": "P005", "quantity": 2, "price": 79000, "discount_price": 63200},
    {"id": "OI005", "order_id": "O004", "product_id": "P004", "quantity": 1, "price": 89000, "discount_price": 89000},
    {"id": "OI006", "order_id": "O005", "product_id": "P004", "quantity": 1, "price": 89000, "discount_price": 89000},
    {"id": "OI007", "order_id": "O006", "product_id": "P007", "quantity": 1, "price": 35000, "discount_price": 30800},
    {"id": "OI008", "order_id": "O007", "product_id": "P009", "quantity": 3, "price": 45000, "discount_price": 40500},
    {"id": "OI009", "order_id": "O008", "product_id": "P012", "quantity": 1, "price": 159000, "discount_price": 135150},
    {"id": "OI010", "order_id": "O009", "product_id": "P015", "quantity": 2, "price": 89000, "discount_price": 84550},
    {"id": "OI011", "order_id": "O010", "product_id": "P016", "quantity": 1, "price": 35000, "discount_price": 35000}
]

# 테이블 6: 배송 데이터
deliveries = [
    {"id": "D001", "order_id": "O001", "courier": "CJ대한통운", "tracking_number": "123456789012", "start_date": "2025-04-02", "end_date": "2025-04-04", "status": "배송완료"},
    {"id": "D002", "order_id": "O002", "courier": "로젠택배", "tracking_number": "234567890123", "start_date": "2025-04-06", "end_date": None, "status": "배송중"},
    {"id": "D003", "order_id": "O003", "courier": "한진택배", "tracking_number": "345678901234", "start_date": None, "end_date": None, "status": "배송준비중"},
    {"id": "D004", "order_id": "O004", "courier": "우체국택배", "tracking_number": "456789012345", "start_date": "2025-03-21", "end_date": "2025-03-23", "status": "배송완료"},
    {"id": "D005", "order_id": "O005", "courier": "", "tracking_number": "", "start_date": None, "end_date": None, "status": "취소됨"},
    {"id": "D006", "order_id": "O006", "courier": "CJ대한통운", "tracking_number": "567890123456", "start_date": "2025-04-12", "end_date": "2025-04-13", "status": "배송완료"},
    {"id": "D007", "order_id": "O007", "courier": "로젠택배", "tracking_number": "678901234567", "start_date": "2025-04-13", "end_date": None, "status": "배송중"},
    {"id": "D008", "order_id": "O008", "courier": "한진택배", "tracking_number": "789012345678", "start_date": None, "end_date": None, "status": "배송준비중"},
    {"id": "D009", "order_id": "O009", "courier": "CJ대한통운", "tracking_number": "890123456789", "start_date": None, "end_date": None, "status": "배송준비중"},
    {"id": "D010", "order_id": "O010", "courier": "", "tracking_number": "", "start_date": None, "end_date": None, "status": "주문접수"}
]

# 테이블 7: 리뷰 데이터
reviews = [
    {"id": "R001", "user_id": "U001", "product_id": "P001", "order_id": "O001", "rating": 5, "content": "음질이 정말 좋고 착용감도 편안합니다.", "date": "2025-04-05", "helpful_count": 12},
    {"id": "R002", "user_id": "U001", "product_id": "P003", "order_id": "O001", "rating": 4, "content": "가볍고 성능이 좋아요. 배터리가 조금 아쉽습니다.", "date": "2025-04-05", "helpful_count": 8},
    {"id": "R003", "user_id": "U002", "product_id": "P002", "order_id": "O002", "rating": 5, "content": "정말 맛있고 신선해요! 다음에 또 구매할게요.", "date": "2025-04-10", "helpful_count": 5},
    {"id": "R004", "user_id": "U001", "product_id": "P004", "order_id": "O004", "rating": 4, "content": "가죽 질감이 좋고 수납공간이 넉넉합니다.", "date": "2025-03-25", "helpful_count": 3},
    {"id": "R005", "user_id": "U003", "product_id": "P005", "order_id": "O003", "rating": 3, "content": "디자인은 좋지만 내구성이 조금 아쉽습니다.", "date": "2025-04-12", "helpful_count": 1},
    {"id": "R006", "user_id": "U005", "product_id": "P007", "order_id": "O006", "rating": 5, "content": "향이 너무 좋고 효과도 만족스러워요.", "date": "2025-04-14", "helpful_count": 7},
    {"id": "R007", "user_id": "U006", "product_id": "P009", "order_id": "O007", "rating": 4, "content": "맛은 괜찮은데 가격이 조금 비싼 것 같아요.", "date": "2025-04-15", "helpful_count": 2},
    {"id": "R008", "user_id": "U007", "product_id": "P012", "order_id": "O008", "rating": 5, "content": "열전도율이 좋고 세척도 편리해요.", "date": "2025-04-16", "helpful_count": 4},
    {"id": "R009", "user_id": "U008", "product_id": "P015", "order_id": "O009", "rating": 5, "content": "게임할 때 정확하고 반응속도가 빨라요.", "date": "2025-04-16", "helpful_count": 6},
    {"id": "R010", "user_id": "U001", "product_id": "P008", "order_id": "O001", "rating": 4, "content": "노이즈캔슬링 기능이 훌륭하네요.", "date": "2025-04-05", "helpful_count": 9}
]

# 테이블 8: 쿠폰 데이터
coupons = [
    {"id": "CP001", "name": "신규가입 10% 할인", "discount_type": "percent", "discount_value": 10, "min_order": 50000, "max_discount": 50000, "start_date": "2025-01-01", "end_date": "2025-12-31"},
    {"id": "CP002", "name": "전자기기 15% 할인", "discount_type": "percent", "discount_value": 15, "min_order": 100000, "max_discount": 100000, "start_date": "2025-04-01", "end_date": "2025-04-30"},
    {"id": "CP003", "name": "5천원 할인", "discount_type": "amount", "discount_value": 5000, "min_order": 30000, "max_discount": 5000, "start_date": "2025-04-01", "end_date": "2025-04-20"},
    {"id": "CP004", "name": "패션 20% 할인", "discount_type": "percent", "discount_value": 20, "min_order": 50000, "max_discount": 30000, "start_date": "2025-04-01", "end_date": "2025-05-31"},
    {"id": "CP005", "name": "VIP 회원 특별 20% 할인", "discount_type": "percent", "discount_value": 20, "min_order": 200000, "max_discount": 100000, "start_date": "2025-04-01", "end_date": "2025-04-15"},
    {"id": "CP006", "name": "생일 축하 15% 할인", "discount_type": "percent", "discount_value": 15, "min_order": 20000, "max_discount": 30000, "start_date": "2025-04-10", "end_date": "2025-05-10"},
    {"id": "CP007", "name": "반려동물용품 10% 할인", "discount_type": "percent", "discount_value": 10, "min_order": 30000, "max_discount": 20000, "start_date": "2025-04-15", "end_date": "2025-04-30"},
    {"id": "CP008", "name": "식품 2만원 할인", "discount_type": "amount", "discount_value": 20000, "min_order": 100000, "max_discount": 20000, "start_date": "2025-04-01", "end_date": "2025-04-30"},
    {"id": "CP009", "name": "주방용품 30% 할인", "discount_type": "percent", "discount_value": 30, "min_order": 50000, "max_discount": 50000, "start_date": "2025-04-10", "end_date": "2025-04-25"},
    {"id": "CP010", "name": "첫 구매 1만원 할인", "discount_type": "amount", "discount_value": 10000, "min_order": 30000, "max_discount": 10000, "start_date": "2025-01-01", "end_date": "2025-12-31"}
]

# 테이블 9: 사용자 쿠폰 데이터
user_coupons = [
    {"id": "UC001", "user_id": "U001", "coupon_id": "CP001", "issue_date": "2023-05-15", "used": True, "use_date": "2025-04-01"},
    {"id": "UC002", "user_id": "U001", "coupon_id": "CP002", "issue_date": "2025-04-01", "used": False, "use_date": None},
    {"id": "UC003", "user_id": "U002", "coupon_id": "CP003", "issue_date": "2025-04-02", "used": True, "use_date": "2025-04-05"},
    {"id": "UC004", "user_id": "U003", "coupon_id": "CP003", "issue_date": "2025-04-05", "used": True, "use_date": "2025-04-08"},
    {"id": "UC005", "user_id": "U004", "coupon_id": "CP004", "issue_date": "2025-04-03", "used": False, "use_date": None},
    {"id": "UC006", "user_id": "U005", "coupon_id": "CP005", "issue_date": "2025-04-01", "used": False, "use_date": None},
    {"id": "UC007", "user_id": "U006", "coupon_id": "CP006", "issue_date": "2025-04-11", "used": True, "use_date": "2025-04-12"},
    {"id": "UC008", "user_id": "U007", "coupon_id": "CP004", "issue_date": "2025-04-10", "used": True, "use_date": "2025-04-13"},
    {"id": "UC009", "user_id": "U008", "coupon_id": "CP002", "issue_date": "2025-04-05", "used": True, "use_date": "2025-04-14"},
    {"id": "UC010", "user_id": "U009", "coupon_id": "CP010", "issue_date": "2025-04-01", "used": False, "use_date": None}
]

# 테이블 10: 약관 데이터
regulations = [
    # 주문 취소
    {"keyword": "주문 취소", "content": "주문 취소는 상품이 출고되기 전에는 언제든 가능합니다. 출고 이후에는 반품으로 처리됩니다."},
    {"keyword": "주문 취소", "content": "주문 취소 시 사용한 포인트는 자동 환불됩니다."},
    {"keyword": "주문 취소", "content": "주문 취소는 상준몰 주문내역 > 주문취소 버튼을 통해 가능합니다."},

    # 반품
    {"keyword": "반품", "content": "반품 신청은 배송일로부터 5일 이내에 가능합니다."},
    {"keyword": "반품", "content": "반품 시 왕복 배송비가 부과됩니다."},
    {"keyword": "반품", "content": "반품 신청은 상준몰 주문내역 > 배송완료 > 반품 버튼을 눌러 신청할 수 있습니다."},

    # 환불
    {"keyword": "환불", "content": "환불 처리는 반품 완료 후 3영업일 이내에 진행됩니다."},
    {"keyword": "환불", "content": "결제 수단에 따라 환불 소요 시간이 달라질 수 있습니다."},
    {"keyword": "환불", "content": "카드 환불은 카드사 영업일 기준으로 약 5~7일 소요됩니다."},

    # 배송
    {"keyword": "배송", "content": "상품은 결제일로부터 2~3일 이내 출고됩니다."},
    {"keyword": "배송", "content": "배송은 택배사를 통해 이루어지며 평균 배송 소요 기간은 3~5일입니다."},
    {"keyword": "배송", "content": "배송 조회는 상준몰 마이페이지 > 주문내역 > 배송조회 버튼을 통해 확인할 수 있습니다."},

    # 재입고
    {"keyword": "재입고", "content": "일부 품절 상품은 재입고 시점이 불확정입니다."},
    {"keyword": "재입고", "content": "상품 상세 페이지에서 '재입고 알림 신청'이 가능하면 알림 설정을 해주세요."},
    {"keyword": "재입고", "content": "재입고 여부는 판매자 또는 상준몰 담당자가 별도 안내드립니다."}
]


# ============================================================
# 3. DataFrame 생성
# ============================================================
# -------------------------------
# 1. DataFrame 생성 (이미 리스트에 저장된 데이터를 사용)
# (실제 서비스에서는 외부 데이터베이스나 API를 통해 데이터가 입력된다고 가정)
df_products   = pd.DataFrame(products)
df_users      = pd.DataFrame(users)
df_carts      = pd.DataFrame(carts)
df_orders     = pd.DataFrame(orders)
df_order_items= pd.DataFrame(order_items)
df_deliveries = pd.DataFrame(deliveries)
df_reviews    = pd.DataFrame(reviews)
df_coupons    = pd.DataFrame(coupons)
df_user_coupons = pd.DataFrame(user_coupons)
df_regulations = pd.DataFrame(regulations)


# ============================================================
# 4. 함수 정의 (8개)
# ============================================================
# 1. 장바구니 상태 조회 함수
def show_cart(user_id):
    user_cart = df_carts[df_carts['user_id'] == user_id].copy()
    # 제품 정보와 조인 (제품명, 가격, 수량 등)
    user_cart = user_cart.merge(df_products[['id', 'name', 'price']],
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

# 2. 제품 검색 함수 (예, "노트북")
def search_product(keyword, category=None):
    # 기본 키워드로 제품명에 포함하는 항목 검색
    condition = df_products['name'].str.contains(keyword, case=False, na=False)
    if category:
        condition &= df_products['category'] == category
    results = df_products[condition]
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

# 3. 장바구니에 상품 추가 함수
def add_to_cart(user_id, product_id, quantity=1):
    global df_carts
    new_id = f"C{str(len(df_carts) + 1).zfill(3)}"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    new_item = {
        "id": new_id,
        "user_id": user_id,
        "product_id": product_id,
        "quantity": quantity,
        "added_at": now_str
    }

    df_carts = pd.concat([df_carts, pd.DataFrame([new_item])], ignore_index=True)

    return {
        "success": True,
        "message": f"상품 {product_id}가 장바구니에 {quantity}개 추가되었습니다.",
        "cart_item": new_item
    }

# 4. 장바구니에서 상품 제거 함수
def remove_from_cart(user_id, keyword=None, product_id=None):
    global df_carts

    if product_id is not None:
        to_remove = df_carts[(df_carts['user_id'] == user_id) & (df_carts['product_id'] == product_id)]
        if to_remove.empty:
            return {
                "success": False,
                "message": f"장바구니에서 상품 ID {product_id}를 찾을 수 없습니다."
            }
        df_carts = df_carts.drop(to_remove.index)
        return {
            "success": True,
            "removed_by": "product_id",
            "product_id": product_id,
            "removed_count": len(to_remove),
            "message": f"장바구니에서 상품 {product_id}를 제거했습니다."
        }

    if keyword is not None:
        user_cart = df_carts[df_carts['user_id'] == user_id].merge(
            df_products[['id', 'name']], left_on='product_id', right_on='id', suffixes=('', '_prod')
        )
        to_remove = user_cart[user_cart['name'].str.contains(keyword, case=False, na=False)]
        if to_remove.empty:
            return {
                "success": False,
                "message": f"장바구니에서 '{keyword}'와 관련된 상품을 찾지 못했습니다."
            }
        df_carts = df_carts[~df_carts['id'].isin(to_remove['id'])]
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

# 5. 주문 내역 전체 보기 함수
def view_order_history(user_id):
    """
    해당 사용자의 전체 주문 내역과 관련 배송 정보, 그리고 주문에 포함된 상품명을 집계하여 반환합니다.
    반환 형식은 JSON(list of dict)입니다.
    """
    orders = df_orders[df_orders["user_id"] == user_id].copy()
    if orders.empty:
        return {"message": f"사용자 {user_id}님의 주문 내역이 없습니다."}

    orders["order_date"] = pd.to_datetime(orders["order_date"])
    orders = orders.sort_values(by="order_date", ascending=False)

    orders = orders.merge(
        df_deliveries[["order_id", "courier", "tracking_number", "status"]],
        left_on="id", right_on="order_id",
        how="left",
        suffixes=('_order', '_delivery')
    )

    order_items_agg = (
        df_order_items
        .merge(df_products[["id", "name"]], left_on="product_id", right_on="id", how="left")
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

# 6. 특정 주문의 상세 내역 보기 함수
def view_order_details(user_id, order_id):
    """
    특정 주문의 상세 내역(주문 상품, 수량, 가격, 할인 가격 등)을 JSON 형식으로 반환합니다.
    """
    order = df_orders[(df_orders["id"] == order_id) & (df_orders["user_id"] == user_id)]
    if order.empty:
        return {"error": f"주문 {order_id}은/는 사용자 {user_id}님의 주문 내역에 없습니다."}

    details = df_order_items[df_order_items["order_id"] == order_id].copy()
    details = details.merge(df_products[["id", "name"]],
                            left_on="product_id", right_on="id", how="left")

    result = details[["order_id", "product_id", "name", "quantity", "price", "discount_price"]]
    return result.to_dict(orient="records")

# 7. 사용자 정보 조회
def view_user_profile(user_id):
    """
    주어진 user_id에 해당하는 사용자의 프로필 정보를 반환합니다.
    - 사용자 기본 정보: 이름, 이메일, 전화번호, 주소, 포인트, 멤버십 등
    - 사용자 쿠폰 정보: 쿠폰 ID, 쿠폰명, 할인 유형/값, 최소 주문 금액, 최대 할인 한도, 유효 기간, 사용 여부, 사용 일자
    """
    # 1) 사용자 기본 정보 조회
    user = df_users[df_users["id"] == user_id].copy()
    if user.empty:
        return f"사용자 {user_id}을(를) 찾을 수 없습니다."
    user_info = user.iloc[0].to_dict()

    # 2) 사용자 쿠폰 정보 조회 및 쿠폰 상세 조인
    user_cp = df_user_coupons[df_user_coupons["user_id"] == user_id].copy()
    if not user_cp.empty:
        user_cp = user_cp.merge(
            df_coupons,
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
    results = df_regulations[df_regulations["keyword"] == keyword]["content"].tolist()
    if not results:
        return {
            "keyword": keyword,
            "search_result": [f"'{keyword}'에 대한 정책 정보를 찾을 수 없습니다."]
        }
    return {
        "keyword": keyword,
        "search_result": results
    }


# ============================================================
# 5. Tools 명세
# ============================================================
tools = [
    {
        "type": "function",
        "name": "show_cart",
        "description": "지정된 사용자(user_id)의 현재 장바구니에 담긴 모든 상품을 반환합니다. 각 항목에 대해 상품 ID, 상품명, 가격, 수량, 장바구니에 추가된 일시를 포함합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "장바구니를 조회할 사용자의 고유 식별자 (예: 'U001')"
                }
            },
            "required": ["user_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "search_product",
        "description": "상품명에 특정 키워드를 포함하는 제품을 검색하고, 평점 순으로 정렬된 결과를 반환합니다. 필요시 카테고리(category)로 추가 필터링이 가능합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "검색할 상품명 키워드 (예: '노트북')"
                },
                "category": {
                    "type": "string",
                    "description": "선택적 카테고리 필터 (예: '전자기기')"
                }
            },
            "required": ["keyword"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "add_to_cart",
        "description": "사용자의 장바구니에 지정된 상품(product_id)과 수량(quantity)을 추가합니다. 동일 상품이 이미 있으면 수량을 증가시키고, 새 항목으로 추가합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "장바구니에 상품을 추가할 사용자의 고유 식별자 (예: 'U001')"
                },
                "product_id": {
                    "type": "string",
                    "description": "장바구니에 추가할 상품의 고유 식별자 (예: 'P003')"
                },
                "quantity": {
                    "type": "integer",
                    "description": "추가할 상품 수량 (기본값: 1)",
                    "default": 1,
                    "minimum": 1
                }
            },
            "required": ["user_id", "product_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "remove_from_cart",
        "description": "사용자의 장바구니에서 상품명을 포함하는 키워드(keyword) 또는 특정 상품 ID(product_id)를 사용해 항목을 제거합니다. keyword 또는 product_id 중 하나를 반드시 지정해야 합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "장바구니에서 상품을 제거할 사용자의 고유 식별자 (예: 'U001')"
                },
                "keyword": {
                    "type": "string",
                    "description": "상품명에 포함된 키워드로 제거 대상을 지정 (예: '우산')"
                },
                "product_id": {
                    "type": "string",
                    "description": "제거할 정확한 상품 ID (예: 'P005')"
                }
            },
            "required": ["user_id"],
            "anyOf": [
                { "required": ["keyword"] },
                { "required": ["product_id"] }
            ],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "view_order_history",
        "description": "사용자의 전체 주문 내역을 반환합니다. 각 주문에 대해 주문 번호, 주문 일자, 총 결제 금액, 결제 상태, 배송 상태, 택배사, 운송장 번호, 배송 진행 단계, 주문에 포함된 상품명 목록을 제공합니다. 이 함수로도 최근 주문의 배송 상태를 확인할 수 있습니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "주문 내역을 조회할 사용자의 고유 식별자 (예: 'U001')"
                }
            },
            "required": ["user_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "view_order_details",
        "description": "특정 주문(order_id)의 상세 내역을 조회합니다. 주문에 포함된 각 상품의 ID, 상품명, 수량, 단가, 할인 적용 가격을 반환합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "주문 상세를 조회할 사용자의 고유 식별자 (예: 'U001')"
                },
                "order_id": {
                    "type": "string",
                    "description": "상세 내역을 조회할 주문의 고유 식별자 (예: 'O001')"
                }
            },
            "required": ["user_id", "order_id"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "view_user_profile",
        "description": "사용자의 기본 프로필 정보(이름, 이메일, 전화번호, 주소, 포인트, 멤버십)와 보유 쿠폰 정보를 반환합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "프로필을 조회할 사용자의 고유 식별자, 예: 'U001'"
                }
            },
            "required": ["user_id"],
            "additionalProperties": False
        }
    },
    {
    "type": "function",
    "name": "search_policy_info",
    "description": "지정된 키워드에 대한 상준몰 정책/약관 정보를 검색합니다. 예: '주문 취소', '반품', '환불', '배송', '재입고'에 관련된 약관만 질문하세요.",
    "parameters": {
        "type": "object",
        "properties": {
            "keyword": {
                "type": "string",
                "description": "정책을 검색할 키워드 (예: '주문 취소', '반품', '환불', '배송', '재입고'만 넣을 수 있습니다.)"
            }
        },
        "required": ["keyword"],
        "additionalProperties": False
    }
  }
]


# ============================================================
# 6. Tools 반환 포맷
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


# ============================================================
# 7. 시나리오 정의
# ============================================================
# 위에서 만든 함수들로 처리 가능한 시나리오
question_topics = [
    "장바구니 조회",
    "장바구니에 상품 추가",
    "장바구니에서 상품 제거",
    "상품 키워드 검색",
    "궁금한 상품 조회",
    "카테고리별 상품 검색",
    "평점순 제품 정렬 조회",
    "전체 주문 내역 조회",
    "최근 주문 배송 상태 조회",
    "특정 주문 상세 조회",
    "주문에 포함된 상품 목록 조회",
    "배송 정보 조회 (택배사/운송장/배송 상태)",
    "결제 상태 조회",
    "주문 총액 조회",
    "주문 일자 조회",
    "위시리스트 조회",
    "사용자 쿠폰 조회",
    "리뷰 작성",
    "사용자 프로필 조회",
    "사용자 주소 조회",
    "사용자 포인트 조회",
    "사용자 멤버십 등급 조회"
    "환불 약관 확인",
    "교환 약관 확인",
    "재입고 약관 확인",
    "반품 약관 확인",
    "배송 약관 확인",
    "환불 약관 확인",
]

# 현재 함수로 처리 불가능한 시나리오
unsupported_scenarios = [
    "리뷰 삭제",
    "리뷰 수정",
    "사용자 프로필 수정",
    "비밀번호 변경",
    "주문 취소 요청",
    "환불 요청",
    "교환 요청",
    "배송지 변경",
    "장바구니 전체 비우기",
    "장바구니 수량 수정",
    "비회원 주문 조회",
    "결제 수단 변경",
    "결제 취소",
    "알림 설정 변경",
    "회원 탈퇴",
    "비밀번호 초기화",
    "SMS 수신 동의 변경",
    "리뷰 스팸 신고",
    "상품 재입고 알림 신청",
    "연애 상담",
    "날씨 문의",
    "심리 상담",
    "상품 비교",
    "이벤트 응모",
    "적립금 사용 설정",
    "쿠폰 직접 등록",
    "카드 영수증 발급",
    "배송 기사 변경 요청",
    "구매 확정 철회",
    "마일리지 전환",
    "선물하기",
    "상품 사용 후기 이미지 등록"]


# ============================================================
# 8. 잡담(노이즈) 데이터 로드
# ============================================================
question_df = pd.read_csv('https://raw.githubusercontent.com/songys/Chatbot_data/master/ChatbotData.csv')
question_df.head()
question_df = question_df.drop_duplicates(subset='Q')
chit_chat_question = question_df['Q'].to_list()
questions = ['"' + question +'"과 같은 사용자의 단순한 잡담' for question in chit_chat_question]


# ============================================================
# 9. 유틸리티 함수
# ============================================================
def generate_random_date():
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2025, 12, 31)
    delta_days = (end_date - start_date).days
    random_days = random.randint(0, delta_days)
    random_date = start_date + timedelta(days=random_days)
    return random_date.strftime('%Y-%m-%d')

# 예시 출력
print(generate_random_date())

import random

def pick_random_yn():
    return random.choice(['Yes', 'No'])

# 예시 출력
print(pick_random_yn())


# ============================================================
# 10. 데이터 생성 함수
# ============================================================
def make_function_calling_data(tools, cids, tools_return_format, question_topics, unsupported_scenarios):
  client = openai.OpenAI()

  # 유저 ID를 1개 랜덤 선택.
  # 함수 호출 시 유저의 ID에 맞춰서 호출될 것이기 때문.
  cid = random.sample(cids, 1)

  # 함수가 처리 가능한 시나리오를 2개 선택
  # 위에서 선언한 question_topics에서 랜덤으로 2개 선택.
  two_question_topics = random.sample(question_topics, 2)

  # 함수가 처리 불가능한 시나리오를 1개 선택
  # 위에서 선언한 unsupported_scenarios와 일상 대화 데이터 questions에서 랜덤으로 1개 선택.
  one_unsupported_scenario = random.sample(unsupported_scenarios, 1)

  # 오늘 날짜를 랜덤으로 생성. ex) 2025-04-21
  # 여기서는 랜덤으로 하지만 실제로는 여러분들의 시나리오에 맞게 또는 아래 이루어지는 대화와 모순되지 않게 날짜를 생성하세요.
  chat_date = generate_random_date()

  # 'Yes' or 'No' 문자열 둘 중 하나 랜덤으로 선택
  complain = pick_random_yn()

  prompt = f"""
  당신은 온라인 쇼핑몰 '상준몰'의 AI 챗봇을 파인튜닝하기 위한 펑션콜링 학습 데이터를 생성해야 합니다.

  1. 챗봇은 상준몰 AI 상담사입니다. 고객의 문의에 답변하기 위해 tools에 기반하려 function call을 해야 합니다.

  2. 사용 가능한 tools 목록(function name, 설명, parameters)
  {tools}

  3. 각 tools 함수의 return 결과물 형식은 다음과 같습니다.
  {tools_return_format}

  4. 고객의 ID는 {cid} 라고 가정합니다.

  5. 채팅 날짜는 {chat_date} 라고 가정합니다.

  6. complain 이 'Yes'면 고객이 컴플레인 하는 상황을, 'No'면 그렇지 않은 상황을 가정하세요.
  complain: {complain}

  7. 대화의 주제는 다음을 반드시 포함하세요. 이는 필수입니다.
  주제: {two_question_topics}

  8. 함수를 호출해도 해결할 수 없거나 함수랑 상관없는 대화 요청도 중간에 포함하십시오. 예를 들어 아래의 주제도 고려해볼 수 있겠습니다.
  주제: {one_unsupported_scenario}

  9. 함수로 처리할 수 없는 고객의 요청 또는 쇼핑몰 컴플레인은 담당자에게 전달하겠다고 하십시오.

  10. 멀티턴 대화에서 이전에 했던 대화 내용을 계속 끌고가는 양상을 보여주십시오. 질문마다 주제를 다르게 하는 것은 지양하세요.
"""

  prompt += """
  8. AI 상담사는 다음과 같은 일을 할 수 있습니다.
   - AI 상담사는 고객 발화에 맞는 응답을 생성해야 합니다. 이를 위해 일련의 tools 또는 function calls을 생성하며 멀티턴의 대화를 통해 고객을 응대해야 합니다.
   예를 들어서 고객이 포인트를 문의하는 경우 view_user_profile를 호출하여 호출 결과를 참고하여 적절한 답변하는 것이 가능합니다.
   호출 결과는 가상으로 만드십시오.
   - 고객과의 대화를 종료하기 전, '더 궁금하신 사항이 있으신가요?' 라고 물으세요. 고객이 더 문의할 사항이 없으면, 다음과 같이 진행하세요.
   - 고객이 너는 누구인지 물어보면, '저는 상준몰의 AI 상담사입니다. 상준몰에서 판매중인 제품에 대한 문의, 또는 고객님의 주문에 대한 문의를 도와드릴 수 있습니다.' 라고 답변하세요.

  9. AI 상담사는 주어진 함수 외의 일은 할 수 없습니다. ** 절대로 아래와 같은 일을 직접 해주는 것처럼 답변해서는 안됩니다.**
   - AI 상담사는 함수에 없는 문제는 결코 해결할 수 없습니다.
   - AI 상담사는 고객의 환불, 교환, 주문 등 업무 처리 요청을 직접적으로 처리해 수는 없습니다.
   - AI 상담사의 역할은 실제 인간 담당자 부재 시, 고객의 요구사항을 파악하여 실제 인간 담당자에게 요약하여 전달하는 것임을 명심하세요.
   - 고객이 환불, 교환, 주문 취소 등 업무 처리 요청을 할 경우, 직접 처리하겠다고 답변하지 말고, '문의하신 내용을 담당자에게 전달하여 신속히 처리하겠습니다.' 라고 답변하세요.
   - 쇼핑몰 고객센터 업무 외의 다른 질문에 대해서는 '죄송하지만, 제가 답변할 수 없습니다' 라고 답하세요.

  ### 학습 데이터 생성 시 주의 사항

  10. 고객이 주문 내역에 대해 문의할 때에는, 상품명 및 주문 기간에 대한 정보를 포함하여 구체적인 질문을 한다고 가정하세요.
      get_order_history 함수를 호출해야 할 상황에서, 고객이 정확한 주문 일자를 말하지 않고, 그냥 '최근에' 또는 '이번에' 와 같이 요청한 경우, 대화날짜로부터 이전 3개월 간의 이력을 조회하세요. start_date를 대화날짜로부터 3개월 전의 날짜, end_date를 대화날짜로 지정하면 됩니다.
      그렇지 않고, 고객이 특정 주문일자를 말한 경우, start_date과 end_date를 해당 주문일자 -1일, +1일로 설정하세요.
      **고객이 쇼핑몰 운영 정책이나 상품 정보 등에 대한 문의를 했을 때, 검색되지 않은 내용을 지어서 답변하지 마세요.**

  11. 출력 형식: 다음과 같이 '(role) 내용' 순으로 생성하며, 각 대화 사이에는 '\n'으로 구분하세요. 실제 현실에서 고객과 AI 상담사 간에 일어날 수 있는 대화처럼 구어체로 자연스럽게 구성하세요. 6~12회의 멀티턴으로 구성하세요.
  [고객 ID] 고객 ID
  [대화날짜] 대화날짜
  (고객) 고객 발화
  (AI 상담사) AI 상담사 응답
  (function_call) list(dict) 형식, dict에는 name, arguments(dict 형식) 포함
  (function_response) function 수행 결과를 list(dict) 형식으로 리턴

  **예시 1**
  [고객 ID] U001
  [대화날짜] 2025-04-10

  (고객) 안녕하세요.
  (AI 상담사) 안녕하세요! 상준몰 AI 상담사입니다. 무엇을 도와드릴까요?
  (고객) 최근에 주문한 캣타워 배송 문의드리려구요.
  (function_call) [{"name": "view_order_history", "arguments": {"user_id": "U001"}}]
  (function_response) [{'order_id': 'O001', 'order_date': '2025-01-22', 'total': 34000, 'payment_status': '결제완료', 'delivery_status': '배송중', 'courier': '우체국택배', 'tracking_number': '138705465401', 'status': '출고완료', 'products': '프리미엄 캣타워 XL'}]
  (AI 상담사) 네, 2025년 1월 22일 프리미엄 캣타워 XL 상품을 주문하신 내역을 확인하였습니다. 배송 현황을 조회해 보겠습니다.
  (function_call) [{"name": "view_order_details", "arguments": {"user_id": "U001", "order_id": "O001"}}]
  (function_response) [{'order_id': 'O001', 'product_id': 'P001', 'name': '프리미엄 캣타워 XL', 'quantity': 2, 'price': 23000, 'discount_price': 17000}]
  (AI 상담사) 고객님께서 주문하신 프리미엄 캣타워 XL 상품은 현재 배송중에 있으며, 배송사는 우체국택배, 송장번호는 138705465401입니다.
  (고객) 저 근데 어제 고양이가 커튼을 찢어놨어요… 집안이 난리예요.
  (AI 상담사) 아이고, 많이 놀라셨겠어요. 고양이가 갑자기 활발해지는 시기일 수도 있겠네요. 혹시 캣타워 사용하시기 시작하면 좀 더 안정될 수도 있어요.
  (고객) 요즘 강아지 샴푸 괜찮은 거 혹시 들어온 거 있나요?
  (function_call) [{"name": "search_product", "arguments": {"keyword": "강아지 샴푸"}}]
  (function_response) [{'success': True, 'keyword': '강아지 샴푸', 'category_filter': None, 'result_count': 1, 'products': [{'id': 'P701', 'name': '무향 저자극 강아지 샴푸 500ml', 'price': 16800, 'category': '반려동물', 'rating': 4.9}]}]
  (AI 상담사) ‘무향 저자극 강아지 샴푸 500ml’ 상품이 있습니다. 평점도 높고 저자극 제품으로 인기 있는 상품입니다.
  (고객) 아까 그 택배 말인데요, 그냥 안 받고 싶어졌어요.
  (AI 상담사) 고객님, 프리미엄 캣타워 XL 주문 건을 취소하고자 하시는 걸까요? 관련 정책을 확인해보겠습니다.
  (function_call) [{"name": "search_policy_info", "arguments": {"keyword": "주문 취소"}}]
  (function_response) [{'keyword': '주문 취소', 'search_result': ['주문 취소는 상품이 출고되기 전에는 언제든 가능합니다. 출고 이후에는 반품으로 처리됩니다.', '주문 취소 시 사용한 포인트는 자동 환불됩니다.', '주문 취소는 상준몰 주문내역 > 주문취소 버튼을 통해 가능합니다.']}]
  (AI 상담사) 네 고객님, 상품이 이미 출고되어 배송중에 있으므로 현재 주문 취소는 불가하며, 배송을 받으신 후 반품으로 처리하실 수 있습니다.
  (고객) 네, 그럼 반품해주세요.
  (function_call) [{"name": "search_policy_info", "arguments": {"keyword": "반품"}}]
  (function_response) [{'keyword': '반품', 'search_result': ['반품 신청은 배송일로부터 5일 이내에 가능합니다.', '반품 시 왕복 배송비가 부과됩니다.', '반품 신청은 상준몰 주문내역 > 배송완료 > 반품 버튼을 눌러 신청할 수 있습니다.']}]
  (AI 상담사) 반품은 상준몰 주문내역 > 배송 완료 > 반품 버튼을 눌러 신청하실 수 있습니다. 원하실 경우, 담당자에게 연결해드릴 수도 있습니다.
  (고객) 상준몰에 그 버튼이 안 보여요.
  (AI 상담사) 확인하였습니다. 담당자에게 요청 내용을 전달하여 직접 처리해드리겠습니다. 더 궁금하신 점이 있으실까요?
  (고객) 아니요.
  (AI 상담사) 네, 문의해 주셔서 감사합니다. 상준몰 고객센터 AI 상담사였습니다.

  **예시 2**
  [고객 ID] C002
  [대화날짜] 2025-04-09

  (고객) 안녕하세요.
  (AI 상담사) 안녕하세요! 상준몰 AI 상담사입니다. 무엇을 도와드릴까요?
  (고객) 남성용 기모 후드 집업 사이즈 문의드려요.
  (function_call) [{"name": "search_product", "arguments": {"keyword": "남성용 기모 후드 집업"}}]
  (function_response) [{'success': True, 'keyword': '남성용 기모 후드 집업', 'category_filter': None, 'result_count': 1, 'products': [{'id': 'P024', 'name': '남성용 기모 후드 집업', 'price': 49000, 'category': '상의', 'rating': 4.6, 'size_info': 'S, M, L, XL, XXL', 'description': '넉넉한 사이즈로 제작된 겨울용 기모 후드 집업입니다.'}]}]
  (AI 상담사) 남성용 기모 후드 집업은 넉넉한 사이즈로 제작되어 편안한 착용감을 제공합니다. 사이즈는 S, M, L, XL, XXL까지 준비되어 있습니다. 어떤 사이즈가 궁금하신가요?
  (고객) 근데 어제 와이셔츠 다림질하다가 태웠어요… 옷이란 게 참 어렵네요.
  (AI 상담사) 아이고, 많이 당황하셨겠어요. 옷 관리 정말 쉽지 않죠. 그래도 새 옷으로 기분 전환하시면 좋을 것 같아요.
  (고객) 혹시 L보다 더 큰 거 있는 거였죠?
  (AI 상담사) 네, 해당 상품은 L보다 큰 XL, XXL 사이즈도 함께 준비되어 있습니다.
  (고객) 감사합니다.
  (AI 상담사) 더 궁금하신 점이 있으신가요?
  (고객) 아뇨
  (AI 상담사) 그럼 상담을 종료하겠습니다. 지금까지 상준몰 고객센터 AI 상담사였습니다. 감사합니다.

  **예시 3**
  [고객 ID] C003
  [대화날짜] 2025-02-20

  (고객) 안녕하세요 ㅜㅜ
  (AI 상담사) 안녕하세요! 상준몰 AI 상담사입니다. 무엇을 도와드릴까요?
  (고객) 어제 대저토마토 2kg 주문하려고 했는데 품절돼가지구요 ㅜㅜ 혹시 재고 없는건가요?
  (function_call) [{"name": "search_product", "arguments": {"keyword": "대저토마토"}}]
  (function_response) [{'success': True, 'keyword': '대저토마토', 'category_filter': None, 'result_count': 2, 'products': [{'id': 'P902', 'name': '부산 짭짤이 대저 토마토 1kg', 'price': 12800, 'rating': 4.7, 'stock': 1}, {'id': 'P294', 'name': '대저토마토 산지직배송 5kg', 'price': 41900, 'rating': 4.8, 'stock': 24}]}]
  (AI 상담사) 고객님, 현재 상준몰에는 '대저토마토 2kg' 상품은 없고, 대신 '부산 짭짤이 대저 토마토 1kg', '대저토마토 산지직배송 5kg' 상품이 있습니다. 혹시 이 중 문의하신 상품이 있으실까요?
  (고객) 부산 짭짤이 대저 토마토 1kg이요. 1kg짜리를 2개 시키려고 했어요.
  (AI 상담사) 네, 확인해 보니 '부산 짭짤이 대저 토마토 1kg' 상품의 현재 재고 수량은 1개입니다.
  (고객) 1개만 남아서 2개로 수량 지정하면 품절로 뜬거군요.
  (AI 상담사) 네, 현재는 1개까지만 주문 가능합니다.
  (고객) 오늘 보니까 장바구니에 있던 운동화가 없어진 것 같던데요.
  (AI 상담사) 말씀해주신 상품이 장바구니에서 보이지 않는다면, 장바구니 상태를 직접 확인해드릴 수 있습니다. 원하시면 조회해드릴까요?
  (고객) 괜찮아요. 그 토마토 혹시 다시 들어올 가능성은 없을까요?
  (AI 상담사) 네, 재입고 관련 정책을 확인해보겠습니다.
  (function_call) [{"name": "search_policy_info", "arguments": {"keyword": "재입고"}}]
  (function_response) [{'keyword': '재입고', 'search_result': ['일부 품절 상품은 재입고 시점이 불확정입니다.', '상품 상세 페이지에서 '재입고 알림 신청'이 가능하면 알림 설정을 해주세요.', '재입고 여부는 판매자 또는 상준몰 담당자가 별도 안내드립니다.']}]
  (AI 상담사) 현재 해당 상품의 정확한 재입고 일정은 확인되지 않았습니다. 상품 상세 페이지에서 ‘재입고 알림 신청’이 가능하면 알림을 설정해주시거나, 요청하신 내용을 담당자에게 전달해드릴 수 있습니다.
  (고객) 그렇게 해주세요. 문자로 알려주세요.
  (AI 상담사) 네 알겠습니다. 요청하신 내용을 담당자에게 전달하겠습니다. 더 궁금하신 점 있으실까요?
  (고객) 아뇨 없어요.
  (AI 상담사) 네, 그럼 상담을 종료하겠습니다. 지금까지 상준몰 고객센터 AI 상담사였습니다. 감사합니다.

  **예시 4**
  [고객 ID] C004
  [대화날짜] 2025-04-12
  (고객) 안녕하세요
  (AI 상담사) 안녕하세요! 상준몰 AI 상담사입니다. 무엇을 도와드릴까요?
  (고객) 저 저번에 주문했던 전기포트 있잖아요, 그거 배송 조회하고 싶어요
  (function_call) [{"name": "view_order_history", "arguments": {"user_id": "C004"}}]
  (function_response) [{'order_id': 'O088', 'order_date': '2025-04-09', 'total': 32000, 'payment_status': '결제완료', 'delivery_status': '배송중', 'courier': 'CJ대한통운', 'tracking_number': '413982530245', 'status': '출고완료', 'products': '프리미엄 유리 전기포트'}]
  (AI 상담사) 고객님께서 4월 9일에 주문하신 ‘프리미엄 유리 전기포트’ 상품은 현재 배송중이며, 택배사는 CJ대한통운, 송장번호는 413982530245입니다.
  (고객) 그렇군요! 근데 오늘 날씨 왜 이렇게 덥죠
  (AI 상담사) 네, 오늘 정말 초여름 날씨처럼 덥죠. 시원한 음료 많이 드시면서 건강 유의하세요!
  (고객) 맞다, 근데 그 포트 있잖아요, 유리로 된 거 말고 제가 시킨 그거, 그거 정확히 어떤 거였죠?
  (AI 상담사) 고객님께서 말씀하신 상품은 '프리미엄 유리 전기포트'로 확인됩니다. 주문 상세 내역을 다시 보여드릴게요.
  (function_call) [{"name": "view_order_details", "arguments": {"user_id": "C004", "order_id": "O088"}}]
  (function_response) [{'order_id': 'O088', 'product_id': 'P110', 'name': '프리미엄 유리 전기포트', 'quantity': 1, 'price': 39000, 'discount_price': 32000}]
  (AI 상담사) 주문하신 상품은 '프리미엄 유리 전기포트'이며, 수량은 1개, 결제 금액은 32,000원입니다.
  (고객) 네 맞아요. 제가 기억을 잘 못해서요.
  (AI 상담사) 괜찮습니다. 언제든지 편하게 문의 주세요. 더 궁금하신 점 있으신가요?
  (고객) 아뇨, 그거면 됐어요
  (AI 상담사) 네, 문의해 주셔서 감사합니다. 지금까지 상준몰 고객센터 AI 상담사였습니다. 좋은 하루 되세요!
  """

  try:
    response = client.chat.completions.create(
        model = 'gpt-4o',
        messages = [{'role': 'system',
                     'content': "당신은 상준몰 AI 상담사를 위해 멀티턴 챗봇 파인튜닝용 데이터를 생성하는 전문가입니다."},
                    {'role': 'user',
                     'content': prompt}],
        temperature = 0.4)
    result = response.choices[0].message.content
    return result
  except openai.APIError as e:
    print(f"OpenAI API returned an API Error: {e}")
  except openai.APIConnectionError as e:
    print(f"OpenAI API connection failed: {e}")
  except openai.ReteLimitError as e:
    print(f"OpenAI API request limit reached: {e}")


# ============================================================
# 11. 파싱 함수
# ============================================================
def parse_metadata(text: str):
    """고객 ID와 대화날짜 추출"""
    customer_id_match = re.search(r'\[고객 ID\]\s*(\w+)', text)
    date_match = re.search(r'\[대화날짜\]\s*([\d\-]+)', text)
    customer_id = customer_id_match.group(1) if customer_id_match else None
    date = date_match.group(1) if date_match else None
    return customer_id, date

def parse_to_qwen_format(text: str):
    messages = []
    pattern = re.compile(r'\((고객|AI 상담사|function_call|function_response)\)\s*(.+?)(?=\n\(|\Z)', re.DOTALL)

    last_role = None  # 직전 메시지의 역할 추적

    for match in pattern.finditer(text.strip()):
        role_type, content = match.groups()
        content = content.strip()

        if role_type == "고객":
            messages.append({
                "role": "user",
                "content": content
            })
            last_role = "user"

        elif role_type == "AI 상담사":
            messages.append({
                "role": "assistant",
                "content": content
            })
            last_role = "assistant"

        elif role_type == "function_call":
            try:
                calls = ast.literal_eval(content)
                # 직전 assistant 메시지 제거
                if last_role == "assistant":
                    messages.pop()
                for call in calls:
                    messages.append({
                        "role": "assistant",
                        "content": f"<tool_call>\n{json.dumps(call, ensure_ascii=False)}\n</tool_call>"
                    })
                last_role = "assistant"
            except Exception as e:
                raise ValueError(f"[function_call 파싱 실패] 원본: {content}\n오류: {e}")

        elif role_type == "function_response":
            try:
                parsed = ast.literal_eval(content)
                payload = json.dumps(parsed, ensure_ascii=False)
                messages.append({
                    "role": "user",
                    "content": f"<tool_response>\n{payload}\n</tool_response>"
                })
                last_role = "user"
            except Exception as e:
                raise ValueError(f"[function_response 파싱 실패] 원본: {content}\n오류: {e}")

    return messages


# ============================================================
# 12. 시스템 프롬프트 생성 함수
# ============================================================
import json
import random

def generate_qwen_system_prompt(tools: list, cid: str, current_date: str = "2024-09-30") -> str:
    header = """당신은 상준몰의 AI 상담사입니다. 성심성의껏 상담하십시오.

로그인한 사용자의 현재 ID: %s
오늘 날짜: %s

# Tools

You may call one or more functions to assist with the user query.

You are provided with function signatures within <tools></tools> XML tags:
<tools>
""" % (cid, current_date)

    shuffled_tools = tools[:]
    random.shuffle(shuffled_tools)

    tool_defs = ""
    for tool in shuffled_tools:
        entry = {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["parameters"]
            }
        }
        tool_defs += json.dumps(entry, ensure_ascii=False) + "\n"

    footer = """</tools>

For each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:
<tool_call>
{"name": <function-name>, "arguments": <args-json-object>}
</tool_call>"""

    return header + tool_defs + footer


# ============================================================
# 13. 메인 실행
# ============================================================
cids = ['U001', 'U002', 'U003', 'U004', 'U005', 'U006', 'U007', 'U008', 'U009', 'U010']

# 데이터 생성 (400건)
result_lst = []
for question in tqdm(questions[:400]):
    result_lst.append(make_function_calling_data(tools, cids, tools_return_format, question_topics, unsupported_scenarios + [question]))

# 파싱
cids_parsed = []
dates = []
messages = []
for sample in result_lst:
    try:
        cid, date = parse_metadata(sample)
        message = parse_to_qwen_format(sample)
        cids_parsed.append(cid)
        dates.append(date)
        messages.append(message)
    except:
        continue

# DataFrame 구성
tools_lst = [tools] * len(messages)
df = pd.DataFrame({
    'tools': tools_lst,
    'cid': cids_parsed,
    'dates': dates,
    'messages': messages
})

# 시스템 프롬프트 생성
system_prompts = []
for cid, today_date in zip(df['cid'].to_list(), df['dates'].to_list()):
    system_prompts.append(generate_qwen_system_prompt(tools, cid, today_date))
df['system_prompt'] = system_prompts

# HuggingFace 업로드
dataset = datasets.Dataset.from_pandas(df)
dataset.push_to_hub("ecommerce-function-calling-datasets-korean")
