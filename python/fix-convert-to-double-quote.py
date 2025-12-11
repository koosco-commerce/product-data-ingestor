import pandas as pd
import ast
import json

df = pd.read_csv("./dataset/catalog_product_skus.csv")

def fix_options(o):
    try:
        obj = ast.literal_eval(o)   # Python dict string → dict 변환
        return json.dumps(obj, ensure_ascii=False)  # dict → JSON 문자열
    except:
        return json.dumps({})  # 혹시 이상한 값 있으면 null 대신 빈 객체

df["options"] = df["options"].apply(fix_options)

df.to_csv("./dataset/sku_fixed.csv", index=False)