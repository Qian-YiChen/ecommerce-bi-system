# =============================================================================
# ml/ml_pipeline.py — 电商BI系统 · 机器学习管道 
# 作者：薛淞  日期：2026-06-10 基于init.sql和seed_data.sql 还未测试
# 说明：
#   1. 销售预测（P0） → 线性回归，特征含 category_id
#   2. 异常检测（P0） → 规则引擎，基于销售额7日均线
#   3. 库存补货（P0） → 安全库存公式，库存从 product.stock_quantity 读取
#   4. 用户画像（P1） → RFM + 偏好品类 + 促销敏感度，写入 user_profile
#   5. 营销评估（P1） → 已结束活动的增量/ROI 分析，输出报告
#   依赖：pymysql, pandas, numpy, scikit-learn, joblib
#   执行：python ml_pipeline.py
# =============================================================================

import os
import joblib
import numpy as np
import pandas as pd
import pymysql
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# ── 配置（可外置 config.py）─────────────────────────────────────────
try:
    from config import DB_CONFIG, FORECAST_HORIZON, MODEL_DIR
except ImportError:
    DB_CONFIG = {
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': '123456',       # 请改为你的真实密码
        'database': 'ecommerce_bi',
        'charset': 'utf8mb4'
    }
    FORECAST_HORIZON = 7
    MODEL_DIR = 'models'

# 特征列：时间 + 滞后 + 品类
FEATURE_COLS = [
    'dayofweek', 'month', 'day', 'is_weekend',
    'lag_1', 'rolling_mean_7',
    'category_id',
]

# 大促日期范围（用于用户画像的促销敏感度计算）
PROMO_PERIODS = [
    ('2025-06-01','2025-06-20'), ('2025-11-01','2025-11-12'),
    ('2025-12-01','2025-12-12'), ('2026-01-10','2026-02-05'),
    ('2026-05-20','2026-05-20')
]

# =============================================================================
# 数据库工具
# =============================================================================
def get_conn():
    """获取数据库连接"""
    return pymysql.connect(**DB_CONFIG)

# =============================================================================
# 数据加载
# =============================================================================
def load_sales_aggregated():
    """按日聚合销量，并 JOIN product 获取 category_id"""
    sql = """
        SELECT DATE(sr.order_date) AS order_date,
               sr.product_id,
               p.category_id,
               SUM(sr.quantity) AS total_qty,
               SUM(sr.total_amount) AS total_amount
        FROM sales_record sr
        JOIN product p ON sr.product_id = p.product_id
        GROUP BY DATE(sr.order_date), sr.product_id, p.category_id
        ORDER BY sr.product_id, order_date
    """
    conn = get_conn()
    df = pd.read_sql(sql, conn, parse_dates=['order_date'])
    conn.close()
    return df

def load_product_info():
    """加载商品信息（含 stock_quantity）"""
    conn = get_conn()
    df = pd.read_sql(
        "SELECT product_id, product_name, category_id, price, stock_quantity FROM product",
        conn
    )
    conn.close()
    return df

def load_inventory():
    """从 product 表读取真实库存，返回 {product_id: stock_quantity}"""
    conn = get_conn()
    df = pd.read_sql("SELECT product_id, stock_quantity FROM product WHERE status = 1", conn)
    conn.close()
    return dict(zip(df['product_id'], df['stock_quantity']))

def load_alert_rules():
    """加载启用的预警规则"""
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM alert_rule WHERE is_enabled = 1", conn)
    conn.close()
    return df

# =============================================================================
# 特征工程
# =============================================================================
def create_features(df):
    """构造时间特征与滞后销量特征"""
    df = df.sort_values(['product_id', 'order_date']).reset_index(drop=True)

    df['dayofweek'] = df['order_date'].dt.dayofweek
    df['month'] = df['order_date'].dt.month
    df['day'] = df['order_date'].dt.day
    df['is_weekend'] = df['dayofweek'].isin([5, 6]).astype(int)

    df['lag_1'] = df.groupby('product_id')['total_qty'].shift(1)
    df['rolling_mean_7'] = (
        df.groupby('product_id')['total_qty']
          .shift(1)
          .rolling(window=7, min_periods=1)
          .mean()
          .reset_index(level=0, drop=True)
    )

    # 缺失值用中位数填充
    fill_vals = {
        'lag_1': df['total_qty'].median(),
        'rolling_mean_7': df['total_qty'].median()
    }
    df.fillna(fill_vals, inplace=True)
    return df

