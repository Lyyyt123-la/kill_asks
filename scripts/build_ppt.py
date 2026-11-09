"""生成《问数 AskData》答辩 PPT（16:9，14 页）。"""

from __future__ import annotations

from pathlib import Path

from PIL import Image
from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

ROOT = Path(r"D:\dsworking\kill_asks")
DOCS = ROOT / "docs"
SHOTS = DOCS / "screenshots"
OUT = DOCS / "问数AskData_答辩PPT.pptx"

# 品牌色
CREAM = RGBColor(0xF7, 0xF5, 0xEF)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
INK = RGBColor(0x23, 0x26, 0x1F)
MUTED = RGBColor(0x6F, 0x74, 0x68)
GREEN = RGBColor(0x1E, 0x3A, 0x2C)
GREEN2 = RGBColor(0x2E, 0x5A, 0x43)
SOFT = RGBColor(0xE8, 0xEF, 0xE9)
SOFT2 = RGBColor(0xEF, 0xF3, 0xEC)
GOLD = RGBColor(0xD9, 0xA4, 0x41)
GOLD_SOFT = RGBColor(0xF2, 0xE5, 0xC8)
CARD_LINE = RGBColor(0xE2, 0xDD, 0xD0)

FONT = "Microsoft YaHei"

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]


def set_cn(run, size, color=INK, bold=False, font=FONT):
    run.font.name = font
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    rpr = run._r.get_or_add_rPr()
    ea = rpr.find(qn("a:ea"))
    if ea is None:
        ea = etree.SubElement(rpr, qn("a:ea"))
    ea.set("typeface", font)


def text(slide, x, y, w, h, content, size=14, color=INK, bold=False,
         align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, spacing=1.12):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    para = tf.paragraphs[0]
    para.alignment = align
    para.line_spacing = spacing
    run = para.add_run()
    run.text = content
    set_cn(run, size, color, bold)
    return box


def lines(slide, x, y, w, h, rows, spacing=1.18):
    """rows: [(text, size, color, bold, space_after)]"""
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    for index, (content, size, color, bold, space_after) in enumerate(rows):
        para = tf.paragraphs[0] if index == 0 else tf.add_paragraph()
        para.line_spacing = spacing
        para.space_after = Pt(space_after)
        run = para.add_run()
        run.text = content
        set_cn(run, size, color, bold)
    return box


def rect(slide, x, y, w, h, fill=WHITE, line=None, radius=0.08, line_w=1.0):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    try:
        shape.adjustments[0] = radius
    except Exception:
        pass
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    if line is None:
        shape.line.fill.background()
    else:
        shape.line.color.rgb = line
        shape.line.width = Pt(line_w)
    shape.shadow.inherit = False
    return shape


def pill(slide, x, y, w, h, label, fill=SOFT, color=GREEN2, size=11.5, bold=True, line=None):
    rect(slide, x, y, w, h, fill, line, radius=0.5)
    text(slide, x + 0.12, y + h / 2 - 0.13, w - 0.24, 0.28, label, size=size, color=color, bold=bold, align=PP_ALIGN.CENTER)


def bg(slide, color=CREAM):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def new_slide(color=CREAM):
    slide = prs.slides.add_slide(BLANK)
    bg(slide, color)
    return slide


def add_image_fit(slide, path, x, y, w, h, pad=0.0):
    image = Image.open(path)
    iw, ih = image.size
    box_w = w - pad * 2
    box_h = h - pad * 2
    scale = min(box_w / iw, box_h / ih)
    dw = iw * scale
    dh = ih * scale
    px = x + pad + (box_w - dw) / 2
    py = y + pad + (box_h - dh) / 2
    return slide.shapes.add_picture(str(path), Inches(px), Inches(py), Inches(dw), Inches(dh))


def image_card(slide, path, x, y, w, h, pad=0.16, fill=WHITE, line=CARD_LINE, caption=None):
    rect(slide, x, y, w, h, fill, line, radius=0.06)
    image_h = h - 0.42 if caption else h
    add_image_fit(slide, path, x, y, w, image_h, pad=pad)
    if caption:
        text(slide, x + 0.18, y + h - 0.34, w - 0.36, 0.24, caption, size=10.5, color=MUTED)


def kicker(slide, label, x=0.8, y=0.62):
    text(slide, x, y, 6.5, 0.28, label, size=11, color=GOLD, bold=True)


