"""
随机数据生成脚本
===============
为电商BI系统生成更大量的模拟数据，扩充种子数据量。
零外部依赖，仅用 Python 标准库。

功能:
    1. 生成更多客户 (从20扩充至100)
    2. 生成更多销售记录 (从163扩充至≥1000条，覆盖2025-01-01 ~ 2026-06-08)
    3. 生成用户画像记录 (为全部100位客户)
    4. 保留现有品类/商品维表不动

输出:
    - 默认生成 SQL 文件: scripts/output/seed_data.sql
    - 可选直接写入 MySQL: --insert-db

用法:
    python scripts/generate_mock_data.py
    python scripts/generate_mock_data.py --records 2000
    python scripts/generate_mock_data.py --insert-db

作者: 苏文韬
日期: 2026-06-09
"""

import os
import sys
import random
import argparse
from datetime import datetime, timedelta, date
from typing import List, Dict

# ═══════════════════════════════════════════════════════════════
# 配置常量（修改此处即可调整生成行为）
# ═══════════════════════════════════════════════════════════════

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
SQL_FILENAME = "seed_data.sql"

# 引用数据（与 init.sql 种子数据保持一致，不动）
PRODUCTS = [
    # (product_id, product_name, sku_code, category_id, price, cost, stock_quantity)
    (1,  "纯棉简约T恤女",        "WM-TEE-001",   11, 79.00,  35.00,  80),
    (2,  "法式碎花连衣裙",        "WM-DRS-002",   11, 259.00, 120.00, 120),
    (3,  "高腰阔腿牛仔裤女",      "WM-JNS-003",   11, 189.00, 85.00,  55),
    (4,  "商务免烫衬衫男",        "MN-SHT-001",   12, 199.00, 95.00,  90),
    (5,  "轻薄羽绒服男",          "MN-JKT-002",   12, 499.00, 280.00, 150),
    (6,  "复古跑步鞋",            "SH-RUN-001",   13, 329.00, 160.00, 200),
    (7,  "真皮商务皮鞋男",        "SH-BUS-002",   13, 459.00, 230.00, 45),
    (8,  "无线蓝牙耳机 Pro",      "PH-BUD-001",   21, 299.00, 150.00, 65),
    (9,  "快充数据线套装",        "PH-CBL-002",   21, 39.00,  12.00,  140),
    (10, "手机防窥钢化膜",        "PH-FLM-003",   21, 29.00,  8.00,   70),
    (11, "机械键盘青轴87键",      "PC-KBD-001",   22, 259.00, 130.00, 110),
    (12, "无线静音鼠标",          "PC-MOU-002",   22, 99.00,  45.00,  95),
    (13, "智能手环NFC版",         "WL-BND-001",   23, 199.00, 90.00,  60),
    (14, "每日坚果礼盒750g",      "FD-NUT-001",   31, 89.00,  50.00,  85),
    (15, "抹茶夹心饼干240g",      "FD-CKY-002",   31, 29.90,  14.00,  130),
    (16, "手撕牛肉干五香味200g",  "FD-JKY-003",   31, 59.90,  32.00,  35),
    (17, "冷萃咖啡液12颗装",      "FD-COF-001",   32, 69.00,  35.00,  160),
    (18, "冻干柠檬片罐装",        "FD-LEM-002",   32, 25.00,  10.00,  75),
    (19, "氨基酸洁面乳120g",      "BC-FAC-001",   41, 89.00,  38.00,  40),
    (20, "玻尿酸补水面膜5片装",   "BC-MSK-002",   41, 59.00,  22.00,  105),
    (21, "雾面哑光口红",          "BC-LIP-001",   42, 99.00,  40.00,  145),
    (22, "纯棉四件套1.8m床",      "HM-BED-001",   51, 399.00, 200.00, 125),
    (23, "不粘锅三件套",          "HM-COK-001",   52, 299.00, 150.00, 50),
    (24, "保温杯500ml不锈钢",     "HM-CUP-002",   52, 79.00,  32.00,  115),
]

