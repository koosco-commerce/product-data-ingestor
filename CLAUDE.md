# CLAUDE.md

## 프로젝트 개요

E-commerce 부하 테스트용 더미 상품 데이터(~103K 상품, ~483K SKU)를 생성하여
PostgreSQL(catalog, inventory DB)에 삽입하는 프로젝트.

## 프로젝트 구조

```
python/
  insert_product_pg.py   # PostgreSQL 더미 데이터 생성/삽입 (주요 실행 스크립트)
  insert_product.py      # MySQL 버전 (레거시)
  data_sampling.ipynb    # Kaggle 원본 → 10만건 샘플링
  data_cleaning.ipynb    # description 정제
  generate_sku.ipynb     # Template 기반 SKU 생성
  generate_seed.ipynb    # 카테고리 시드 생성
  save_data.ipynb        # CSV 파일 생성
Makefile                 # 실행 편의 명령어
```

## 실행 방법

```bash
# 의존성
pip install psycopg2-binary python-dotenv

# 일반 실행 (테이블이 비어있어야 함)
make insert-products

# 멱등 실행 (TRUNCATE 후 재삽입, 반복 실행 가능)
make insert-products-reset
```

## 환경 변수

`.env` 파일 또는 환경 변수로 설정:

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `PG_HOST` | `localhost` | PostgreSQL 호스트 |
| `PG_PORT` | `5432` | PostgreSQL 포트 |
| `PG_USER` | `admin` | DB 사용자 |
| `PG_PASS` | `admin` | DB 비밀번호 |

## 데이터베이스

- **catalog**: categories, products, product_option_groups, product_options, product_skus
- **inventory**: inventory

DB와 테이블은 `insert_product_pg.py` 실행 시 자동 생성됨 (CREATE DATABASE / CREATE TABLE IF NOT EXISTS).

## 커밋 컨벤션

Conventional Commits 스타일 사용: `feat:`, `fix:`, `docs:`, `chore:` 등.

## 주의사항

- `--reset` 옵션은 TRUNCATE ... RESTART IDENTITY CASCADE 를 사용하므로 모든 데이터가 삭제됨
- 데이터 생성에 `random`을 사용하므로 시드 고정 없이는 매 실행마다 내용이 달라짐 (건수는 동일)
- CSV 기반 MySQL 삽입(`insert_product.py`)은 레거시이며, PostgreSQL 버전(`insert_product_pg.py`)이 현행
