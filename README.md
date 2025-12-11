# Product Data Ingestor

## 프로젝트 개요

E-commerce 시스템의 부하 테스트를 위한 상품 데이터 생성 프로젝트입니다.
[Amazon Product Data](https://www.kaggle.com/datasets/piyushjain16/amazon-product-data) 기반으로 10만 건의 더미 데이터를 생성하여 Category Service 및 Inventory Service의 성능 테스트에 활용합니다.

## 주요 기능

- Kaggle 오픈 데이터를 활용한 실제적인 상품 데이터 생성
- 상품, SKU, 옵션 그룹, 옵션을 포함한 완전한 카탈로그 데이터 구조
- Template 기반 다양한 상품 유형별 SKU 조합 생성

## 데이터 생성 프로세스

### 1. 데이터 샘플링 (`data_sampling.ipynb`)

**목적**: 부하 테스트용 적정 규모 데이터 확보

- 원본 1,000만 건 → 10만 건 샘플링: 전체 데이터 사용 시 처리 시간 과다, 부하 테스트에는 10만 건으로 충분
- Null 값 제거 후 샘플링: 데이터 클리닝 작업 최소화, 유효한 데이터만 선별

### 2. 데이터 정제 (`data_cleaning.ipynb`)

**목적**: 실제 상품 설명에 가까운 텍스트 데이터 구성

- DESCRIPTION + BULLET_POINTS 병합 → `description` 생성: 상세 설명과 특징을 결합하여 풍부한 텍스트 데이터 생성
- 상품 설명 길이 제한 (30~2,000자): 실무 환경의 현실적인 텍스트 길이 반영

### 3. 데이터 생성 (`generate_sku.ipynb`)

**목적**: 실제 E-commerce 상품 구조를 반영한 카탈로그 데이터 생성

**상품 정보 매핑**

- Kaggle 데이터를 실제 상품 테이블 구조에 맞게 변환
- `base_price`: 한국 시장 가격대를 반영하여 5,000원~150,000원 랜덤 생성

**Template 기반 SKU 생성 전략**

- 상품 유형별로 다른 옵션 조합 패턴 구현
  - 의류/신발 → 사이즈/색상 조합 필요 (복수 SKU)
  - 도서/기본 상품 → 옵션 불필요 (단일 SKU)

**Template 분류 (10가지 유형)**

```
DEFAULT         60,526건  (단일 SKU)
FASHION_TOP     11,175건  (사이즈 × 색상)
HOME_DECOR       8,918건  (사이즈 × 색상)
KITCHEN          7,610건  (용량 × 색상)
ACCESSORY        4,471건  (사이즈 × 색상)
SHOES            3,888건  (사이즈 × 색상)
ELECTRONICS      2,170건  (색상)
BEAUTY           2,163건  (용량)
FASHION_BOTTOM   1,788건  (사이즈 × 색상)
BOOK               797건  (단일 SKU)
```

**SKU 생성 로직**

- `product_type_id` 기반 Template 매핑
- 매핑 실패 시 `TITLE` 키워드로 분류
- 최종 미분류 → `DEFAULT` 처리
- 자동 분류 시스템으로 수작업 최소화

### 4. 시드 생성 (`generate_seed.ipynb`)

**목적**: 기존 상품 카테고리와 매핑을 위한 시드 생성

### 5. 데이터 저장 (`save_data.ipynb`)

**목적**: 실제 DB 테이블 구조에 맞는 CSV 파일 생성

최종 4개 CSV 파일 생성:

- `catalog_products.csv` - 상품 기본 정보
- `catalog_product_skus.csv` - SKU 및 가격 정보
- `catalog_option_groups.csv` - 옵션 그룹 (색상, 사이즈 등)
- `catalog_options.csv` - 개별 옵션 값
- DB 마이그레이션 스크립트로 바로 적재 가능한 형식

## 환경 설정

```bash
# 가상환경 생성 및 활성화
cd python
virtualenv venv
source venv/bin/activate

# 의존성 설치
pip install kaggle jupyter jupyterlab tabulate

# Kaggle API 설정
# https://www.kaggle.com/docs/api#authentication 참고
```

## 데이터베이스 스키마

### products

```
+---------------------+--------------+------+-----+---------+----------------+
| Field               | Type         | Null | Key | Default | Extra          |
+---------------------+--------------+------+-----+---------+----------------+
| id                  | bigint(20)   | NO   | PRI | NULL    | auto_increment |
| product_code        | varchar(50)  | NO   | UNI | NULL    |                |
| name                | varchar(255) | NO   |     | NULL    |                |
| description         | text         | YES  |     | NULL    |                |
| price               | bigint(20)   | NO   |     | NULL    |                |
| status              | varchar(20)  | NO   |     | NULL    |                |
| category_id         | bigint(20)   | YES  | MUL | NULL    |                |
| thumbnail_image_url | varchar(500) | YES  |     | NULL    |                |
| brand               | varchar(100) | YES  |     | NULL    |                |
| created_at          | datetime     | NO   |     | NULL    |                |
| updated_at          | datetime     | NO   |     | NULL    |                |
+---------------------+--------------+------+-----+---------+----------------+
```

### product_option_groups

```
+------------+--------------+------+-----+---------+----------------+
| Field      | Type         | Null | Key | Default | Extra          |
+------------+--------------+------+-----+---------+----------------+
| id         | bigint(20)   | NO   | PRI | NULL    | auto_increment |
| product_id | bigint(20)   | NO   | MUL | NULL    |                |
| name       | varchar(100) | NO   |     | NULL    |                |
| ordering   | int(11)      | NO   |     | 0       |                |
| created_at | datetime     | NO   |     | NULL    |                |
| updated_at | datetime     | NO   |     | NULL    |                |
+------------+--------------+------+-----+---------+----------------+
```

### product_options

```
+------------------+--------------+------+-----+---------+----------------+
| Field            | Type         | Null | Key | Default | Extra          |
+------------------+--------------+------+-----+---------+----------------+
| id               | bigint(20)   | NO   | PRI | NULL    | auto_increment |
| option_group_id  | bigint(20)   | NO   | MUL | NULL    |                |
| name             | varchar(100) | NO   |     | NULL    |                |
| additional_price | bigint(20)   | NO   |     | 0       |                |
| ordering         | int(11)      | NO   |     | 0       |                |
| created_at       | datetime     | NO   |     | NULL    |                |
| updated_at       | datetime     | NO   |     | NULL    |                |
+------------------+--------------+------+-----+---------+----------------+
```

### product_skus

```
+---------------+--------------+------+-----+---------------------+----------------+
| Field         | Type         | Null | Key | Default             | Extra          |
+---------------+--------------+------+-----+---------------------+----------------+
| id            | bigint(20)   | NO   | PRI | NULL                | auto_increment |
| sku_id        | varchar(100) | NO   | UNI | NULL                |                |
| product_id    | bigint(20)   | NO   | MUL | NULL                |                |
| price         | bigint(20)   | NO   |     | NULL                |                |
| option_values | longtext     | YES  |     | NULL                |                |
| created_at    | datetime     | NO   |     | current_timestamp() |                |
+---------------+--------------+------+-----+---------------------+----------------+
```

### inventory

```
+----------------+-------------+------+-----+---------+-------+
| Field          | Type        | Null | Key | Default | Extra |
+----------------+-------------+------+-----+---------+-------+
| reserved_stock | int(11)     | NO   |     | NULL    |       |
| total_stock    | int(11)     | NO   |     | NULL    |       |
| created_at     | datetime(6) | NO   |     | NULL    |       |
| updated_at     | datetime(6) | NO   |     | NULL    |       |
| sku_id         | varchar(50) | NO   | PRI | NULL    |       |
+----------------+-------------+------+-----+---------+-------+
```

## 결과물

생성된 CSV 파일은 다음 서비스에서 활용됩니다:

- **Category Service**: 상품 카탈로그 관리
- **Inventory Service**: 재고 관리 및 성능 테스트

> **참고**: 부하 테스트 목적으로 생성된 더미 데이터로, 실제 상품-옵션 매핑 관계는 의미가 없습니다.
