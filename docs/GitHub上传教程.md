# GitHub 上传教程 — 从零到推送

> 适用：Windows 系统，首次使用 GitHub 的小白。
> 预计耗时：15 分钟。

---

## 第1步：检查 Git 是否已安装

打开终端（Git Bash 或 CMD），输入：

```bash
git --version
```

如果显示类似 `git version 2.x.x` 说明已安装，跳到第3步。

如果提示"不是内部命令"，进入第2步。

---

## 第2步：安装 Git

1. 打开 https://git-scm.com/downloads/win
2. 下载 **64-bit Git for Windows Setup**
3. 双击安装，一路 Next（全部默认选项即可）
4. 安装完成后重新打开终端，输入 `git --version` 确认

---

## 第3步：配置 Git 用户信息

在终端输入（替换成你自己的信息）：

```bash
git config --global user.name "严辰乐"
git config --global user.email "你的邮箱@example.com"
```

---

## 第4步：在 GitHub 上创建远程仓库

1. 打开 https://github.com 并登录（没有账号先去注册）
2. 点击右上角 **+** → **New repository**
3. 填写：
   - **Repository name**：`ecommerce-bi-system`（或你喜欢的名字）
   - **Description**：基于AI智能的电商商品销售分析与预测系统
   - **Public** 或 **Private**（课程项目建议 Private）
   - ⚠️ **不要勾选** "Add a README file"（我们本地已有）
   - ⚠️ **不要勾选** ".gitignore"（我们本地已有）
4. 点击 **Create repository**
5. 创建后，GitHub 会显示一段命令。记下仓库地址，类似：
   ```
   https://github.com/你的用户名/ecommerce-bi-system.git
   ```

---

## 第5步：在本机项目文件夹初始化 Git

打开终端，进入工程文件夹：

```bash
cd "C:\Users\MSI-NB\Desktop\Learning\软工大作业\工程"
```

初始化 Git 仓库：

```bash
git init
```

---

## 第6步：添加所有文件并提交

```bash
# 添加所有文件（.gitignore 会自动排除不应上传的文件）
git add .

# 查看将要提交的文件列表（确认没有敏感信息、大数据文件等）
git status

# 提交
git commit -m "初始提交：需求分析文档 + 后端框架 + JWT认证模块"
```

---

## 第7步：关联远程仓库并推送

```bash
# 关联远程仓库（把下面地址换成你在第4步创建的仓库地址）
git remote add origin https://github.com/你的用户名/ecommerce-bi-system.git

# 推送到 GitHub
git branch -M main
git push -u origin main
```

如果弹出登录窗口，用 GitHub 账号密码登录。
（GitHub 现在可能要求用 Personal Access Token 代替密码，见附录。）

---

## 第8步：验证

刷新 GitHub 仓库页面，应该能看到所有文件已经上传。

---

## 后续日常提交

每次修改完代码后：

```bash
git add .
git commit -m "简短描述你改了什么"
git push
```

组员各自在自己的 feature 分支上工作（见 `团队分工说明.md` 的协作规则）。

---

## 组员克隆项目

组员在自己电脑上：

```bash
git clone https://github.com/你的用户名/ecommerce-bi-system.git
cd ecommerce-bi-system
```

---

## 附录：常见问题

### Q1: push 时弹窗要求输入用户名密码，但密码不对？

GitHub 从2021年起不再支持密码登录 Git 操作，需要用 **Personal Access Token**：

1. GitHub 右上角头像 → **Settings**
2. 左侧菜单最下面 → **Developer settings** → **Personal access tokens** → **Tokens (classic)**
3. **Generate new token (classic)**
4. 勾选 `repo`（全部勾上），点击 Generate
5. 复制生成的 token（只显示一次！）
6. push 时密码栏粘贴这个 token

### Q2: 怎么让组员也能推送代码？

GitHub 仓库页面 → **Settings** → **Collaborators** → **Add people**，输入组员的 GitHub 用户名。

### Q3: 误传了大文件怎么办？

在 `.gitignore` 中添加文件路径，然后：
```bash
git rm --cached 大文件名
git commit -m "移除大文件"
```

### Q4: 提交记录太乱？

养成好习惯：每次 commit 只做一件事，message 写清楚做了什么。
好的 message：`"新增：用户登录API POST /api/auth/login"`
坏的 message：`"修bug"`  `"111"`  `"update"`
