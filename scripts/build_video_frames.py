# -*- coding: utf-8 -*-
"""渲染问数 AskData 演示视频：1080p、配音、烧录字幕，混剪录屏/截图/架构图/难点卡片。"""
from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SHOTS = DOCS / "screenshots"
FRONT = ROOT / "frontend"
FFMPEG = FRONT / "node_modules/@ffmpeg-installer/win32-x64/ffmpeg.exe"
TIMELINE = FRONT / ".video_timeline.json"
FRAMES = FRONT / ".video_frames"
CLIP_FRAMES = FRONT / ".video_clip"
OUT = DOCS / "问数AskData_演示视频_成片.mp4"
AUDIO = DOCS / "配音_成片.wav"
FPS = 8
W, H = 1920, 1080

BG = (247, 245, 239)
INK = (35, 33, 29)
INK2 = (62, 58, 50)
GRAY = (122, 116, 104)
BRAND = (31, 61, 46)
BRAND2 = (47, 107, 79)
BRAND_TINT = (232, 240, 234)
ACCENT = (217, 164, 65)
WHITE = (255, 255, 255)

FONT_PATH = "C:/Windows/Fonts/msyh.ttc"
BOLD_PATH = "C:/Windows/Fonts/msyhbd.ttc"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(BOLD_PATH if bold else FONT_PATH, size, index=0)


def rounded(draw: ImageDraw.ImageDraw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def wrap(draw, text, fnt, max_width):
    lines = []
    current = ""
    for char in text:
        if char == "\n":
            lines.append(current)
            current = ""
            continue
        trial = current + char
        if draw.textlength(trial, font=fnt) <= max_width:
            current = trial
        else:
            lines.append(current)
            current = char
    if current:
        lines.append(current)
    return lines


def cover(image: Image.Image, width: int, height: int) -> Image.Image:
    ratio = max(width / image.width, height / image.height)
    resized = image.resize((max(1, int(image.width * ratio)), max(1, int(image.height * ratio))), Image.LANCZOS)
    left = (resized.width - width) // 2
    top = (resized.height - height) // 2
    return resized.crop((left, top, left + width, top + height))


def screenshot(name: str) -> Image.Image:
    return Image.open(SHOTS / name).convert("RGB")


def blank(color=BG) -> Image.Image:
    return Image.new("RGB", (W, H), color)


def paste_shadow(base: Image.Image, image: Image.Image, box, radius=18, shadow=28):
    x, y, w, h = box
    card = image.resize((w, h), Image.LANCZOS)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w, h), radius=radius, fill=255)
    shadow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow_layer).rounded_rectangle((x + 8, y + 12, x + w + 8, y + h + 12), radius=radius, fill=(0, 0, 0, shadow))
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(14))
    base.paste(shadow_layer, (0, 0), shadow_layer)
    base.paste(card, (x, y), mask)


def header(base: Image.Image, title: str, kicker="问数 AskData · 演示"):
    draw = ImageDraw.Draw(base)
    rounded(draw, (48, 42, 48 + 700, 42 + 64), 18, (255, 255, 255, 235))
    draw.ellipse((66, 56, 98, 88), fill=BRAND)
    draw.text((74, 60), "问", font=font(19, True), fill=WHITE)
    draw.text((110, 58), "问数 AskData", font=font(21, True), fill=BRAND)
    draw.text((280, 60), kicker, font=font(16), fill=GRAY)
    draw.text((1012, 58), title, font=font(22, True), fill=INK2)


