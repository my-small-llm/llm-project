-- 1. Users & Addresses

CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE addresses (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    recipient_name VARCHAR(100) NOT NULL,
    phone VARCHAR(50) NOT NULL,
    line1 VARCHAR(255) NOT NULL,
    line2 VARCHAR(255),
    is_default BOOLEAN DEFAULT FALSE,
    gate_password VARCHAR(100),
    delivery_note TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Partial Unique Index for single default address per user
CREATE UNIQUE INDEX idx_addresses_user_default ON addresses (user_id) WHERE is_default = TRUE;

-- 2. Restaurants & Menu

CREATE TABLE restaurants (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    category VARCHAR(50),
    phone VARCHAR(50),
    min_order_amount INTEGER,
    rating_avg NUMERIC(3,2),
    rating_count INTEGER,
    is_active BOOLEAN,
    is_open_weekday BOOLEAN,
    weekday_open TIME,
    weekday_close TIME,
    is_open_weekend BOOLEAN,
    weekend_open TIME,
    weekend_close TIME,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE menu_items (
    id UUID PRIMARY KEY,
    restaurant_id UUID NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    base_price INTEGER NOT NULL,
    is_available BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 3. Cart (Server-side)

CREATE TABLE carts (
    id UUID PRIMARY KEY,
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    restaurant_id UUID NOT NULL REFERENCES restaurants(id),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE cart_items (
    id UUID PRIMARY KEY,
    cart_id UUID NOT NULL REFERENCES carts(id) ON DELETE CASCADE,
    menu_item_id UUID NOT NULL REFERENCES menu_items(id),
    name_snapshot VARCHAR(255) NOT NULL,
    unit_price_snapshot INTEGER NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    special_request TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 4. Orders (Snapshot + Payment Columns)

CREATE TABLE orders (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id), -- User can be null if deleted? Requirement says "NULL 허용 권장"
    restaurant_id UUID REFERENCES restaurants(id), -- Restaurant can be null if deleted? Requirement says "NULL 허용 권장"
    status VARCHAR(50) NOT NULL, -- pending/paid/preparing/delivering/delivered/cancelled
    
    -- Delivery Address Snapshot
    delivery_recipient_name VARCHAR(100),
    delivery_phone VARCHAR(50),
    delivery_line1 VARCHAR(255),
    delivery_line2 VARCHAR(255),
    delivery_gate_password VARCHAR(100),
    delivery_note TEXT,
    
    -- Amounts
    subtotal_amount INTEGER,
    discount_amount INTEGER,
    delivery_fee_amount INTEGER,
    total_amount INTEGER,
    
    -- Payment Info (Absorbed)
    payment_method VARCHAR(20), -- card/kakao etc
    pg_id VARCHAR(100),
    payment_status VARCHAR(20), -- pending/paid/failed/cancelled/refunded
    paid_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE order_items (
    id UUID PRIMARY KEY,
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    menu_item_id UUID REFERENCES menu_items(id), -- Nullable if menu item deleted
    name_snapshot VARCHAR(255),
    unit_price_snapshot INTEGER,
    quantity INTEGER,
    special_request TEXT
);