# =============================================================================
# 模型训练
# =============================================================================
def train_model(df):
    """训练线性回归基线模型，返回 (model, mape)"""
    from sklearn.linear_model import LinearRegression
    from sklearn.metrics import mean_absolute_error, mean_squared_error

    X = df[FEATURE_COLS]
    y = df['total_qty']

    # 按时间切分：前80%训练，后20%测试
    split = int(len(df) * 0.8)
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]

    model = LinearRegression()
    model.fit(X_train, y_train)
    preds = model.predict(X_test)

    mae = mean_absolute_error(y_test, preds)
    rmse = np.sqrt(mean_squared_error(y_test, preds))
    mape = np.mean(np.abs((y_test - preds) / y_test.replace(0, np.nan))) * 100

    print(f"[模型训练] MAE={mae:.2f}, RMSE={rmse:.2f}, MAPE={mape:.2f}%")

    os.makedirs(MODEL_DIR, exist_ok=True)
    path = os.path.join(MODEL_DIR, 'sales_lr_baseline.pkl')
    joblib.dump(model, path)
    print(f"[模型训练] 模型已保存至 {path}")
    return model, mape

def load_model(model_name: str = 'sales_lr_baseline.pkl'):
    """加载已保存的模型（自动解析相对于 ml_pipeline.py 的路径）"""
    # 确保无论从哪里调用（Flask backend/ 或 ml/ 目录），都能找到模型
    _ml_dir = os.path.dirname(os.path.abspath(__file__))
    _model_dir = os.path.join(_ml_dir, MODEL_DIR)
    path = os.path.join(_model_dir, model_name)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"模型文件不存在: {path}。请先运行 python ml/ml_pipeline.py 训练模型。"
        )
    return joblib.load(path)

# =============================================================================
# 销售预测
# =============================================================================
def predict_future(model, latest_features_dict):
    """递归预测未来 FORECAST_HORIZON 天，返回预测列表"""
    predictions = []
    for pid, last_row in latest_features_dict.items():
        cur = pd.DataFrame([last_row], columns=FEATURE_COLS)
        start_date = last_row['order_date'] + timedelta(days=1)

        for i in range(FORECAST_HORIZON):
            pred = max(0, model.predict(cur)[0])
            forecast_date = start_date + timedelta(days=i)
            predictions.append({
                'product_id': pid,
                'forecast_date': forecast_date.strftime('%Y-%m-%d'),
                'predicted_quantity': int(round(pred)),
                'model_type': 'linear',
            })

            # 递归更新特征（除 category_id 外）
            cur['lag_1'] = pred
            cur['rolling_mean_7'] = (cur['rolling_mean_7'] * 6 + pred) / 7
            next_d = forecast_date + timedelta(days=1)
            cur['dayofweek'] = next_d.weekday()
            cur['month'] = next_d.month
            cur['day'] = next_d.day
            cur['is_weekend'] = 1 if next_d.weekday() in (5, 6) else 0
    return predictions

def get_latest_features(df, product_ids):
    """提取每个商品最新一天的特征行"""
    latest = {}
    for pid in product_ids:
        pid_data = df[df['product_id'] == pid]
        if not pid_data.empty:
            last = pid_data.iloc[-1]
            latest[pid] = last[FEATURE_COLS + ['order_date']]
    return latest