# ---------------- 卡片渲染 ----------------
def card_title() -> Image.Image:
    base = blank((18, 42, 32))
    draw = ImageDraw.Draw(base)
    for index, radius in enumerate(range(1060, 300, -80)):
        draw.ellipse((1440 - radius, 120 + index * 6, 1440 + radius, 120 + radius * 2 + index * 6), outline=(34, 70, 52))
    draw.text((120, 240), "问数 AskData", font=font(92, True), fill=WHITE)
    draw.text((126, 372), "对话式数据分析平台", font=font(44), fill=(205, 224, 210))
    draw.text((126, 448), "上传数据 / 文档，用一句中文提问，拿到 SQL、图表与洞察", font=font(26), fill=(165, 190, 173))
    chips = ["取数等两天", "不会写 SQL", "PDF / 截图难分析"]
    x = 126
    for chip in chips:
        width = int(draw.textlength(chip, font=font(22))) + 44
        rounded(draw, (x, 540, x + width, 540 + 52), 26, (45, 88, 65))
        draw.text((x + 22, 550), chip, font=font(22), fill=(220, 235, 223))
        x += width + 16
    draw.text((126, 780), "广东科贸职业学院 · 指导老师 林龙键 · 罗勇添 / 辛嘉炜 / 林俊宁", font=font(22), fill=(150, 178, 156))
    draw.line((126, 740, 700, 740), fill=(64, 110, 84), width=2)
    return base


def card_welcome() -> Image.Image:
    base = cover(screenshot("01-welcome.png"), W, H)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for i in range(700):
        alpha = int(190 * (1 - i / 700))
        draw.rectangle((0, 0, i, H), fill=(15, 32, 24, alpha))
    base.paste(Image.new("RGB", (W, H), (0, 0, 0)), (0, 0), overlay)
    draw = ImageDraw.Draw(base)
    draw.text((100, 250), "一句话提问", font=font(64, True), fill=WHITE)
    draw.text((100, 340), "SQL · 图表 · 洞察 · 文档问答", font=font(36), fill=(200, 222, 205))
    items = ["自动生成可核对 SQL", "ECharts 自动图表", "PDF / Word / 截图数据化", "多轮追问与澄清"]
    y = 440
    for item in items:
        draw.ellipse((104, y + 8, 124, y + 28), fill=ACCENT)
        draw.text((142, y), item, font=font(26), fill=(235, 243, 237))
        y += 64
    return base


def card_architecture() -> Image.Image:
    base = blank()
    draw = ImageDraw.Draw(base)
    draw.text((90, 150), "技术架构", font=font(54, True), fill=BRAND)
    draw.text((92, 224), "前端 Vue3 + ECharts ｜ FastAPI ｜ DuckDB + SQLite ｜ 百炼 qwen-plus / qwen3-vl-plus", font=font(22), fill=GRAY)
    image = screenshot("00-architecture.png")
    paste_shadow(base, image, (110, 280, 1700, 660), radius=16, shadow=36)
    draw.text((150, 250), "模型可替换 · 数据不出域 · SQL 可核对", font=font(22), fill=BRAND2)
    return base


def card_robust() -> Image.Image:
    base = blank()
    draw = ImageDraw.Draw(base)
    draw.text((90, 150), "鲁棒性：让演示现场不翻车", font=font(50, True), fill=BRAND)
    paste_shadow(base, screenshot("04-inspector.png"), (90, 260, 1080, 800), radius=16)
    items = [
        ("模糊问题", "主动澄清：7 天 / 30 天 / 本月"),
        ("SQL 报错", "报错回喂模型，自动修复 ≤ 2 次"),
        ("时间口径", "以数据实际时间范围为基准"),
        ("模型超时", "自动降级演示模式，界面不中断"),
    ]
    y = 270
    for title, desc in items:
        rounded(draw, (1210, y, 1830, y + 120), 16, WHITE, outline=(228, 222, 208))
        draw.text((1236, y + 18), title, font=font(24, True), fill=BRAND)
        draw.text((1236, y + 60), desc, font=font(19), fill=GRAY)
        y += 128
    return base


