"""
应用配置
-------
所有环境相关配置集中管理，通过环境变量或直接修改此文件来切换环境。
"""

import os


class Config:
    """基础配置"""
    # JWT
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    JWT_ACCESS_TOKEN_EXPIRES = 7200  # 2 小时（秒）

    # MySQL
    MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.environ.get("MYSQL_PORT", 3306))
    MYSQL_USER = os.environ.get("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "123456")
    MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "ecommerce_bi")

    # Flask
    DEBUG = os.environ.get("FLASK_DEBUG", "1") == "1"

    # CORS
    CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]  # Vue3 dev server

    # Bcrypt
    BCRYPT_ROUNDS = 12


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    # 生产环境强制使用 HTTPS
    SESSION_COOKIE_SECURE = True


def get_config() -> Config:
    """根据环境变量返回对应配置"""
    env = os.environ.get("FLASK_ENV", "development")
    if env == "production":
        return ProductionConfig()
    return DevelopmentConfig()