def title(slide, content, sub=None, x=0.8, y=1.02, w=11.7, size=32):
    text(slide, x, y, w, 0.7, content, size=size, color=INK, bold=True)
    if sub:
        text(slide, x, y + 0.52, w, 0.32, sub, size=12.5, color=MUTED)


def footer(slide, number, dark=False):
    color = RGBColor(0x9A, 0xB4, 0xA1) if dark else MUTED
    text(slide, 11.9, 7.02, 0.8, 0.22, f"{number:02d}", size=9.5, color=color, align=PP_ALIGN.RIGHT)
    text(slide, 0.8, 7.02, 6.0, 0.22, "问数 AskData · AI WEB 挑战赛", size=9.5, color=color)


def badge_number(slide, number, x, y, size=0.55, fill=GOLD_SOFT, color=GREEN):
    rect(slide, x, y, size, size, fill, radius=0.5)
    text(slide, x, y + 0.1, size, size - 0.1, number, size=13, color=color, bold=True, align=PP_ALIGN.CENTER)


# ---------------------------------------------------------------- 01 封面
slide = new_slide(GREEN)
# 装饰
for (ox, oy, ow, oh, color) in [
    (10.0, -1.2, 5.6, 5.6, RGBColor(0x2A, 0x4A, 0x38)),
    (11.4, 4.6, 3.2, 3.2, RGBColor(0x27, 0x48, 0x35)),
]:
    shp = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(ox), Inches(oy), Inches(ow), Inches(oh))
    shp.fill.solid()
    shp.fill.fore_color.rgb = color
    shp.line.fill.background()
    shp.shadow.inherit = False

text(slide, 0.85, 0.62, 5.0, 0.3, "AI WEB 网页开发挑战赛 · 赛道二", size=12, color=GOLD, bold=True)
text(slide, 0.85, 1.35, 6.6, 1.25, "问数 AskData", size=52, color=CREAM, bold=True)
text(slide, 0.85, 2.55, 6.4, 0.62, "基于自然语言交互的数据分析平台", size=24, color=RGBColor(0xE9, 0xF0, 0xE7), bold=False)
rect(slide, 0.87, 3.34, 0.7, 0.06, GOLD, radius=0.5)
text(slide, 1.75, 3.28, 5.4, 0.26, "让业务人员用一句话，完成从数据到结论的全过程", size=13, color=RGBColor(0xC9, 0xD8, 0xCC))
lines(slide, 0.85, 4.55, 6.4, 1.1, [
    ("自然语言分析 · 自动选图 · 商品图创意可视化", 12.5, RGBColor(0xC9, 0xD8, 0xCC), False, 5),
    ("PDF / Word / 图片数据化 · 带引用的文档问答", 12.5, RGBColor(0xC9, 0xD8, 0xCC), False, 0),
])
text(slide, 0.85, 6.42, 6.3, 0.6,
     "广东科贸职业学院  ·  指导老师 林龙键  ·  罗勇添 / 辛嘉炜 / 林俊宁",
     size=11.5, color=RGBColor(0xA9, 0xBD, 0xAE))

# 右侧商品图展示
image_card(slide, SHOTS / "chart-product-showcase.png", 7.55, 1.18, 5.05, 4.9, pad=0.14,
           fill=RGBColor(0xFB, 0xF8, 0xF0), line=RGBColor(0x4A, 0x63, 0x50))
pill(slide, 10.95, 6.22, 1.85, 0.32, "商品图 · 内部占比", fill=GOLD, color=GREEN, size=9.5)

# ---------------------------------------------------------------- 02 痛点
slide = new_slide()
kicker(slide, "WHY · 为什么需要问数")
title(slide, "数据很近，分析很远", "业务人员被四道门槛挡在数据之外")
cards = [
    ("01", "工具门槛", "不会写 SQL，取数依赖数据团队，一次需求常常按天排队。"),
    ("02", "流程门槛", "工具要求先懂维度、度量、聚合，分析链路在第一步就中断。"),
    ("03", "数据形态门槛", "关键数据躺在 PDF 财报、Word 报告、聊天截图里，看得见却分析不了。"),
    ("04", "可视化门槛", "图表类型选错、信息密度低，有图仍然看不懂、用不上。"),
]
x0, y0, cw, gap = 0.8, 2.25, 2.78, 0.2
for i, (num, head, desc) in enumerate(cards):
    x = x0 + i * (cw + gap)
    rect(slide, x, y0, cw, 3.25, WHITE, CARD_LINE, radius=0.07)
    text(slide, x + 0.28, y0 + 0.28, 0.8, 0.6, num, size=24, color=GOLD, bold=True)
    text(slide, x + 0.28, y0 + 1.02, cw - 0.56, 0.45, head, size=17, color=INK, bold=True)
    text(slide, x + 0.28, y0 + 1.6, cw - 0.5, 1.4, desc, size=11.5, color=MUTED, spacing=1.35)
