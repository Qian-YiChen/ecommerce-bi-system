# =============================================================================
# ml/ml_pipeline.py — 电商BI系统 · 机器学习管道（含销售预测/异常检测/库存补货）
# 作者：薛淞  日期：2026-06-08
# 修改：严辰乐  日期：2026-06-08
#   - 库存数据从数据库 product.stock_quantity 读取（移除 MOCK_INVENTORY）
#   - 新增 category_id 特征（每个品类有独立的销售规律）
#   - 新增 load_model() / predict_sales_for_api() / predict_stock_for_api()
#     等独立函数，供 Flask 后端 API 调用
# =============================================================================

import os
import sys
import joblib
import numpy as np
import pandas as pd
import pymysql
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# ─── 配置 ──────────────────────────────────────────────────────────────────
try:
    from config import DB_CONFIG, FORECAST_HORIZON, MODEL_DIR
except ImportError:
    DB_CONFIG = {
        'host': 'localhost', 'port': 3306, 'user': 'root',
        'password': '123456', 'database': 'ecommerce_bi', 'charset': 'utf8mb4'
    }
    FORECAST_HORIZON = 7
    MODEL_DIR = 'models'

# 特征列：时间特征 + 滞后特征 + 品类特征
# category_id 让模型知道不同品类的商品有不同的销售基准（手机 ≠ 零食）
FEATURE_COLS = [
    'dayofweek', 'month', 'day', 'is_weekend',
    'lag_1', 'rolling_mean_7',
    'category_id',
]


# =============================================================================
# 1. 数据库工具
# =============================================================================
def get_conn():
    return pymysql.connect(**DB_CONFIG)


# =============================================================================
# 2. 数据加载
# =============================================================================
def load_sales_aggregated():
    """从 sales_record 聚合日粒度销量，JOIN product 获取 category_id，返回 DataFrame"""
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
    """加载商品维表"""
    conn = get_conn()
    df = pd.read_sql(
        "SELECT product_id, product_name, category_id, price, stock_quantity FROM product",
        conn
    )
    conn.close()
    return df


def load_inventory():
    """
    从 product 表读取真实库存数据。
    返回 dict: {product_id: stock_quantity}
    （之前用 MOCK_INVENTORY 随机生成，现已改为数据库真实数据）
    """
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
# 3. 特征工程
# =============================================================================
def create_features(df):
    """
    构造时序特征。
    category_id 已通过 load_sales_aggregated() 的 JOIN 带入，
    这里不需要额外处理——它直接作为模型特征使用。
    """
    df = df.sort_values(['product_id', 'order_date']).reset_index(drop=True)

    # 时间特征
    df['dayofweek'] = df['order_date'].dt.dayofweek
    df['month'] = df['order_date'].dt.month
    df['day'] = df['order_date'].dt.day
    df['is_weekend'] = df['dayofweek'].isin([5, 6]).astype(int)

    # 滞后销量特征
    df['lag_1'] = df.groupby('product_id')['total_qty'].shift(1)
    df['rolling_mean_7'] = (
        df.groupby('product_id')['total_qty']
          .shift(1)
          .rolling(window=7, min_periods=1)
          .mean()
          .reset_index(level=0, drop=True)
    )

    # 缺失值填充
    fill_vals = {
        'lag_1': df['total_qty'].median(),
        'rolling_mean_7': df['total_qty'].median()
    }
    df.fillna(fill_vals, inplace=True)
    return df


# =============================================================================
# 4. 模型训练
# =============================================================================
def train_model(df):
    """
    训练线性回归基线模型。
    现在包含 category_id 特征，模型能区分不同品类的销售基准。
    返回 (model, mape)。
    """
    from sklearn.linear_model import LinearRegression
    from sklearn.metrics import mean_absolute_error, mean_squared_error

    X = df[FEATURE_COLS]
    y = df['total_qty']

    # 按时间切分（前80%训练，后20%测试）
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
    """
    从磁盘加载已训练的模型。
    供 Flask 后端 API 调用——无需每次重新训练。

    用法:
        model = load_model()
        preds = model.predict(features)
    """
    path = os.path.join(MODEL_DIR, model_name)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"模型文件不存在: {path}。请先运行 train_model() 训练模型。"
        )
    return joblib.load(path)


