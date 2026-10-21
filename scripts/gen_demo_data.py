"""生成比赛演示数据：双11大促销售数据（含脏数据，便于展示数据质量与鲁棒性）。

用法：python scripts/gen_demo_data.py
输出：
  demo_data/double11_sales.csv                 英文列名，供「载入示例数据」与 NL2SQL 主流程
  demo_data/双11大促销售数据.xlsx               中文表头 + 前 8000 行，用于演示 Excel 上传
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "demo_data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

RNG = np.random.default_rng(42)
N = 36000

REGION_CITY = {
    "华东": ["上海", "杭州", "南京", "苏州", "宁波"],
    "华南": ["广州", "深圳", "东莞", "厦门", "南宁"],
    "华北": ["北京", "天津", "石家庄", "太原", "济南"],
    "西南": ["成都", "重庆", "昆明", "贵阳"],
    "东北": ["沈阳", "大连", "长春", "哈尔滨"],
    "华中": ["武汉", "长沙", "郑州", "合肥"],
}
REGION_P = [0.32, 0.20, 0.16, 0.12, 0.10, 0.10]

CATEGORY_PRICE = {"女装": 189, "3C数码": 1899, "家居": 429, "美妆": 269, "食品": 89}
CATEGORY_P = [0.30, 0.22, 0.16, 0.17, 0.15]
CATEGORY_REFUND = {"女装": 0.095, "3C数码": 0.028, "家居": 0.052, "美妆": 0.041, "食品": 0.018}

CHANNELS = ["天猫", "京东", "抖音", "小程序"]
CHANNEL_P = [0.42, 0.24, 0.22, 0.12]


def build_frame() -> pd.DataFrame:
    days = pd.date_range("2025-10-01", "2025-11-12", freq="D")
    day_w = np.ones(len(days))
    for i, day in enumerate(days):
        if day == pd.Timestamp("2025-11-11"):
            day_w[i] = 8.0
        elif day in (pd.Timestamp("2025-11-10"), pd.Timestamp("2025-11-12")):
            day_w[i] = 1.9
        elif day.weekday() >= 5:
            day_w[i] = 1.25
    day_w = day_w / day_w.sum()
    day_idx = RNG.choice(len(days), size=N, p=day_w)

    hour_w = np.array([0.5, 0.3, 0.25, 0.2, 0.2, 0.25, 0.4, 0.6, 0.9, 1.3,
                       1.9, 2.1, 2.0, 1.5, 1.4, 1.4, 1.5, 1.7, 2.0, 2.4,
                       2.6, 2.5, 2.0, 1.3])
    hour_w = hour_w / hour_w.sum()
    hours = RNG.choice(24, size=N, p=hour_w)

    # 双11 凌晨 0-2 点额外集中爆发
    is_1111 = np.array([d == pd.Timestamp("2025-11-11") for d in days[day_idx]])
    early = is_1111 & (RNG.random(N) < 0.32)
    hours = np.where(early, RNG.choice([0, 1, 2], size=N, p=[0.5, 0.3, 0.2]), hours)

    order_time = (
        days[day_idx]
        + pd.to_timedelta(hours, unit="h")
        + pd.to_timedelta(RNG.integers(0, 3600, size=N), unit="s")
    )

    region = RNG.choice(list(REGION_CITY.keys()), size=N, p=REGION_P)
    city = [str(RNG.choice(REGION_CITY[r])) for r in region]
    category = RNG.choice(list(CATEGORY_PRICE.keys()), size=N, p=CATEGORY_P)
    channel = RNG.choice(CHANNELS, size=N, p=CHANNEL_P)

    quantity = RNG.integers(1, 5, size=N)
    base = np.array([CATEGORY_PRICE[c] for c in category], dtype=float)
    noise = np.exp(RNG.normal(0, 0.28, size=N))
    amount = np.round(base * quantity * noise, 2)

    refund_p = np.array([CATEGORY_REFUND[c] for c in category])
    refund = RNG.random(N) < refund_p
    user_id = RNG.integers(100000, 260000, size=N)

    df = pd.DataFrame({
        "order_id": [f"SO2025{i:07d}" for i in range(1, N + 1)],
        "order_time": order_time,
        "region": region,
        "city": city,
        "category": category,
        "channel": channel,
        "quantity": quantity,
        "amount": amount,
        "refund": refund,
        "user_id": user_id,
    })

    # 注入脏数据：空值（演示数据质量提示）
    dirty_category = RNG.choice(N, size=int(N * 0.008), replace=False)
    dirty_city = RNG.choice(N, size=int(N * 0.004), replace=False)
    dirty_amount = RNG.choice(N, size=int(N * 0.003), replace=False)
    df.loc[dirty_category, "category"] = None
    df.loc[dirty_city, "city"] = None
    df.loc[dirty_amount, "amount"] = np.nan

    return df.sort_values("order_time").reset_index(drop=True)


def main() -> None:
    df = build_frame()

    csv_path = OUT_DIR / "double11_sales.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    cn_df = df.head(8000).rename(columns={
        "order_id": "订单编号",
        "order_time": "下单时间",
        "region": "区域",
        "city": "城市",
        "category": "品类",
        "channel": "渠道",
        "quantity": "数量",
        "amount": "金额",
        "refund": "是否退款",
        "user_id": "用户ID",
    })
    xlsx_path = OUT_DIR / "双11大促销售数据.xlsx"
    cn_df.to_excel(xlsx_path, index=False)

    total = df["amount"].sum()
    print(f"rows={len(df):,}  amount_total={total:,.2f}")
    print("date range:", df["order_time"].min(), "->", df["order_time"].max())
    print("csv :", csv_path, f"{csv_path.stat().st_size / 1024:.0f} KB")
    print("xlsx:", xlsx_path, f"{xlsx_path.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
