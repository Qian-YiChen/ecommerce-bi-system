# 基于AI智能的电商商品销售分析与预测系统

> 中山大学《软件工程》课程期末实践 — 选题三(1)
> 团队：严辰乐（组长）、苏文韬、闫维岳、薛淞、姚凯曦

## 项目简介

面向电商企业内部的商业智能（BI）分析决策平台，利用机器学习和大数据技术对销售数据进行深度挖掘，实现销售趋势预测、库存优化、用户画像构建和异常检测预警。

## 项目结构

```
工程/
├── backend/                 # Python Flask 后端
│   ├── app.py               # 主入口
│   ├── config.py            # 配置（JWT/MySQL）
│   ├── requirements.txt     # Python 依赖
│   ├── auth/                # JWT 认证模块
│   ├── models/              # 数据模型
│   ├── middleware/           # 中间件（JWT/RBAC）
│   └── routes/              # API 路由
├── frontend/                # Vue 3 前端（待搭建）
├── ml/                      # ML 模型（薛淞）
├── database/                # 数据库脚本（苏文韬）
│   └── init.sql             # 建表 DDL
├── docs/                    # 项目文档
│   ├── 需求分析文档.md
│   ├── 团队分工说明.md
│   ├── 函数参数需求文档.md
│   └── design/              # 设计文档
│       └── 设计文档-架构章.md
└── tests/                   # 测试（姚凯曦）
```

## 快速开始

### 环境要求

- Python 3.10+（推荐 D:\Anaconda\python.exe）
- MySQL 8.0+
- Node.js 18+（前端）

### 后端启动

```bash
cd backend
pip install -r requirements.txt
python app.py
```

访问 http://127.0.0.1:5000/api/health

### 数据库初始化

```bash
mysql -u root -p < database/init.sql
```

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | Vue 3 + Element Plus + ECharts |
| 后端 | Python Flask + PyJWT + bcrypt |
| 数据库 | MySQL 8.0 |
| ML | scikit-learn + statsmodels |
| 部署 | Docker Compose |