def card_ai() -> Image.Image:
    base = blank()
    draw = ImageDraw.Draw(base)
    draw.text((90, 140), "AI 技术亮点：准确、安全、可解释", font=font(48, True), fill=BRAND)
    items = [
        ("01", "Schema 注入", "类型 / 样例 / 枚举 / 空值率 / 时间范围全部交给模型"),
        ("02", "SQL 只读校验", "sqlglot：单条 SELECT、表名白名单、强制 LIMIT、执行超时"),
        ("03", "失败自动修复", "数据库报错回喂模型，最多重试 2 次"),
        ("04", "洞察二次生成", "结论必须引用真实查询数字，禁止编造"),
    ]
    y = 240
    for number, title, desc in items:
        rounded(draw, (90, y, 1180, y + 124), 18, WHITE, outline=(228, 222, 208))
        rounded(draw, (114, y + 22, 114 + 96, y + 106), 14, BRAND_TINT)
        draw.text((128, y + 28), number, font=font(30, True), fill=BRAND)
        draw.text((236, y + 20), title, font=font(28, True), fill=INK2)
        draw.text((236, y + 66), desc, font=font(19), fill=GRAY)
        y += 146
    # 右侧评测卡
    rounded(draw, (1240, 240, 1820, 780), 18, (31, 61, 46))
    draw.text((1280, 272), "模型实测", font=font(26, True), fill=(210, 230, 216))
    rows = [("qwen-plus（采用）", "8–12 s"), ("glm-5.2-fast", "4–6 s"), ("qwen3.8-max", "30–90 s")]
    y = 340
    for name, value in rows:
        draw.text((1280, y), name, font=font(22), fill=(240, 246, 241))
        draw.text((1680, y), value, font=font(22, True), fill=ACCENT)
        y += 92
    draw.text((1280, 640), "6 类典型问题 6/6 正确", font=font(22, True), fill=(200, 224, 208))
    draw.text((1280, 684), "复杂问题可自动修复后成功", font=font(19), fill=(160, 188, 170))
    return base


def card_difficulty() -> Image.Image:
    base = blank((26, 32, 27))
    draw = ImageDraw.Draw(base)
    draw.text((100, 150), "目前的难点", font=font(54, True), fill=WHITE)
    items = [
        ("数据形态复杂", "PDF 复杂版式、扫描件、合并单元格，很难一次还原"),
        ("口径不统一", "同名指标口径不一致，跨部门分析容易失真"),
        ("多表关系缺失", "没人在上传时告诉你表之间怎么 JOIN"),
        ("模型输出不稳定", "长链路推理偶发格式错误或答非所问"),
    ]
    y = 270
    for index, (title, desc) in enumerate(items, start=1):
        rounded(draw, (100, y, 1240, y + 116), 16, (38, 48, 40))
        draw.text((128, y + 18), f"0{index}", font=font(30, True), fill=ACCENT)
        draw.text((212, y + 16), title, font=font(29, True), fill=(240, 246, 241))
        draw.text((212, y + 66), desc, font=font(19), fill=(178, 200, 184))
        y += 138
    # 右侧截图条
    shots = [("10-doc-ready.png", "PDF 表格提取"), ("13-image-extracted.png", "截图识别")]
    y = 280
    for name, label in shots:
        image = screenshot(name)
        paste_shadow(base, image, (1300, y, 520, 260), radius=14, shadow=20)
        draw.text((1300, y + 270), label, font=font(19), fill=(190, 210, 194))
        y += 320
    return base


def card_tech() -> Image.Image:
    base = blank()
    draw = ImageDraw.Draw(base)
    draw.text((90, 140), "技术难点：我们把它们拆成了四件事", font=font(46, True), fill=BRAND)
    columns = [
        ("NL2SQL 准确率", ["Schema 注入", "数据时间口径", "中文别名约束", "少样本校准"]),
        ("SQL 安全", ["只读连接", "单条 SELECT", "表名白名单", "强制 LIMIT + 超时"]),
        ("幻觉与可信", ["洞察二次生成", "强制引用真实数字", "SQL / 引用可核对", "失败时明确报错"]),
        ("时延与稳定", ["模型实测选型", "失败自动重试", "演示模式兜底", "前端步骤可视化"]),
    ]
    x = 90
    width = 420
    for title, items in columns:
        rounded(draw, (x, 270, x + width - 30, 810), 20, WHITE, outline=(228, 222, 208))
        draw.text((x + 26, 300), title, font=font(26, True), fill=BRAND)
        draw.line((x + 26, 366, x + width - 56, 366), fill=(230, 224, 210), width=2)
        y = 400
        for item in items:
            draw.ellipse((x + 28, y + 8, x + 42, y + 22), fill=ACCENT)
            draw.text((x + 56, y), item, font=font(20), fill=INK2)
            y += 72
        x += width
    return base


