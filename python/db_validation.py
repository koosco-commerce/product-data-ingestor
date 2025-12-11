import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

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

if __name__ == "__main__":
    conn = get_connection(os.getenv("DB_NAME_CATALOG"))
    with conn.cursor() as cur:
        cur.execute("SELECT DATABASE()")
        print("Connected to:", cur.fetchone())
    conn.close()

    conn = get_connection(os.getenv("DB_NAME_INVENTORY"))
    with conn.cursor() as cur:
        cur.execute("SELECT DATABASE()")
        print("Connected to:", cur.fetchone())
    conn.close()