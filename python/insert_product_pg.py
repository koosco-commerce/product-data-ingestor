"""
PostgreSQL 더미 데이터 생성 및 삽입 스크립트

~103K 상품 + ~483K SKU 더미 데이터를 in-memory 생성하여
catalog / inventory DB에 배치 삽입한다.

의존성: pip install psycopg2-binary python-dotenv
"""

import itertools
import json
import os
import random
import uuid
from datetime import datetime

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_USER = os.getenv("PG_USER", "admin")
PG_PASS = os.getenv("PG_PASS", "admin")

BATCH_SIZE = 5000

# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------

OPTION_TEMPLATE = {
    "FASHION_TOP": {
        "Color": ["Black", "White", "Beige", "Navy"],
        "Size": ["S", "M", "L", "XL"],
    },
    "FASHION_BOTTOM": {
        "Color": ["Black", "Navy", "Gray"],
        "Size": ["S", "M", "L", "XL"],
    },
    "SHOES": {
        "Color": ["White", "Black"],
        "Size": ["230", "240", "250", "260", "270", "280"],
    },
    "HOME_DECOR": {
        "Color": ["Gray", "Beige", "Navy"],
        "Size": ["140x230", "160x260"],
    },
    "BEAUTY": {
        "Volume": ["30ml", "50ml", "100ml"],
        "Package": ["Single", "2-Pack"],
    },
    "ELECTRONICS": {
        "Model": ["Standard", "Pro", "Max"],
        "Color": ["Black", "White"],
    },
    "KITCHEN": {
        "Color": ["Black", "Silver", "White"],
        "Capacity": ["Small", "Medium", "Large"],
    },
    "ACCESSORY": {
        "Color": ["Black", "Brown", "Gray"],
        "Style": ["Classic", "Modern"],
    },
    "BOOK": {},
    "DEFAULT": {},
}

