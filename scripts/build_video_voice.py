# -*- coding: utf-8 -*-
"""生成演示视频的配音、时间轴、字幕（DashScope CosyVoice TTS）——加长版（目标 5-8 分钟）。"""
from __future__ import annotations

import json
import re
import subprocess
import wave
from pathlib import Path

import dashscope
from dashscope.audio.tts_v2 import SpeechSynthesizer

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
WORK = ROOT / "frontend" / ".video_tts"
FFMPEG = ROOT / "frontend" / "node_modules/@ffmpeg-installer/win32-x64/ffmpeg.exe"
OUT_WAV = DOCS / "配音_成片.wav"
OUT_SRT = DOCS / "字幕_成片.srt"
OUT_TXT = DOCS / "配音稿_成片.txt"
TIMELINE = ROOT / "frontend" / ".video_timeline.json"
GAP = 0.5
MIN_TOTAL = 330.0
MODEL = "cosyvoice-v2"
VOICE = "longxiaochun_v2"

BLOCKS = [
    {"visual": "title", "title": "片头 · 痛点",
     "text": "业务同学想查一个数，平均要等两天。不会写 SQL、报表永远慢半拍；更麻烦的是，数据往往躺在 PDF 财报、Word 报告和聊天截图里，传统 BI 根本接不进来。这三道门槛，让一线同学只能靠感觉做决策。"},
    {"visual": "welcome", "title": "产品定位",
     "text": "问数 AskData 是一个对话式数据分析平台。上传数据或文档，用一句中文提问，它自动完成查询、图表、洞察；还能把 PDF、Word、截图里的表格变成可分析的数据集。整个过程，不用写一行 SQL。"},
    {"visual": "architecture", "title": "技术架构",
     "text": "架构上前端 Vue3 加 ECharts，后端 FastAPI，分析数据用 DuckDB、元数据用 SQLite。大模型通过 OpenAI 兼容协议接入阿里云百炼 qwen-plus，截图识别用 qwen3-vl-plus。模型随时可以替换，排查问题也方便，哪一步出错都能定位。数据层用 DuckDB 做分析、SQLite 管元数据，上传文件留在本地，数据不出域。"},
    {"visual": "clip:0:30", "title": "核心功能 · 数据问答",
     "text": "看最常用的场景。打开示例数据，问各区域的销售额对比。几秒钟生成 SQL、柱状图和结论：华东 1853.94 万排名第一，领先华南 777 万。展开 SQL 能看到它自动排除空值、按销售额降序，结论不是黑盒。图表还支持折线、柱状、环形和表格切换，也能导出图片和数据。"},
    {"visual": "clip:30:48", "title": "核心功能 · 多轮与检查器",
     "text": "继续追问销售额最低的三个品类。它记住上一轮口径，给出食品、美妆、女装，食品只有 123 万，不到女装四分之一。打开检查器，结果表、SQL、字段结构和执行耗时都可以核对。"},
    {"visual": "clip:48:63", "title": "核心功能 · PDF 财报",
     "text": "更关键的是数据不只在 Excel 里。上传一份 PDF 财报，自动提取正文和表格，六行区域数据直接变成可分析数据集。问华东区 Q3 销售额和同比，回答 1853.94 万、同比下降百分之十一点二，还标注引用片段可以核对。文档问答基于切片和向量检索，回答带引用，避免模型瞎编。正文按四百二十字切片，向量加关键词混合检索，命中片段才会被引用。"},
    {"visual": "clip:63:77", "title": "核心功能 · 截图识别",
     "text": "连截图也能用。上传退款率截图，视觉模型识别成四行四列的数据集。问哪个渠道退款率最高，答案是：小程序，百分之五点五七。这相当于把图片里的表格，直接接进了分析链路。"},
    {"visual": "robust", "title": "鲁棒性设计",
     "text": "遇到模糊问题，比如最近卖得怎么样，它会主动反问你要看七天、三十天还是本月；SQL 写错也不会崩，系统把数据库报错回喂模型，自动修复后重新执行。这些兜底设计，保证现场演示不翻车。"},
    {"visual": "ai", "title": "AI 技术亮点",
     "text": "AI 部分做了三件事。Schema 注入，把字段类型、样例、枚举、空值率和时间范围交给模型；SQL 只读校验，用 sqlglot 只允许单条 SELECT，做表名白名单、强制 LIMIT 和超时；失败自动修复，结论二次生成且必须引用真实数字。前端还会把执行步骤可视化，让用户知道系统在做什么。模型实测后选 qwen-plus，单问八到十二秒。在六类典型问题上全部生成正确结果，复杂问题还能自动修复后成功。"},
    {"visual": "difficulty", "title": "目前难点",
     "text": "当然现在还有难点。企业数据形态复杂，PDF 版式、扫描件、合并单元格很难一次还原；口径不统一、多表关系缺失，都会影响回答；模型输出偶尔也不稳定，需要工程手段兜底。这些问题不是模型一个人能解决的，需要产品流程配合。我们的应对是把表格统一转成数据集、把口径与时间范围写进 schema，并允许人工纠正。"},
    {"visual": "tech", "title": "技术难点",
     "text": "技术上最难的是四点：第一，NL2SQL 准确率，要用 Schema 注入、时间口径和中文别名约束；第二，安全，必须只读、单语句、白名单和强制 LIMIT；第三，幻觉，洞察必须引用真实数字；第四，时延和稳定性，靠模型选型、失败重试和演示降级。我们在 prompt 和工程层都做了对应约束。"},
    {"visual": "scope", "title": "应用场景",
     "text": "它适合的场景很明确：业务同学自助取数，分析师快速出初版 SQL，财务和管理者读财报，运营做大促复盘；也可以作为教学和科研的轻量分析工具。不过目前它更适合单表分析，多表关联还在规划里。对学校场景来说，它也适合课程作业和课程设计，上传即可分析。"},
    {"visual": "roadmap", "title": "发展规划",
     "text": "下一步我们会补上多表关联和语义层，让口径可以配置；再做看板分享和更多数据源，并建立五十题以上的评测集，把准确率、修复率和响应时延都量化出来。如果条件允许，我们也希望把部署做成长期在线服务，让评委直接访问。"},
    {"visual": "team", "title": "团队与结尾",
     "text": "目前它还是单表为主的端到端原型，但已经能真实跑通。广东科贸职业学院，指导老师林龙键，团队成员罗勇添、辛嘉炜、林俊宁。问数 AskData，让数据回答。"},
]