# 各地区概率（大致反映中国电商消费分布）
REGION_NAMES = [
    "广东", "浙江", "江苏", "上海", "北京", "四川", "山东", "福建",
    "河南", "湖北", "湖南", "安徽", "辽宁", "重庆", "陕西", "江西",
    "广西", "河北", "天津", "山西",
]
REGION_WEIGHTS = [
    0.14, 0.10, 0.09, 0.07, 0.07, 0.06, 0.06, 0.05,
    0.05, 0.04, 0.04, 0.04, 0.03, 0.03, 0.03, 0.03,
    0.02, 0.02, 0.01, 0.01,
]

# 渠道分布
CHANNEL_NAMES = ["PC", "Mobile", "Miniprogram"]
CHANNEL_WEIGHTS = [0.35, 0.45, 0.20]

# 月度销量因子（反映季节性和大促，1.0 = 基准）
MONTHLY_FACTOR = {
     1: 1.15,   # 元旦+年货节
     2: 0.85,   # 春节（物流减少）
     3: 1.20,   # 春节后恢复+38节
     4: 1.00,   # 正常
     5: 1.05,   # 五一+520
     6: 1.60,   # 618大促
     7: 0.80,   # 618后回落
     8: 0.85,   # 暑期淡季
     9: 1.20,   # 开学季
    10: 1.15,   # 国庆
    11: 2.00,   # 双11
    12: 1.40,   # 双12+年末
}

# 客户姓氏库
SURNAMES = [
    "王","李","张","刘","陈","杨","黄","赵","吴","周",
    "徐","孙","马","朱","胡","郭","何","高","林","罗",
    "郑","梁","谢","宋","唐","许","韩","冯","邓","曹",
    "彭","曾","肖","田","董","潘","袁","蔡","蒋","余",
]

# 现有20位客户ID → 新客户从21开始
EXISTING_CUSTOMER_COUNT = 20

# 日期范围
DATE_START = date(2025, 1, 1)
DATE_END = date(2026, 6, 8)

# 商品权重：高频消费品权重高，高价低频商品权重低
PRODUCT_WEIGHTS = [
    1.5,  # 1  纯棉T恤 — 高频消费品
    1.0,  # 2  碎花连衣裙
    0.9,  # 3  牛仔裤
    1.2,  # 4  衬衫 — 高频
    0.7,  # 5  羽绒服 — 单价高，销量低
    1.1,  # 6  跑步鞋
    0.5,  # 7  皮鞋 — 高价低频
    1.3,  # 8  耳机 — 热门
    1.6,  # 9  数据线 — 低单价高频
    1.4,  # 10 钢化膜 — 高频
    0.9,  # 11 键盘
    1.2,  # 12 鼠标
    0.8,  # 13 手环
    1.5,  # 14 坚果 — 食品高频
    1.3,  # 15 饼干 — 高频零食
    0.7,  # 16 牛肉干
    1.0,  # 17 咖啡
    1.1,  # 18 柠檬片
    0.9,  # 19 洁面乳
    1.2,  # 20 面膜
    1.1,  # 21 口红
    0.5,  # 22 四件套 — 高价低频
    0.4,  # 23 锅具 — 超低频
    1.0,  # 24 保温杯
]

# 购买数量分布
QUANTITY_POOL = [1, 1, 1, 1, 1, 2, 2, 2, 3, 4, 5]
QUANTITY_WEIGHTS = [0.35, 0.20, 0.12, 0.08, 0.05, 0.08, 0.04, 0.03, 0.02, 0.02, 0.01]


# ═══════════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════════

def weighted_choice(population, weights, k=1):
    """带权重的随机抽样（纯 stdlib）。"""
    return random.choices(population, weights=weights, k=k)


def weighted_choice_one(population, weights):
    """抽一个。"""
    return random.choices(population, weights=weights, k=1)[0]


def normalize_weights(weights):
    """归一化权重列表，使其和为 1。"""
    total = sum(weights)
    return [w / total for w in weights]


# ═══════════════════════════════════════════════════════════════
# 生成器函数
# ═══════════════════════════════════════════════════════════════