CATEGORY_LEAF_POOLS = {
    "FASHION_TOP": [26, 27, 28, 29, 30, 31, 32, 33, 34],
    "FASHION_BOTTOM": [59, 60, 61, 62, 63, 64, 65, 66],
    "SHOES": [18, 19, 20, 21, 22, 23, 24],
    "ACCESSORY": [89, 90, 91, 92, 93, 94, 95, 96],
    "BEAUTY": [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
    "ELECTRONICS": [104, 105, 106, 107, 108, 109],
    "HOME_DECOR": [106],
    "KITCHEN": [107],
    "BOOK": [105],
    "DEFAULT": [1, 17, 25, 35, 58, 67, 74, 88, 97, 103],
}

TEMPLATE_PRODUCT_COUNTS = {
    "DEFAULT": 60526,
    "FASHION_TOP": 11175,
    "HOME_DECOR": 8918,
    "KITCHEN": 7610,
    "ACCESSORY": 4471,
    "SHOES": 3888,
    "ELECTRONICS": 2170,
    "BEAUTY": 2163,
    "FASHION_BOTTOM": 1788,
    "BOOK": 797,
}

# 카테고리 목록 (id -> name) : CATEGORY_LEAF_POOLS 에 등장하는 모든 id 포함
CATEGORIES = {
    1: "Beauty", 2: "Skincare", 3: "Makeup", 4: "Hair Care",
    5: "Fragrance", 6: "Bath & Body", 7: "Nail Care", 8: "Tools & Brushes",
    9: "Men's Grooming", 10: "Sun Care", 11: "Lip Care", 12: "Eye Care",
    13: "Face Masks", 14: "Essential Oils", 15: "Oral Care",
    17: "Shoes", 18: "Running Shoes", 19: "Sneakers", 20: "Boots",
    21: "Sandals", 22: "Loafers", 23: "Formal Shoes", 24: "Slippers",
    25: "Tops", 26: "T-Shirts", 27: "Shirts", 28: "Blouses",
    29: "Tank Tops", 30: "Hoodies", 31: "Sweaters", 32: "Polo Shirts",
    33: "Crop Tops", 34: "Long Sleeve Shirts",
    35: "Outerwear",
    58: "Pants", 59: "Jeans", 60: "Chinos", 61: "Joggers",
    62: "Cargo Pants", 63: "Dress Pants", 64: "Leggings",
    65: "Shorts", 66: "Sweatpants",
    67: "Dresses & Skirts",
    74: "Bags",
    88: "Fashion Accessories", 89: "Bracelets", 90: "Rings",
    91: "Necklaces", 92: "Earrings", 93: "Watches",
    94: "Belts", 95: "Scarves", 96: "Hats",
    97: "Underwear & Homewear",
    103: "Digital & Life", 104: "Smartphones", 105: "Culture & Hobby",
    106: "Furniture & Interior", 107: "Living & Kitchen",
    108: "Computers", 109: "Audio",
}

# 상품명 생성용 단어 풀
ADJECTIVES = [
    "Premium", "Classic", "Modern", "Essential", "Elegant",
    "Stylish", "Comfortable", "Durable", "Lightweight", "Professional",
    "Luxury", "Natural", "Organic", "Ultra", "Smart",
    "Vintage", "Trendy", "Deluxe", "Compact", "Portable",
]

NOUNS_BY_TEMPLATE = {
    "FASHION_TOP": ["T-Shirt", "Shirt", "Hoodie", "Sweater", "Blouse", "Polo", "Top"],
    "FASHION_BOTTOM": ["Jeans", "Chinos", "Joggers", "Pants", "Shorts", "Leggings"],
    "SHOES": ["Sneakers", "Running Shoes", "Boots", "Loafers", "Sandals", "Slippers"],
    "HOME_DECOR": ["Rug", "Cushion", "Curtain", "Mat", "Pillow", "Throw Blanket"],
    "BEAUTY": ["Serum", "Cream", "Lotion", "Shampoo", "Oil", "Perfume", "Mask"],
    "ELECTRONICS": ["Charger", "Adapter", "Headphone", "Speaker", "Cable", "Battery"],
    "KITCHEN": ["Pot", "Pan", "Bottle", "Cup", "Container", "Storage Box", "Kettle"],
    "ACCESSORY": ["Bracelet", "Necklace", "Ring", "Belt", "Scarf", "Watch", "Hat"],
    "BOOK": ["Novel", "Guide", "Handbook", "Collection", "Edition", "Textbook"],
    "DEFAULT": ["Item", "Product", "Set", "Kit", "Pack", "Bundle", "Collection"],
}

MODEL_SUFFIXES = [
    "Pro", "Plus", "Max", "Lite", "Air", "SE", "GT", "X",
    "V2", "MK2", "Elite", "Core", "One", "Neo", "Prime",
]

# description 생성용 문장 풀
DESC_SENTENCES = [
    "High quality materials ensure long-lasting durability.",
    "Designed for everyday use with maximum comfort in mind.",
    "Perfect for both casual and formal occasions.",
    "Easy to clean and maintain, saving you time.",
    "Available in multiple colors and sizes to suit your preference.",
    "Crafted with attention to detail for a premium feel.",
    "Lightweight and portable, ideal for travel.",
    "Eco-friendly manufacturing process for a sustainable choice.",
    "Backed by our satisfaction guarantee for peace of mind.",
    "A must-have addition to your collection.",
    "Features an ergonomic design for optimal user experience.",
    "Made from premium grade materials sourced responsibly.",
    "Versatile design that complements any style.",
    "Built to withstand daily wear and tear.",
    "The perfect gift for friends and family.",
    "Innovative technology delivers superior performance.",
    "Tested rigorously to meet the highest standards.",
    "Combines functionality with aesthetic appeal.",
    "Your go-to choice for reliability and value.",
    "Sleek and modern design fits seamlessly into your lifestyle.",
]


# ---------------------------------------------------------------------------
# 연결 헬퍼
# ---------------------------------------------------------------------------

def get_connection(dbname: str):
    return psycopg2.connect(
        host=PG_HOST, port=PG_PORT,
        user=PG_USER, password=PG_PASS,
        dbname=dbname,
    )


# ---------------------------------------------------------------------------
# Phase 1: 데이터베이스 / 테이블 생성
# ---------------------------------------------------------------------------

def ensure_databases():
    conn = psycopg2.connect(
        host=PG_HOST, port=PG_PORT,
        user=PG_USER, password=PG_PASS,
        dbname="postgres",
    )
    conn.autocommit = True
    cur = conn.cursor()
    for db in ("catalog", "inventory"):
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db,))
        if not cur.fetchone():
            cur.execute(f"CREATE DATABASE {db} OWNER {PG_USER}")
            print(f"  Created database: {db}")
        else:
            print(f"  Database already exists: {db}")
    cur.close()
    conn.close()