def load_key() -> str:
    for line in (ROOT / "backend" / ".env").read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.strip().startswith("LLM_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("缺少 LLM_API_KEY")


def synth(block_index: int, text: str) -> Path:
    import time
    WORK.mkdir(parents=True, exist_ok=True)
    mp3 = WORK / f"block_{block_index:02d}.mp3"
    wav = WORK / f"block_{block_index:02d}.wav"
    if wav.exists() and wav.stat().st_size > 2000:
        return wav
    last_error = None
    for attempt in range(1, 5):
        try:
            synthesizer = SpeechSynthesizer(model=MODEL, voice=VOICE, speech_rate=0.85)
            audio = synthesizer.call(text)
            if audio:
                mp3.write_bytes(audio)
                subprocess.run(
                    [str(FFMPEG), "-y", "-hide_banner", "-loglevel", "error", "-i", str(mp3),
                     "-ar", "44100", "-ac", "1", "-sample_fmt", "s16", str(wav)],
                    check=True,
                )
                return wav
            last_error = RuntimeError("TTS 返回为空")
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            print(f"第 {block_index} 段第 {attempt} 次失败：{type(exc).__name__} {str(exc)[:120]}")
            time.sleep(2.5)
    raise RuntimeError(f"第 {block_index} 段合成失败：{last_error}")


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as handle:
        return handle.getnframes() / handle.getframerate()


def fmt_srt(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def split_sentences(text: str) -> list[str]:
    pieces = [piece.strip() for piece in re.split(r"(?<=[。！？；])", text) if piece.strip()]
    return pieces or [text]


def main() -> None:
    dashscope.api_key = load_key()
    files: list[Path] = []
    for index, block in enumerate(BLOCKS, start=1):
        print(f"TTS {index:02d}/{len(BLOCKS)} ...")
        files.append(synth(index, block["text"]))

    durations = [wav_duration(path) for path in files]
    total = sum(durations) + GAP * (len(files) - 1)
    extra = max(0.0, (MIN_TOTAL - total) / (len(files) - 1))
    gap = GAP + extra

    with wave.open(str(files[0]), "rb") as handle:
        channels, sample_width, framerate = handle.getnchannels(), handle.getsampwidth(), handle.getframerate()
    frames_list = []
    for path in files:
        with wave.open(str(path), "rb") as handle:
            frames_list.append(handle.readframes(handle.getnframes()))
        frames_list.append(b"\x00" * (int(framerate * gap) * channels * sample_width))
    total = sum(durations) + gap * (len(files) - 1)
    with wave.open(str(OUT_WAV), "wb") as out:
        out.setnchannels(channels)
        out.setsampwidth(sample_width)
        out.setframerate(framerate)
        for frames in frames_list:
            out.writeframes(frames)

    cursor = 0.0
    timeline_blocks = []
    srt_lines = []
    srt_index = 1
    for index, block in enumerate(BLOCKS):
        start = cursor
        end = cursor + durations[index]
        cursor = end + gap
        sentences = split_sentences(block["text"])
        char_total = max(1, sum(len(s) for s in sentences))
        sentence_cursor = start
        sentence_items = []
        for sentence in sentences:
            sentence_duration = (end - start) * len(sentence) / char_total
            sentence_end = min(end, sentence_cursor + sentence_duration)
            if sentence_end - sentence_cursor < 0.4:
                sentence_end = sentence_cursor + 0.4
            srt_lines.append(f"{srt_index}\n{fmt_srt(sentence_cursor)} --> {fmt_srt(sentence_end)}\n{sentence}\n")
            sentence_items.append({"start": sentence_cursor, "end": sentence_end, "text": sentence})
            srt_index += 1
            sentence_cursor = sentence_end
        timeline_blocks.append({
            "title": block["title"],
            "text": block["text"],
            "visual": block["visual"],
            "start": start,
            "end": end,
            "sentences": sentence_items,
        })
    OUT_SRT.write_text("\n".join(srt_lines), encoding="utf-8")
    OUT_TXT.write_text("\n\n".join(block["text"] for block in BLOCKS), encoding="utf-8")
    TIMELINE.write_text(json.dumps({"total": total, "blocks": timeline_blocks}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"总时长：{total / 60:.2f} 分钟（{total:.1f}s）")
    print("音频 ->", OUT_WAV)
    print("字幕 ->", OUT_SRT)
    print("时间轴 ->", TIMELINE)


if __name__ == "__main__":
    main()