def generate_customers(n: int, start_id: int = 21) -> List[Dict]:
    """
    生成 n 位新客户。
    每位客户有: customer_id, customer_name, gender, age_group, region, register_date
    """
    # 性别偏好: 女性略多于男性（电商特征）
    genders = weighted_choice(["F", "M"], [0.52, 0.48], k=n)

    # 年龄段分布（电商主力: 25-34）
    age_groups = weighted_choice(
        ["18-24", "25-34", "35-44", "45+"],
        [0.20, 0.38, 0.27, 0.15], k=n
    )

    # 地区
    regions = weighted_choice(REGION_NAMES, REGION_WEIGHTS, k=n)

    # 注册日期（在2024-06 ~ 2026-05之间均匀分布）
    reg_start = date(2024, 6, 1)
    reg_end = date(2026, 5, 31)
    reg_days = (reg_end - reg_start).days
    register_dates = [
        (reg_start + timedelta(days=random.randint(0, reg_days))).strftime("%Y-%m-%d")
        for _ in range(n)
    ]

    customers = []
    for i in range(n):
        cid = start_id + i
        surname = random.choice(SURNAMES)
        name = f"{surname}***"  # 脱敏格式
        customers.append({
            "customer_id": cid,
            "customer_name": name,
            "gender": genders[i],
            "age_group": age_groups[i],
            "region": regions[i],
            "register_date": register_dates[i],
        })
    return customers


def generate_sales_record(product_id, customer_id, order_date):
    """
    生成一条销售记录。
    价格在大促月份有折扣，平时在原价附近波动。
    """
    prod = PRODUCTS[product_id - 1]  # product_id 从1开始
    base_price = prod[4]  # price
    month = order_date.month
    day = order_date.day

    # 大促月份打折
    if month == 6 and day <= 18:
        price_mult = random.uniform(0.82, 0.95)  # 618促销
    elif month == 11:
        price_mult = random.uniform(0.75, 0.90)  # 双11
    elif month == 12 and day <= 12:
        price_mult = random.uniform(0.80, 0.92)  # 双12
    elif month == 9:
        price_mult = random.uniform(0.85, 1.0)   # 开学季
    else:
        price_mult = random.uniform(0.95, 1.05)

    unit_price = round(base_price * price_mult, 2)

    # 购买数量
    quantity = weighted_choice_one(QUANTITY_POOL, QUANTITY_WEIGHTS)

    total_amount = round(unit_price * quantity, 2)

    # 渠道
    channel = weighted_choice_one(CHANNEL_NAMES, CHANNEL_WEIGHTS)

    # 地区
    region = weighted_choice_one(REGION_NAMES, REGION_WEIGHTS)

    # 随机时间（9:00-22:00）
    hour = random.randint(9, 22)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    order_datetime = datetime(
        order_date.year, order_date.month, order_date.day,
        hour, minute, second
    )

    return {
        "product_id": product_id,
        "customer_id": customer_id,
        "quantity": quantity,
        "unit_price": unit_price,
        "total_amount": total_amount,
        "order_date": order_datetime.strftime("%Y-%m-%d %H:%M:%S"),
        "region": region,
        "channel": channel,
    }


def generate_sales_records(n_target: int, customers: List[Dict]) -> List[Dict]:
    """
    生成 n_target 条销售记录。
    遵循月度季节因子，工作日/周末有区分。
    """
    # 计算每天应生成几条记录（按月度因子加权）
    total_days = (DATE_END - DATE_START).days + 1
    daily_weights = []

    current = DATE_START
    for _ in range(total_days):
        m = current.month
        wd = current.weekday()  # 0=Mon, 6=Sun
        weekend_bonus = 1.15 if wd >= 5 else 1.0
        weight = MONTHLY_FACTOR.get(m, 1.0) * weekend_bonus
        daily_weights.append(weight)
        current += timedelta(days=1)

    # 归一化
    daily_weights = normalize_weights(daily_weights)

    # 抽 n_target 个日期索引
    day_indices = list(range(total_days))
    chosen_indices = weighted_choice(day_indices, daily_weights, k=n_target)
    selected_dates = [DATE_START + timedelta(days=i) for i in chosen_indices]

    # 商品/客户
    all_customer_ids = [c["customer_id"] for c in customers]
    product_ids = [p[0] for p in PRODUCTS]
    prod_weights_norm = normalize_weights(PRODUCT_WEIGHTS)

    records = []
    for order_date in selected_dates:
        prod_id = weighted_choice_one(product_ids, prod_weights_norm)
        cust_id = random.choice(all_customer_ids)
        rec = generate_sales_record(prod_id, cust_id, order_date)
        records.append(rec)

    # 按日期排序
    records.sort(key=lambda r: r["order_date"])
    return records


