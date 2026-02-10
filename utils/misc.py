import random
from datetime import datetime, timedelta

## 랜덤 날짜 생성 함수
def generate_random_date():
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2025, 12, 31)
    delta_days = (end_date - start_date).days
    random_days = random.randint(0, delta_days)
    random_date = start_date + timedelta(days=random_days)
    return random_date.strftime('%Y-%m-%d')

## 랜덤으로 Yes No를 반환하는 함수
def pick_random_yn():
    return random.choice(['Yes', 'No'])