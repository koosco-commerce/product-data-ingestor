.PHONY: insert-products insert-products-reset

insert-products:
	python3 python/insert_product_pg.py

insert-products-reset:
	python3 python/insert_product_pg.py --reset