rect(slide, 0.8, 5.92, 11.73, 0.78, GREEN, radius=0.12)
text(slide, 1.05, 6.12, 11.2, 0.4, "不是缺数据，而是缺一条从“问题”到“结论”的短路径。", size=17, color=CREAM, bold=True)
footer(slide, 2)

# ---------------------------------------------------------------- 03 方案
slide = new_slide()
kicker(slide, "SOLUTION · 一句话方案")
title(slide, "把分析链路压缩成一次对话", "上传数据 → 用中文提问 → 直接得到可核对的结果")
items = [
    ("01", "自然语言分析", "NL2SQL + SQL 校验 + 失败重试，一句话出结果。"),
    ("02", "按数据推荐图表", "自动判断趋势 / 对比 / 占比 / 矩阵 / 相关性。"),
    ("03", "商品图可视化", "灰色商品图形做底，颜色在图像内部显示占比。"),
    ("04", "非结构化数据", "PDF / Word / 图片表格 → 可分析数据集 + 带引用问答。"),
]
for i, (num, head, desc) in enumerate(items):
    col, row = i % 2, i // 2
    x = 0.8 + col * 2.85
    y = 1.95 + row * 2.3
    rect(slide, x, y, 2.62, 2.0, WHITE, CARD_LINE, radius=0.08)
    badge_number(slide, num, x + 0.2, y + 0.2, 0.46)
    text(slide, x + 0.8, y + 0.2, 1.7, 0.35, head, size=14.5, color=INK, bold=True)
    text(slide, x + 0.22, y + 0.88, 2.2, 0.9, desc, size=11, color=MUTED, spacing=1.3)
image_card(slide, SHOTS / "01-welcome.png", 6.55, 1.6, 6.0, 4.72, pad=0.14,
           caption="左侧数据源 · 中间对话 · 右侧检查器")
text(slide, 6.75, 6.5, 5.6, 0.28, "CSV / Excel / PDF / Word / 图片：上传即可问", size=11, color=MUTED)
footer(slide, 3)

# ---------------------------------------------------------------- 04 架构
slide = new_slide()
kicker(slide, "ARCHITECTURE · 架构")
title(slide, "系统架构：五层解耦，单机可跑", "Vue 3 + FastAPI + DuckDB，一套代码本地、云端、考官包通用")
layers = [
    ("用户层", "Vue 3 · Vite · ECharts", "对话 / 图表 / 检查器 / 文档问答"),
    ("接入层", "FastAPI", "数据集 / 对话 / 文档 API，访问口令与限流"),
    ("能力层", "NL2SQL · 图表推荐 · RAG", "SQL 校验、DuckDB 执行、洞察生成"),
    ("模型层", "qwen-plus / qwen3-vl-plus", "OpenAI 兼容协议，可切换模型"),
    ("数据层", "DuckDB + SQLite", "分析数据、元数据、原始文件分层存储"),
]
y = 2.0
for i, (name, tech, desc) in enumerate(layers):
    rect(slide, 0.8, y + i * 0.94, 4.35, 0.8, WHITE, CARD_LINE, radius=0.08)
    rect(slide, 0.8, y + i * 0.94, 0.08, 0.8, GOLD if i in (2, 3) else GREEN2, radius=0.2)
    text(slide, 1.05, y + i * 0.94 + 0.11, 1.15, 0.3, name, size=12.5, color=GREEN, bold=True)
    text(slide, 2.05, y + i * 0.94 + 0.11, 2.9, 0.26, tech, size=10.5, color=INK, bold=True)
    text(slide, 1.05, y + i * 0.94 + 0.43, 3.9, 0.26, desc, size=9.5, color=MUTED)
