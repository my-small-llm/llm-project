import uuid
import random
from datetime import datetime, timedelta

def generate_uuid():
    return str(uuid.uuid4())

def get_random_phone():
    return f"010-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}"

def escape_sql(text):
    if text is None:
        return "NULL"
    return "'" + text.replace("'", "''") + "'"

# Data Pools
first_names = ["철수", "영희", "민수", "지우", "동현", "서준", "하은", "도윤", "수아", "예준"]
last_names = ["김", "이", "박", "최", "정", "강", "조", "윤", "장", "임"]
locations = ["서울시 강남구", "서울시 서초구", "서울시 송파구"]
restaurant_names = [
    ("BBQ 황금올리브", "치킨"), ("교촌치킨", "치킨"), ("BHC 뿌링클", "치킨"),
    ("도미노피자", "피자"), ("피자헛", "피자"), ("미스터피자", "피자"),
    ("본죽", "한식"), ("엽기떡볶이", "분식"), ("김가네", "분식"), ("홍콩반점", "중식")
]
menu_pool = {
    "치킨": [("황금올리브치킨", 20000), ("양념치킨", 21000), ("반반치킨", 21000), ("자소만", 5000), ("치즈볼", 4000)],
    "피자": [("포테이토피자", 25000), ("콤비네이션", 23000), ("페퍼로니", 22000), ("치즈오븐스파게티", 8000), ("콜라 1.25L", 2000)],
    "한식": [("야채죽", 10000), ("전복죽", 12000), ("소고기버섯죽", 11000), ("낙지김치죽", 11000), ("호박죽", 9000)],
    "분식": [("떡볶이", 14000), ("순대", 4000), ("모듬튀김", 5000), ("오뎅탕", 6000), ("주먹밥", 3000)],
    "중식": [("짜장면", 7000), ("짬뽕", 8000), ("탕수육(소)", 15000), ("군만두", 6000), ("볶음밥", 8000)]
}

users = []
restaurants = []
menu_items = []
carts = []
cart_items = []
orders = []
order_items = []

# 1. Users & Addresses
print("-- Generated Seed Data")
print("TRUNCATE order_items, orders, cart_items, carts, menu_items, restaurants, addresses, users CASCADE;")
print("")

print("-- 1. Users & Addresses")
for i in range(10):
    uid = generate_uuid()
    name = random.choice(last_names) + random.choice(first_names)
    email = f"user{i+1}@example.com"
    phone = get_random_phone()
    users.append({"id": uid, "name": name, "phone": phone})
    
    print(f"INSERT INTO users (id, email, phone, name) VALUES ('{uid}', '{email}', '{phone}', '{name}');")
    
    addr_id = generate_uuid()
    line1 = f"{random.choice(locations)} 테헤란로 {random.randint(100, 999)}"
    line2 = f"{random.randint(101, 2005)}호"
    print(f"INSERT INTO addresses (id, user_id, recipient_name, phone, line1, line2, is_default) VALUES ('{addr_id}', '{uid}', '{name}', '{phone}', '{line1}', '{line2}', TRUE);")

print("")

# 2. Restaurants & Menu Items
print("-- 2. Restaurants & Menu Items")
for i, (r_name, category) in enumerate(restaurant_names):
    rid = generate_uuid()
    phone = get_random_phone()
    rating = round(random.uniform(3.5, 5.0), 1)
    count = random.randint(10, 2000)
    
    restaurants.append({"id": rid, "name": r_name})
    
    print(f"INSERT INTO restaurants (id, name, category, phone, min_order_amount, rating_avg, rating_count, is_active, is_open_weekday, weekday_open, weekday_close, is_open_weekend, weekend_open, weekend_close) VALUES ('{rid}', '{r_name}', '{category}', '{phone}', 15000, {rating}, {count}, TRUE, TRUE, '09:00', '22:00', TRUE, '10:00', '22:00');")
    
    # Menus
    menus = menu_pool.get(category, menu_pool["치킨"]) # Fallback to chicken if category not found (should not happen)
    for j, (m_name, price) in enumerate(menus):
        mid = generate_uuid()
        menu_items.append({"id": mid, "restaurant_id": rid, "name": m_name, "price": price})
        print(f"INSERT INTO menu_items (id, restaurant_id, name, base_price, sort_order) VALUES ('{mid}', '{rid}', '{m_name}', {price}, {j+1});")

print("")

# 3. Carts (4 users)
print("-- 3. Carts")
cart_users = random.sample(users, 4)
for u in cart_users:
    cid = generate_uuid()
    # Pick a random restaurant
    r = random.choice(restaurants)
    rid = r["id"]
    
    print(f"INSERT INTO carts (id, user_id, restaurant_id) VALUES ('{cid}', '{u['id']}', '{rid}');")
    
    # Pick random menu items from this restaurant
    r_menus = [m for m in menu_items if m["restaurant_id"] == rid]
    selected_menus = random.sample(r_menus, random.randint(1, 3))
    
    for m in selected_menus:
        ciid = generate_uuid()
        qty = random.randint(1, 3)
        print(f"INSERT INTO cart_items (id, cart_id, menu_item_id, name_snapshot, unit_price_snapshot, quantity) VALUES ('{ciid}', '{cid}', '{m['id']}', '{m['name']}', {m['price']}, {qty});")

print("")

# 4. Orders (2 users)
print("-- 4. Orders")
order_users = random.sample(users, 2)
for u in order_users:
    oid = generate_uuid()
    # Pick a random restaurant
    r = random.choice(restaurants)
    rid = r["id"]
    
    # Delivery info (mock)
    d_name = u["name"]
    d_phone = u["phone"]
    d_line1 = "서울시 강남구"
    d_line2 = "101호"
    
    # Items
    r_menus = [m for m in menu_items if m["restaurant_id"] == rid]
    selected_menus = random.sample(r_menus, random.randint(1, 4))
    
    subtotal = 0
    items_sql = []
    
    for m in selected_menus:
        oiid = generate_uuid()
        qty = random.randint(1, 2)
        price = m['price']
        subtotal += price * qty
        items_sql.append(f"INSERT INTO order_items (id, order_id, menu_item_id, name_snapshot, unit_price_snapshot, quantity) VALUES ('{oiid}', '{oid}', '{m['id']}', '{m['name']}', {price}, {qty});")
        
    delivery_fee = 3000
    discount = 0
    total = subtotal + delivery_fee - discount
    
    # Payment
    pg_id = f"imp_{random.randint(100000, 999999)}"
    
    print(f"INSERT INTO orders (id, user_id, restaurant_id, status, delivery_recipient_name, delivery_phone, delivery_line1, delivery_line2, subtotal_amount, delivery_fee_amount, discount_amount, total_amount, payment_method, pg_id, payment_status, paid_at) VALUES ('{oid}', '{u['id']}', '{rid}', 'delivered', '{d_name}', '{d_phone}', '{d_line1}', '{d_line2}', {subtotal}, {delivery_fee}, {discount}, {total}, 'card', '{pg_id}', 'paid', NOW());")
    
    for sql in items_sql:
        print(sql)