def generate_user_profiles(customers: List[Dict]) -> List[Dict]:
    """
    为所有客户生成用户画像（RFM模型简化版）。
    """
    n = len(customers)
    # 价值分层: 高15% / 中45% / 低40%
    value_levels = weighted_choice(
        ["高价值", "中价值", "低价值"],
        [0.15, 0.45, 0.40], k=n
    )

    # 偏好品类池
    cat_pool = ["女装", "男装", "鞋靴", "数码", "食品", "美妆", "家居", "厨具"]
    promo_options = ["高", "中", "低"]
    promo_weights = [0.30, 0.45, 0.25]

    profiles = []
    for i, cust in enumerate(customers):
        vl = value_levels[i]
        cid = cust["customer_id"]

        # 根据价值等级生成合理的指标
        if vl == "高价值":
            avg_price = round(random.uniform(200, 500), 2)
            freq = round(random.uniform(2.5, 5.0), 2)
        elif vl == "中价值":
            avg_price = round(random.uniform(100, 300), 2)
            freq = round(random.uniform(1.2, 3.0), 2)
        else:
            avg_price = round(random.uniform(40, 150), 2)
            freq = round(random.uniform(0.5, 1.5), 2)

        # 偏好品类（随机选1-3个）
        n_pref = random.randint(1, 3)
        pref_sample = random.sample(cat_pool, min(n_pref, len(cat_pool)))
        pref_cats = ",".join(pref_sample)

        # 促销敏感度
        promo = weighted_choice_one(promo_options, promo_weights)

        # 最近购买日期
        last_days_ago = random.randint(1, 180)
        last_purchase = (DATE_END - timedelta(days=last_days_ago)).strftime("%Y-%m-%d")

        profiles.append({
            "customer_id": cid,
            "value_level": vl,
            "avg_order_price": avg_price,
            "purchase_frequency": freq,
            "preferred_category": pref_cats,
            "promo_sensitivity": promo,
            "last_purchase_date": last_purchase,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
    return profiles


# ═══════════════════════════════════════════════════════════════
# 输出
# ═══════════════════════════════════════════════════════════════

def escape_sql(val) -> str:
    """将 Python 值转为 SQL 字面量"""
    if val is None:
        return "NULL"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, str):
        escaped = val.replace("\\", "\\\\").replace("'", "\\'")
        return f"'{escaped}'"
    return str(val)


def to_sql_insert(table: str, columns: List[str], rows: List[List]) -> str:
    """生成 INSERT INTO ... VALUES ... 语句块。"""
    col_str = ", ".join(columns)
    lines = [f"INSERT INTO {table} ({col_str}) VALUES"]
    for i, row in enumerate(rows):
        vals = ", ".join(escape_sql(v) for v in row)
        comma = "," if i < len(rows) - 1 else ";"
        lines.append(f"    ({vals}){comma}")
    return "\n".join(lines) + "\n"


def write_sql(new_customers, sales, profiles, output_path: str):
    """将所有生成数据写为 SQL 文件"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("-- ============================================================\n")
        f.write("-- 随机数据生成脚本 输出的补充种子数据\n")
        f.write(f"-- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"-- 新客户: {len(new_customers)} 位\n")
        f.write(f"-- 销售记录: {len(sales)} 条\n")
        f.write(f"-- 用户画像: {len(profiles)} 位\n")
        f.write("--\n")
        f.write("-- 用法: 在 MySQL 中 source 此文件，或追加到 init.sql 种子数据后\n")
        f.write("--       注意: 需在已执行 init.sql 的基础上运行\n")
        f.write("-- ============================================================\n\n")

        # ── 新客户 ──
        f.write("-- 补充客户（第21-100位）\n")
        cust_cols = ["customer_id", "customer_name", "gender",
                     "age_group", "region", "register_date"]
        cust_rows = [
            [c["customer_id"], c["customer_name"], c["gender"],
             c["age_group"], c["region"], c["register_date"]]
            for c in new_customers
        ]
        f.write(to_sql_insert("customer", cust_cols, cust_rows))
        f.write("\n")

        # ── 销售记录 ──
        f.write("-- 补充销售记录\n")
        sales_cols = ["product_id", "customer_id", "quantity", "unit_price",
                      "total_amount", "order_date", "region", "channel"]
        sales_rows = [
            [s["product_id"], s["customer_id"], s["quantity"],
             s["unit_price"], s["total_amount"], s["order_date"],
             s["region"], s["channel"]]
            for s in sales
        ]
        f.write(to_sql_insert("sales_record", sales_cols, sales_rows))
        f.write("\n")

        # ── 用户画像 ──
        f.write("-- 补充用户画像\n")
        prof_cols = ["customer_id", "value_level", "avg_order_price",
                     "purchase_frequency", "preferred_category",
                     "promo_sensitivity", "last_purchase_date", "updated_at"]
        prof_rows = [
            [p["customer_id"], p["value_level"], p["avg_order_price"],
             p["purchase_frequency"], p["preferred_category"],
             p["promo_sensitivity"], p["last_purchase_date"], p["updated_at"]]
            for p in profiles
        ]
        f.write(to_sql_insert("user_profile", prof_cols, prof_rows))
        f.write("\n")

        f.write("-- EOF\n")

    print(f"\n✅ SQL 文件已生成: {output_path}")
    print(f"   新客户: {len(new_customers)} 位")
    print(f"   销售记录: {len(sales)} 条")
    print(f"   用户画像: {len(profiles)} 位")


def insert_to_db(new_customers, sales, profiles):
    """直接写入 MySQL 数据库"""
    try:
        import pymysql
    except ImportError:
        print("❌ 需要 pymysql 库: pip install pymysql")
        sys.exit(1)

    # 添加 backend 到 sys.path 以导入 config
    backend_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "backend"
    )
    sys.path.insert(0, backend_dir)
    from config import get_config
    cfg = get_config()

    conn = pymysql.connect(
        host=cfg.MYSQL_HOST, port=cfg.MYSQL_PORT,
        user=cfg.MYSQL_USER, password=cfg.MYSQL_PASSWORD,
        database=cfg.MYSQL_DATABASE, charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )

    try:
        with conn.cursor() as cur:
            # 插入客户（跳过已存在的）
            for c in new_customers:
                cur.execute(
                    "INSERT IGNORE INTO customer (customer_id, customer_name, "
                    "gender, age_group, region, register_date) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (c["customer_id"], c["customer_name"], c["gender"],
                     c["age_group"], c["region"], c["register_date"])
                )
            conn.commit()
            print(f"✅ 客户: {len(new_customers)} 位已写入")

            # 插入销售记录
            batch_size = 200
            for i in range(0, len(sales), batch_size):
                batch = sales[i:i + batch_size]
                for s in batch:
                    cur.execute(
                        "INSERT INTO sales_record (product_id, customer_id, "
                        "quantity, unit_price, total_amount, order_date, "
                        "region, channel) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                        (s["product_id"], s["customer_id"], s["quantity"],
                         s["unit_price"], s["total_amount"], s["order_date"],
                         s["region"], s["channel"])
                    )
                conn.commit()
                print(f"  销售记录: {min(i + batch_size, len(sales))}/{len(sales)} 条")
            print(f"✅ 销售记录: {len(sales)} 条已写入")

            # 插入用户画像
            for p in profiles:
                cur.execute(
                    "INSERT INTO user_profile (customer_id, value_level, "
                    "avg_order_price, purchase_frequency, preferred_category, "
                    "promo_sensitivity, last_purchase_date, updated_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
                    "ON DUPLICATE KEY UPDATE "
                    "value_level=VALUES(value_level), "
                    "avg_order_price=VALUES(avg_order_price), "
                    "purchase_frequency=VALUES(purchase_frequency), "
                    "last_purchase_date=VALUES(last_purchase_date), "
                    "updated_at=VALUES(updated_at)",
                    (p["customer_id"], p["value_level"], p["avg_order_price"],
                     p["purchase_frequency"], p["preferred_category"],
                     p["promo_sensitivity"], p["last_purchase_date"],
                     p["updated_at"])
                )
            conn.commit()
            print(f"✅ 用户画像: {len(profiles)} 位已写入")

            # 验证
            cur.execute("SELECT COUNT(*) AS cnt FROM customer")
            cust_cnt = cur.fetchone()["cnt"]
            cur.execute("SELECT COUNT(*) AS cnt FROM sales_record")
            sales_cnt = cur.fetchone()["cnt"]
            cur.execute("SELECT COUNT(*) AS cnt FROM user_profile")
            prof_cnt = cur.fetchone()["cnt"]
            print(f"\n📊 数据库当前: customer={cust_cnt}  "
                  f"sales_record={sales_cnt}  user_profile={prof_cnt}")

    except Exception as e:
        conn.rollback()
        print(f"❌ 数据库写入失败: {e}")
        raise
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="电商BI系统 — 随机数据生成脚本（零依赖，纯标准库）"
    )
    parser.add_argument(
        "--records", type=int, default=1200,
        help="生成销售记录条数 (默认: 1200)"
    )
    parser.add_argument(
        "--customers", type=int, default=80,
        help="新生成客户数 (默认: 80, 总计100)"
    )
    parser.add_argument(
        "--insert-db", action="store_true",
        help="直接写入 MySQL 而非生成 SQL 文件"
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="自定义 SQL 输出路径"
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="随机种子 (默认: 42, 可复现)"
    )
    args = parser.parse_args()

    # 设置随机种子
    random.seed(args.seed)

    print("=" * 60)
    print("  电商BI系统 — 随机数据生成")
    print(f"  目标: {args.records} 条销售记录 + {args.customers} 位新客户")
    print(f"  随机种子: {args.seed}")
    print("=" * 60)

    # 1. 生成客户
    new_customers = generate_customers(
        n=args.customers,
        start_id=EXISTING_CUSTOMER_COUNT + 1,
    )
    # 合并所有客户（含现有20位的占位信息，用于销售记录关联）
    all_customers = [
        {"customer_id": i, "customer_name": f"seed{i}", "gender": "U",
         "age_group": "25-34", "region": "广东", "register_date": "2025-01-01"}
        for i in range(1, EXISTING_CUSTOMER_COUNT + 1)
    ] + new_customers

    print(f"\n👥 客户总数: {len(all_customers)} (新生成 {len(new_customers)} 位)")

    # 2. 生成销售记录
    sales = generate_sales_records(
        n_target=args.records,
        customers=all_customers,
    )
    print(f"💰 销售记录: {len(sales)} 条")
    print(f"   日期范围: {sales[0]['order_date']} ~ {sales[-1]['order_date']}")

    # 3. 生成用户画像
    profiles = generate_user_profiles(all_customers)
    print(f"🏷️  用户画像: {len(profiles)} 位")

    # 4. 输出统计
    total_amount = sum(s["total_amount"] for s in sales)
    month_counts = {}
    for s in sales:
        m = s["order_date"][:7]
        month_counts[m] = month_counts.get(m, 0) + 1
    print(f"\n📈 数据统计:")
    print(f"   总销售额: ¥{total_amount:,.2f}")
    print(f"   月均记录: {len(sales) // max(len(month_counts), 1)} 条")
    print(f"   覆盖月份: {len(month_counts)} 个月")
    print(f"   月度分布:")
    for m in sorted(month_counts.keys()):
        bar = "█" * (month_counts[m] // 5)
        print(f"     {m}: {month_counts[m]:4d} {bar}")

    # 5. 输出
    if args.insert_db:
        insert_to_db(new_customers, sales, profiles)
    else:
        output_path = args.output or os.path.join(OUTPUT_DIR, SQL_FILENAME)
        write_sql(new_customers, sales, profiles, output_path)
        print(f"\n💡 导入 MySQL:")
        print(f"   mysql -u root -p ecommerce_bi < {output_path}")
        print(f"   或: python scripts/generate_mock_data.py --insert-db")


if __name__ == "__main__":
    main()