def create_catalog_tables():
    conn = get_connection("catalog")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id BIGSERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL
        );

        CREATE TABLE IF NOT EXISTS products (
            id BIGSERIAL PRIMARY KEY,
            product_code VARCHAR(50) NOT NULL UNIQUE,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            price BIGINT NOT NULL,
            status VARCHAR(20) NOT NULL,
            category_id BIGINT REFERENCES categories(id),
            thumbnail_image_url VARCHAR(500),
            brand VARCHAR(100),
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NOT NULL
        );

        CREATE TABLE IF NOT EXISTS product_option_groups (
            id BIGSERIAL PRIMARY KEY,
            product_id BIGINT NOT NULL REFERENCES products(id),
            name VARCHAR(100) NOT NULL,
            ordering INT NOT NULL DEFAULT 0,
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NOT NULL
        );

        CREATE TABLE IF NOT EXISTS product_options (
            id BIGSERIAL PRIMARY KEY,
            option_group_id BIGINT NOT NULL REFERENCES product_option_groups(id),
            name VARCHAR(100) NOT NULL,
            additional_price BIGINT NOT NULL DEFAULT 0,
            ordering INT NOT NULL DEFAULT 0,
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NOT NULL
        );

        CREATE TABLE IF NOT EXISTS product_skus (
            id BIGSERIAL PRIMARY KEY,
            sku_id VARCHAR(100) NOT NULL UNIQUE,
            product_id BIGINT NOT NULL REFERENCES products(id),
            price BIGINT NOT NULL,
            option_values JSONB,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("  Catalog tables created.")


def create_inventory_table():
    conn = get_connection("inventory")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            sku_id VARCHAR(50) PRIMARY KEY,
            total_stock INT NOT NULL,
            reserved_stock INT NOT NULL,
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NOT NULL
        );
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("  Inventory table created.")


# ---------------------------------------------------------------------------
# Phase 2: 데이터 생성 (in-memory)
# ---------------------------------------------------------------------------

def _generate_name(template_key: str) -> str:
    adj = random.choice(ADJECTIVES)
    noun = random.choice(NOUNS_BY_TEMPLATE[template_key])
    suffix = random.choice(MODEL_SUFFIXES)
    return f"{adj} {noun} {suffix}"


def _generate_description() -> str:
    n = random.randint(3, 12)
    sentences = random.sample(DESC_SENTENCES, min(n, len(DESC_SENTENCES)))
    desc = " ".join(sentences)
    # 30 ~ 2000 자 보장
    if len(desc) < 30:
        desc = desc + " " + " ".join(random.choices(DESC_SENTENCES, k=3))
    return desc[:2000]


