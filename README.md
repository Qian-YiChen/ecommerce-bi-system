# 基于AI智能的电商商品销售分析与预测系统

> 中山大学《软件工程》课程期末实践 — 选题三(1)
> 团队：严辰乐（组长）、苏文韬、姚凯曦、薛淞、闫维岳
> 版本：v1.0 | 日期：2026-06-20

## 项目简介

面向电商企业内部的商业智能（BI）分析决策平台，利用机器学习对销售数据进行深度挖掘，实现销售趋势预测、库存优化、用户画像构建和异常检测预警。

## 技术栈

| 层 | 技术 | 版本 |
|----|------|------|
| 前端 | Vue 3 + Element Plus + ECharts + Vite | Vue≥3.3, Vite 8 |
| 后端 | Python Flask + PyJWT + bcrypt | Flask 3.x |
| 数据库 | MySQL + PyMySQL | MySQL 8.4, PyMySQL 2.2 |
| ML | scikit-learn + pandas + numpy | ≥1.3 |
| 定时 | APScheduler | ≥3.10 |
| 部署 | Docker Compose（预留） | — |

## 项目结构

```
工程/
├── backend/                    # Python Flask 后端（严辰乐 + 苏文韬）
│   ├── app.py                  # 主入口（24条路由，APScheduler）
│   ├── config.py               # 配置中心（JWT/MySQL/CORS）
│   ├── scheduler.py            # 定时预警调度（每小时扫描）
│   ├── requirements.txt        # Python 依赖
│   ├── auth/                   # JWT 认证服务
│   ├── middleware/              # JWT + RBAC 中间件
│   ├── models/                 # 数据模型（User）
│   ├── routes/                 # API 路由（7个模块，24条路由）
│   │   ├── auth_routes.py      # 认证：登录/注册/当前用户
│   │   ├── data_routes.py      # 数据查询：多维度销售分析
│   │   ├── report_routes.py    # 报表：生成/下载
│   │   ├── predict_routes.py   # 预测：销售预测/库存补货
│   │   ├── alert_routes.py     # 预警：规则CRUD/日志/扫描
│   │   ├── admin_routes.py     # 管理：用户CRUD（P1）
│   │   ├── datasource_routes.py # 数据源：状态/历史（P1）
│   │   └── profile_routes.py   # 用户画像（P1）
│   ├── database/               # 数据库服务层
│   ├── test_auth_integration.py         # 认证测试（36项）
│   └── test_predict_alert_integration.py # 预测+预警测试（60项）
│
├── frontend/                   # Vue 3 前端（姚凯曦）
│   ├── package.json            # 依赖配置
│   ├── vite.config.js          # Vite 构建配置
│   ├── src/
│   │   ├── main.js             # 入口
│   │   ├── App.vue             # 根组件
│   │   ├── router/index.js     # 路由（含守卫）
│   │   ├── stores/user.js      # Pinia 用户状态
│   │   ├── api/index.js        # API 封装层（24条后端路由全对接）
│   │   ├── api/mock.js         # 演示模式（无需后端即可浏览）
│   │   ├── components/layout/  # 布局组件
│   │   └── views/              # 页面（8个）
│   │       ├── dashboard/      # 仪表盘首页
│   │       ├── query/          # 数据查询（P1）
│   │       ├── predict/        # 预测分析（P1）
│   │       ├── report/         # 报表中心（P1）
│   │       ├── alert/          # 预警中心
│   │       ├── admin/          # 用户管理 + 数据源配置
│   │       └── login/          # 登录页
│   ├── tests/                  # 测试数据 + 测试计划文档
│   └── docs/                   # 部署操作说明
│
├── ml/                          # ML 模块（薛淞 + 严辰乐）
│   ├── ml_pipeline.py           # 8步管道（训练→预测→异常→库存→画像→营销）
│   ├── config.py                # ML 配置
│   ├── ml.md                    # ML 设计文档
│   └── models/                  # 训练好的模型文件
│
├── database/                    # 数据库脚本（苏文韬）
│   └── init.sql                 # 10张表 DDL + 种子数据
│
├── scripts/                     # 数据工具（苏文韬）
│   ├── generate_mock_data.py    # 随机数据生成脚本
│   └── output/seed_data.sql     # 生成的批量种子数据
│
└── docs/                        # 项目文档
    ├── 需求分析文档.md           # v1.0（943行8章）
    ├── 团队分工说明.md           # 分工+2周冲刺计划
    ├── 函数参数需求文档.md       # 组员接口约定
    ├── 项目管理文档.md           # 甘特图+风险+交付清单
    └── design/
        ├── 设计文档-架构章.md    # 四层B/S架构
        └── 软件设计文档.md       # 总体+详细设计
```

## 快速开始

### 环境要求

| 组件 | 版本 | 说明 |
|------|------|------|
| Python | 3.10+ | 推荐 `D:\Anaconda\python.exe`（Python 3.13.9） |
| MySQL | 8.0+ | 端口 3306，root 密码 123456 |
| Node.js | 18+ | 前端 Vite 开发服务器 |

