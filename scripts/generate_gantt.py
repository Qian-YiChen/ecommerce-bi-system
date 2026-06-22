"""
甘特图生成脚本
生成电商BI系统项目甘特图PNG，用于项目管理文档
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.font_manager as fm
from datetime import datetime, timedelta

# ---- 中文字体配置 ----
plt.rcParams['font.family'] = 'Microsoft YaHei'
plt.rcParams['axes.unicode_minus'] = False

# 项目基准日期：2026-06-08 = Day 1
BASE_DATE = datetime(2026, 6, 8)

# 任务定义：(任务名, 开始日, 持续天数, 负责人, 色带)
tasks = [
    # 文档
    ("需求分析文档",        1,  3,  "严辰乐",   "#4CAF50"),
    ("软件设计文档",        1,  8,  "严辰乐",   "#4CAF50"),
    ("项目管理文档",        1, 14,  "严辰乐",   "#4CAF50"),
    ("测试文档",            4,  9,  "姚凯曦",   "#4CAF50"),
    # 后端
    ("后端框架+认证",       1,  3,  "严辰乐",   "#2196F3"),
    ("数据库DDL+ETL",       1,  3,  "苏文韬",   "#2196F3"),
    ("数据查询API(UC01)",   4,  5,  "苏文韬",   "#2196F3"),
    ("预测API(UC02/03)",    4,  5,  "严辰乐",   "#2196F3"),
    ("预警模块(UC08)",      4,  5,  "严辰乐",   "#2196F3"),
    ("报表API(UC09)",       4,  5,  "苏文韬",   "#2196F3"),
    ("P1路由(admin/profile)",9, 4,  "严辰乐",   "#2196F3"),
    # 前端
    ("Vue3框架+仪表盘",     1,  3,  "姚凯曦",   "#FF9800"),
    ("前端核心页面(4页)",   4,  5,  "姚凯曦",   "#FF9800"),
    ("前端管理页面(3页)",   4,  9,  "闫维岳",   "#FF9800"),
    ("前端演示模式",        9,  4,  "姚凯曦",   "#FF9800"),
    ("API封装层(23路由)",   4,  5,  "姚凯曦",   "#FF9800"),
    # ML
    ("ML基线模型",          1,  3,  "薛淞",     "#9C27B0"),
    ("ML模型优化+画像",     4,  9,  "薛淞",     "#9C27B0"),
    # 测试与演示
    ("集成测试(96项)",      9,  4,  "姚凯曦",   "#F44336"),
    ("UML图绘制(15个)",     9,  4,  "严辰乐",   "#F44336"),
    ("HTML演示页+截图",     9,  6,  "闫维岳",   "#F44336"),
    ("文档补全+整理",      11,  4,  "严辰乐",   "#F44336"),
]

# 颜色图例
legend_map = [
    ("文档撰写", "#4CAF50"),
    ("后端开发", "#2196F3"),
    ("前端开发", "#FF9800"),
    ("ML算法",   "#9C27B0"),
    ("测试演示", "#F44336"),
]

# ====== 绘图 ======
fig, ax = plt.subplots(figsize=(18, 10))
ax.set_facecolor('#FAFAFA')
fig.patch.set_facecolor('white')

for i, (name, start, duration, owner, color) in enumerate(tasks):
    ax.barh(i, duration, left=start - 1, height=0.65,
            color=color, edgecolor='white', linewidth=0.5, alpha=0.92)
    ax.text(start - 0.3, i, f"{name}  [{owner}]", ha='right', va='center',
            fontsize=8.5, color='#333333')

# 里程碑线
milestones = [
    (3,  "M1\n需求定稿",    "#E91E63"),
    (8,  "M3\nP0完成",      "#FF5722"),
    (12, "M4\n测试完成",     "#FF5722"),
    (14, "M6\n最终提交",     "#D32F2F"),
]
for day, label, color in milestones:
    ax.axvline(x=day - 0.5, color=color, linestyle='--', linewidth=2, alpha=0.7)
    ax.text(day - 0.5, len(tasks) - 0.25, label, ha='center', va='bottom',
            fontsize=8, fontweight='bold', color=color,
            bbox=dict(boxstyle='round,pad=0.2', facecolor='white',
                      edgecolor=color, alpha=0.85))

# X轴
day_labels = []
for d in range(1, 15):
    dt = BASE_DATE + timedelta(days=d - 1)
    day_labels.append(f"Day{d}\n{dt.strftime('%m/%d')}")
ax.set_xticks(range(0, 14))
ax.set_xticklabels(day_labels, fontsize=7.5)
ax.set_xlim(-0.5, 14.5)

# 阶段背景
stages = [
    (0, 3,   "阶段一\n骨架搭建",     "#E8F5E9"),
    (3, 8,   "阶段二\nP0猛攻",       "#E3F2FD"),
    (8, 12,  "阶段三\nP1补刀+测试",   "#FFF3E0"),
    (12, 14, "阶段四\n整理提交",      "#FFEBEE"),
]
for start, end, label, color in stages:
    ax.axvspan(start, end, alpha=0.35, color=color, zorder=0)
    mid = (start + end) / 2
    ax.text(mid, len(tasks) + 0.9, label, ha='center', va='bottom',
            fontsize=8.5, fontweight='bold', color='#555555')

# Y轴
ax.set_yticks(range(len(tasks)))
ax.set_yticklabels([])
ax.set_ylim(-0.8, len(tasks) + 2.2)
ax.invert_yaxis()

# 图例
patches = [mpatches.Patch(color=c, label=l) for l, c in legend_map]
legend = ax.legend(handles=patches, loc='lower right', ncol=5,
                   framealpha=0.9, fontsize=9, title="任务类别", title_fontsize=10)
legend.get_frame().set_edgecolor('#CCCCCC')

# 标题
ax.set_title("电商BI系统 — 项目甘特图（2026.06.08 – 06.21）", fontsize=15,
             fontweight='bold', pad=18)

# 底部说明
fig.text(0.5, 0.01, "项目周期 14 天 | 5 人团队 | 中山大学《软件工程》课程实践",
         ha='center', fontsize=9, color='#888888')

# 网格
ax.grid(axis='x', alpha=0.3, linestyle=':', color='#999999')
ax.set_axisbelow(True)

plt.tight_layout(rect=[0, 0.03, 1, 0.97])

OUTPUT = "C:/Users/MSI-NB/Desktop/Learning/软工大作业/工程/demo/演示用图/甘特图.png"
plt.savefig(OUTPUT, dpi=200, bbox_inches='tight', facecolor='white', edgecolor='none')
print(f"DONE: {OUTPUT}")