image_card(slide, SHOTS / "00-architecture.png", 5.55, 2.1, 6.95, 4.45, pad=0.14)
footer(slide, 4)

# ---------------------------------------------------------------- 05 对话式分析
slide = new_slide()
kicker(slide, "CORE 01 · 对话式分析")
title(slide, "一句话，从问题到结论", "自然语言 → SQL → 图表 → 洞察，全链路可核对")
lines(slide, 0.8, 2.0, 4.55, 3.9, [
    ("① 计划 + SQL", 15, GREEN, True, 3),
    ("Schema / 口径 / 历史上下文注入，模型输出 JSON 计划与 SQL。", 11.2, MUTED, False, 14),
    ("② 静态校验 + 执行", 15, GREEN, True, 3),
    ("sqlglot 只读校验、表白名单、强制 LIMIT，DuckDB 只读执行。", 11.2, MUTED, False, 14),
    ("③ 失败自动修复", 15, GREEN, True, 3),
    ("数据库报错回喂模型，最多重试 2 次，复杂问题也能救回来。", 11.2, MUTED, False, 14),
    ("④ 洞察二次生成", 15, GREEN, True, 3),
    ("结论必须引用真实查询数字，禁止编造；检查器可展开 SQL 核对。", 11.2, MUTED, False, 0),
])
image_card(slide, SHOTS / "chart-bar-recommended.png", 5.85, 1.62, 6.6, 4.45, pad=0.14,
           caption="推荐柱状图 · KPI 概览 · 可展开 SQL")
rect(slide, 0.8, 6.22, 11.66, 0.6, GREEN, radius=0.1)
text(slide, 1.02, 6.36, 11.2, 0.3, "真实模型 6/6 正确 · 单问 8–12 秒 · 多轮继承上下文 · 模糊问题主动澄清",
     size=12.5, color=CREAM, bold=True)
footer(slide, 5)

# ---------------------------------------------------------------- 06 自动选图
slide = new_slide()
kicker(slide, "CORE 02 · 自动选图")
title(slide, "数据长什么样，就画什么图", "前端先做数据画像，再推荐图表；推荐第一，其他随时切换")
rules = [
    ("时间字段", "折线图", "趋势优先"),
    ("两个分类 + 数值", "热力图", "矩阵关系"),
    ("两个连续数值", "散点图", "相关性"),
    ("占比 / 构成", "环形图 · 树图", "部分与整体"),
    ("品类 4–12 类", "商品图", "图像化占比"),
]
y = 1.92
for i, (left, right, note) in enumerate(rules):
    rect(slide, 0.8, y + i * 0.78, 4.85, 0.66, WHITE if i != 4 else SOFT, CARD_LINE, radius=0.08)
    text(slide, 1.0, y + i * 0.78 + 0.16, 1.65, 0.28, left, size=10.5, color=INK, bold=True)
    text(slide, 2.62, y + i * 0.78 + 0.16, 1.65, 0.28, "→  " + right, size=11.2, color=GREEN, bold=True)
    text(slide, 4.25, y + i * 0.78 + 0.16, 1.2, 0.28, note, size=9.5, color=MUTED)
text(slide, 0.8, 5.92, 4.9, 0.5, "推荐类型排第一位并标注“推荐”，同时显示理由；表格收进底部“数据明细”。",
     size=10.5, color=MUTED, spacing=1.25)
image_card(slide, SHOTS / "chart-heatmap.png", 5.95, 1.62, 6.5, 4.92, pad=0.14,
           caption="热力图：两个分类维度 + 一个数值")
pill(slide, 5.95, 6.55, 2.15, 0.3, "热力 · 树图 · 散点", fill=SOFT, color=GREEN2, size=9.5)
footer(slide, 6)

