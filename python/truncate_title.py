import pandas as pd

df = pd.read_csv('./dataset/catalog_products.csv')

df['name'] = df['name'].str.slice(0, 255)

df.to_csv('./dataset/catalog_products_sliced.csv', index=False)