def card_scope() -> Image.Image:
    base = blank()
    draw = ImageDraw.Draw(base)
    draw.text((90, 140), "能用在哪些场景", font=font(52, True), fill=BRAND)
    tiles = [
        ("业务自助取数", "运营 / 市场直接问数，\n不再排队等分析师"),
        ("财报与报告解读", "PDF / Word 表格进数据集，\n关键数字可引用核对"),
        ("大促与经营复盘", "多轮追问下钻，\n自动图表 + 结论"),
        ("教学与科研", "零环境分析，\n上传即用、SQL 可学习"),
    ]
    positions = [(90, 250), (990, 250), (90, 560), (990, 560)]
    for (title, desc), (x, y) in zip(tiles, positions):
        rounded(draw, (x, y, x + 840, y + 260), 22, WHITE, outline=(228, 222, 208))
        draw.ellipse((x + 34, y + 26, x + 82, y + 74), fill=BRAND_TINT)
        draw.text((x + 46, y + 30), "⇢", font=font(28, True), fill=BRAND)
        draw.text((x + 110, y + 26), title, font=font(30, True), fill=INK2)
        draw.multiline_text((x + 34, y + 110), desc, font=font(22), fill=GRAY, spacing=14)
    return base


def card_roadmap() -> Image.Image:
    base = blank()
    draw = ImageDraw.Draw(base)
    draw.text((90, 140), "边界与下一步", font=font(52, True), fill=BRAND)
    draw.text((92, 220), "当前：单表分析为主的端到端原型 · 需要模型 Key · 上传 ≤ 30MB", font=font(22), fill=GRAY)
    steps = [
        ("近期", "多表关联 + 语义层", "口径可配置，支持跨表 JOIN"),
        ("中期", "看板分享 + 更多数据源", "MySQL / 飞书表格 / 企业微信文档"),
        ("长期", "50+ 题评测集", "量化准确率、修复率与延迟"),
    ]
    y = 320
    for index, (phase, title, desc) in enumerate(steps, start=1):
        rounded(draw, (110, y, 1810, y + 148), 20, WHITE, outline=(228, 222, 208))
        rounded(draw, (140, y + 34, 140 + 120, y + 114), 16, BRAND)
        draw.text((162, y + 50), phase, font=font(22, True), fill=WHITE)
        draw.text((300, y + 30), title, font=font(30, True), fill=INK2)
        draw.text((300, y + 84), desc, font=font(21), fill=GRAY)
        y += 172
    return base


def card_team() -> Image.Image:
    base = blank((18, 42, 32))
    draw = ImageDraw.Draw(base)
    draw.text((120, 220), "问数 AskData", font=font(76, True), fill=WHITE)
    draw.text((124, 330), "让数据回答", font=font(40), fill=(205, 224, 210))
    draw.line((124, 430, 760, 430), fill=(64, 110, 84), width=2)
    draw.text((124, 480), "广东科贸职业学院", font=font(28), fill=(220, 235, 223))
    draw.text((124, 540), "指导老师：林龙键", font=font(24), fill=(180, 205, 187))
    draw.text((124, 596), "团队成员：罗勇添 · 辛嘉炜 · 林俊宁", font=font(24), fill=(180, 205, 187))
    draw.text((124, 760), "赛道二 · AI WEB 网页开发挑战赛", font=font(22), fill=(150, 178, 156))
    return base


CARDS = {
    "welcome": card_welcome,
    "architecture": card_architecture,
    "robust": card_robust,
    "ai": card_ai,
    "difficulty": card_difficulty,
    "tech": card_tech,
    "scope": card_scope,
    "roadmap": card_roadmap,
    "team": card_team,
}


def ensure_clip_frames() -> list[Path]:
    CLIP_FRAMES.mkdir(parents=True, exist_ok=True)
    existing = sorted(CLIP_FRAMES.glob("f_*.jpg"))
    if len(existing) > 700:
        return existing
    for path in CLIP_FRAMES.glob("*.jpg"):
        path.unlink()
    subprocess.run(
        [str(FFMPEG), "-hide_banner", "-loglevel", "error", "-i", str(DOCS / "demo_recording.mp4"),
         "-vf", "fps=10", "-q:v", "2", str(CLIP_FRAMES / "f_%05d.jpg")],
        check=True,
    )
    return sorted(CLIP_FRAMES.glob("f_*.jpg"))


