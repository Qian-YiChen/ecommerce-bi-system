"""
APScheduler 定时任务调度
======================
负责定时执行预警扫描（每小时检查一次销售异常）。

启动方式:
    from scheduler import init_scheduler
    init_scheduler(app)  # Flask 启动时调用

依赖:
    apscheduler>=3.10  (已在 requirements.txt 中)
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)

# 全局调度器实例（模块级单例）
_scheduler: BackgroundScheduler = None


def _scan_alerts_job():
    """
    定时扫描任务：调用 ML 管道检测异常并写入 alert_log。
    此函数在 APScheduler 线程中运行，不阻塞 Flask 请求处理。
    """
    try:
        from ml.ml_pipeline import detect_anomalies_for_api
        alerts = detect_anomalies_for_api()
        if alerts:
            logger.info(f"[定时预警] 扫描完成，触发 {len(alerts)} 条告警")
            for a in alerts:
                logger.info(f"  - [{a['severity']}] {a['content'][:80]}...")
        else:
            logger.debug("[定时预警] 扫描完成，未发现异常")
    except Exception as e:
        logger.error(f"[定时预警] 扫描失败: {e}")


def init_scheduler(app=None):
    """
    初始化并启动后台调度器。

    参数:
        app: Flask 应用实例（可选，用于日志配置）

    调度规则:
        - 异常检测扫描：每小时执行一次（第 0 分钟，如 10:00, 11:00...）
        - 未来可扩展：每日凌晨 2 点触发 ML 重训练

    用法:
        # 在 app.py 的 create_app() 返回前调用
        init_scheduler(app)
    """
    global _scheduler

    if _scheduler is not None:
        logger.warning("调度器已在运行，跳过重复初始化")
        return _scheduler

    _scheduler = BackgroundScheduler(
        daemon=True,
        job_defaults={
            'coalesce': True,        # 合并错过的任务（如系统休眠后）
            'max_instances': 1,      # 同一任务最多同时运行 1 个实例
            'misfire_grace_time': 300  # 错过 5 分钟内的任务仍执行
        }
    )

    # ── 注册定时任务 ──
    # 每小时执行异常检测（第 0 分钟触发）
    _scheduler.add_job(
        _scan_alerts_job,
        trigger='cron',
        minute=0,  # 每小时整点
        id='alert_scan_hourly',
        name='每小时异常检测扫描',
        replace_existing=True,
    )

    # 预留：每日凌晨 2 点重训练（当前 ML 管道较重，暂时注释）
    # _scheduler.add_job(
    #     retrain_job,
    #     trigger='cron',
    #     hour=2, minute=7,  # 2:07am（避开整点高峰）
    #     id='ml_retrain_daily',
    #     name='每日模型重训练',
    #     replace_existing=True,
    # )

    _scheduler.start()

    if app:
        app.logger.info("[调度器] APScheduler 已启动 — 每小时整点执行异常扫描")
    else:
        logger.info("[调度器] APScheduler 已启动 — 每小时整点执行异常扫描")

    return _scheduler


def shutdown_scheduler():
    """关闭调度器（Flask 应用退出时调用）"""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("[调度器] 已关闭")