# =============================================================================
# 5. 销售预测
# =============================================================================
def predict_future(model, latest_features_dict):
    """递归预测未来 FORECAST_HORIZON 天（内部使用）"""
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

            # 递归更新特征
            cur['lag_1'] = pred
            cur['rolling_mean_7'] = (cur['rolling_mean_7'] * 6 + pred) / 7
            next_d = forecast_date + timedelta(days=1)
            cur['dayofweek'] = next_d.weekday()
            cur['month'] = next_d.month
            cur['day'] = next_d.day
            cur['is_weekend'] = 1 if next_d.weekday() in (5, 6) else 0
            # category_id 保持不变（商品的品类不会变）
    return predictions


def get_latest_features(df, product_ids):
    """提取每个商品最新一天的特征（内部使用）"""
    latest = {}
    for pid in product_ids:
        pid_data = df[df['product_id'] == pid]
        if not pid_data.empty:
            last = pid_data.iloc[-1]
            latest[pid] = last[FEATURE_COLS + ['order_date']]
    return latest


def write_forecasts(predictions, mape):
    """将预测结果写入 sales_forecast 表"""
    conn = get_conn()
    cur = conn.cursor()
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


# ═══════════════════════════════════════════════════════════════
# 5a. 独立 API 函数 — 供 Flask 后端调用
# ═══════════════════════════════════════════════════════════════

def predict_sales_for_api() -> List[Dict]:
    """
    加载已训练模型，预测未来销量，返回 JSON 友好格式。
    此函数供 Flask predict_routes.py 调用，不会重新训练模型。

    返回:
        [
            {
                "product_id": 1,
                "product_name": "纯棉简约T恤女",
                "forecast_date": "2026-06-09",
                "predicted_quantity": 15,
                "model_type": "linear"
            },
            ...
        ]
    """
    model = load_model()
    sales_df = load_sales_aggregated()
    products = load_product_info()
    product_ids = products['product_id'].unique()

    feat_df = create_features(sales_df)
    latest_feats = get_latest_features(feat_df, product_ids)
    predictions = predict_future(model, latest_feats)

    # 关联商品名称
    name_map = dict(zip(products['product_id'], products['product_name']))
    for p in predictions:
        p['product_name'] = name_map.get(p['product_id'], '未知商品')

    return predictions


def predict_stock_for_api() -> List[Dict]:
    """
    基于 sales_forecast 中最新预测，计算补货建议。
    库存数据从 product.stock_quantity 读取（数据库真实数据）。

    返回:
        [
            {
                "product_id": 1,
                "product_name": "纯棉简约T恤女",
                "current_stock": 80,
                "demand_next_3_days": 45,
                "safety_stock": 12,
                "suggest_replenish": 0
            },
            ...
        ]
    """
    inventory = load_inventory()
    products = load_product_info()
    name_map = dict(zip(products['product_id'], products['product_name']))

    # 从 sales_forecast 读取最新预测
    sql = """SELECT product_id, forecast_date, predicted_quantity
             FROM sales_forecast
             WHERE forecast_date >= CURDATE()
             ORDER BY product_id, forecast_date"""
    conn = get_conn()
    df_fc = pd.read_sql(sql, conn)
    conn.close()

    if df_fc.empty:
        return []

    results = []
    for pid, group in df_fc.groupby('product_id'):
        future = group['predicted_quantity'].tolist()
        stock = inventory.get(pid, 0)
        demand_lt = sum(future[:3])           # 提前期 3 天
        std_d = np.std(future) if len(future) > 1 else 1.0
        safety = max(0, 1.65 * np.sqrt(3) * std_d)  # z=1.65 (95%)
        suggest = max(0, int(np.ceil(demand_lt + safety - stock)))

        results.append({
            'product_id': pid,
            'product_name': name_map.get(pid, '未知商品'),
            'current_stock': stock,
            'demand_next_3_days': int(demand_lt),
            'safety_stock': int(np.ceil(safety)),
            'suggest_replenish': suggest,
        })

    return results