def subtitle_overlay(base: Image.Image, text: str, block_title: str, progress: float):
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    # 顶部章节标签
    label = f"{block_title}"
    label_font = font(20, True)
    width = int(draw.textlength(label, font=label_font)) + 32
    rounded(draw, (W - width - 48, 36, W - 48, 76), 12, (31, 61, 46, 200))
    draw.text((W - width - 30, 43), label, font=label_font, fill=(245, 250, 246))
    # 底部字幕
    fnt = font(31, True)
    while True:
        lines = wrap(draw, text, fnt, 1740)
        if len(lines) <= 2:
            break
        size = fnt.size - 2
        fnt = font(size, True)
    line_height = int(fnt.size * 1.45)
    box_height = 40 + line_height * len(lines)
    top = H - 96 - box_height
    rounded(draw, (60, top, W - 60, top + box_height), 18, (12, 18, 14, 200))
    y = top + 18
    for line in lines:
        line_width = draw.textlength(line, font=fnt)
        draw.text(((W - line_width) / 2, y), line, font=fnt, fill=(250, 250, 246))
        y += line_height
    # 进度条
    draw.rectangle((0, H - 6, int(W * progress), H), fill=(217, 164, 65, 255))
    draw.rectangle((int(W * progress), H - 6, W, H), fill=(60, 70, 62, 160))
    return Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")


def still_frame(card: Image.Image, progress: float) -> Image.Image:
    scale = 1.0 + 0.05 * progress
    crop_w = int(W / scale)
    crop_h = int(H / scale)
    left = (W - crop_w) // 2
    top = (H - crop_h) // 2
    return card.crop((left, top, left + crop_w, top + crop_h)).resize((W, H), Image.LANCZOS)


def clip_frame(frames: list[Path], start: float, end: float, progress: float) -> Image.Image:
    target = start + (end - start) * progress
    index = int(target * 10)
    index = max(0, min(len(frames) - 1, index))
    image = Image.open(frames[index]).convert("RGB")
    return cover(image, W, H)


def main() -> None:
    timeline = json.loads(TIMELINE.read_text(encoding="utf-8"))
    FRAMES.mkdir(parents=True, exist_ok=True)
    for path in FRAMES.glob("*.jpg"):
        path.unlink()
    clip = ensure_clip_frames()
    print("clip frames:", len(clip))

    cards = {key: builder() for key, builder in CARDS.items()}
    cards["title"] = card_title()
    blocks = timeline["blocks"]
    frame_index = 0
    for block_index, block in enumerate(blocks):
        next_start = blocks[block_index + 1]["start"] if block_index + 1 < len(blocks) else timeline["total"]
        duration = max(0.2, next_start - block["start"])
        count = max(1, round(duration * FPS))
        visual = block["visual"]
        for i in range(count):
            progress = i / max(1, count - 1)
            if visual.startswith("clip:"):
                _, start, end = visual.split(":")
                base = clip_frame(clip, float(start), float(end), progress)
            elif visual == "title":
                base = still_frame(cards["title"], progress)
            else:
                base = still_frame(cards.get(visual, cards["team"]), progress)
            # 当前句子
            sentence = block["sentences"][-1]["text"]
            for item in block["sentences"]:
                if item["start"] <= block["start"] + duration * progress <= item["end"] + 0.001:
                    sentence = item["text"]
                    break
            base = subtitle_overlay(base, sentence, block["title"], (block["start"] + duration * progress) / timeline["total"])
            base.save(FRAMES / f"frame_{frame_index:05d}.jpg", quality=84)
            frame_index += 1
        print(f"{block['title']}: {count} frames")

    print("total frames:", frame_index)
    subprocess.run(
        [str(FFMPEG), "-y", "-hide_banner", "-loglevel", "error",
         "-framerate", str(FPS), "-i", str(FRAMES / "frame_%05d.jpg"),
         "-i", str(AUDIO),
         "-c:v", "libx264", "-preset", "medium", "-crf", "21",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
         "-shortest", "-movflags", "+faststart", str(OUT)],
        check=True,
    )
    print("video ->", OUT, f"{OUT.stat().st_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
