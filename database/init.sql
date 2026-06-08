-- ============================================================
-- 电商BI系统 — 数据库建表脚本
-- ============================================================
-- 基于：《需求分析文档》v1.0 §6.2 数据字典
-- 引擎：InnoDB，字符集：utf8mb4
-- 总表数：10 张（含系统用户表）
--
-- 执行方式：
--   mysql -u root -p < init.sql
--   或在 MySQL 客户端中 source init.sql
-- ============================================================

-- ── 创建数据库 ──────────────────────────────────────────────
CREATE DATABASE IF NOT EXISTS ecommerce_bi
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE ecommerce_bi;

-- ============================================================
-- 第1部分：建表
-- ============================================================

-- ────────────────────────────────────────────────────────────
-- 1. 系统用户表（user）
--    用途：系统登录认证与权限管理
--    对应模型：backend/models/user.py → User 类
-- ────────────────────────────────────────────────────────────
DROP TABLE IF EXISTS alert_log;
DROP TABLE IF EXISTS alert_rule;
DROP TABLE IF EXISTS sales_forecast;
DROP TABLE IF EXISTS user_profile;
DROP TABLE IF EXISTS campaign;
DROP TABLE IF EXISTS sales_record;
DROP TABLE IF EXISTS product;
DROP TABLE IF EXISTS category;
DROP TABLE IF EXISTS customer;
DROP TABLE IF EXISTS user;

