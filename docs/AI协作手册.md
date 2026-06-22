# AI 协作手册 — 电商BI系统

> **用途**：新 AI（或人类）接手此项目时的必读文件。含环境配置、启动命令、踩坑记录、协作规范。
> **来源**：合并自 `prompt.txt` + `skill.txt` + `project-brief.txt`（2026-06-22 整理）
> **更新日期**：2026-06-22

---

## 一、项目核心信息

| 项目 | 内容 |
|------|------|
| 组长 | 严辰乐（24325289） |
| 组员 | 苏文韬（24325237）、姚凯曦（24325298）、薛淞（24325286）、闫维岳（24325288） |
| 选题 | 三(1) — 基于AI智能的电商商品销售分析与预测系统 |
| 仓库 | https://github.com/Qian-YiChen/ecommerce-bi-system |
| 项目根 | `C:\Users\MSI-NB\Desktop\Learning\软工大作业\工程\` |

---

## 二、环境与启动命令

### Python

- **解释器**：`D:\Anaconda\python.exe`（Python 3.13.9）
- ⚠️ **不要用** WindowsApps 下的 python3（功能受限、易超时）
- 包管理器：`D:\Anaconda\Scripts\pip.exe`

```bash
# 依赖安装
D:\Anaconda\python.exe -m pip install flask flask-cors pyjwt bcrypt \
  pymysql openpyxl apscheduler numpy pandas scikit-learn joblib
```

### MySQL

- 版本：8.4.9
- 端口：3306
- root 密码：123456
- 数据库名：ecommerce_bi
- 二进制：`C:\Program Files\MySQL\MySQL Server 8.4\bin\`
- 数据目录：`C:\Users\MSI-NB\mysql-data\`
- 配置文件：`C:\Users\MSI-NB\mysql-data\my.ini`

```bash
# 启动 MySQL
"C:/Program Files/MySQL/MySQL Server 8.4/bin/mysqld.exe" \
  --defaults-file="C:/Users/MSI-NB/mysql-data/my.ini" --console &

# 导入建表脚本
mysql -u root -p123456 < database/init.sql

# （可选）导入随机数据
mysql -u root -p123456 < scripts/output/seed_data.sql
```

### Flask 后端

```bash
cd backend
D:\Anaconda\python.exe app.py
# → http://127.0.0.1:5000
# 健康检查：GET /api/health
```

### ML 管道

```bash
cd ml
D:\Anaconda\python.exe ml_pipeline.py
```

### 前端

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

### 演示材料

```bash
# 双击 start.bat，或手动：
cd demo
D:\Anaconda\python.exe -m http.server 8000
# → http://127.0.0.1:8000/项目演示-交互版.html
```

### 运行测试

```bash
cd backend
PYTHONPATH=$PWD:$PYTHONPATH python test_auth_integration.py          # 36项
PYTHONPATH=$PWD:$PYTHONPATH python test_predict_alert_integration.py  # 60项
```

### 种子账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | 系统管理员 |
| manager | manager123 | 运营经理 |
| analyst1 | test123 | 数据分析师 |

---

## 三、关键文件路径索引

### 项目规格

| 文件 | 说明 |
|------|------|
| `README.md` | 项目总览（技术栈、API、快速开始） |
| `进度.txt` | 当前进度 + 剩余任务 |
| `docs/AI协作手册.md` | 本文件 |

### 核心文档

| 文件 | 说明 |
|------|------|
| `docs/需求分析文档.md` | 功能/非功能需求、用例、数据字典 |
| `docs/design/软件设计文档.md` | 架构/模块/接口/DB/部署设计 |
| `docs/项目管理文档.md` | 甘特图/里程碑/风险/交付清单 |
| `docs/团队分工说明.md` | 角色+2周冲刺计划 |
| `docs/函数参数需求文档.md` | 组员接口约定 |
| `docs/测试报告.md` | 96/96测试结果 |
| `docs/分工与工作情况说明.md` | 组长提交：5人工作情况 |

### 后端代码

| 文件 | 说明 |
|------|------|
| `backend/app.py` | Flask 主入口 |
| `backend/config.py` | JWT密钥+MySQL配置 |
| `backend/scheduler.py` | APScheduler 定时预警 |
| `backend/auth/auth_service.py` | JWT + bcrypt 认证 |
| `backend/middleware/jwt_middleware.py` | @jwt_required + @role_required |
| `backend/models/user.py` | User 模型 |
| `backend/database/db_service.py` | 6个函数（连接/CRUD/查询/导出） |
| `backend/routes/auth_routes.py` | 登录/注册/当前用户 |
| `backend/routes/data_routes.py` | 多维度销售查询 |
| `backend/routes/report_routes.py` | 报表生成/下载 |
| `backend/routes/predict_routes.py` | 销售预测/库存补货 |
| `backend/routes/alert_routes.py` | 预警规则CRUD/日志/扫描 |
| `backend/routes/admin_routes.py` | 用户管理CRUD |
| `backend/routes/datasource_routes.py` | 数据源状态/历史/上传 |
| `backend/routes/profile_routes.py` | 用户画像 |
| `backend/test_auth_integration.py` | 认证测试（36项） |
| `backend/test_predict_alert_integration.py` | 预测+预警测试（60项） |

### ML 代码

| 文件 | 说明 |
|------|------|
| `ml/config.py` | ML 配置 |
| `ml/ml_pipeline.py` | 8步管道（训练→预测→异常→库存→画像→营销） |
| `ml/models/sales_lr_baseline.pkl` | 训练好的模型 |

### 数据库

| 文件 | 说明 |
|------|------|
| `database/init.sql` | 10张表DDL + 种子数据 |
| `scripts/generate_mock_data.py` | 随机数据生成（1200条） |
| `scripts/output/seed_data.sql` | 生成的补充数据 |

---

## 四、踩坑记录与经验

### 4.1 Python 环境
- 只能用 `D:\Anaconda\python.exe`
- WindowsApps 下的 python3 会超时/权限受限
- pip 安装也用完整路径：`D:\Anaconda\python.exe -m pip install ...`

### 4.2 MySQL
- `mysqld`（带 d = daemon/服务器）≠ `mysql`（客户端）
- 必须先启动 mysqld 才能连接
- MySQL 8.4 **不支持** `default_authentication_plugin=mysql_native_password`
- 数据目录不能放 Program Files 下（权限不够）
- `DECIMAL(5,4)` 只能存到 9.9999，MAPE 百分比值需 `DECIMAL(8,2)` 以上
- 每库 = 一个子目录，每张 InnoDB 表 = 一个 `.ibd` 文件

### 4.3 ML 模块
- `pd.read_sql()` 直接传 `pymysql.Connection` 会 UserWarning，但能工作
- 线性回归基线模型 MAPE 可能 100%+，小数据集正常
- 递归预测只能用 `lag_1`，不能用 `lag_7`/`lag_30`（未来值不存在）
- 库存数据必须来自数据库真实值，不能用 MOCK_INVENTORY 随机生成
- ML 须提供独立 API 函数（`load_model`、`predict_xxx_for_api`），不能只靠 `main()`
- 全局模型需 `category_id` 特征区分品类

### 4.4 认证模块
- auth_service 使用依赖注入（login 接收 `get_user_fn` 参数）
- 测试用 mock 替代真实数据库
- patch 目标必须是被 import 的位置，不是定义位置
- JWT 是无状态认证——解码不需查库，安全靠签名

### 4.5 Git 操作
- 只上传 `工程/` 文件夹
- Token 绝不能写入会被 push 的文件（GitHub Push Protection 会扫描）
- amend 后 commit hash 会变，已 push 过的不要 amend
- fetch 先看别人改了什么（`git diff HEAD..origin/main`），再 pull
- commit message 不能为空
- 每个逻辑独立的文件单独 commit

### 4.6 代理配置
```bash
# 查看 Windows 系统代理
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" | grep ProxyServer

