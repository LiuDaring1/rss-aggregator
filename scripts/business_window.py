#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
业务真实时间窗口与截稿计算模块 (Business Time Window & Cutoff Engine)
统一时区: Asia/Shanghai (UTC+8)

核心业务规则:
1. 资料截止时间: 每周四 20:00:00 (Asia/Shanghai)
2. 出刊发放时间: 每周五 10:00:00 (Asia/Shanghai)
3. 资料窗口区间: [上一个周四 20:00:00, 本次周四 20:00:00)
   - 起点包含 (inclusive)，终点不包含 (exclusive)
   - 相邻常规期次首尾相接，无重复边界与缺口
4. 日期精度与截稿日模糊时间保护:
   - 报道时间仅有日期 (YYYY-MM-DD) 时标记 date_only
   - 截稿当天的 date_only 条目进入待确认，不得擅自补为 00:00 漏过截稿点
"""

import datetime
from typing import Dict, Any, Optional, Tuple

try:
    from zoneinfo import ZoneInfo
    BEIJING_TZ = ZoneInfo("Asia/Shanghai")
except Exception:
    BEIJING_TZ = datetime.timezone(datetime.timedelta(hours=8))


def get_beijing_now() -> datetime.datetime:
    """获取当前北京时间"""
    return datetime.datetime.now(BEIJING_TZ)


def format_beijing_iso(dt: datetime.datetime) -> str:
    """格式化为北京时间 ISO 字符串"""
    return dt.astimezone(BEIJING_TZ).isoformat()


def parse_beijing_time(dt_str: str) -> datetime.datetime:
    """解析为北京时区 datetime"""
    dt = datetime.datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        return dt.replace(tzinfo=BEIJING_TZ)
    return dt.astimezone(BEIJING_TZ)


def get_business_window(ref_dt: Optional[datetime.datetime] = None) -> Dict[str, Any]:
    """返回规范化命名的当前窗口对象，便于测试与调用"""
    res = get_current_and_next_windows(ref_dt)
    cur = res["current_window"]
    return {
        "current_cutoff": cur["cutoff_dt"],
        "current_start": cur["start_dt"],
        "current_delivery": cur["delivery_dt"],
        "current": cur,
        "next": res["next_window"],
        "w40": res["w40_standard_window"]
    }


def calculate_window_for_cutoff(cutoff_dt: datetime.datetime) -> Dict[str, Any]:
    """
    根据给定的周四 20:00 截稿点计算完整的业务窗口
    [cutoff_dt - 7 days, cutoff_dt)
    """
    cutoff_dt = cutoff_dt.astimezone(BEIJING_TZ)
    start_dt = cutoff_dt - datetime.timedelta(days=7)
    delivery_dt = cutoff_dt + datetime.timedelta(hours=14) # 周五 10:00 (相隔 14 小时)

    return {
        "start": start_dt.isoformat(),
        "cutoff": cutoff_dt.isoformat(),
        "delivery": delivery_dt.isoformat(),
        "start_dt": start_dt,
        "cutoff_dt": cutoff_dt,
        "delivery_dt": delivery_dt,
        "window_label": f"{start_dt.strftime('%m.%d %H:%M')} ~ {cutoff_dt.strftime('%m.%d %H:%M')}",
        "description": f"回望连续7天: {start_dt.strftime('%Y-%m-%d 20:00')} 至 {cutoff_dt.strftime('%Y-%m-%d 20:00')}"
    }


def get_current_and_next_windows(ref_dt: Optional[datetime.datetime] = None) -> Dict[str, Any]:
    """
    动态计算当前业务周期窗口与下一个业务周期窗口
    """
    now = (ref_dt or get_beijing_now()).astimezone(BEIJING_TZ)

    # 找到最近的一个周四 (weekday: Monday=0, Tuesday=1, Wednesday=2, Thursday=3)
    # Python weekday(): Monday is 0 and Sunday is 6. So Thursday is 3.
    weekday = now.weekday()
    
    # 本周周四 20:00
    days_to_thursday = (3 - weekday) % 7
    this_thursday_date = (now + datetime.timedelta(days=days_to_thursday)).date()
    this_thursday_20pm = datetime.datetime(
        this_thursday_date.year, this_thursday_date.month, this_thursday_date.day,
        20, 0, 0, tzinfo=BEIJING_TZ
    )

    if now < this_thursday_20pm:
        # 当前处于本周四 20:00 之前：当前周期截稿点就是本周四 20:00
        current_cutoff = this_thursday_20pm
    else:
        # 当前已过本周四 20:00：当前周期截稿点转入下周四 20:00
        current_cutoff = this_thursday_20pm + datetime.timedelta(days=7)

    next_cutoff = current_cutoff + datetime.timedelta(days=7)

    current_window = calculate_window_for_cutoff(current_cutoff)
    next_window = calculate_window_for_cutoff(next_cutoff)

    # 特殊基线标注: W39 为 2026-09-24 试发件, W40 对应常规周窗口 (2026-09-24 20:00 至 2026-10-01 20:00)
    w40_cutoff = datetime.datetime(2026, 10, 1, 20, 0, 0, tzinfo=BEIJING_TZ)
    w40_window = calculate_window_for_cutoff(w40_cutoff)

    return {
        "now": now.isoformat(),
        "current_window": current_window,
        "next_window": next_window,
        "w40_standard_window": w40_window
    }


def classify_article_window(
    pub_date_str: str,
    cutoff_dt: datetime.datetime
) -> Dict[str, Any]:
    """
    判断文章是否落在 [cutoff_dt - 7d, cutoff_dt) 窗口内
    处理日期精度与截稿日模糊时间
    """
    if not pub_date_str:
        return {
            "in_window": False,
            "status": "missing_date",
            "reason": "缺少发布时间"
        }

    cutoff_dt = cutoff_dt.astimezone(BEIJING_TZ)
    start_dt = cutoff_dt - datetime.timedelta(days=7)
    cutoff_date_str = cutoff_dt.strftime("%Y-%m-%d")

    # 检查是否仅有年月日 (如 2026-09-24)
    is_date_only = len(pub_date_str.strip()) <= 10

    # 截稿当天且仅有日期: 无法确定是 20:00 之前还是之后 -> 需人工/二次核验
    if is_date_only and pub_date_str.strip() == cutoff_date_str:
        return {
            "in_window": True,
            "precision": "date_only",
            "ambiguity": True,
            "status": "needs_time_confirmation",
            "reason": "发布于截稿当天但缺失精确时分，需确认是否在 20:00 前发布"
        }

    # 解析具体时间
    try:
        # 支持 ISO 格式
        dt = datetime.datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=BEIJING_TZ)
        else:
            dt = dt.astimezone(BEIJING_TZ)
        
        if start_dt <= dt < cutoff_dt:
            return {
                "in_window": True,
                "precision": "exact_time",
                "ambiguity": False,
                "status": "in_window",
                "article_dt": dt.isoformat()
            }
        elif dt >= cutoff_dt:
            return {
                "in_window": False,
                "precision": "exact_time",
                "ambiguity": False,
                "status": "after_cutoff",
                "reason": "发布于截稿时间之后，归入下期窗口"
            }
        else:
            return {
                "in_window": False,
                "precision": "exact_time",
                "ambiguity": False,
                "status": "before_window",
                "reason": "早于本期窗口起始点 (超过7天前)"
            }
    except Exception:
        # 纯日期匹配
        date_part = pub_date_str[:10]
        start_date_part = start_dt.strftime("%Y-%m-%d")
        if start_date_part <= date_part < cutoff_date_str:
            return {
                "in_window": True,
                "precision": "date_only",
                "ambiguity": False,
                "status": "in_window_date_only"
            }
        else:
            return {
                "in_window": False,
                "precision": "date_only",
                "ambiguity": False,
                "status": "out_of_window"
            }


if __name__ == "__main__":
    res = get_current_and_next_windows()
    print("=== 业务真实时间窗口动态计算 ===")
    print("当前时间:", res["now"])
    print("当前周期截稿点:", res["current_window"]["cutoff"])
    print("当前周期发放点:", res["current_window"]["delivery"])
    print("W40 标准验收窗口:")
    print("  开始:", res["w40_standard_window"]["start"])
    print("  截止:", res["w40_standard_window"]["cutoff"])
    print("  发放:", res["w40_standard_window"]["delivery"])
