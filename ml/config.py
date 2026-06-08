# ml/config.py
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '123456',
    'database': 'ecommerce_bi',
    'charset': 'utf8mb4'
}

FORECAST_HORIZON = 7  # 预测未来 7 天
MODEL_DIR = 'models'  # 模型保存目录（相对于 ml/）
