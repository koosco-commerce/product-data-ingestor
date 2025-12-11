import csv
import pymysql
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

DB_NAME_CATALOG = os.getenv("DB_NAME_CATALOG")
DB_NAME_INVENTORY = os.getenv("DB_NAME_INVENTORY")

def get_connection(db_name):
    return pymysql.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        db=db_name,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )


# ----------------------------
# 1) Insert products
# ----------------------------
def insert_products():
    conn = get_connection(DB_NAME_CATALOG)
    cursor = conn.cursor()

    print("Inserting products...")

    with open("./dataset/catalog_products_sliced.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cursor.execute("""
                INSERT INTO products 
                    (product_code, name, description, price, status, category_id,
                     thumbnail_image_url, brand, created_at, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                row["product_code"], row["name"], row["description"],
                int(row["price"]), row["status"], int(row["category_id"]) if row["category_id"] else None,
                row["thumbnail_image_url"], row["brand"],
                row["created_at"], row["updated_at"]
            ))

    conn.commit()
    cursor.close()
    conn.close()
    print("Products inserted.\n")


# ----------------------------
# 2) Load product_id ↔ product_code mapping
# ----------------------------
def load_product_map():
    conn = get_connection(DB_NAME_CATALOG)
    cursor = conn.cursor()

    cursor.execute("SELECT id AS product_id, product_code FROM products")
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    df = pd.DataFrame(rows)
    df.to_csv("./dataset/product_map.csv", index=False)

    print("Generated product_map.csv with", len(df), "rows\n")
    return df


# ----------------------------
# 3) Create & insert option groups
# ----------------------------
def insert_option_groups(product_map):
    og = pd.read_csv("./dataset/catalog_option_groups.csv")
    merged = og.merge(product_map, on="product_code")

    final_groups = merged[[
        "product_id", "name", "ordering", "created_at", "updated_at"
    ]]

    final_groups.to_csv("./dataset/catalog_option_groups_final.csv", index=False)

    print("Prepared option_groups_final.csv")

    # Insert into DB
    conn = get_connection(DB_NAME_CATALOG)
    cursor = conn.cursor()

    print("Inserting product_option_groups...")

    for _, row in final_groups.iterrows():
        cursor.execute("""
            INSERT INTO product_option_groups (product_id, name, ordering, created_at, updated_at)
            VALUES (%s,%s,%s,%s,%s)
        """, (
            int(row["product_id"]), row["name"], int(row["ordering"]),
            row["created_at"], row["updated_at"]
        ))

    conn.commit()
    cursor.close()
    conn.close()
    print("Option groups inserted.\n")


def load_option_group_map():
    conn = get_connection(DB_NAME_CATALOG)
    cursor = conn.cursor()

    cursor.execute("SELECT id AS option_group_id, product_id, name FROM product_option_groups")
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    df = pd.DataFrame(rows)
    df.to_csv("./dataset/option_group_map.csv", index=False)

    print("Generated option_group_map.csv with", len(df), "rows\n")
    return df


# ----------------------------
# 4) Insert options (NO MERGE)
# ----------------------------
def insert_options():
    options = pd.read_csv("./dataset/catalog_options.csv")

    conn = get_connection(DB_NAME_CATALOG)
    cursor = conn.cursor()

    print("Inserting product_options...")

    for _, row in options.iterrows():
        cursor.execute("""
            INSERT INTO product_options
                (option_group_id, name, additional_price, ordering, created_at, updated_at)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (
            int(row["option_group_id"]),
            row["name"],
            int(row["additional_price"]),
            int(row["ordering"]),
            row["created_at"],
            row["updated_at"]
        ))

    conn.commit()
    cursor.close()
    conn.close()
    print("Options inserted.\n")


# ----------------------------
# 5) Create & insert SKUs
# ----------------------------
def insert_skus(product_map):
    skus = pd.read_csv("./dataset/sku_fixed.csv")
    merged = skus.merge(product_map, on="product_code")

    final_skus = merged[[
        "sku_id", "product_id", "price", "options", "created_at"
    ]]

    final_skus.to_csv("./dataset/catalog_product_skus_final.csv", index=False)
    print("Prepared catalog_product_skus_final.csv")

    conn = get_connection(DB_NAME_CATALOG)
    cursor = conn.cursor()

    print("Inserting product_skus...")

    for _, row in final_skus.iterrows():
        cursor.execute("""
            INSERT INTO product_skus (sku_id, product_id, price, option_values, created_at)
            VALUES (%s,%s,%s,%s,%s)
        """, (
            row["sku_id"], int(row["product_id"]), int(row["price"]),
            row["options"], row["created_at"]
        ))

    conn.commit()
    cursor.close()
    conn.close()
    print("SKUs inserted.\n")


# ----------------------------
# 6) Insert inventory
# ----------------------------
def insert_inventory():
    conn = get_connection(DB_NAME_INVENTORY)
    cursor = conn.cursor()

    print("Inserting inventory...")

    with open("./dataset/inventory.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cursor.execute("""
                INSERT INTO inventory (sku_id, total_stock, reserved_stock, created_at, updated_at)
                VALUES (%s,%s,%s,%s,%s)
            """, (
                row["sku_id"], int(row["total_stock"]), int(row["reserved_stock"]),
                row["created_at"], row["updated_at"]
            ))

    conn.commit()
    cursor.close()
    conn.close()
    print("Inventory inserted.\n")



if __name__ == "__main__":
    insert_products()
    product_map = load_product_map()

    insert_option_groups(product_map)
    option_group_map = load_option_group_map()

    insert_options()
    insert_skus(product_map)

    insert_inventory()

    print("\n🎉 DONE! All catalog & inventory data inserted successfully.")