### 1. 数据库初始化

```bash
# 启动 MySQL（Windows）
"C:/Program Files/MySQL/MySQL Server 8.4/bin/mysqld.exe" \
  --defaults-file="C:/Users/MSI-NB/mysql-data/my.ini" --console &

# 导入建表脚本 + 种子数据
mysql -u root -p123456 < database/init.sql

# （可选）导入更多随机数据
mysql -u root -p123456 < scripts/output/seed_data.sql
```

### 2. ML 模型训练

```bash
cd ml
D:\Anaconda\python.exe ml_pipeline.py
```

### 3. 后端启动

```bash
cd backend
pip install -r requirements.txt
D:\Anaconda\python.exe app.py
```

访问 http://127.0.0.1:5000/api/health 确认后端运行。

### 4. 前端启动

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173 打开前端。

## 功能状态

### P0 — 已完成 ✅

| 用例 | 功能 | 后端 | 前端 |
|------|------|------|------|
| UC-01 | 多维度销售数据查询 | `GET /api/data/sales` | QueryPage |
| UC-02 | 销售趋势预测 | `GET /api/predict/sales` | PredictPage |
| UC-03 | 库存补货建议 | `GET /api/predict/stock` | PredictPage |
| UC-08 | 异常检测预警 | `POST /api/alert/scan` + rules CRUD | AlertPage |
| UC-09 | 报表生成导出 | `POST /api/report/generate` | ReportPage |
| UC-10 | 用户认证授权 | JWT login/register/me | LoginPage |

### P1 — 已完成 ✅

| 功能 | 后端 | 前端 | 说明 |
|------|------|------|------|
| 用户画像 | `GET /api/profile/users` | — | RFM模型 |
| 用户管理 | `GET/POST/PUT /api/admin/users` | UserManagement | 仅admin |
| 数据源状态 | `GET /api/admin/datasource/status` | DatasourceConfig | 仅admin |
| 定时预警 | APScheduler 每小时扫描 | — | 自动触发 |

### P2 — 已砍

> 推荐算法、竞品分析、营销评估

## API 总览（24 条路由）

```
认证：  POST /api/auth/login       POST /api/auth/register     GET /api/auth/me
数据：  GET  /api/data/sales
报表：  POST /api/report/generate   GET  /api/report/download/<filename>
预测：  GET  /api/predict/sales     GET  /api/predict/stock
预警：  POST /api/alert/scan        GET  /api/alert/rules        POST /api/alert/rules
        PUT  /api/alert/rules/<id>  GET  /api/alert/logs         PUT  /api/alert/logs/<id>/resolve
管理：  GET  /api/admin/users       POST /api/admin/users        PUT  /api/admin/users/<id>
        PUT  /api/admin/users/<id>/toggle-status
        GET  /api/admin/datasource/status   GET /api/admin/datasource/history
画像：  GET  /api/profile/users
```

统一响应格式：
```json
// 成功：{"success": true, "data": {...}, "message": "ok"}
// 失败：{"success": false, "data": null, "error": "描述", "code": "ERROR_CODE"}
```

## 演示模式

前端内置演示模式，**无需后端和数据库**即可浏览全部 8 个页面：

1. 打开 `http://localhost:5173/login`
2. 点击"演示模式"按钮
3. 所有页面以 mock 数据渲染

## 测试

```bash
cd backend
D:\Anaconda\python.exe test_auth_integration.py          # 36项
D:\Anaconda\python.exe test_predict_alert_integration.py  # 60项
# 总计：96/96 通过
```

## 种子账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | 系统管理员 |
| manager | manager123 | 运营经理 |
| analyst1 | test123 | 数据分析师 |

## 团队

| 姓名 | 学号 | 核心贡献 |
|------|------|----------|
| 严辰乐 | 24325289 | 组长/后端核心/项目管理：架构设计、JWT认证、预测+预警API、P1路由、前后端对接、文档 |
| 苏文韬 | 24325237 | 数据库设计+后端数据：10表DDL、db_service、data+report路由、随机数据脚本 |
| 姚凯曦 | 24325298 | 前端核心：Vue3框架、仪表盘+数据查询+预测+报表+预警+登录+管理页、演示模式、测试文档 |
| 薛淞 | 24325286 | ML算法：销售预测+库存补货+异常检测+用户画像+营销评估（8步管道） |
| 闫维岳 | 24325288 | PPT + 联调测试 |

## 提交物清单

| # | 交付物 | 状态 |
|---|--------|------|
| 1 | 需求分析文档 | ✅ v1.0 |
| 2 | 软件设计文档 | ⚠️ 骨架完成，UML图待补 |
| 3 | 测试计划与用例报告 | ⚠️ 功能测试完成，性能/安全待补 |
| 4 | 项目管理文档 | ✅ v1.0 |
| 5 | 程序源代码 | ✅ 24路由+8页面+ML管道 |
| 6 | 测试数据 | ✅ |
| 7 | 系统原型视频 | ❌ |
| 8 | 演示PPT | ❌ 闫维岳 |
| 9 | 部署操作说明 | ✅ 287行 |
