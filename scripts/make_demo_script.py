# -*- coding: utf-8 -*-
"""生成 5-8 分钟演示视频的逐字配音稿、字幕与录制操作卡（按语速估算时间轴，不依赖 TTS）。

输出：docs/录制与配音脚本_7分钟.md、docs/字幕_演示.srt、docs/配音稿.txt
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
OUT_MD = DOCS / "录制与配音脚本_7分钟.md"
OUT_SRT = DOCS / "字幕_演示.srt"
OUT_TXT = DOCS / "配音稿.txt"
TARGET = 390.0
GAP = 0.45
SPEED = 4.0  # 普通话朗读约 4 字/秒

BLOCKS = [
    ("01 片头：痛点",
     "标题页（作品名 + 一句话定位）→ 三道门槛关键词动画",
     "剪映做 3 张字幕卡：①问数 AskData ②对话式数据分析平台 ③等两天→等十秒；无需录屏。",
     "业务同学想查一个数，往往要提需求、排队、等上两天。不会写 SQL、报表永远慢半拍，数据还散落在 PDF 和截图里。这三道门槛，让一线同学只能靠感觉做决策。"),
    ("02 产品定位",
     "欢迎页 → 载入示例数据后的数据集卡片（录屏 00:00–00:10）",
     "录屏 0–10 秒原速播放；结尾停在 36,000 行 · 10 列的数据集卡片。",
     "问数 AskData 是一个对话式数据分析平台。上传数据或者文档，用一句中文提问，它就能完成查询、自动图表和智能洞察，还能把 PDF、Word、截图里的表格变成可分析的数据集。"),
    ("03 技术架构",
     "架构图 docs/screenshots/00-architecture.png",
     "截图缓推：讲到哪一层放大哪一层（剪映关键帧缩放）。",
     "整体是前后端分离架构。前端用 Vue3 加 ECharts，后端用 FastAPI；分析数据放在 DuckDB，元数据用 SQLite。大模型通过 OpenAI 兼容协议接入阿里云百炼的 qwen-plus，截图识别用 qwen3-vl-plus。这样既保留了数据库的分析性能，也让模型可以随时替换。"),
    ("04 数据问答演示",
     "录屏 00:10–00:30：区域销售额对比 → 图表 + 洞察 + SQL",
     "录屏段变速 0.6 倍；出图后停 2 秒，鼠标指向华东 1853.94 万和 SQL 条。",
     "先看最常用的场景。打开示例数据，直接问：各区域的销售额对比。几秒钟，系统生成了 SQL、柱状图和结论：华东销售额 1853.94 万元排名第一，领先第二名华南 777 万元。展开 SQL 可以看到，它自动排除了空值、按销售额降序，结论不是黑盒。"),
    ("05 多轮追问 + 检查器",
     "录屏 00:30–00:48：最低三个品类 → 图表 → 检查器（结果表 / SQL / 字段）",
     "0.6 倍放慢；讲「记住上一轮」时停在用户问题与结论；讲检查器时打开右侧抽屉。",
     "继续追问：销售额最低的三个品类。它记住了上一轮的数据和口径，直接给出食品、美妆、女装，并指出食品只有 123 万元，不到女装的四分之一。点开右侧检查器，结果表、SQL、执行耗时全部可以核对。"),
    ("06 PDF 财报数据化",
     "录屏 00:48–01:03：上传 PDF → 文档就绪（6×4 表格）→ 文档问答 + 引用",
     "重点停顿：①表格被提取为数据集 ②回答中的引用片段 [1]（可用红框标注）。",
     "更关键的是，数据不只在 Excel 里。上传一份 PDF 财报，系统自动提取正文和表格，六行区域数据直接变成可分析的数据集。问：华东区 Q3 销售额和同比是多少？它回答 1853.94 万元、同比下降百分之十一点二，并且标注了引用片段，可以逐句核对。"),
    ("07 图片截图识别",
     "录屏 01:03–01:17：上传退款率截图 → 4×4 数据集 → 问答 5.57%",
     "0.6 倍放慢；识别完成停 2 秒展示 4 行 4 列；回答出现时给结论加字幕。",
     "连截图也能用。上传渠道退款率截图，视觉模型自动识别成四行四列的数据集。问哪个渠道退款率最高，它回答：小程序，百分之五点五七。"),
    ("08 澄清与鲁棒性",
     "录屏结尾「最近卖得怎么样」→ 澄清卡片；配 SQL 自动修复截图",
     "讲澄清时停在三个选项；讲自动修复时切 04-inspector 截图或文字卡。",
     "遇到说不清的问题，比如最近卖得怎么样，它会主动反问你要看七天、三十天还是本月。SQL 写错也不会崩，系统会把数据库报错回喂给模型，自动修复之后重新执行。"),
    ("09 AI 技术亮点",
     "架构图局部 + 3 张文字卡（Schema 注入 / 只读校验 / 自动修复）+ 模型评测表",
     "文字卡各 4-6 秒；最后放评测表，念出 8–12 秒、6/6 正确两个数字。",
     "AI 部分我们重点做了三件事。第一，Schema 注入：字段类型、样例、枚举、空值率和时间范围都交给模型，并且锁定数据时间口径；第二，SQL 只读校验：用 sqlglot 只允许单条 SELECT，做表名白名单、强制 LIMIT 和执行超时；第三，失败自动修复和结论二次生成，洞察必须引用真实数字。模型选型上，我们实测了百炼上的多个模型，最终选择 qwen-plus，单问八到十二秒，质量和速度最平衡。在六类典型问题上全部生成正确结果，复杂问题还能自动修复后成功。"),
    ("10 价值与规划",
     "三屏字幕：对业务 / 对分析师 / 对组织；真实截图轮播",
     "每屏 4-6 秒；规划逐行出现。",
     "对业务同学，它把等两天变成等十秒；对分析师，它把重复取数交给 AI；对组织，PDF 和截图里的数据第一次变成可分析的资产。下一步我们会补上多表关联、看板分享和更严格的评测集，让它在真实业务里跑得更稳。"),
    ("11 团队与结尾",
     "团队信息页：作品名 + 学校 + 指导老师 + 成员 → slogan 定格",
     "团队卡停 5-6 秒；背景音乐渐弱，最后出现「问数 AskData，让数据回答」。",
     "广东科贸职业学院，指导老师林龙键，团队成员罗勇添、辛嘉炜、林俊宁。问数 AskData，让数据回答。感谢观看。"),
]


def fmt_srt(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def main() -> None:
    durations = [max(6.0, len(block[3]) / SPEED) for block in BLOCKS]
    total = sum(durations) + GAP * (len(BLOCKS) - 1)
    extra = max(0.0, (TARGET - total) / (len(BLOCKS) - 1))
    gap = GAP + extra

    timings = []
    cursor = 0.0
    for duration in durations:
        timings.append((cursor, cursor + duration))
        cursor += duration + gap
    total = cursor - gap

    srt = []
    for index, (start, end) in enumerate(timings, start=1):
        srt.append(f"{index}\n{fmt_srt(start)} --> {fmt_srt(end)}\n{BLOCKS[index - 1][3]}\n")
    OUT_SRT.write_text("\n".join(srt), encoding="utf-8")
    OUT_TXT.write_text("\n\n".join(block[3] for block in BLOCKS), encoding="utf-8")

    md = ["# 问数 AskData · 录制与配音脚本（5–8 分钟版）", ""]
    md.append(f"> 目标成片：**约 {total / 60:.1f} 分钟**（配音可直接用剪映「文本朗读」，也可自己念；字幕 `字幕_演示.srt` 已按本时间轴生成）。")
    md.append("> 录屏素材：`demo_recording.mp4`（1 分 17 秒）；其余画面用 `截图/` 里的截图、架构图与文字卡补齐。")
    md.append("")
    md.append("## 一、时间轴总表")
    md.append("")
    md.append("| 时间 | 段落 | 画面/素材 | 操作 | 口播要点 |")
    md.append("|---|---|---|---|---|")
    for index, block in enumerate(BLOCKS):
        start, end = timings[index]
        md.append(f"| {fmt_srt(start)[:8]}–{fmt_srt(end)[:8]} | {block[0]} | {block[1]} | {block[2]} | {block[3][:38]}… |")
    md.append("")
    md.append("## 二、逐段口播稿（直接粘贴到剪映「文本朗读」）")
    md.append("")
    for index, block in enumerate(BLOCKS):
        start, end = timings[index]
        md.append(f"### {block[0]}（{fmt_srt(start)[:8]}–{fmt_srt(end)[:8]}）")
        md.append("")
        md.append(f"- **画面**：{block[1]}")
        md.append(f"- **操作**：{block[2]}")
        md.append(f"- **口播**：{block[3]}")
        md.append("")
    md.append("## 三、剪映制作步骤（约 15 分钟）")
    md.append("")
    md.append("1. 新建 1920×1080 / 30fps 项目，导入 `demo_recording.mp4`、`字幕_演示.srt`；")
    md.append("2. 把录屏按画面切成 6 段：载入数据 / 区域对比 / 最低品类 / 检查器 / PDF 问答 / 图片识别 / 澄清；")
    md.append("3. 按时间轴把录屏放到 01:00–04:30 区间的对应段落，**录屏片段统一变速 0.6–0.7 倍**，与配音节奏对齐；空档用 `截图/` 的架构图、检查器、文档截图补齐；")
    md.append("4. 字幕：导入 `字幕_演示.srt`；或全选字幕 → 文本朗读，用 AI 声音替换；")
    md.append("5. 背景音乐 -25dB，片头片尾各留 5 秒；导出 MP4（1080p、30fps，文件名 `问数AskData_演示视频_广东科贸职业学院.mp4`）。")
    md.append("")
    md.append("## 四、操作卡（按当前界面实际按钮）")
    md.append("")
    md.append("| 步骤 | 操作 | 预期画面 |")
    md.append("|---|---|---|")
    steps = [
        ("打开 http://127.0.0.1:8000", "欢迎页，右上角显示 qwen-plus"),
        ("点击「载入示例数据」", "数据集就绪：36,000 行 · 10 列"),
        ("输入「各区域的销售额对比」回车", "约 10 秒：柱状图 + 洞察 + SQL"),
        ("点底部 SQL 条展开", "显示 SELECT region AS 「区域」…"),
        ("输入「销售额最低的3个品类」回车", "约 10 秒：食品/美妆/女装 升序柱状图"),
        ("点右上角检查器图标", "右侧抽屉：结果表 / SQL / 字段 / 执行耗时"),
        ("点左侧「上传数据/文档」→ 选择 PDF 财报", "约 2 秒：文档就绪卡 + 已提取 6×4 表格"),
        ("输入「这份报告里华东区 Q3 的销售额和同比是多少？」", "回答 1853.94 万 / -11.2%，带引用 [1]"),
        ("点「文档与截图」右侧 +，上传退款率截图", "视觉识别约 3–5 秒：4 行 4 列数据集"),
        ("输入「截图里哪个渠道退款率最高？是多少？」", "回答：小程序 5.57%"),
        ("切回「双11大促销售数据（示例）」，输入「最近卖得怎么样」", "澄清卡片：7 天 / 30 天 / 本月"),
    ]
    for index, (action, expect) in enumerate(steps, start=1):
        md.append(f"| {index} | {action} | {expect} |")
    md.append("")
    md.append("## 五、常见问题")
    md.append("")
    md.append("- **模型偶尔慢**：单问 8–12 秒正常，剪辑时把等待段加速即可；")
    md.append("- **显示演示模式**：没读到 Key，界面功能仍完整；检查 `backend/.env` 或 `judge/backend.env`；")
    md.append("- **录屏太短**：1:17 的素材变速 0.6 倍约 2:10，再配合架构图/截图/技术卡即可到 5–8 分钟；")
    md.append("- **不想自己配音**：导入 `字幕_演示.srt`，剪映「文本朗读」一键生成 AI 配音。")
    OUT_MD.write_text("\n".join(md), encoding="utf-8")

    print(f"总时长（估算）: {total / 60:.2f} 分钟（{total:.1f} 秒）")
    print(f"脚本 -> {OUT_MD}")
    print(f"字幕 -> {OUT_SRT}")
    print(f"配音稿 -> {OUT_TXT}")


if __name__ == "__main__":
    main()
