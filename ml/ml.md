X. 智能分析与预测模块设计（更新版）  2026.6.10

X.1 模块总体架构
管道架构：数据抽取 → 特征工程 → 模型训练 → 预测 / 检测 → 结果写入
技术栈：Python 3, pandas, scikit-learn, joblib, PyMySQL
模型管线图：
plaintext
MySQL (sales_record, product, customer)
        |
        ▼
[ 日粒度聚合 + 特征工程 ]
        |
        ├─[ 线性回归预测 ] ──→ sales_forecast
        ├─[ 安全库存计算 ] ──→ 补货建议
        ├─[ 规则引擎异常检测 ] ──→ alert_log
        ├─[ RFM 画像计算 ] ──→ user_profile
        └─[ 同期对比营销评估 ] ──→ 报告输出

X.2 数据源与特征工程
数据聚合：从 sales_record 按 (日期，商品) 聚合，JOIN product 保留 category_id
特征列表（共 7 个，用于销售预测）
特征名	         描述	                    构造方式
dayofweek	   星期几 (0-6)	              日期字段提取
month	         月份	                  日期字段提取
day	             日期	                  日期字段提取
is_weekend	    是否周末	               周末 → 1，工作日 → 0
lag_1	       前一日销量	           按商品分组 shift(1)
rolling_mean_7	前 7 天滚动均值	      不含当日，shift(1).rolling(7).mean()
category_id	    所属品类	                 JOIN 自 product 表

X.3 销售预测（UC-02）
业务目标：预测每个商品未来 7 天的日销量
模型选型
基线：多元线性回归
理由：实现简单、训练快、可解释，为后续 ARIMA/LightGBM 提供基准
训练与评估
划分：前 80% 数据训练，后 20% 测试（时间顺序切分）
指标：MAE, RMSE, MAPE（已处理除零）
模型保存：models/sales_lr_baseline.pkl
预测流程
提取每个商品最新一天的特征向量
递归多步预测（每次预测 1 天，滚动更新 lag_1、rolling_mean_7）
结果写入 sales_forecast 表（先清空当日及以后的旧预测）
预期效果（实测后填入）
MAE: ___ / RMSE: ___ / MAPE: ___%

X.4 库存预测与补货建议（UC-03）
算法逻辑

总需求 = 未来 3 天预测销量之和
安全库存 = 1.65 * qrt{3} * sigma（95% 服务水平，提前期 3 天）
建议补货量 = max(0, 总需求 + 安全库存 - 当前库存)
数据来源
当前库存：product.stock_quantity
预测销量：sales_forecast 表
输出：控制台打印补货建议，同时提供 API 函数 predict_stock_for_api() 返回 JSON

X.5 异常检测（UC-08）
方案：规则引擎（P0 首选）
规则类型：sales_drop（全品类销售额突降）
基线计算：前 7 天（不含当日）日销售额均值
告警条件：当日销售额较基线下降幅度 ≥ 阈值（如 -30%）
告警级别
下降 30%-50% → yellow
下降 ≥50% → orange
结果写入：alert_log 表，状态 pending
扩展性：可新增 stock_low、return_spike 等规则，只需扩展规则分支

X.6 用户画像计算（UC-04）
算法模型：RFM + 偏好品类 + 促销敏感度
R：最近购买距今天数
F：月均购买次数（交易数 / 活跃月数）
M：平均客单价
价值分层：R/F/M 各自分位数打分（1-5 分），总分 ≥12 → 高价值，8-11 → 中价值，≤7 → 低价值
偏好品类：历史购买最多的品类（众数）
促销敏感度：大促期订单占比 ≥50% → 高，30%-50% → 中，<30% → 低
数据来源：sales_record JOIN product（获取 category_id），结合大促日期表
更新方式：全量重算，清空 user_profile 后写入新画像

X.7 营销活动评估（UC-07）
评估方法：同期对比法
活动期间销量 / 销售额 vs 活动前相同天数（若缺失则用前 30 天日均推算）
增量 = 活动期 - 基线期
ROI = (增量收入 - 活动成本) / 活动成本（成本 > 0 时计算）
数据来源：campaign 表（status='ended'） + sales_record
输出：控制台报告（活动名、销量增量、ROI），未来可扩展至前端报表

X.8 模型更新与维护
训练频率：每次手动执行 ml_pipeline.py 完成全量重训练和全链路更新
线上调用：Flask 后端可通过 load_model() 等函数加载已保存模型，避免每次重训
模型替换：未来可将 LinearRegression 替换为 ARIMA 或 LightGBM，仅需修改 train_model() 和特征工程部分
