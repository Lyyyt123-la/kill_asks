# -*- coding: utf-8 -*-
"""用 Windows SAPI 直接合成 11 段演示配音（字面量方式，避开文件读取编码问题），合并成 WAV。"""
from __future__ import annotations

import subprocess
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
WORK = ROOT / "frontend" / ".voice_blocks2"
OUT_WAV = DOCS / "配音_演示.wav"
OUT_SRT = DOCS / "字幕_演示_配音版.srt"
GAP = 0.45
MIN_TOTAL = 330.0

BLOCKS = [
    "业务同学想查一个数，往往要提需求、排队、等上两天。不会写 SQL、报表永远慢半拍，数据还散落在 PDF 和截图里。这三道门槛，让一线同学只能靠感觉做决策。",
    "问数 AskData 是一个对话式数据分析平台。上传数据或者文档，用一句中文提问，它就能完成查询、自动图表和智能洞察，还能把 PDF、Word、截图里的表格变成可分析的数据集。",
    "整体是前后端分离架构。前端用 Vue3 加 ECharts，后端用 FastAPI；分析数据放在 DuckDB，元数据用 SQLite。大模型通过 OpenAI 兼容协议接入阿里云百炼的 qwen-plus，截图识别用 qwen3-vl-plus。这样既保留了数据库的分析性能，也让模型可以随时替换。",
    "先看最常用的场景。打开示例数据，直接问：各区域的销售额对比。几秒钟，系统生成了 SQL、柱状图和结论：华东销售额 1853.94 万元排名第一，领先第二名华南 777 万元。展开 SQL 可以看到，它自动排除了空值、按销售额降序，结论不是黑盒。",
    "继续追问：销售额最低的三个品类。它记住了上一轮的数据和口径，直接给出食品、美妆、女装，并指出食品只有 123 万元，不到女装的四分之一。点开右侧检查器，结果表、SQL、执行耗时全部可以核对。",
    "更关键的是，数据不只在 Excel 里。上传一份 PDF 财报，系统自动提取正文和表格，六行区域数据直接变成可分析的数据集。问：华东区 Q3 销售额和同比是多少？它回答 1853.94 万元、同比下降百分之十一点二，并且标注了引用片段，可以逐句核对。",
    "连截图也能用。上传渠道退款率截图，视觉模型自动识别成四行四列的数据集。问哪个渠道退款率最高，它回答：小程序，百分之五点五七。",
    "遇到说不清的问题，比如最近卖得怎么样，它会主动反问你要看七天、三十天还是本月。SQL 写错也不会崩，系统会把数据库报错回喂给模型，自动修复之后重新执行。",
    "AI 部分我们重点做了三件事。第一，Schema 注入：字段类型、样例、枚举、空值率和时间范围都交给模型，并且锁定数据时间口径；第二，SQL 只读校验：用 sqlglot 只允许单条 SELECT，做表名白名单、强制 LIMIT 和执行超时；第三，失败自动修复和结论二次生成，洞察必须引用真实数字。模型选型上，我们实测了百炼上的多个模型，最终选择 qwen-plus，单问八到十二秒，质量和速度最平衡。在六类典型问题上全部生成正确结果，复杂问题还能自动修复后成功。",
    "对业务同学，它把等两天变成等十秒；对分析师，它把重复取数交给 AI；对组织，PDF 和截图里的数据第一次变成可分析的资产。下一步我们会补上多表关联、看板分享和更严格的评测集，让它在真实业务里跑得更稳。",
    "广东科贸职业学院，指导老师林龙键，团队成员罗勇添、辛嘉炜、林俊宁。问数 AskData，让数据回答。感谢观看。",
]