def write_forecasts(predictions, mape):
    """将预测结果写入 sales_forecast 表（先删除当天及以后预测，避免重复）"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM sales_forecast WHERE forecast_date >= CURDATE()")
    sql = """INSERT INTO sales_forecast
             (product_id, forecast_date, predicted_quantity, model_type, mape)
             VALUES (%s, %s, %s, %s, %s)"""
    for p in predictions:
        cur.execute(sql, (p['product_id'], p['forecast_date'],
                          p['predicted_quantity'], p['model_type'], mape))
    conn.commit()
    cur.close()
    conn.close()
    print(f"[预测写入] 已写入 {len(predictions)} 条预测记录")

# =============================================================================
# 异常检测
# =============================================================================
def run_anomaly_detection():
    """基于预警规则进行销售额突降检测，并打印告警信息"""
    rules = load_alert_rules()
    if rules.empty:
        print("[异常检测] 无启用规则，跳过")
        return

    sql = """SELECT DATE(order_date) as dt, SUM(total_amount) as daily_revenue
             FROM sales_record
             WHERE order_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
             GROUP BY dt ORDER BY dt"""
    conn = get_conn()
    df_rev = pd.read_sql(sql, conn, parse_dates=['dt'])
    conn.close()

    if df_rev.shape[0] < 8:
        print("[异常检测] 近30天数据不足8条，跳过")
        return

    # 计算前7天（不含当天）的基线
    df_rev['baseline_7'] = df_rev['daily_revenue'].shift(1).rolling(7).mean()
    df_rev['baseline_std'] = df_rev['daily_revenue'].shift(1).rolling(7).std()
    last = df_rev.iloc[-1]
    latest_rev = last['daily_revenue']
    baseline = last['baseline_7']
    if pd.isna(baseline) or baseline <= 0:
        print("[异常检测] 基线数据不可用，跳过")
        return

    for _, rule in rules.iterrows():
        if rule['rule_type'] == 'sales_drop':
            threshold_pct = float(rule['threshold'])
            change_pct = (latest_rev - baseline) / baseline * 100
            if change_pct <= threshold_pct:
                severity = 'orange' if change_pct <= -50 else 'yellow'
                content = (f"全品类销售额较前7日均线下降{abs(change_pct):.1f}% "
                           f"(当前{latest_rev:.2f}, 基线{baseline:.2f})")
                _insert_alert(rule['rule_id'], content, change_pct, baseline, severity)
                print(f"[异常检测] 触发告警: {content}")
    print("[异常检测] 完成")

def _insert_alert(rule_id, content, anomaly_val, baseline_val, severity):
    """写入告警日志到 alert_log 表"""
    conn = get_conn()
    cur = conn.cursor()
    sql = """INSERT INTO alert_log (rule_id, trigger_time, alert_content,
             anomaly_value, baseline_value, severity, status)
             VALUES (%s, NOW(), %s, %s, %s, %s, 'pending')"""
    cur.execute(sql, (rule_id, content, anomaly_val, baseline_val, severity))
    conn.commit()
    cur.close()
    conn.close()

# =============================================================================
# 库存预测与补货建议
# =============================================================================
def run_inventory():
    """基于 sales_forecast 中的预测和 product.stock_quantity 计算补货建议"""
    # 取最新一批预测（以最大 forecast_date 为准，兼容历史数据）
    sql = """SELECT sf.product_id, sf.forecast_date, sf.predicted_quantity
             FROM sales_forecast sf
             INNER JOIN (
                 SELECT product_id, MAX(forecast_date) AS max_date
                 FROM sales_forecast GROUP BY product_id
             ) latest ON sf.product_id = latest.product_id
             AND sf.forecast_date >= DATE_SUB(latest.max_date, INTERVAL 7 DAY)
             ORDER BY sf.product_id, sf.forecast_date"""
    conn = get_conn()
    df_fc = pd.read_sql(sql, conn)
    conn.close()

    if df_fc.empty:
        print("[库存预测] 无预测数据，跳过")
        return

    inventory = load_inventory()
    print("\n===== 库存补货建议 =====")
    for pid, group in df_fc.groupby('product_id'):
        future = group['predicted_quantity'].tolist()
        stock = inventory.get(pid, 0)
        demand_lt = sum(future[:3])                   # 提前期3天
        std_d = np.std(future) if len(future) > 1 else 1
        safety = 1.65 * np.sqrt(3) * std_d            # 安全库存 (z=1.65, L=3)
        suggest = max(0, demand_lt + safety - stock)
        print(f"商品 {pid:>2}: 库存={stock:>3}, 未来7天总需求={sum(future):>3}, 建议补货={int(np.ceil(suggest)):>3}")
    print("========================\n")

# =============================================================================
# 用户画像计算 (UC-04, P1)
# =============================================================================
def compute_user_profiles():
    """基于全量销售记录，用 RFM 模型计算所有客户的画像，写入 user_profile 表"""
    conn = get_conn()
    customers = pd.read_sql("SELECT customer_id FROM customer", conn)
    if customers.empty:
        conn.close()
        print("[用户画像] 无客户数据，跳过")
        return
    cids = customers['customer_id'].tolist()

    # 拉取所有销售记录（含品类ID）
    sales_sql = """
        SELECT sr.customer_id, sr.order_date, sr.quantity, sr.total_amount,
               p.category_id
        FROM sales_record sr
        JOIN product p ON sr.product_id = p.product_id
        WHERE sr.customer_id IS NOT NULL
    """
    sales = pd.read_sql(sales_sql, conn, parse_dates=['order_date'])
    cat_df = pd.read_sql("SELECT category_id, category_name FROM category", conn)
    conn.close()

    if sales.empty:
        print("[用户画像] 无销售数据，跳过")
        return

    cat_dict = dict(zip(cat_df['category_id'], cat_df['category_name']))
    # 标记促销订单
    sales['is_promo'] = 0
    for s, e in PROMO_PERIODS:
        mask = (sales['order_date'] >= pd.to_datetime(s)) & (sales['order_date'] <= pd.to_datetime(e))
        sales.loc[mask, 'is_promo'] = 1

    now = pd.Timestamp.now().date()
    profiles = []
    for cid in cids:
        cust = sales[sales['customer_id'] == cid]
        if cust.empty:
            continue
        last_date = cust['order_date'].max().date()
        recency = (now - last_date).days
        first_month = cust['order_date'].min().to_period('M')
        last_month = cust['order_date'].max().to_period('M')
        active = (last_month - first_month).n + 1
        freq = len(cust) / active                         # 月均购买次数
        avg_price = cust['total_amount'].sum() / len(cust)
        top_cat = cust['category_id'].mode()
        pref = cat_dict.get(top_cat[0], '未知') if not top_cat.empty else '未知'
        promo_ratio = cust['is_promo'].mean()
        if promo_ratio >= 0.5:
            sens = '高'
        elif promo_ratio >= 0.3:
            sens = '中'
        else:
            sens = '低'
        profiles.append({
            'customer_id': cid,
            'recency': recency,
            'freq': freq,
            'avg_price': avg_price,
            'pref_cat': pref,
            'promo_sens': sens,
            'last_purchase_date': last_date
        })

    if not profiles:
        print("[用户画像] 无有效画像数据")
        return

    pf = pd.DataFrame(profiles)
    # RFM打分（按分位数分1-5）
    try:
        pf['R_score'] = pd.qcut(pf['recency'], 5, labels=[5,4,3,2,1], duplicates='drop')
        pf['F_score'] = pd.qcut(pf['freq'], 5, labels=[1,2,3,4,5], duplicates='drop')
        pf['M_score'] = pd.qcut(pf['avg_price'], 5, labels=[1,2,3,4,5], duplicates='drop')
    except ValueError:
        # 数据太少导致分位失败时，给默认值
        pf['R_score'] = 3
        pf['F_score'] = 3
        pf['M_score'] = 3

    pf['total_score'] = pf[['R_score','F_score','M_score']].astype(int).sum(axis=1)
    pf['value_level'] = pd.cut(pf['total_score'], bins=[0,7,11,15],
                               labels=['低价值','中价值','高价值'], right=True)

    # 写入 user_profile（先清空，避免数据冲突）
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM user_profile")
    ins = """INSERT INTO user_profile (customer_id, value_level, avg_order_price,
               purchase_frequency, preferred_category, promo_sensitivity, last_purchase_date)
             VALUES (%s, %s, %s, %s, %s, %s, %s)"""
    for _, row in pf.iterrows():
        cur.execute(ins, (row['customer_id'], row['value_level'], row['avg_price'],
                          row['freq'], row['pref_cat'], row['promo_sens'],
                          row['last_purchase_date']))
    conn.commit()
    cur.close()
    conn.close()
    print(f"[用户画像] 已生成 {len(pf)} 个客户画像")

# =============================================================================
# 营销活动评估 (UC-07, P1)
# =============================================================================
def evaluate_campaigns():
    """分析已结束活动的销售增量与ROI，打印报告"""
    conn = get_conn()
    camps = pd.read_sql("SELECT * FROM campaign WHERE status='ended'", conn)
    if camps.empty:
        conn.close()
        print("[营销评估] 无已结束活动，跳过（请先在 campaign 表中插入 ended 状态的活动）")
        return
    sales = pd.read_sql("SELECT order_date, quantity, total_amount FROM sales_record",
                        conn, parse_dates=['order_date'])
    conn.close()
    sales = sales.sort_values('order_date')

    print("\n===== 营销活动效果评估 =====")
    for _, camp in camps.iterrows():
        start = pd.to_datetime(camp['start_date'])
        end = pd.to_datetime(camp['end_date'])
        duration = (end - start).days + 1
        cost = camp['campaign_cost'] if pd.notna(camp['campaign_cost']) else 0

        mask = (sales['order_date'] >= start) & (sales['order_date'] <= end)
        camp_qty = sales.loc[mask, 'quantity'].sum()
        camp_rev = sales.loc[mask, 'total_amount'].sum()

        # 基线：活动前相同天数，若缺失则用近30天日均推算
        base_start = start - pd.Timedelta(days=duration)
        base_mask = (sales['order_date'] >= base_start) & (sales['order_date'] < start)
        base = sales[base_mask]
        if base.empty:
            early = sales[sales['order_date'] < start].tail(30)
            days = max(len(early), 1)
            daily_qty = early['quantity'].sum() / days
            daily_rev = early['total_amount'].sum() / days
            base_qty = daily_qty * duration
            base_rev = daily_rev * duration
        else:
            base_qty = base['quantity'].sum()
            base_rev = base['total_amount'].sum()

        inc_qty = camp_qty - base_qty
        inc_rev = camp_rev - base_rev
        inc_pct = (inc_qty / base_qty * 100) if base_qty > 0 else float('inf')
        roi = (inc_rev - cost) / cost if cost > 0 else None

        print(f"\n活动：{camp['campaign_name']} ({start.date()} ~ {end.date()})")
        print(f"  销量: {camp_qty:.0f} / 基线: {base_qty:.0f} → 增量: {inc_qty:.0f} ({inc_pct:.1f}%)")
        print(f"  销售额: {camp_rev:.2f} / 基线: {base_rev:.2f} → 增量收入: {inc_rev:.2f}")
        if roi is not None:
            print(f"  ROI: {roi:.2f}")
        else:
            print("  ROI: 无成本数据")
    print("================================\n")

# ═══════════════════════════════════════════════════════════════
# API 函数 — 供 Flask 后端调用（严辰乐 2026-06-20 补回）
# ═══════════════════════════════════════════════════════════════

def predict_sales_for_api() -> List[Dict]:
    """
    加载已训练模型，预测未来销量，返回 JSON 友好格式。
    供 Flask predict_routes.py 调用。

    返回:
        [{"product_id": 1, "product_name": "纯棉简约T恤女",
          "forecast_date": "2026-06-21", "predicted_quantity": 15,
          "model_type": "linear"}, ...]
    """
    model = load_model()
    sales_df = load_sales_aggregated()
    products = load_product_info()
    product_ids = products['product_id'].unique()

    feat_df = create_features(sales_df)
    latest_feats = get_latest_features(feat_df, product_ids)
    predictions = predict_future(model, latest_feats)

    name_map = dict(zip(products['product_id'], products['product_name']))
    for p in predictions:
        p['product_name'] = name_map.get(int(p['product_id']), '未知商品')
        p['product_id'] = int(p['product_id'])
        p['predicted_quantity'] = int(p['predicted_quantity'])

    return predictions


def predict_stock_for_api() -> List[Dict]:
    """
    基于 sales_forecast 中最新预测，计算补货建议。
    库存数据从 product.stock_quantity 读取（数据库真实数据）。
    供 Flask predict_routes.py 调用。

    返回:
        [{"product_id": 1, "product_name": "纯棉简约T恤女",
          "current_stock": 80, "demand_next_3_days": 12,
          "safety_stock": 6, "suggest_replenish": 0}, ...]
    """
    inventory = load_inventory()
    products = load_product_info()
    name_map = dict(zip(products['product_id'], products['product_name']))

    # 取最新一批预测（以最大 forecast_date 为准，兼容历史数据）
    sql = """SELECT sf.product_id, sf.forecast_date, sf.predicted_quantity
             FROM sales_forecast sf
             INNER JOIN (
                 SELECT product_id, MAX(forecast_date) AS max_date
                 FROM sales_forecast GROUP BY product_id
             ) latest ON sf.product_id = latest.product_id
             AND sf.forecast_date >= DATE_SUB(latest.max_date, INTERVAL 7 DAY)
             ORDER BY sf.product_id, sf.forecast_date"""
    conn = get_conn()
    df_fc = pd.read_sql(sql, conn)
    conn.close()

    if df_fc.empty:
        return []

    results = []
    for pid, group in df_fc.groupby('product_id'):
        future = group['predicted_quantity'].tolist()
        stock = inventory.get(pid, 0)
        demand_lt = sum(future[:3])
        std_d = np.std(future) if len(future) > 1 else 1.0
        safety = max(0, 1.65 * np.sqrt(3) * std_d)
        suggest = max(0, int(np.ceil(demand_lt + safety - stock)))

        results.append({
            'product_id': int(pid),
            'product_name': name_map.get(int(pid), '未知商品'),
            'current_stock': int(stock),
            'demand_next_3_days': int(demand_lt),
            'safety_stock': int(np.ceil(safety)),
            'suggest_replenish': int(suggest),
        })

    return results


def detect_anomalies_for_api() -> List[Dict]:
    """
    执行异常检测，返回触发的告警列表。
    供 Flask alert_routes.py 调用。

    返回:
        [{"rule_id": 1, "rule_type": "sales_drop",
          "content": "全品类销售额较前7日均线下降35.2%...",
          "severity": "yellow", "anomaly_value": -35.2,
          "baseline_value": 50000.0}, ...]
        无异常时返回空列表 []
    """
    rules = load_alert_rules()
    if rules.empty:
        return []

    sql = """SELECT DATE(order_date) as dt, SUM(total_amount) as daily_revenue
             FROM sales_record
             WHERE order_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
             GROUP BY dt ORDER BY dt"""
    conn = get_conn()
    df_rev = pd.read_sql(sql, conn, parse_dates=['dt'])
    conn.close()

    if df_rev.shape[0] < 8:
        return []

    df_rev['baseline_7'] = df_rev['daily_revenue'].shift(1).rolling(7).mean()
    df_rev['baseline_std'] = df_rev['daily_revenue'].shift(1).rolling(7).std()
    last = df_rev.iloc[-1]
    latest_rev = last['daily_revenue']
    baseline = last['baseline_7']
    std = last['baseline_std'] if not pd.isna(last['baseline_std']) else 0

    alerts = []
    for _, rule in rules.iterrows():
        if rule['rule_type'] == 'sales_drop':
            threshold_pct = float(rule['threshold'])
            if baseline <= 0:
                continue
            change_pct = (latest_rev - baseline) / baseline * 100
            if change_pct <= threshold_pct:
                severity = 'orange' if change_pct <= -50 else 'yellow'
                content = (f"全品类销售额较前7日均线下降{abs(change_pct):.1f}% "
                           f"(当前{latest_rev:.2f}, 基线{baseline:.2f})")
                alerts.append({
                    'rule_id': int(rule['rule_id']),
                    'rule_type': rule['rule_type'],
                    'content': content,
                    'severity': severity,
                    'anomaly_value': round(change_pct, 2),
                    'baseline_value': round(baseline, 2),
                })
                _insert_alert(rule['rule_id'], content, change_pct, baseline, severity)

    return alerts


# =============================================================================
# 主流程 (P0 + P1 一键执行)
# =============================================================================
def main():
    print("=" * 50)
    print("ML 管道启动 (含 P0+P1)")
    print("=" * 50)

    # 1. 数据加载
    print("[1/8] 加载销售数据...")
    sales_df = load_sales_aggregated()
    products = load_product_info()
    product_ids = products['product_id'].unique()

    # 2. 特征工程
    print("[2/8] 构造特征（含 category_id）...")
    feat_df = create_features(sales_df)

    # 3. 模型训练
    print("[3/8] 训练预测模型...")
    model, mape = train_model(feat_df)

    # 4. 销售预测 + 写入数据库
    print("[4/8] 预测未来 7 天销量并写入 sales_forecast ...")
    latest_feats = get_latest_features(feat_df, product_ids)
    preds = predict_future(model, latest_feats)
    write_forecasts(preds, mape)

    # 5. 异常检测
    print("[5/8] 异常检测...")
    run_anomaly_detection()

    # 6. 库存补货建议
    print("[6/8] 库存预测与补货建议...")
    run_inventory()

    # 7. 用户画像 (P1)
    print("[7/8] 用户画像计算...")
    compute_user_profiles()

    # 8. 营销活动评估 (P1)
    print("[8/8] 营销活动评估...")
    evaluate_campaigns()

    print("\n[完成] ML 全管道执行完毕")

if __name__ == "__main__":
    main()