# ---------------------------------------------------------------- 07 商品图
slide = new_slide()
kicker(slide, "CORE 03 · 商品图创意可视化")
title(slide, "让商品图成为数据载体", "不是把数字放进图表，而是让商品图形本身表达占比")
bullets = [
    ("灰色商品图形做底", "统一风格的手机 / 沙发 / 连衣裙 / 口红 / 苹果等 Canvas 自绘图形。"),
    ("颜色只在图像内部", "按占比从图形底部向上填充，颜色不溢出轮廓，不同品类不同浅色。"),
    ("入场动画 + 下钻", "中心向外扩散、羽化边缘、透明到不透明；悬停放大，点击填入下钻问题。"),
    ("自适应排列", "每行最多 4 个，超出向下换行；窄屏自动 3 / 2 列；无边框、无购物袋。"),
]
for i, (head, desc) in enumerate(bullets):
    y = 1.95 + i * 1.15
    rect(slide, 0.8, y, 0.08, 0.88, GOLD if i == 0 else GREEN2, radius=0.3)
    text(slide, 1.05, y + 0.02, 4.6, 0.3, head, size=14, color=INK, bold=True)
    text(slide, 1.05, y + 0.38, 4.55, 0.5, desc, size=10.5, color=MUTED, spacing=1.25)
rect(slide, 0.8, 6.45, 4.85, 0.42, GOLD_SOFT, radius=0.1)
text(slide, 1.0, 6.53, 4.5, 0.25, "“灰色做底，颜色在图像内部由下往上显示占比。”", size=10.5, color=GREEN, bold=True)
image_card(slide, SHOTS / "chart-product-showcase.png", 5.95, 1.62, 6.5, 4.95, pad=0.14,
           caption="品类销售构成 · 100% · 5 个品类")
footer(slide, 7)

# ---------------------------------------------------------------- 08 文档
slide = new_slide()
kicker(slide, "CORE 04 · 非结构化数据")
title(slide, "PDF、Word、截图，都能直接问", "先变成 DataFrame，再复用同一套分析链路")
steps = [
    ("01", "上传解析", "pdfplumber / python-docx / 视觉模型"),
    ("02", "转为数据集", "DataFrame → DuckDB，自动识别字段类型"),
    ("03", "直接提问", "NL2SQL + 图表 + 文档 RAG 带引用"),
]
for i, (num, head, desc) in enumerate(steps):
    x = 0.8 + i * 4.0
    rect(slide, x, 1.85, 3.72, 1.12, WHITE, CARD_LINE, radius=0.08)
    badge_number(slide, num, x + 0.2, 2.05, 0.44, SOFT, GREEN)
    text(slide, x + 0.78, 2.03, 2.7, 0.3, head, size=13, color=INK, bold=True)
    text(slide, x + 0.78, 2.38, 2.7, 0.4, desc, size=9.5, color=MUTED, spacing=1.2)
image_card(slide, SHOTS / "10-doc-ready.png", 0.8, 3.28, 5.45, 2.95, pad=0.1,
           caption="PDF：正文 + 6×4 区域销售额表")
image_card(slide, SHOTS / "13-image-extracted.png", 6.45, 3.28, 5.45, 2.95, pad=0.1,
           caption="截图：视觉模型识别 4×4 退款率表")
text(slide, 0.85, 6.42, 11.6, 0.3,
     "文档问答带 [1] 引用片段；表格可直接“作为数据集分析”，复用检查器与图表能力。",
     size=10.8, color=MUTED)
footer(slide, 8)

# ---------------------------------------------------------------- 09 AI Pipeline
slide = new_slide(GREEN)
text(slide, 0.8, 0.62, 6.0, 0.3, "AI PIPELINE · 技术链路", size=11, color=GOLD, bold=True)
text(slide, 0.8, 1.02, 11.5, 0.7, "模型负责理解，代码负责兜底", size=32, color=CREAM, bold=True)
text(slide, 0.8, 1.62, 11.2, 0.35, "把不确定的模型输出，放进确定性的工程链路里", size=13, color=RGBColor(0xC9, 0xD8, 0xCC))
steps = [
    ("Schema", "类型 / 枚举\n样例 / 范围"),
    ("Plan + SQL", "JSON 输出\n计划与 SQL"),
    ("sqlglot", "只读 / 单条\n白名单 / LIMIT"),
    ("DuckDB", "只读执行\n超时中断"),
    ("Retry", "报错回喂\n最多 2 次"),
    ("Insight", "引用真实数字\n禁止编造"),
]
x0, y0, bw, gap = 0.8, 2.55, 1.86, 0.12
for i, (head, desc) in enumerate(steps):
    x = x0 + i * (bw + gap)
    rect(slide, x, y0, bw, 1.55, RGBColor(0x2B, 0x4C, 0x3A), RGBColor(0x4E, 0x6B, 0x57), radius=0.1)
    text(slide, x + 0.15, y0 + 0.16, bw - 0.3, 0.3, head, size=13.5, color=GOLD, bold=True, align=PP_ALIGN.CENTER)
    text(slide, x + 0.12, y0 + 0.62, bw - 0.24, 0.7, desc, size=9.8, color=RGBColor(0xD6, 0xE3, 0xD9), align=PP_ALIGN.CENTER, spacing=1.3)
    if i < len(steps) - 1:
        text(slide, x + bw + 0.005, y0 + 0.62, 0.1, 0.3, "›", size=16, color=GOLD, bold=True, align=PP_ALIGN.CENTER)