def generate_all_data():
    """모든 데이터를 in-memory 로 생성하여 dict 리스트로 반환."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    products = []       # (product_code, name, desc, price, status, cat_id, thumb, brand, created, updated, template_key)
    skus = []           # (sku_id, product_code, price, option_values_json)
    inventories = []    # (sku_id, total_stock, reserved_stock, created, updated)

    for template_key, count in TEMPLATE_PRODUCT_COUNTS.items():
        template = OPTION_TEMPLATE[template_key]

        for _ in range(count):
            product_code = str(uuid.uuid4())[:12]
            name = _generate_name(template_key)
            description = _generate_description()
            base_price = random.randint(5000, 150000)
            category_id = random.choice(CATEGORY_LEAF_POOLS[template_key])

            products.append((
                product_code, name, description, base_price,
                "ACTIVE", category_id, None, None, now, now,
                template_key,  # 임시 — 옵션그룹 생성에 사용
            ))

            # SKU 생성
            if not template:
                sid = str(uuid.uuid4())
                skus.append((sid, product_code, base_price, json.dumps({})))
                inventories.append((sid, random.randint(0, 500), 0, now, now))
            else:
                keys = list(template.keys())
                values = list(template.values())
                for comb in itertools.product(*values):
                    sid = str(uuid.uuid4())
                    sku_price = base_price + random.randint(-3000, 3000)
                    opt_json = json.dumps(dict(zip(keys, comb)), ensure_ascii=False)
                    skus.append((sid, product_code, sku_price, opt_json))
                    inventories.append((sid, random.randint(0, 500), 0, now, now))

    # 옵션 그룹 & 옵션 생성 (product_code 기준)
    option_groups = []  # (product_code, name, ordering, created, updated)
    options = []        # (group_key, name, additional_price, ordering, created, updated)
    #   group_key = (product_code, group_name)

    for prod_tuple in products:
        product_code = prod_tuple[0]
        template_key = prod_tuple[10]
        template = OPTION_TEMPLATE[template_key]
        if not template:
            continue
        for ordering, (group_name, vals) in enumerate(sorted(template.items())):
            option_groups.append((product_code, group_name, ordering, now, now))
            for opt_order, val in enumerate(vals):
                options.append(((product_code, group_name), val, 0, opt_order, now, now))

    print(f"  Generated {len(products):,} products")
    print(f"  Generated {len(skus):,} SKUs")
    print(f"  Generated {len(option_groups):,} option groups")
    print(f"  Generated {len(options):,} options")
    print(f"  Generated {len(inventories):,} inventory rows")

    return products, skus, inventories, option_groups, options


# ---------------------------------------------------------------------------
# Phase 3: 배치 삽입
# ---------------------------------------------------------------------------

def _batch_execute(cur, sql, data, page_size=BATCH_SIZE):
    for i in range(0, len(data), page_size):
        psycopg2.extras.execute_values(cur, sql, data[i:i + page_size], page_size=page_size)


def insert_categories(conn):
    cur = conn.cursor()
    rows = [(cid, name) for cid, name in sorted(CATEGORIES.items())]
    psycopg2.extras.execute_values(
        cur,
        "INSERT INTO categories (id, name) VALUES %s ON CONFLICT (id) DO NOTHING",
        rows,
    )
    # 시퀀스를 최대 id 이후로 맞춤
    max_id = max(CATEGORIES.keys())
    cur.execute(f"SELECT setval('categories_id_seq', {max_id}, true)")
    conn.commit()
    cur.close()
    print(f"  Inserted {len(rows)} categories.")


def insert_products(conn, products):
    """products 삽입 후 product_code -> product_id 매핑 반환."""
    cur = conn.cursor()
    # template_key(index 10) 제외한 데이터
    data = [p[:10] for p in products]
    sql = """
        INSERT INTO products
            (product_code, name, description, price, status, category_id,
             thumbnail_image_url, brand, created_at, updated_at)
        VALUES %s
        RETURNING product_code, id
    """
    product_map = {}
    for i in range(0, len(data), BATCH_SIZE):
        batch = data[i:i + BATCH_SIZE]
        results = psycopg2.extras.execute_values(cur, sql, batch, page_size=BATCH_SIZE, fetch=True)
        for row in results:
            product_map[row[0]] = row[1]
        conn.commit()
        done = min(i + BATCH_SIZE, len(data))
        print(f"\r  Products: {done:,} / {len(data):,}", end="", flush=True)
    cur.close()
    print()
    return product_map


def insert_option_groups(conn, option_groups, product_map):
    """옵션 그룹 삽입 후 (product_code, group_name) -> group_id 매핑 반환."""
    cur = conn.cursor()
    # product_code -> product_id 변환
    data = [
        (product_map[g[0]], g[1], g[2], g[3], g[4])
        for g in option_groups
    ]
    sql = """
        INSERT INTO product_option_groups
            (product_id, name, ordering, created_at, updated_at)
        VALUES %s
        RETURNING id, product_id, name
    """
    # product_id -> product_code 역매핑
    id_to_code = {v: k for k, v in product_map.items()}

    group_map = {}
    for i in range(0, len(data), BATCH_SIZE):
        batch = data[i:i + BATCH_SIZE]
        results = psycopg2.extras.execute_values(cur, sql, batch, page_size=BATCH_SIZE, fetch=True)
        for row in results:
            gid, pid, gname = row
            pcode = id_to_code[pid]
            group_map[(pcode, gname)] = gid
        conn.commit()
        done = min(i + BATCH_SIZE, len(data))
        print(f"\r  Option groups: {done:,} / {len(data):,}", end="", flush=True)
    cur.close()
    print()
    return group_map


def insert_options(conn, options, group_map):
    cur = conn.cursor()
    data = [
        (group_map[o[0]], o[1], o[2], o[3], o[4], o[5])
        for o in options
    ]
    sql = """
        INSERT INTO product_options
            (option_group_id, name, additional_price, ordering, created_at, updated_at)
        VALUES %s
    """
    for i in range(0, len(data), BATCH_SIZE):
        batch = data[i:i + BATCH_SIZE]
        psycopg2.extras.execute_values(cur, sql, batch, page_size=BATCH_SIZE)
        conn.commit()
        done = min(i + BATCH_SIZE, len(data))
        print(f"\r  Options: {done:,} / {len(data):,}", end="", flush=True)
    cur.close()
    print()


def insert_skus(conn, skus, product_map):
    cur = conn.cursor()
    data = [
        (s[0], product_map[s[1]], s[2], s[3])
        for s in skus
    ]
    sql = """
        INSERT INTO product_skus
            (sku_id, product_id, price, option_values)
        VALUES %s
    """
    for i in range(0, len(data), BATCH_SIZE):
        batch = data[i:i + BATCH_SIZE]
        psycopg2.extras.execute_values(cur, sql, batch, page_size=BATCH_SIZE)
        conn.commit()
        done = min(i + BATCH_SIZE, len(data))
        print(f"\r  SKUs: {done:,} / {len(data):,}", end="", flush=True)
    cur.close()
    print()


def insert_inventory(inventories):
    conn = get_connection("inventory")
    cur = conn.cursor()
    sql = """
        INSERT INTO inventory
            (sku_id, total_stock, reserved_stock, created_at, updated_at)
        VALUES %s
    """
    for i in range(0, len(inventories), BATCH_SIZE):
        batch = inventories[i:i + BATCH_SIZE]
        psycopg2.extras.execute_values(cur, sql, batch, page_size=BATCH_SIZE)
        conn.commit()
        done = min(i + BATCH_SIZE, len(inventories))
        print(f"\r  Inventory: {done:,} / {len(inventories):,}", end="", flush=True)
    cur.close()
    conn.close()
    print()


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("PostgreSQL Dummy Data Generator")
    print("=" * 60)

    print("\n[1/7] Ensuring databases exist...")
    ensure_databases()

    print("\n[2/7] Creating catalog tables...")
    create_catalog_tables()

    print("\n[3/7] Creating inventory table...")
    create_inventory_table()

    print("\n[4/7] Generating all data in-memory...")
    products, skus, inventories, option_groups, options = generate_all_data()

    conn = get_connection("catalog")
    try:
        print("\n[5/7] Inserting categories...")
        insert_categories(conn)

        print("\n[6/7] Inserting products...")
        product_map = insert_products(conn, products)

        print("  Inserting option groups...")
        group_map = insert_option_groups(conn, option_groups, product_map)

        print("  Inserting options...")
        insert_options(conn, options, group_map)

        print("  Inserting SKUs...")
        insert_skus(conn, skus, product_map)
    finally:
        conn.close()

    print("\n[7/7] Inserting inventory...")
    insert_inventory(inventories)

    # Summary
    print("\n" + "=" * 60)
    print("DONE!")
    print(f"  Products:      {len(products):>10,}")
    print(f"  Option Groups: {len(option_groups):>10,}")
    print(f"  Options:       {len(options):>10,}")
    print(f"  SKUs:          {len(skus):>10,}")
    print(f"  Inventory:     {len(inventories):>10,}")
    print("=" * 60)


if __name__ == "__main__":
    main()