def detect_anomalies_for_api() -> List[Dict]:
    """
    执行异常检测，返回触发的告警列表。

    返回:
        [
            {
                "rule_id": 1,
                "rule_type": "sales_drop",
                "content": "全品类销售额较前7日均线下降35%...",
                "severity": "yellow",
                "anomaly_value": -35.2,
                "baseline_value": 50000.0
            },
            ...
        ]
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
                    'rule_id': rule['rule_id'],
                    'rule_type': rule['rule_type'],
                    'content': content,
                    'severity': severity,
                    'anomaly_value': round(change_pct, 2),
                    'baseline_value': round(baseline, 2),
                })
                _insert_alert(rule['rule_id'], content, change_pct, baseline, severity)

    return alerts


# =============================================================================
# 6. 异常检测（内部）
# =============================================================================
def run_anomaly_detection():
    """执行异常检测并打印结果（供 main() 调用）"""
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
        print("[异常检测] 数据不足，跳过")
        return

    df_rev['baseline_7'] = df_rev['daily_revenue'].shift(1).rolling(7).mean()
    df_rev['baseline_std'] = df_rev['daily_revenue'].shift(1).rolling(7).std()
    last = df_rev.iloc[-1]
    latest_rev = last['daily_revenue']
    baseline = last['baseline_7']

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
                _insert_alert(rule['rule_id'], content, change_pct, baseline, severity)
                print(f"[异常检测] 触发告警: {content}")
    print("[异常检测] 完成")


def _insert_alert(rule_id, content, anomaly_val, baseline_val, severity):
    """写入告警日志到 alert_log 表。使用 pymysql 参数化查询，安全防注入。"""
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
# 7. 库存预测与补货建议
# =============================================================================
def run_inventory():
    """
    基于 sales_forecast 中最新预测，计算补货建议。
    库存数据从 product.stock_quantity 读取（数据库真实数据）。
    """
    sql = """SELECT product_id, forecast_date, predicted_quantity
             FROM sales_forecast
             WHERE forecast_date >= CURDATE()
             ORDER BY product_id, forecast_date"""
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
        demand_lt = sum(future[:3])
        std_d = np.std(future) if len(future) > 1 else 1
        safety = 1.65 * np.sqrt(3) * std_d
        suggest = max(0, demand_lt + safety - stock)
        print(f"商品 {pid:>2}: 库存={stock:>3}, 未来7天总需求={sum(future):>3}, 建议补货={int(np.ceil(suggest)):>3}")
    print("========================\n")


# =============================================================================
# 8. 主流程（训练 + 预测 + 异常 + 库存，全链路）
# =============================================================================
def main():
    print("=" * 50)
    print("ML 管道启动")
    print("=" * 50)

    # 1. 数据加载
    print("[1/6] 加载销售数据...")
    sales_df = load_sales_aggregated()
    products = load_product_info()
    product_ids = products['product_id'].unique()

    # 2. 特征工程
    print("[2/6] 构造特征（含 category_id）...")
    feat_df = create_features(sales_df)

    # 3. 模型训练
    print("[3/6] 训练预测模型...")
    model, mape = train_model(feat_df)

    # 4. 未来预测 + 写入数据库
    print("[4/6] 预测未来 7 天销量并写入 sales_forecast ...")
    latest_feats = get_latest_features(feat_df, product_ids)
    preds = predict_future(model, latest_feats)
    write_forecasts(preds, mape)

    # 5. 异常检测
    print("[5/6] 异常检测...")
    run_anomaly_detection()

    # 6. 库存补货建议
    print("[6/6] 库存预测与补货建议...")
    run_inventory()

    print("\n[完成] ML 管道执行完毕")


if __name__ == "__main__":
    main()
