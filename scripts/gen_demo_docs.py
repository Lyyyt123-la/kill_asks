"""生成文档/图片演示素材：PDF 财报、Word 复盘报告、表格截图（用于验证 PDF/Word/视觉识别）。

用法：backend\\.venv\\Scripts\\python.exe scripts/gen_demo_docs.py
输出：demo_data/documents/
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.shared import Pt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "demo_data" / "documents"
OUT.mkdir(parents=True, exist_ok=True)

pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
CN_STYLE = ParagraphStyle(name="cn", fontName="STSong-Light", fontSize=11, leading=19, spaceAfter=8)
CN_TITLE = ParagraphStyle(name="cntitle", fontName="STSong-Light", fontSize=18, leading=26, spaceAfter=14)


def build_pdf() -> Path:
    path = OUT / "2025年Q3经营情况报告.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=A4, title="2025年Q3经营情况报告")
    story = [
        Paragraph("2025 年 Q3 经营情况报告", CN_TITLE),
        Paragraph(
            "本季度公司整体销售额 4,621 万元，较去年同期增长 3.2%。华东区实现销售额 1,853.94 万元，"
            "仍为第一大区域，但同比下滑 11.2%，是拖累整体增速的主要原因。",
            CN_STYLE,
        ),
        Paragraph(
            "分品类看，3C 数码销售额 3,881.57 万元，占比接近七成，是增长的核心引擎；"
            "女装受尺码问题影响，退货率上升至 6.4%，需要重点跟进。",
            CN_STYLE,
        ),
        Paragraph("表 1：2025 年 Q3 各区域销售额与同比", CN_STYLE),
    ]
    table_data = [
        ["区域", "销售额（万元）", "同比", "退货率"],
        ["华东", "1853.94", "-11.2%", "6.4%"],
        ["华南", "1076.43", "+4.6%", "4.9%"],
        ["华北", "878.66", "+2.1%", "5.2%"],
        ["西南", "691.66", "+7.8%", "4.1%"],
        ["东北", "534.89", "-3.4%", "5.8%"],
        ["华中", "585.36", "+1.2%", "5.0%"],
    ]
    table = Table(table_data, colWidths=[70, 110, 70, 70])
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8F0EA")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#999999")),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
    ]))
    story.append(table)
    story.append(Spacer(1, 14))
    story.append(Paragraph(
        "风险提示：双 11 大促期间，华东区未参加平台主活动，8 月销售额环比下降 16.7%，"
        "为全年最低点；9 月已环比回升 4.5%。整体判断：需求并未萎缩，主要是促销投入与退货率问题。",
        CN_STYLE,
    ))
    doc.build(story)
    return path


def build_docx() -> Path:
    path = OUT / "双11大促复盘摘要.docx"
    doc = Document()
    title = doc.add_heading("双 11 大促复盘摘要", level=1)
    title.style.font.size = Pt(18)
    doc.add_paragraph(
        "本次双 11 大促期间（11 月 1 日–11 月 12 日），平台整体销售额 3,067.59 万元，"
        "其中 11 月 11 日当天销售额 809.78 万元，占大促总销售额的 26.4%。"
    )
    doc.add_paragraph(
        "分渠道看，小程序退款率最高（5.57%），天猫 5.53% 紧随其后，京东最低（5.03%）。"
        "各渠道退款率整体接近，没有明显断层，说明退款问题更可能来自商品与尺码本身。"
    )
    doc.add_paragraph("重点结论：")
    for item in (
        "1. 双 11 销售额峰值出现在凌晨 0 点，单小时 147.90 万元，是次高峰（20 点）的 3.05 倍；",
        "2. 凌晨 3–5 点为低谷，建议优化该时段的客服与投放排班；",
        "3. 女装退货率 6.4%，较上季度上升 1.8 个百分点，需要排查尺码表调整的影响。",
    ):
        doc.add_paragraph(item)
    table = doc.add_table(rows=1, cols=4)
    table.style = "Table Grid"
    for cell, text in zip(table.rows[0].cells, ["渠道", "退款率", "订单量", "客单价"]):
        cell.text = text
    data = [
        ["小程序", "5.57%", "8,120", "¥148.3"],
        ["天猫", "5.53%", "15,430", "¥156.2"],
        ["抖音", "5.15%", "9,860", "¥151.7"],
        ["京东", "5.03%", "7,402", "¥159.5"],
    ]
    for row in data:
        cells = table.add_row().cells
        for cell, text in zip(cells, row):
            cell.text = text
    doc.save(path)
    return path


def build_image() -> Path:
    path = OUT / "各渠道退款率截图.png"
    width, height = 860, 460
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    font_path = "C:/Windows/Fonts/msyh.ttc"
    try:
        title_font = ImageFont.truetype(font_path, 26)
        body_font = ImageFont.truetype(font_path, 20)
        small_font = ImageFont.truetype(font_path, 17)
    except OSError:
        title_font = body_font = small_font = ImageFont.load_default()

    draw.text((40, 26), "双 11 各渠道退款率（截图）", fill="#1F2937", font=title_font)
    draw.text((40, 72), "数据来源：电商后台 · 2025-11-12 导出", fill="#6B7280", font=small_font)

    headers = ["渠道", "退款率", "订单量", "客单价"]
    rows = [
        ["小程序", "5.57%", "8,120", "148.3"],
        ["天猫", "5.53%", "15,430", "156.2"],
        ["抖音", "5.15%", "9,860", "151.7"],
        ["京东", "5.03%", "7,402", "159.5"],
    ]
    left, top, row_h = 40, 120, 56
    col_widths = [200, 180, 200, 200]
    for index, header in enumerate(headers):
        x = left + sum(col_widths[:index])
        draw.rectangle([x, top, x + col_widths[index], top + row_h], fill="#E8F0EA", outline="#9CA3AF")
        draw.text((x + 22, top + 16), header, fill="#1F2937", font=body_font)
    for row_index, row in enumerate(rows):
        y = top + row_h * (row_index + 1)
        for col_index, value in enumerate(row):
            x = left + sum(col_widths[:col_index])
            draw.rectangle([x, y, x + col_widths[col_index], y + row_h], outline="#D1D5DB")
            draw.text((x + 22, y + 16), value, fill="#374151", font=body_font)
    draw.text((40, top + row_h * 6 + 22), "结论：各渠道退款率接近，小程序略高 0.54pp。", fill="#B45309", font=small_font)
    image.save(path)
    return path


def main() -> None:
    pdf_path = build_pdf()
    docx_path = build_docx()
    image_path = build_image()
    for path in (pdf_path, docx_path, image_path):
        print(f"{path.name:40s} {path.stat().st_size / 1024:8.1f} KB")


if __name__ == "__main__":
    main()