CREATE TABLE user (
    user_id    INT           NOT NULL AUTO_INCREMENT  COMMENT '用户ID',
    username   VARCHAR(50)   NOT NULL                 COMMENT '用户名',
    password   VARCHAR(255)  NOT NULL                 COMMENT 'bcrypt 密码哈希',
    role       VARCHAR(20)   NOT NULL DEFAULT 'viewer' COMMENT '角色：admin/analyst/manager/viewer',
    status     TINYINT       NOT NULL DEFAULT 1       COMMENT '状态：1=活跃 0=禁用',
    created_at DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (user_id),
    UNIQUE KEY uk_username (username),
    KEY idx_role (role),
    KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='系统用户表 — 登录认证与权限管理';

-- ────────────────────────────────────────────────────────────
-- 2. 品类表（category）
--    用途：商品分类体系，支持三级品类层级
-- ────────────────────────────────────────────────────────────
CREATE TABLE category (
    category_id   INT          NOT NULL AUTO_INCREMENT  COMMENT '品类ID',
    category_name VARCHAR(50)  NOT NULL                 COMMENT '品类名称',
    parent_id     INT          DEFAULT NULL             COMMENT '父品类ID，NULL=一级类目',
    level         TINYINT      NOT NULL                 COMMENT '品类层级：1=一级 2=二级 3=三级',
    PRIMARY KEY (category_id),
    KEY idx_parent (parent_id),
    KEY idx_level (level),
    CONSTRAINT fk_category_parent
        FOREIGN KEY (parent_id) REFERENCES category(category_id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='商品品类表 — 支持三级分类树';

-- ────────────────────────────────────────────────────────────
-- 3. 商品表（product）
--    用途：商品主数据，关联品类
-- ────────────────────────────────────────────────────────────
CREATE TABLE product (
    product_id   INT           NOT NULL AUTO_INCREMENT  COMMENT '商品ID',
    product_name VARCHAR(200)  NOT NULL                 COMMENT '商品名称',
    sku_code     VARCHAR(50)   NOT NULL                 COMMENT 'SKU编码，唯一',
    category_id  INT           NOT NULL                 COMMENT '所属品类ID',
    price        DECIMAL(10,2) NOT NULL                 COMMENT '销售单价（元）',
    cost            DECIMAL(10,2) DEFAULT NULL             COMMENT '进货成本（元）',
    stock_quantity  INT           NOT NULL DEFAULT 0       COMMENT '当前库存量',
    status          TINYINT       NOT NULL DEFAULT 1       COMMENT '状态：1=在售 0=下架',
    created_at   DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (product_id),
    UNIQUE KEY uk_sku (sku_code),
    KEY idx_category (category_id),
    KEY idx_status (status),
    KEY idx_price (price),
    CONSTRAINT fk_product_category
        FOREIGN KEY (category_id) REFERENCES category(category_id)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='商品表 — 商品主数据';

-- ────────────────────────────────────────────────────────────
-- 4. 客户表（customer）
--    用途：消费者信息（脱敏后的基础属性）
-- ────────────────────────────────────────────────────────────
CREATE TABLE customer (
    customer_id   INT          NOT NULL AUTO_INCREMENT  COMMENT '客户ID',
    customer_name VARCHAR(50)  DEFAULT NULL             COMMENT '客户昵称（可匿名）',
    gender        CHAR(1)      DEFAULT NULL             COMMENT '性别：M=男 F=女 U=未知',
    age_group     VARCHAR(10)  DEFAULT NULL             COMMENT '年龄段：18-24/25-34/35-44/45+',
    region        VARCHAR(30)  DEFAULT NULL             COMMENT '所在省份',
    register_date DATE         DEFAULT NULL             COMMENT '注册日期',
    PRIMARY KEY (customer_id),
    KEY idx_region (region),
    KEY idx_age_group (age_group),
    KEY idx_gender (gender)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='客户表 — 消费者基础信息（脱敏）';

-- ────────────────────────────────────────────────────────────
-- 5. 销售记录表（sales_record）
--    用途：核心事实表，记录每笔订单明细
--    注：这是系统最大、查询最频繁的表
-- ────────────────────────────────────────────────────────────
CREATE TABLE sales_record (
    record_id    BIGINT        NOT NULL AUTO_INCREMENT  COMMENT '记录ID',
    product_id   INT           NOT NULL                 COMMENT '商品ID',
    customer_id  INT           DEFAULT NULL             COMMENT '客户ID（匿名可为NULL）',
    quantity     INT           NOT NULL                 COMMENT '销售数量',
    unit_price   DECIMAL(10,2) NOT NULL                 COMMENT '实际成交单价（元）',
    total_amount DECIMAL(12,2) NOT NULL                 COMMENT '成交金额（元）',
    order_date   DATETIME      NOT NULL                 COMMENT '下单时间',
    region       VARCHAR(30)   NOT NULL                 COMMENT '收货省份',
    channel      VARCHAR(20)   NOT NULL DEFAULT 'PC'    COMMENT '渠道：PC/Mobile/Miniprogram',
    PRIMARY KEY (record_id),
    KEY idx_product (product_id),
    KEY idx_customer (customer_id),
    KEY idx_order_date (order_date),
    KEY idx_region (region),
    KEY idx_channel (channel),
    KEY idx_date_region (order_date, region),
    KEY idx_date_product (order_date, product_id),
    CONSTRAINT fk_sales_product
        FOREIGN KEY (product_id) REFERENCES product(product_id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_sales_customer
        FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='销售记录表 — 核心事实表，记录每笔订单明细';

-- ────────────────────────────────────────────────────────────
-- 6. 用户画像表（user_profile）
--    用途：客户价值分层、消费行为标签
-- ────────────────────────────────────────────────────────────
CREATE TABLE user_profile (
    profile_id           INT           NOT NULL AUTO_INCREMENT  COMMENT '画像ID',
    customer_id          INT           NOT NULL                 COMMENT '客户ID',
    value_level          VARCHAR(10)   NOT NULL                 COMMENT '价值等级：高价值/中价值/低价值',
    avg_order_price      DECIMAL(10,2) NOT NULL                 COMMENT '平均客单价（元）',
    purchase_frequency   DECIMAL(5,2)  NOT NULL                 COMMENT '月均购买次数',
    preferred_category   VARCHAR(100)  DEFAULT NULL             COMMENT '偏好品类（逗号分隔）',
    promo_sensitivity    VARCHAR(10)   DEFAULT NULL             COMMENT '促销敏感度：高/中/低',
    last_purchase_date   DATE          DEFAULT NULL             COMMENT '最近购买日期',
    updated_at           DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (profile_id),
    UNIQUE KEY uk_customer (customer_id),
    KEY idx_value_level (value_level),
    KEY idx_last_purchase (last_purchase_date),
    CONSTRAINT fk_profile_customer
        FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='用户画像表 — RFM分析结果与消费标签';

-- ────────────────────────────────────────────────────────────
-- 7. 销售预测表（sales_forecast）
--    用途：存储预测模型输出的未来销量预测
-- ────────────────────────────────────────────────────────────
CREATE TABLE sales_forecast (
    forecast_id      BIGINT        NOT NULL AUTO_INCREMENT  COMMENT '预测ID',
    product_id       INT           DEFAULT NULL             COMMENT '商品ID，NULL=全品类预测',
    forecast_date    DATE          NOT NULL                 COMMENT '预测日期',
    predicted_quantity INT         NOT NULL                 COMMENT '预测销量',
    confidence_lower DECIMAL(10,2) DEFAULT NULL             COMMENT '95%置信区间下限',
    confidence_upper DECIMAL(10,2) DEFAULT NULL             COMMENT '95%置信区间上限',
    model_type       VARCHAR(30)   NOT NULL                 COMMENT '模型类型：linear/arima/moving_avg',
    mape             DECIMAL(8,2)  DEFAULT NULL             COMMENT '历史拟合MAPE值(%)',
    created_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '预测生成时间',
    PRIMARY KEY (forecast_id),
    KEY idx_product_date (product_id, forecast_date),
    KEY idx_forecast_date (forecast_date),
    KEY idx_model_type (model_type),
    CONSTRAINT fk_forecast_product
        FOREIGN KEY (product_id) REFERENCES product(product_id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='销售预测表 — 存储模型预测结果';

-- ────────────────────────────────────────────────────────────
-- 8. 预警规则表（alert_rule）
--    用途：定义异常检测的触发规则
-- ────────────────────────────────────────────────────────────
CREATE TABLE alert_rule (
    rule_id     INT          NOT NULL AUTO_INCREMENT  COMMENT '规则ID',
    rule_name   VARCHAR(100) NOT NULL                 COMMENT '规则名称',
    rule_type   VARCHAR(30)  NOT NULL                 COMMENT '规则类型：sales_drop/stock_low/return_spike',
    threshold   DECIMAL(5,2) NOT NULL                 COMMENT '触发阈值（百分比，如-30.00=下降30%）',
    product_id  INT          DEFAULT NULL             COMMENT '适用商品ID，NULL=全局规则',
    is_enabled  TINYINT      NOT NULL DEFAULT 1       COMMENT '状态：1=启用 0=禁用',
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (rule_id),
    KEY idx_rule_type (rule_type),
    KEY idx_enabled (is_enabled),
    KEY idx_rule_product (product_id),
    CONSTRAINT fk_alert_product
        FOREIGN KEY (product_id) REFERENCES product(product_id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='预警规则表 — 定义异常检测触发条件';

-- ────────────────────────────────────────────────────────────
-- 9. 预警日志表（alert_log）
--    用途：记录每次预警触发的详情和处理状态
-- ────────────────────────────────────────────────────────────
CREATE TABLE alert_log (
    log_id         BIGINT        NOT NULL AUTO_INCREMENT  COMMENT '日志ID',
    rule_id        INT           NOT NULL                 COMMENT '关联规则ID',
    trigger_time   DATETIME      NOT NULL                 COMMENT '预警触发时间',
    alert_content  VARCHAR(500)  NOT NULL                 COMMENT '预警详情描述',
    anomaly_value  DECIMAL(12,2) DEFAULT NULL             COMMENT '异常指标值',
    baseline_value DECIMAL(12,2) DEFAULT NULL             COMMENT '正常基线值',
    severity       VARCHAR(10)   NOT NULL DEFAULT 'yellow' COMMENT '严重程度：red/orange/yellow',
    status         VARCHAR(20)   NOT NULL DEFAULT 'pending' COMMENT '状态：pending/resolved/ignored',
    resolved_by    INT           DEFAULT NULL             COMMENT '处理人 user_id',
    resolved_at    DATETIME      DEFAULT NULL             COMMENT '处理时间',
    PRIMARY KEY (log_id),
    KEY idx_rule (rule_id),
    KEY idx_trigger_time (trigger_time),
    KEY idx_status (status),
    KEY idx_severity (severity),
    CONSTRAINT fk_log_rule
        FOREIGN KEY (rule_id) REFERENCES alert_rule(rule_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_log_resolver
        FOREIGN KEY (resolved_by) REFERENCES user(user_id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='预警日志表 — 记录预警触发与处理历史';

-- ────────────────────────────────────────────────────────────
-- 10. 营销活动表（campaign）
--     用途：记录营销活动信息，用于营销效果评估
-- ────────────────────────────────────────────────────────────
CREATE TABLE campaign (
    campaign_id         INT          NOT NULL AUTO_INCREMENT  COMMENT '活动ID',
    campaign_name       VARCHAR(100) NOT NULL                 COMMENT '活动名称',
    start_date          DATE         NOT NULL                 COMMENT '活动开始日期',
    end_date            DATE         NOT NULL                 COMMENT '活动结束日期',
    discount_rate       DECIMAL(3,2) DEFAULT NULL             COMMENT '折扣力度（0.85=85折）',
    affected_product_ids TEXT        DEFAULT NULL             COMMENT '参与商品ID列表（JSON数组）',
    campaign_cost       DECIMAL(10,2) DEFAULT NULL            COMMENT '活动成本（元）',
    status              VARCHAR(20)  NOT NULL DEFAULT 'planned' COMMENT '状态：planned/active/ended',
    created_at          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (campaign_id),
    KEY idx_status (status),
    KEY idx_date_range (start_date, end_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='营销活动表 — 记录促销活动与效果评估';

-- ============================================================
-- 第2部分：种子数据
-- ============================================================

-- ────────────────────────────────────────────────────────────
-- 2.1 系统用户（密码均为对应用户名+123）
--     admin    / admin123    → 系统管理员
--     manager  / manager123  → 电商运营经理
--     analyst  / test123     → 数据分析师
--     viewer   / test123     → 高层管理者（只读）
-- ────────────────────────────────────────────────────────────
INSERT INTO user (username, password, role, status) VALUES
('admin',   '$2b$12$lygJ3ILBsxCwTyuGtiPjCOHg61kL5IBmrYHVNtvO385sAYk/p00bu', 'admin',   1),
('manager', '$2b$12$xv9KFG1TzyLMJc5AL.9lJuWywrS8mxVm1BEQOeFBlMRtBiVpHO/Pi', 'manager', 1);

-- ────────────────────────────────────────────────────────────
-- 2.2 品类层级（4大类 → 12子类）
-- ────────────────────────────────────────────────────────────
-- 一级类目（level=1, parent_id=NULL）
INSERT INTO category (category_id, category_name, parent_id, level) VALUES
(1,  '服装鞋包',   NULL, 1),
(2,  '数码电子',   NULL, 1),
(3,  '食品饮料',   NULL, 1),
(4,  '美妆个护',   NULL, 1),
(5,  '家居生活',   NULL, 1);

-- 二级类目（level=2）
-- 服装鞋包
INSERT INTO category (category_id, category_name, parent_id, level) VALUES
(11, '女装',   1, 2),
(12, '男装',   1, 2),
(13, '鞋靴',   1, 2);

-- 数码电子
INSERT INTO category (category_id, category_name, parent_id, level) VALUES
(21, '手机通讯', 2, 2),
(22, '电脑办公', 2, 2),
(23, '智能穿戴', 2, 2);

-- 食品饮料
INSERT INTO category (category_id, category_name, parent_id, level) VALUES
(31, '休闲零食', 3, 2),
(32, '饮料冲调', 3, 2);

-- 美妆个护
INSERT INTO category (category_id, category_name, parent_id, level) VALUES
(41, '护肤',     4, 2),
(42, '彩妆',     4, 2);

-- 家居生活
INSERT INTO category (category_id, category_name, parent_id, level) VALUES
(51, '家纺',     5, 2),
(52, '厨具',     5, 2);

-- ────────────────────────────────────────────────────────────
-- 2.3 示例商品（每个二级品类下 2-3 个 SKU）
-- ────────────────────────────────────────────────────────────
INSERT INTO product (product_id, product_name, sku_code, category_id, price, cost, stock_quantity, status) VALUES
-- 女装 (cat 11)
(1,  '纯棉简约T恤女',        'WM-TEE-001',   11, 79.00,  35.00,  80,  1),
(2,  '法式碎花连衣裙',        'WM-DRS-002',   11, 259.00, 120.00, 120, 1),
(3,  '高腰阔腿牛仔裤女',      'WM-JNS-003',   11, 189.00, 85.00,  55,  1),
-- 男装 (cat 12)
(4,  '商务免烫衬衫男',        'MN-SHT-001',   12, 199.00, 95.00,  90,  1),
(5,  '轻薄羽绒服男',          'MN-JKT-002',   12, 499.00, 280.00, 150, 1),
-- 鞋靴 (cat 13)
(6,  '复古跑步鞋',            'SH-RUN-001',   13, 329.00, 160.00, 200, 1),
(7,  '真皮商务皮鞋男',        'SH-BUS-002',   13, 459.00, 230.00, 45,  1),
-- 手机通讯 (cat 21)
(8,  '无线蓝牙耳机 Pro',      'PH-BUD-001',   21, 299.00, 150.00, 65,  1),
(9,  '快充数据线套装',        'PH-CBL-002',   21, 39.00,  12.00,  140, 1),
(10, '手机防窥钢化膜',        'PH-FLM-003',   21, 29.00,  8.00,   70,  1),
-- 电脑办公 (cat 22)
(11, '机械键盘青轴87键',      'PC-KBD-001',   22, 259.00, 130.00, 110, 1),
(12, '无线静音鼠标',          'PC-MOU-002',   22, 99.00,  45.00,  95,  1),
-- 智能穿戴 (cat 23)
(13, '智能手环NFC版',         'WL-BND-001',   23, 199.00, 90.00,  60,  1),
-- 休闲零食 (cat 31)
(14, '每日坚果礼盒750g',      'FD-NUT-001',   31, 89.00,  50.00,  85,  1),
(15, '抹茶夹心饼干240g',      'FD-CKY-002',   31, 29.90,  14.00,  130, 1),
(16, '手撕牛肉干五香味200g',  'FD-JKY-003',   31, 59.90,  32.00,  35,  1),
-- 饮料冲调 (cat 32)
(17, '冷萃咖啡液12颗装',      'FD-COF-001',   32, 69.00,  35.00,  160, 1),
(18, '冻干柠檬片罐装',        'FD-LEM-002',   32, 25.00,  10.00,  75,  1),
-- 护肤 (cat 41)
(19, '氨基酸洁面乳120g',      'BC-FAC-001',   41, 89.00,  38.00,  40,  1),
(20, '玻尿酸补水面膜5片装',   'BC-MSK-002',   41, 59.00,  22.00,  105, 1),
-- 彩妆 (cat 42)
(21, '雾面哑光口红',          'BC-LIP-001',   42, 99.00,  40.00,  145, 1),
-- 家纺 (cat 51)
(22, '纯棉四件套1.8m床',      'HM-BED-001',   51, 399.00, 200.00, 125, 1),
-- 厨具 (cat 52)
(23, '不粘锅三件套',          'HM-COK-001',   52, 299.00, 150.00, 50,  1),
(24, '保温杯500ml不锈钢',     'HM-CUP-002',   52, 79.00,  32.00,  115, 1);

-- ────────────────────────────────────────────────────────────
-- 2.4 示例客户（匿名化，共20位）
-- ────────────────────────────────────────────────────────────
INSERT INTO customer (customer_id, customer_name, gender, age_group, region, register_date) VALUES
(1,  '张***', 'F', '25-34', '广东',   '2025-01-15'),
(2,  '李***', 'M', '25-34', '广东',   '2025-02-20'),
(3,  '王***', 'F', '35-44', '北京',   '2025-01-08'),
(4,  '赵***', 'M', '18-24', '上海',   '2025-03-10'),
(5,  '钱***', 'F', '35-44', '浙江',   '2025-01-22'),
(6,  '孙***', 'M', '45+',   '江苏',   '2024-11-05'),
(7,  '周***', 'F', '25-34', '四川',   '2025-04-01'),
(8,  '吴***', 'M', '18-24', '湖北',   '2025-05-15'),
(9,  '郑***', 'F', '25-34', '广东',   '2025-02-14'),
(10, '冯***', 'M', '35-44', '山东',   '2024-12-20'),
(11, '陈***', 'F', '18-24', '福建',   '2025-06-01'),
(12, '褚***', 'M', '45+',   '辽宁',   '2024-09-10'),
(13, '卫***', 'F', '25-34', '河南',   '2025-03-18'),
(14, '蒋***', 'M', '35-44', '湖南',   '2025-01-30'),
(15, '沈***', 'F', '45+',   '安徽',   '2024-10-25'),
(16, '韩***', 'M', '25-34', '广东',   '2025-04-12'),
(17, '杨***', 'F', '18-24', '重庆',   '2025-05-20'),
(18, '朱***', 'M', '25-34', '陕西',   '2025-02-28'),
(19, '秦***', 'F', '35-44', '江西',   '2024-11-15'),
(20, '尤***', 'M', '18-24', '广西',   '2025-06-05');

-- ────────────────────────────────────────────────────────────
-- 2.5 示例销售记录（2025-01 ~ 2026-05，覆盖多品类/地区/渠道）
--    共 163 条销售记录，便于立即跑通查询和预测
-- ────────────────────────────────────────────────────────────
INSERT INTO sales_record (product_id, customer_id, quantity, unit_price, total_amount, order_date, region, channel) VALUES
-- === 2025年数据 ===
-- 1月
(1,  1,  2, 79.00,  158.00,  '2025-01-05 10:30:00', '广东', 'PC'),
(4,  2,  1, 199.00, 199.00,  '2025-01-06 14:20:00', '广东', 'Mobile'),
(8,  3,  1, 299.00, 299.00,  '2025-01-08 09:15:00', '北京', 'PC'),
(14, 5,  3, 89.00,  267.00,  '2025-01-10 16:00:00', '浙江', 'Miniprogram'),
(19, 9,  1, 89.00,  89.00,   '2025-01-12 11:45:00', '广东', 'Mobile'),
(11, 10, 1, 259.00, 259.00,  '2025-01-15 20:30:00', '山东', 'PC'),
(2,  1,  1, 259.00, 259.00,  '2025-01-18 13:10:00', '广东', 'PC'),
(6,  12, 1, 329.00, 329.00,  '2025-01-20 10:00:00', '辽宁', 'Mobile'),
(15, 7,  4, 29.90,  119.60,  '2025-01-22 17:30:00', '四川', 'Miniprogram'),
(21, 13, 2, 99.00,  198.00,  '2025-01-25 12:00:00', '河南', 'PC'),
-- 2月
(3,  4,  1, 189.00, 189.00,  '2025-02-03 15:45:00', '上海', 'Mobile'),
(5,  6,  1, 499.00, 499.00,  '2025-02-05 09:30:00', '江苏', 'PC'),
(9,  11, 3, 39.00,  117.00,  '2025-02-08 14:00:00', '福建', 'Mobile'),
(16, 14, 2, 59.90,  119.80,  '2025-02-10 18:20:00', '湖南', 'Miniprogram'),
(22, 15, 1, 399.00, 399.00,  '2025-02-14 10:15:00', '安徽', 'PC'),
(17, 8,  2, 69.00,  138.00,  '2025-02-18 11:30:00', '湖北', 'Mobile'),
(13, 17, 1, 199.00, 199.00,  '2025-02-20 16:00:00', '重庆', 'PC'),
(1,  3,  1, 79.00,  79.00,   '2025-02-22 20:00:00', '北京', 'Miniprogram'),
(24, 16, 2, 79.00,  158.00,  '2025-02-25 13:45:00', '广东', 'Mobile'),
(20, 9,  1, 59.00,  59.00,   '2025-02-28 10:30:00', '广东', 'PC'),
-- 3月
(7,  18, 1, 459.00, 459.00,  '2025-03-05 09:00:00', '陕西', 'PC'),
(10, 19, 5, 29.00,  145.00,  '2025-03-08 14:30:00', '江西', 'Mobile'),
(18, 20, 3, 25.00,  75.00,   '2025-03-12 17:00:00', '广西', 'Miniprogram'),
(23, 2,  1, 299.00, 299.00,  '2025-03-15 11:20:00', '广东', 'PC'),
(12, 5,  1, 99.00,  99.00,   '2025-03-18 15:00:00', '浙江', 'Mobile'),
(4,  10, 1, 199.00, 199.00,  '2025-03-20 10:45:00', '山东', 'PC'),
(8,  7,  1, 299.00, 299.00,  '2025-03-22 12:30:00', '四川', 'Miniprogram'),
(14, 4,  5, 89.00,  445.00,  '2025-03-25 16:15:00', '上海', 'Mobile'),
(19, 1,  2, 89.00,  178.00,  '2025-03-28 20:00:00', '广东', 'PC'),
-- 4月
(2,  6,  1, 259.00, 259.00,  '2025-04-02 10:00:00', '江苏', 'PC'),
(11, 13, 1, 259.00, 259.00,  '2025-04-05 14:30:00', '河南', 'Mobile'),
(15, 16, 6, 29.90,  179.40,  '2025-04-08 18:00:00', '广东', 'Miniprogram'),
(5,  12, 1, 499.00, 499.00,  '2025-04-10 09:45:00', '辽宁', 'PC'),
(22, 17, 1, 399.00, 399.00,  '2025-04-12 13:00:00', '重庆', 'PC'),
(3,  9,  1, 189.00, 189.00,  '2025-04-15 17:30:00', '广东', 'Mobile'),
(6,  3,  1, 329.00, 329.00,  '2025-04-18 11:00:00', '北京', 'PC'),
(21, 11, 3, 99.00,  297.00,  '2025-04-20 15:45:00', '福建', 'Miniprogram'),
(9,  14, 4, 39.00,  156.00,  '2025-04-22 10:20:00', '湖南', 'Mobile'),
(17, 5,  1, 69.00,  69.00,   '2025-04-25 12:00:00', '浙江', 'PC'),
-- 5月
(1,  8,  3, 79.00,  237.00,  '2025-05-03 09:30:00', '湖北', 'Mobile'),
(13, 2,  1, 199.00, 199.00,  '2025-05-06 14:00:00', '广东', 'PC'),
(24, 20, 1, 79.00,  79.00,   '2025-05-08 16:45:00', '广西', 'Miniprogram'),
(7,  19, 1, 459.00, 459.00,  '2025-05-10 10:00:00', '江西', 'PC'),
(16, 15, 2, 59.90,  119.80,  '2025-05-12 18:30:00', '安徽', 'Mobile'),
(10, 18, 8, 29.00,  232.00,  '2025-05-15 12:15:00', '陕西', 'PC'),
(14, 7,  4, 89.00,  356.00,  '2025-05-18 17:00:00', '四川', 'Miniprogram'),
(20, 4,  2, 59.00,  118.00,  '2025-05-20 11:30:00', '上海', 'Mobile'),
(12, 6,  1, 99.00,  99.00,   '2025-05-22 15:00:00', '江苏', 'PC'),
(18, 10, 5, 25.00,  125.00,  '2025-05-25 09:00:00', '山东', 'Miniprogram'),
-- 6月（618大促月，销量明显上涨）
(1,  1,  5, 69.30,  346.50,  '2025-06-01 00:30:00', '广东', 'PC'),       -- 618开门红
(8,  3,  2, 269.10, 538.20,  '2025-06-01 10:15:00', '北京', 'Mobile'),
(14, 5,  6, 80.10,  480.60,  '2025-06-03 14:30:00', '浙江', 'Miniprogram'),
(19, 9,  3, 80.10,  240.30,  '2025-06-05 16:00:00', '广东', 'PC'),
(2,  7,  2, 233.10, 466.20,  '2025-06-08 11:20:00', '四川', 'Mobile'),
(11, 13, 2, 233.10, 466.20,  '2025-06-10 09:45:00', '河南', 'PC'),
(4,  2,  1, 179.10, 179.10,  '2025-06-12 20:00:00', '广东', 'Miniprogram'),
(21, 11, 4, 89.10,  356.40,  '2025-06-15 13:00:00', '福建', 'PC'),
(5,  12, 1, 449.10, 449.10,  '2025-06-18 10:30:00', '辽宁', 'Mobile'),   -- 618当天
(6,  17, 1, 296.10, 296.10,  '2025-06-18 15:00:00', '重庆', 'PC'),
(15, 14, 8, 26.91,  215.28,  '2025-06-20 12:00:00', '湖南', 'Miniprogram'),
(22, 4,  1, 359.10, 359.10,  '2025-06-22 17:45:00', '上海', 'PC'),
(3,  6,  2, 170.10, 340.20,  '2025-06-25 10:00:00', '江苏', 'Mobile'),
(24, 9,  3, 71.10,  213.30,  '2025-06-28 14:20:00', '广东', 'Miniprogram'),
-- 7月（618后回落，正常水平）
(1,  4,  1, 79.00,  79.00,   '2025-07-05 10:00:00', '上海', 'Mobile'),
(7,  18, 1, 459.00, 459.00,  '2025-07-10 15:30:00', '陕西', 'PC'),
(14, 1,  2, 89.00,  178.00,  '2025-07-15 12:00:00', '广东', 'Miniprogram'),
(17, 8,  1, 69.00,  69.00,   '2025-07-20 09:00:00', '湖北', 'Mobile'),
(9,  2,  5, 39.00,  195.00,  '2025-07-25 16:00:00', '广东', 'PC'),
-- 8月
(2,  3,  1, 259.00, 259.00,  '2025-08-03 11:30:00', '北京', 'PC'),
(12, 5,  1, 99.00,  99.00,   '2025-08-08 14:00:00', '浙江', 'Mobile'),
(16, 15, 3, 59.90,  179.70,  '2025-08-12 17:15:00', '安徽', 'Miniprogram'),
(23, 10, 1, 299.00, 299.00,  '2025-08-18 10:45:00', '山东', 'PC'),
(13, 20, 1, 199.00, 199.00,  '2025-08-22 13:00:00', '广西', 'Mobile'),
(19, 7,  2, 89.00,  178.00,  '2025-08-28 20:30:00', '四川', 'PC'),
-- 9月（开学季，数码类销量上涨）
(8,  17, 3, 284.05, 852.15,  '2025-09-01 09:00:00', '重庆', 'PC'),       -- 开学季促销
(11, 2,  2, 246.05, 492.10,  '2025-09-03 15:00:00', '广东', 'PC'),
(12, 4,  1, 94.05,  94.05,   '2025-09-05 11:30:00', '上海', 'Mobile'),
(9,  11, 6, 37.05,  222.30,  '2025-09-08 14:00:00', '福建', 'Miniprogram'),
(1,  1,  1, 79.00,  79.00,   '2025-09-12 10:00:00', '广东', 'PC'),
(5,  6,  1, 499.00, 499.00,  '2025-09-18 16:30:00', '江苏', 'Mobile'),
(21, 13, 2, 99.00,  198.00,  '2025-09-22 12:45:00', '河南', 'PC'),
(18, 19, 4, 25.00,  100.00,  '2025-09-28 18:00:00', '江西', 'Miniprogram'),
-- 10月（国庆假期，旅游类+零食上涨）
(14, 5,  4, 84.55,  338.20,  '2025-10-01 10:00:00', '浙江', 'Miniprogram'), -- 国庆促销
(15, 14, 5, 28.41,  142.05,  '2025-10-02 14:00:00', '湖南', 'PC'),
(6,  9,  1, 312.55, 312.55,  '2025-10-03 16:30:00', '广东', 'Mobile'),
(24, 8,  2, 75.05,  150.10,  '2025-10-05 11:00:00', '湖北', 'Miniprogram'),
(3,  4,  1, 189.00, 189.00,  '2025-10-10 09:30:00', '上海', 'PC'),
(20, 7,  2, 59.00,  118.00,  '2025-10-15 15:00:00', '四川', 'Mobile'),
(10, 2,  3, 29.00,  87.00,   '2025-10-20 12:30:00', '广东', 'PC'),
-- 11月（双11预热+大促，全年最高峰）
(1,  1,  8, 59.25,  474.00,  '2025-11-01 00:15:00', '广东', 'PC'),       -- 双11预售
(8,  3,  3, 224.25, 672.75,  '2025-11-03 10:00:00', '北京', 'Mobile'),
(14, 5,  10, 66.75, 667.50,  '2025-11-05 14:30:00', '浙江', 'Miniprogram'),
(19, 9,  4, 66.75,  267.00,  '2025-11-08 16:00:00', '广东', 'PC'),
(2,  7,  3, 194.25, 582.75,  '2025-11-10 20:00:00', '四川', 'Mobile'),    -- 双11前夜
(4,  2,  2, 149.25, 298.50,  '2025-11-11 00:10:00', '广东', 'PC'),        -- 双11当天
(11, 13, 3, 194.25, 582.75,  '2025-11-11 09:00:00', '河南', 'PC'),
(21, 11, 6, 74.25,  445.50,  '2025-11-11 14:00:00', '福建', 'Miniprogram'),
(5,  12, 2, 374.25, 748.50,  '2025-11-11 18:30:00', '辽宁', 'Mobile'),
(6,  17, 2, 246.75, 493.50,  '2025-11-11 22:00:00', '重庆', 'PC'),
(15, 14, 12,22.43,  269.10,  '2025-11-12 10:00:00', '湖南', 'Miniprogram'),
(22, 4,  2, 299.25, 598.50,  '2025-11-15 12:00:00', '上海', 'PC'),
(3,  6,  1, 189.00, 189.00,  '2025-11-20 15:00:00', '江苏', 'Mobile'),
(24, 9,  5, 59.25,  296.25,  '2025-11-25 17:00:00', '广东', 'Miniprogram'),
-- 12月（双12 + 年末清仓）
(1,  3,  3, 71.10,  213.30,  '2025-12-01 10:00:00', '北京', 'PC'),
(14, 1,  4, 80.10,  320.40,  '2025-12-05 14:00:00', '广东', 'Miniprogram'),
(7,  18, 1, 459.00, 459.00,  '2025-12-10 11:30:00', '陕西', 'Mobile'),
(5,  12, 1, 449.10, 449.10,  '2025-12-12 09:00:00', '辽宁', 'PC'),       -- 双12
(9,  10, 8, 35.10,  280.80,  '2025-12-12 15:00:00', '山东', 'Mobile'),
(17, 6,  2, 62.10,  124.20,  '2025-12-15 12:30:00', '江苏', 'PC'),
(20, 9,  3, 53.10,  159.30,  '2025-12-18 16:00:00', '广东', 'Miniprogram'),
(2,  4,  1, 259.00, 259.00,  '2025-12-22 10:00:00', '上海', 'Mobile'),
(13, 17, 2, 179.10, 358.20,  '2025-12-25 14:30:00', '重庆', 'PC'),
(21, 15, 4, 89.10,  356.40,  '2025-12-28 18:00:00', '安徽', 'Miniprogram'),
(14, 5,  3, 89.00,  267.00,  '2025-12-31 20:00:00', '浙江', 'PC'),

-- === 2026年数据 ===
-- 1月（元旦 + 年货节）
(14, 7,  6, 80.10,  480.60,  '2026-01-03 10:00:00', '四川', 'Miniprogram'),
(16, 14, 4, 53.91,  215.64,  '2026-01-06 14:30:00', '湖南', 'PC'),
(5,  2,  1, 499.00, 499.00,  '2026-01-10 16:00:00', '广东', 'Mobile'),
(23, 6,  1, 284.05, 284.05,  '2026-01-15 11:00:00', '江苏', 'PC'),
(1,  9,  2, 79.00,  158.00,  '2026-01-20 13:45:00', '广东', 'Miniprogram'),
(8,  3,  1, 299.00, 299.00,  '2026-01-25 15:00:00', '北京', 'PC'),
-- 2月（春节 + 情人节）
(21, 13, 6, 89.10,  534.60,  '2026-02-01 10:00:00', '河南', 'PC'),       -- 春节前
(14, 1,  8, 80.10,  640.80,  '2026-02-05 14:00:00', '广东', 'Miniprogram'), -- 年货
(2,  4,  1, 233.10, 233.10,  '2026-02-10 11:30:00', '上海', 'Mobile'),   -- 情人节
(19, 11, 2, 80.10,  160.20,  '2026-02-14 09:00:00', '福建', 'PC'),
(5,  12, 1, 499.00, 499.00,  '2026-02-18 16:00:00', '辽宁', 'Mobile'),
(10, 17, 3, 29.00,  87.00,   '2026-02-22 12:00:00', '重庆', 'Miniprogram'),
-- 3月（春节后恢复，正常销售）
(1,  1,  2, 79.00,  158.00,  '2026-03-05 10:30:00', '广东', 'PC'),
(12, 5,  1, 99.00,  99.00,   '2026-03-10 15:00:00', '浙江', 'Mobile'),
(7,  18, 1, 459.00, 459.00,  '2026-03-15 11:45:00', '陕西', 'PC'),
(18, 8,  6, 25.00,  150.00,  '2026-03-20 17:00:00', '湖北', 'Miniprogram'),
(15, 20, 3, 29.90,  89.70,   '2026-03-25 14:30:00', '广西', 'Mobile'),
(22, 15, 1, 399.00, 399.00,  '2026-03-28 10:00:00', '安徽', 'PC'),
-- 4月
(3,  4,  1, 189.00, 189.00,  '2026-04-03 16:30:00', '上海', 'PC'),
(11, 2,  1, 259.00, 259.00,  '2026-04-08 10:00:00', '广东', 'Mobile'),
(24, 6,  2, 79.00,  158.00,  '2026-04-12 12:15:00', '江苏', 'Miniprogram'),
(9,  10, 4, 39.00,  156.00,  '2026-04-18 09:30:00', '山东', 'PC'),
(6,  17, 1, 329.00, 329.00,  '2026-04-22 14:00:00', '重庆', 'Mobile'),
(16, 13, 2, 59.90,  119.80,  '2026-04-28 18:00:00', '河南', 'Miniprogram'),
-- 5月（520 + 618预热）
(2,  7,  1, 246.05, 246.05,  '2026-05-01 10:00:00', '四川', 'PC'),
(19, 1,  3, 80.10,  240.30,  '2026-05-05 14:30:00', '广东', 'Mobile'),
(21, 9,  4, 89.10,  356.40,  '2026-05-10 11:00:00', '广东', 'Miniprogram'),
(14, 5,  4, 84.55,  338.20,  '2026-05-15 16:45:00', '浙江', 'PC'),
(4,  3,  1, 179.10, 179.10,  '2026-05-20 09:00:00', '北京', 'Mobile'),   -- 520
(8,  11, 2, 269.10, 538.20,  '2026-05-25 12:30:00', '福建', 'PC'),
(13, 4,  1, 189.05, 189.05,  '2026-05-28 15:00:00', '上海', 'Miniprogram'),
(20, 16, 1, 56.05,  56.05,   '2026-05-30 10:00:00', '广东', 'Mobile'),

-- === 最近一周数据（2026-06-01 ~ 2026-06-07，用于预警测试） ===
(1,  1,  3, 79.00,  237.00,  '2026-06-01 09:30:00', '广东', 'PC'),
(14, 5,  5, 89.00,  445.00,  '2026-06-01 14:00:00', '浙江', 'Miniprogram'),
(8,  3,  1, 299.00, 299.00,  '2026-06-02 10:15:00', '北京', 'Mobile'),
(21, 9,  2, 99.00,  198.00,  '2026-06-02 16:30:00', '广东', 'PC'),
(19, 7,  1, 89.00,  89.00,   '2026-06-03 11:00:00', '四川', 'Mobile'),
(11, 2,  1, 259.00, 259.00,  '2026-06-03 15:45:00', '广东', 'PC'),
(5,  12, 1, 499.00, 499.00,  '2026-06-04 09:00:00', '辽宁', 'Mobile'),
(6,  17, 1, 329.00, 329.00,  '2026-06-04 14:30:00', '重庆', 'PC'),
(15, 13, 8, 29.90,  239.20,  '2026-06-05 12:00:00', '河南', 'Miniprogram'),
(2,  4,  1, 259.00, 259.00,  '2026-06-05 17:00:00', '上海', 'Mobile'),
(3,  1,  1, 189.00, 189.00,  '2026-06-05 20:00:00', '广东', 'PC'),
(16, 10, 2, 59.90,  119.80,  '2026-06-06 10:30:00', '山东', 'Miniprogram'),
(22, 15, 1, 399.00, 399.00,  '2026-06-06 14:00:00', '安徽', 'PC'),
(24, 8,  1, 79.00,  79.00,   '2026-06-06 16:15:00', '湖北', 'Mobile'),
(20, 9,  3, 59.00,  177.00,  '2026-06-07 10:00:00', '广东', 'Miniprogram'),
(7,  18, 1, 459.00, 459.00,  '2026-06-07 11:30:00', '陕西', 'PC'),
(4,  6,  2, 199.00, 398.00,  '2026-06-07 15:00:00', '江苏', 'Mobile');

-- ────────────────────────────────────────────────────────────
-- 2.6 用户画像（部分客户的RFM计算结果）
-- ────────────────────────────────────────────────────────────
INSERT INTO user_profile (customer_id, value_level, avg_order_price, purchase_frequency, preferred_category, promo_sensitivity, last_purchase_date) VALUES
(1,  '高价值', 280.00, 3.2, '女装,美妆',    '高', '2026-06-05'),
(2,  '高价值', 320.00, 2.8, '男装,数码',    '中', '2026-06-03'),
(3,  '中价值', 250.00, 2.0, '数码,食品',    '低', '2026-06-02'),
(4,  '中价值', 220.00, 2.5, '女装,鞋靴',    '高', '2026-06-05'),
(5,  '高价值', 350.00, 3.5, '食品,家居',    '高', '2026-06-01'),
(6,  '中价值', 300.00, 1.8, '男装,家居',    '中', '2026-06-07'),
(7,  '中价值', 200.00, 2.3, '美妆,食品',    '高', '2026-06-03'),
(8,  '低价值', 80.00,  0.8, '饮料,零食',    '中', '2026-06-06'),
(9,  '高价值', 290.00, 3.0, '美妆,女装',    '高', '2026-06-07'),
(10, '低价值', 100.00, 1.2, '数码配件,厨具', '低', '2026-06-06'),
(11, '中价值', 180.00, 2.0, '数码,彩妆',    '高', '2026-05-25'),
(12, '高价值', 450.00, 2.5, '男装,数码',    '低', '2026-06-04'),
(13, '中价值', 150.00, 2.2, '彩妆,女装',    '高', '2026-06-05'),
(14, '低价值', 90.00,  1.2, '零食,饮料',    '中', '2026-06-01'),
(15, '中价值', 260.00, 2.0, '家居,厨具',    '低', '2026-06-06'),
(16, '中价值', 180.00, 1.8, '手机配件,零食', '中', '2026-05-30'),
(17, '中价值', 280.00, 2.2, '数码,鞋靴',    '高', '2026-06-04'),
(18, '低价值', 150.00, 1.5, '男装,鞋靴',    '低', '2026-06-07'),
(19, '低价值', 110.00, 1.2, '护肤,零食',    '中', '2025-09-28'),
(20, '低价值', 85.00,  1.0, '饮料,数码配件', '高', '2026-03-25');

-- ────────────────────────────────────────────────────────────
-- 2.7 默认预警规则（3条）
-- ────────────────────────────────────────────────────────────
INSERT INTO alert_rule (rule_id, rule_name, rule_type, threshold, product_id, is_enabled) VALUES
(1, '全品类销售额突降告警',  'sales_drop',  -30.00, NULL, 1),   -- 较7日均线下降30%+
(2, '库存触及安全警戒线',    'stock_low',   20.00,  NULL, 1),   -- 库存低于安全线20%
(3, '退货率异常飙升告警',    'return_spike', 50.00, NULL, 1); -- 退货率较30日均值上升50%+

-- ────────────────────────────────────────────────────────────
-- 2.8 默认预警日志（示例，均已处理）
-- ────────────────────────────────────────────────────────────
INSERT INTO alert_log (log_id, rule_id, trigger_time, alert_content, anomaly_value, baseline_value, severity, status, resolved_by, resolved_at) VALUES
(1, 1, '2026-06-07 10:00:00', '全品类销售额较7日均线下降32.5%', -32.50, 45000.00, 'orange', 'resolved', 1, '2026-06-07 11:00:00'),
(2, 2, '2026-06-07 11:00:00', 'SKU-003 库存低于安全线18%',      18.00, 150.00,   'yellow', 'resolved', 1, '2026-06-07 12:00:00');

-- ============================================================
-- 第3部分：验证
-- ============================================================

-- 查看所有表
SHOW TABLES;

-- 验证各表记录数
SELECT 'user'            AS table_name, COUNT(*) AS row_count FROM user
UNION ALL SELECT 'category'  , COUNT(*) FROM category
UNION ALL SELECT 'product'   , COUNT(*) FROM product
UNION ALL SELECT 'customer'  , COUNT(*) FROM customer
UNION ALL SELECT 'sales_record', COUNT(*) FROM sales_record
UNION ALL SELECT 'user_profile', COUNT(*) FROM user_profile
UNION ALL SELECT 'alert_rule' , COUNT(*) FROM alert_rule
UNION ALL SELECT 'alert_log'  , COUNT(*) FROM alert_log
UNION ALL SELECT 'campaign'   , COUNT(*) FROM campaign;

-- 检查品类层级结构
SELECT
    CONCAT(REPEAT('  ', c1.level - 1), c1.category_name) AS category_tree,
    c1.level,
    c1.category_id
FROM category c1
ORDER BY c1.category_id;

-- ============================================================
-- EOF
-- ============================================================