def fmt_srt(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def synth() -> list[Path]:
    """每个段落用独立的 PowerShell 进程合成，避免 SAPI COM 连续调用偶发失败。"""
    WORK.mkdir(parents=True, exist_ok=True)
    for old in WORK.glob("*.wav"):
        old.unlink()
    files: list[Path] = []
    for index, text in enumerate(BLOCKS, start=1):
        path = WORK / f"block_{index:02d}.wav"
        script = WORK / f"synth_{index:02d}.ps1"
        escaped = text.replace("'", "''")
        script.write_text(
            "$ErrorActionPreference = 'Stop'\r\n"
            f"$path = '{path}'\r\n"
            f"$text = '{escaped}'\r\n"
            "$voice = New-Object -ComObject SAPI.SpVoice\r\n"
            "$voice.Rate = -1\r\n"
            "$voice.Volume = 100\r\n"
            "$stream = New-Object -ComObject SAPI.SpFileStream\r\n"
            "$stream.Open($path, 3, $false)\r\n"
            "$voice.AudioOutputStream = $stream\r\n"
            "$voice.Speak($text)\r\n"
            "$stream.Close()\r\n"
            "$voice.AudioOutputStream = $null\r\n"
            "[System.Runtime.InteropServices.Marshal]::ReleaseComObject($stream) | Out-Null\r\n"
            "[System.Runtime.InteropServices.Marshal]::ReleaseComObject($voice) | Out-Null\r\n"
            "Write-Output 'ok'\r\n",
            encoding="utf-8-sig",
        )
        ok = False
        for attempt in range(2):
            result = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
            )
            if result.returncode == 0 and path.exists() and path.stat().st_size > 1000:
                ok = True
                break
        if ok:
            files.append(path)
        else:
            print(f"第 {index} 段合成失败：{result.stderr[:120]}")
    return files


def main() -> None:
    files = synth()
    print("合成 wav 数量：", len(files), "/", len(BLOCKS))
    if len(files) != len(BLOCKS):
        print("合成失败，终止")
        return
    with wave.open(str(files[0]), "rb") as handle:
        channels, sample_width, framerate = handle.getnchannels(), handle.getsampwidth(), handle.getframerate()
    frames_list = []
    durations = []
    for path in files:
        with wave.open(str(path), "rb") as handle:
            frames = handle.readframes(handle.getnframes())
            durations.append(handle.getnframes() / handle.getframerate())
        frames_list.append(frames)
        frames_list.append(b"\x00" * (int(framerate * GAP) * channels * sample_width))
    total = sum(durations) + GAP * (len(files) - 1)
    extra = 0.0
    if total < MIN_TOTAL:
        extra = (MIN_TOTAL - total) / (len(files) - 1)
        silence = b"\x00" * (int(framerate * (GAP + extra)) * channels * sample_width)
        frames_list = []
        for frames in frames_list:
            pass
        # 重建带补静音的帧序列
        frames_list = []
        for path in files:
            with wave.open(str(path), "rb") as handle:
                frames_list.append(handle.readframes(handle.getnframes()))
            frames_list.append(silence)
        total = sum(durations) + (GAP + extra) * (len(files) - 1)
    with wave.open(str(OUT_WAV), "wb") as out:
        out.setnchannels(channels)
        out.setsampwidth(sample_width)
        out.setframerate(framerate)
        for frames in frames_list:
            out.writeframes(frames)

    gap = GAP + extra
    timings = []
    cursor = 0.0
    for duration in durations:
        timings.append((cursor, cursor + duration))
        cursor += duration + gap
    srt = []
    for index, (start, end) in enumerate(timings, start=1):
        srt.append(f"{index}\n{fmt_srt(start)} --> {fmt_srt(end)}\n{BLOCKS[index - 1]}\n")
    OUT_SRT.write_text("\n".join(srt), encoding="utf-8")
    print(f"总时长：{total / 60:.2f} 分钟（{total:.1f}s）")
    print("音频 ->", OUT_WAV, f"{OUT_WAV.stat().st_size / 1024 / 1024:.1f} MB")
    print("字幕 ->", OUT_SRT)


if __name__ == "__main__":
    main()