metrics = [("6 / 6", "典型问题正确"), ("8–12s", "单问耗时"), ("2 次", "失败自动修复"), ("0", "编造数字")]
for i, (num, label) in enumerate(metrics):
    x = 0.8 + i * 3.0
    rect(slide, x, 5.05, 2.8, 1.25, RGBColor(0x16, 0x2D, 0x22), RGBColor(0x3C, 0x5A, 0x47), radius=0.1)
    text(slide, x + 0.22, 5.18, 2.3, 0.55, num, size=26, color=CREAM, bold=True)
    text(slide, x + 0.22, 5.8, 2.3, 0.3, label, size=10.5, color=RGBColor(0xA9, 0xBD, 0xAE))
footer(slide, 9, dark=True)

# ---------------------------------------------------------------- 10 工程化
slide = new_slide()
kicker(slide, "ENGINEERING · 工程化")
title(slide, "能演示，也能交付", "从“在自己电脑上能跑”到“在别人电脑上也能跑”")
items = [
    ("SQL 安全", "只读连接 + 单条 SELECT + 表白名单 + 强制 LIMIT + 超时"),
    ("失败兜底", "报错回喂修复；模型超时自动降级演示模式，现场不断线"),
    ("数据源状态", "切换保留会话；顶栏“重置数据源”重新读取原文件"),
    ("云端环境", "GitHub Codespaces 一键安装、构建、启动 8000 端口"),
    ("考官启动包", "双击脚本自动建 venv、装依赖、读 Key、开浏览器"),
    ("真实机器验证", "独立目录从零安装：43 个依赖、约 2 分钟跑通"),
]
for i, (head, desc) in enumerate(items):
    col, row = i % 3, i // 3
    x = 0.8 + col * 3.92
    y = 1.9 + row * 2.28
    rect(slide, x, y, 3.65, 1.98, WHITE, CARD_LINE, radius=0.08)
    rect(slide, x + 0.22, y + 0.2, 0.42, 0.06, GOLD, radius=0.5)
    text(slide, x + 0.22, y + 0.42, 3.2, 0.34, head, size=15, color=INK, bold=True)
    text(slide, x + 0.22, y + 0.9, 3.15, 0.9, desc, size=10.3, color=MUTED, spacing=1.3)
rect(slide, 0.8, 6.2, 11.73, 0.62, SOFT, radius=0.1)
text(slide, 1.05, 6.35, 11.2, 0.3, "已通过：干净环境安装 / 示例数据 / 上传 CSV / 文档问答 / 重置数据源 / 切换保留会话",
     size=11.5, color=GREEN, bold=True)
footer(slide, 10)

# ---------------------------------------------------------------- 11 测试
slide = new_slide()
kicker(slide, "RESULTS · 实测数据")
title(slide, "能跑通，也能量化", "36,000 行双11数据 · 真实 qwen-plus 调用")
stats = [("6/6", "典型问题正确"), ("8–12s", "单问耗时"), ("43", "干净环境依赖"), ("6:06", "演示视频时长")]
for i, (num, label) in enumerate(stats):
    x = 0.8 + i * 2.95
    rect(slide, x, 2.0, 2.72, 1.15, WHITE, CARD_LINE, radius=0.08)
    text(slide, x + 0.2, 2.11, 2.3, 0.5, num, size=25, color=GREEN, bold=True)
    text(slide, x + 0.2, 2.63, 2.3, 0.3, label, size=9.8, color=MUTED)

