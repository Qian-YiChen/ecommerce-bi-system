# =============================================================================
# ml/ml_pipeline.py — 电商BI系统 · 机器学习管道（含销售预测/异常检测/库存补货）
# 作者：薛淞  日期：2026-06-08
# 依赖：pymysql, pandas, numpy, scikit-learn, joblib
# 执行：python ml_pipeline.py
# =============================================================================

import os
import sys
import joblib
import numpy as np
import pandas as pd
import pymysql
from datetime import datetime, timedelta

# ─── 配置 ──────────────────────────────────────────────────────────────────
# 如果不想另建 config.py，可以直接把配置写在这里
try:
    from config import DB_CONFIG, FORECAST_HORIZON, MODEL_DIR
except ImportError:
    # 硬编码备用（仅限本地调试）
    DB_CONFIG = {
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': '123456',
        'database': 'ecommerce_bi',
        'charset': 'utf8mb4'
    }
    FORECAST_HORIZON = 7
    MODEL_DIR = 'models'

# 特征列（去掉了 lag_7，避免递归预测无法更新的问题）
FEATURE_COLS = [
    'dayofweek', 'month', 'day', 'is_weekend', 'lag_1', 'rolling_mean_7'
]

# 模拟库存（实际项目中应从真实 inventory 表读取）
MOCK_INVENTORY = {pid: np.random.randint(50, 200) for pid in range(1, 25)}


# =============================================================================
# 1. 数据库工具
# =============================================================================
def get_conn():
    return pymysql.connect(**DB_CONFIG)


# =============================================================================
# 2. 数据加载
# =============================================================================
def load_sales_aggregated():
    """从 sales_record 聚合日粒度销量，返回 DataFrame"""
    sql = """
        SELECT DATE(order_date) AS order_date,
               product_id,
               SUM(quantity) AS total_qty,
               SUM(total_amount) AS total_amount
        FROM sales_record
        GROUP BY DATE(order_date), product_id
        ORDER BY product_id, order_date
    """
    conn = get_conn()
    df = pd.read_sql(sql, conn, parse_dates=['order_date'])
    conn.close()
    return df


def load_product_info():
    """加载商品维表"""
    conn = get_conn()
    df = pd.read_sql(
        "SELECT product_id, product_name, category_id, price FROM product",
        conn)
    conn.close()
    return df


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
    df = df.sort_values(['product_id', 'order_date']).reset_index(drop=True)

    # 时间特征
    df['dayofweek'] = df['order_date'].dt.dayofweek
    df['month'] = df['order_date'].dt.month
    df['day'] = df['order_date'].dt.day
    df['is_weekend'] = df['dayofweek'].isin([5, 6]).astype(int)

    # 滞后销量特征
    df['lag_1'] = df.groupby('product_id')['total_qty'].shift(1)
    df['rolling_mean_7'] = (
        df.groupby('product_id')['total_qty'].shift(1).rolling(
            window=7, min_periods=1).mean().reset_index(level=0, drop=True))

    # 缺失值填充（全局中位数）
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
    """训练线性回归基线模型，返回 (model, mape)"""
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


# =============================================================================
# 5. 销售预测（递归 + 写入 sales_forecast）
# =============================================================================
def predict_future(model, latest_features_dict):
    predictions = []
    for pid, last_row in latest_features_dict.items():
        cur = pd.DataFrame([last_row], columns=FEATURE_COLS)
        start_date = last_row['order_date'] + timedelta(days=1)

        for i in range(FORECAST_HORIZON):
            pred = max(0, model.predict(cur)[0])
            forecast_date = start_date + timedelta(days=i)
            predictions.append({
                'product_id':
                pid,
                'forecast_date':
                forecast_date.strftime('%Y-%m-%d'),
                'predicted_quantity':
                int(round(pred)),
                'model_type':
                'linear',
            })

            # 递归更新特征（简化版：更新 lag_1 和 rolling_mean_7，日期特征前移）
            cur['lag_1'] = pred
            cur['rolling_mean_7'] = (cur['rolling_mean_7'] * 6 + pred) / 7
            next_d = forecast_date + timedelta(days=1)
            cur['dayofweek'] = next_d.weekday()
            cur['month'] = next_d.month
            cur['day'] = next_d.day
            cur['is_weekend'] = 1 if next_d.weekday() in (5, 6) else 0
    return predictions


def get_latest_features(df, product_ids):
    latest = {}
    for pid in product_ids:
        pid_data = df[df['product_id'] == pid]
        if not pid_data.empty:
            last = pid_data.iloc[-1]
            latest[pid] = last[FEATURE_COLS + ['order_date']]
    return latest


def write_forecasts(predictions, mape):
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


# =============================================================================
# 6. 异常检测（基于 alert_rule 规则引擎）
# =============================================================================
def run_anomaly_detection():
    rules = load_alert_rules()
    if rules.empty:
        print("[异常检测] 无启用规则，跳过")
        return

    # 获取最近 30 天全品类日销售额
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

    # 前 7 天（不含当天）作为基线
    df_rev['baseline_7'] = df_rev['daily_revenue'].shift(1).rolling(7).mean()
    df_rev['baseline_std'] = df_rev['daily_revenue'].shift(1).rolling(7).std()
    last = df_rev.iloc[-1]
    latest_rev = last['daily_revenue']
    baseline = last['baseline_7']
    std = last['baseline_std'] if not pd.isna(last['baseline_std']) else 0

    for _, rule in rules.iterrows():
        if rule['rule_type'] == 'sales_drop':
            threshold_pct = float(rule['threshold'])
            if baseline <= 0:
                continue
            change_pct = (latest_rev - baseline) / baseline * 100
            if change_pct <= threshold_pct:  # threshold 为负数，如 -30
                severity = 'orange' if change_pct <= -50 else 'yellow'
                content = (f"全品类销售额较前7日均线下降{abs(change_pct):.1f}% "
                           f"(当前{latest_rev:.2f}, 基线{baseline:.2f})")
                _insert_alert(rule['rule_id'], content, change_pct, baseline,
                              severity)
                print(f"[异常检测] 触发告警: {content}")
        # 这里可扩展 stock_low、return_spike 等规则
    print("[异常检测] 完成")


def _insert_alert(rule_id, content, anomaly_val, baseline_val, severity):
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
    """基于 sales_forecast 中最新预测，计算补货建议"""
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

    print("\n===== 库存补货建议 =====")
    for pid, group in df_fc.groupby('product_id'):
        future = group['predicted_quantity'].tolist()
        stock = MOCK_INVENTORY.get(pid, 100)
        demand_lt = sum(future[:3])  # 提前期 3 天
        std_d = np.std(future) if len(future) > 1 else 1
        safety = 1.65 * np.sqrt(3) * std_d  # z=1.65 (95%)
        suggest = max(0, demand_lt + safety - stock)
        print(
            f"商品 {pid:>2}: 库存={stock:>3}, 未来7天总需求={sum(future):>3}, 建议补货={int(np.ceil(suggest)):>3}"
        )
    print("========================\n")


# =============================================================================
# 8. 主流程
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
    print("[2/6] 构造特征...")
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

    print("\n✅ ML 管道执行完毕")


if __name__ == "__main__":
    main()