# Clash 代理（常见端口 7897）
git -c http.proxy=http://127.0.0.1:7897 -c https.proxy=http://127.0.0.1:7897 fetch origin
```

### 4.7 文件编辑
- `sed` 处理中文全角字符（如 `（）「」`）容易报错，用 Python 替代
- Windows 终端默认 GBK，print emoji 会 `UnicodeEncodeError`
- 用 `io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')` 解决

### 4.8 文档与代码一致性
- 每次组员交付后交叉比对：docs vs 实际代码 vs 项目结构总览
- 函数参数需求文档的签名必须和实际代码严格一致
- 设计文档中模块名应与实际文件结构对应
- 表数量变更需同步更新所有文档
- 常见不一致：函数签名、表数量、模块名、API 路径、提交物状态

---

## 五、GitHub 配置

```
仓库地址：https://github.com/Qian-YiChen/ecommerce-bi-system
用户名：Qian-YiChen
邮箱：18000184@qq.com
远程：origin → main（Token 已在 git remote 中配置）
```

### 日常提交命令
```bash
cd "C:\Users\MSI-NB\Desktop\Learning\软工大作业\工程"
git add <具体文件>
git commit -m "类型：描述改动"
git -c http.proxy=http://127.0.0.1:7897 -c https.proxy=http://127.0.0.1:7897 push origin main
```

### 组员克隆
```bash
git clone https://github.com/Qian-YiChen/ecommerce-bi-system.git
```

---

## 六、协作原则

- 大学生期末作业，不要过于深奥。重点：软件工程过程 + 文档规范性 + 代码可运行
- P0 用例必须完成，P1 力争，P2 可砍
- 文档和代码并行推进，不能按瀑布模型串行
- 技术选型以"组员会什么"和"截止日前能否完成"为准
- 组员交付后先验证再集成（mock 测试 → 真实数据库测试 → 端到端测试）
- 每次代码修改后检查是否需要同步更新文档
- Git 提交：每个逻辑独立的文件单独 commit，写清楚改了什么

---

> **来源文件**（已合并到本文档后删除）：
> `prompt.txt`、`skill.txt`、`project-brief.txt`