rows = [
    ("各区域销售额对比", "✅ 正确 SQL + 中文洞察", "8.9s"),
    ("双11当天各小时趋势", "✅ 正确日期过滤 + 双峰洞察", "12.2s"),
    ("销售额最低的 3 个品类", "✅ 升序 + “最低”洞察", "7.8s"),
    ("各渠道退款率排名", "✅ CASE WHEN 比率计算", "9.3s"),
    ("最近 30 天销售额趋势", "✅ 以数据最大日期为基准", "12.5s"),
    ("华东销售额最高 3 个城市", "✅ 自动修复后成功", "12.5s"),
]
table_shape = slide.shapes.add_table(len(rows) + 1, 3, Inches(0.8), Inches(3.45), Inches(11.7), Inches(2.85))
table = table_shape.table
table.columns[0].width = Inches(4.1)
table.columns[1].width = Inches(5.55)
table.columns[2].width = Inches(2.05)
headers = ["问题", "结果", "耗时"]
for j, header in enumerate(headers):
    cell = table.cell(0, j)
    cell.text = ""
    cell.fill.solid()
    cell.fill.fore_color.rgb = GREEN
    para = cell.text_frame.paragraphs[0]
    run = para.add_run()
    run.text = header
    set_cn(run, 11, CREAM, True)
    cell.margin_left = Inches(0.12)
for i, row in enumerate(rows, start=1):
    for j, value in enumerate(row):
        cell = table.cell(i, j)
        cell.text = ""
        cell.fill.solid()
        cell.fill.fore_color.rgb = WHITE if i % 2 else SOFT2
        para = cell.text_frame.paragraphs[0]
        run = para.add_run()
        run.text = value
        set_cn(run, 10, INK if j == 0 else MUTED, j == 0)
        cell.margin_left = Inches(0.12)
text(slide, 0.8, 6.42, 11.6, 0.35,
     "另已验证：热力图去重、退款率 KPI、切换保留会话、重置数据源、商品图悬停/点击下钻。",
     size=10.5, color=MUTED)
footer(slide, 11)

# ---------------------------------------------------------------- 12 场景
slide = new_slide()
kicker(slide, "VALUE · 场景与价值")
title(slide, "把数据能力还给业务", "不改变业务习惯，只缩短从问题到答案的距离")
aud = [
    ("运营 / 市场", "不会 SQL，取数靠排队", "上传活动数据，直接问渠道退款率、活动复盘。"),
    ("财务 / 管理者", "PDF 财报数字难定位", "上传财报，问区域销售额、同比与关键指标。"),
    ("学生 / 研究者", "数据散在 Excel / 截图", "上传文件即分析，不做环境配置。"),
]
for i, (role, pain, use) in enumerate(aud):
    x = 0.8 + i * 4.0
    rect(slide, x, 1.9, 3.72, 3.3, WHITE, CARD_LINE, radius=0.08)
    pill(slide, x + 0.22, 2.1, 1.55, 0.34, role, fill=SOFT, color=GREEN2, size=10.5)
    text(slide, x + 0.22, 2.66, 3.2, 0.32, "痛点： " + pain, size=10, color=MUTED)
    text(slide, x + 0.22, 3.18, 3.2, 1.35, use, size=12, color=INK, bold=True, spacing=1.3)
    text(slide, x + 0.22, 4.62, 3.2, 0.3, "→ 一句话拿到图表与结论", size=9.8, color=GOLD, bold=True)
rect(slide, 0.8, 5.62, 11.7, 0.9, GREEN, radius=0.1)
text(slide, 1.05, 5.8, 11.2, 0.5, "降低门槛  ·  缩短链路  ·  沉淀可复用的数据资产", size=19, color=CREAM, bold=True)
footer(slide, 12)

# ---------------------------------------------------------------- 13 规划
slide = new_slide()
kicker(slide, "ROADMAP · 边界与下一步")
title(slide, "边界清晰，方向明确", "当前是单表分析为主的端到端原型")
rect(slide, 0.8, 1.9, 4.4, 3.7, WHITE, CARD_LINE, radius=0.08)
text(slide, 1.05, 2.08, 3.8, 0.32, "当前边界", size=15, color=INK, bold=True)
lines(slide, 1.05, 2.55, 3.85, 2.8, [
    ("· 单表分析为主，多表 JOIN 需明确关系", 10.8, MUTED, False, 9),
    ("· 需要模型 Key；无 Key 自动演示模式", 10.8, MUTED, False, 9),
    ("· 上传 ≤ 30MB，大文件需先抽样", 10.8, MUTED, False, 9),
    ("· 商品图为自绘矢量图形，尚未接入真实照片", 10.8, MUTED, False, 9),
    ("· 公网部署与多用户权限待完善", 10.8, MUTED, False, 0),
])
phases = [
    ("近期", "语义层 + 多表关联", "口径可配置，支持跨表 JOIN"),
    ("中期", "真实商品图 + 看板分享", "透明 PNG/SVG 素材，分析卡片固定为看板"),
    ("长期", "50+ 题评测集 + 企业权限", "量化准确率、修复率与延迟"),
]
for i, (phase, head, desc) in enumerate(phases):
    y = 1.9 + i * 1.48
    rect(slide, 5.65, y, 6.85, 1.22, WHITE, CARD_LINE, radius=0.08)
    pill(slide, 5.86, y + 0.2, 0.85, 0.34, phase, fill=GREEN, color=CREAM, size=10.5)
    text(slide, 6.9, y + 0.17, 5.3, 0.32, head, size=14, color=INK, bold=True)
    text(slide, 6.9, y + 0.58, 5.2, 0.3, desc, size=10.2, color=MUTED)
    if i < 2:
        text(slide, 5.98, y + 1.22, 0.2, 0.25, "↓", size=12, color=GOLD, bold=True)
footer(slide, 13)

# ---------------------------------------------------------------- 14 团队
slide = new_slide(GREEN)
for (ox, oy, ow, oh, color) in [
    (-1.2, 5.3, 4.4, 4.4, RGBColor(0x27, 0x48, 0x35)),
    (10.4, -1.4, 4.8, 4.8, RGBColor(0x2A, 0x4A, 0x38)),
]:
    shp = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(ox), Inches(oy), Inches(ow), Inches(oh))
    shp.fill.solid()
    shp.fill.fore_color.rgb = color
    shp.line.fill.background()
    shp.shadow.inherit = False

text(slide, 0.85, 0.8, 12.0, 0.32, "TEAM · 从 0 到 1", size=11.5, color=GOLD, bold=True)
text(slide, 0.85, 1.35, 11.6, 0.8, "四个人，完成一次完整交付", size=36, color=CREAM, bold=True)
text(slide, 0.85, 2.45, 11.0, 0.4, "后端链路 · 前端可视化 · 文档解析 · 部署与演示", size=16, color=RGBColor(0xC9, 0xD8, 0xCC))
team = [
    ("罗勇添", "项目统筹 / 后端架构", "NL2SQL · 模型接入 · 部署"),
    ("辛嘉炜", "前端开发 / 图表交互", "Vue 3 · ECharts · E2E"),
    ("林俊宁", "文档解析 / 内容", "RAG · 测试数据 · 文档视频"),
    ("林龙键", "指导老师", "选题 · 方案评审 · 材料把关"),
]
for i, (name, role, desc) in enumerate(team):
    x = 0.85 + i * 2.95
    rect(slide, x, 3.45, 2.68, 1.85, RGBColor(0x27, 0x48, 0x35), RGBColor(0x4E, 0x6B, 0x57), radius=0.1)
    text(slide, x + 0.2, 3.62, 2.2, 0.34, name, size=17, color=CREAM, bold=True)
    text(slide, x + 0.2, 4.02, 2.3, 0.28, role, size=10, color=GOLD, bold=True)
    text(slide, x + 0.2, 4.42, 2.25, 0.7, desc, size=9.5, color=RGBColor(0xB9, 0xCB, 0xBD), spacing=1.25)
rect(slide, 0.85, 5.85, 11.6, 0.06, GOLD, radius=0.5)
text(slide, 0.85, 6.12, 8.6, 0.6, "问数 AskData · 让数据分析回归对话", size=18, color=CREAM, bold=True)
text(slide, 9.3, 6.15, 3.3, 0.5, "广东科贸职业学院\n指导老师：林龙键", size=9.8, color=RGBColor(0xA9, 0xBD, 0xAE), align=PP_ALIGN.RIGHT, spacing=1.3)
footer(slide, 14, dark=True)

prs.save(OUT)
print("pptx ->", OUT, f"({OUT.stat().st_size / 1024:.0f} KB), slides={len(prs.slides)}")
