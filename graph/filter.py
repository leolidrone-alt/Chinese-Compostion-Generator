"""
词云筛选脚本 - Qwen 版
功能：对词云关系网进行质量筛选，剔除低质量关联，保留“像人”的高质量素材。
使用：python filter_graph.py
"""
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='ignore')

import json
import os
import time
import requests
from typing import Optional, Tuple
import re

# ================= 配置 =================
# 改为你的 Qwen API Key (DashScope)
QWEN_API_KEY = "sk-fb6d25287473485bbb3e52da02fb8002"
QWEN_API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
MODEL_NAME = "qwen-max"  # 可换成 qwen-plus, qwen-turbo 等

INPUT_FILE = "relation_graph.json"
OUTPUT_FILE = "relation_graph_filtered.json"
PROGRESS_FILE = "filter_progress.json"

MIN_DETAIL_LENGTH = 10
MAX_DETAIL_LENGTH = 60
BATCH_SIZE = 10


# ================= 工具函数 =================
def load_graph(input_file: str = INPUT_FILE) -> dict:
    if not os.path.exists(input_file):
        print(f"错误：找不到 {input_file}")
        return {"edges": []}
    with open(input_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_graph(graph: dict, output_file: str = OUTPUT_FILE):
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)


def load_progress() -> dict:
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"last_index": 0, "kept_edges": []}


def save_progress(progress: dict):
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


# ================= 本地硬性规则过滤 =================
def local_filter(edge: dict) -> Tuple[bool, str]:
    detail = edge.get("detail", "")
    length = len(detail)
    if length < MIN_DETAIL_LENGTH:
        return False, f"描述过短（{length}字）"
    if length > MAX_DETAIL_LENGTH:
        return False, f"描述过长（{length}字）"
    cliches = [
        "父爱如山", "深沉而伟大", "温暖的怀抱", "岁月如梭",
        "时光荏苒", "教会了我", "让我明白", "这就是……的力量",
        "充满了爱", "无私奉献", "默默付出", "永远记得",
    ]
    for cliche in cliches:
        if cliche in detail:
            return False, f"包含套话: {cliche}"
    relation = edge.get("relation", "")
    if relation == "场景/空间共现":
        if not any(word in detail for word in ["里", "上", "旁", "边", "中", "前", "后", "下"]):
            return True, "场景关系缺乏方位词"
    obscure_words = ["瞬误", "孤创谜径", "夭蓝幼梦", "残翼", "寂灭"]
    for obscure in obscure_words:
        if obscure in detail:
            return False, f"包含晦涩自造词: {obscure}"
    if re.search(r'[他她它我你]|父亲|母亲|老师|同学|邻居|老板|司机|老人|小孩|猫|狗|鸟|树|花|雨|雪|风|月|灯|门|窗|路',
                 detail):
        return False, ""
    if length >= 20:
        return False, ""
    return True, "需要AI判断"


# ================= Qwen API 调用 =================
def call_qwen(prompt: str, temperature: float = 0.2, max_tokens: int = 100) -> Optional[str]:
    headers = {
        "Authorization": f"Bearer {QWEN_API_KEY}",
        "Content-Type": "application/json; charset=utf-8"
    }
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    for attempt in range(3):
        try:
            resp = requests.post(QWEN_API_URL, headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"].strip()
            else:
                print(f"  Qwen API错误 {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            print(f"  API请求异常: {type(e).__name__}")
        time.sleep(3 * (attempt + 1))
    return None


def ai_filter(edge: dict) -> Tuple[bool, str]:
    prompt = f"""请判断下面这条词语关联是否应该保留。
词语A：{edge['from']}
词语B：{edge['to']}
关系类型：{edge['relation']}
关联描述：{edge['detail']}
从以下四个维度评估（0-10分）：
1. 语句通顺度
2. 逻辑合理性
3. 细节具体性
4. 词语熟悉度
总分 >= 28分（满分40）则保留；否则剔除。
返回JSON：{{"keep": true/false, "total_score": 28, "reason": "简要说明"}}"""
    response = call_qwen(prompt)
    if response:
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return data.get("keep", True), data.get("reason", "AI判断完成")
        except:
            pass
    return True, "AI判断失败，默认保留"


# ================= 主程序 =================
def main():
    print("=" * 50)
    print("词云质量筛选程序 (Qwen 版)")
    print("=" * 50)

    print("\n正在加载原始词云数据...")
    graph = load_graph()
    total_edges = len(graph.get("edges", []))
    print(f"原始边数: {total_edges}")

    if total_edges == 0:
        print("词云数据为空，无需筛选。")
        return

    progress = load_progress()
    start_index = progress["last_index"]
    kept_edges = progress["kept_edges"]
    if start_index > 0:
        print(f"从上次中断处继续，已完成 {start_index}/{total_edges} 条边的筛选。")

    local_filtered = 0
    ai_filtered = 0
    kept = len(kept_edges)

    for i in range(start_index, total_edges):
        edge = graph["edges"][i]
        suspicious, reason = local_filter(edge)
        if not suspicious:
            if reason:
                local_filtered += 1
                if local_filtered % 100 == 0:
                    print(f"  [本地过滤] 已过滤 {local_filtered} 条")
                continue
            else:
                kept_edges.append(edge)
                kept += 1
                if kept % 500 == 0:
                    print(f"  [直接保留] {i + 1}/{total_edges} (已保留 {kept} 条)")
        else:
            keep, reason = ai_filter(edge)
            if keep:
                kept_edges.append(edge)
                kept += 1
                if kept % 100 == 0:
                    print(f"  [Qwen保留] {i + 1}/{total_edges} (已保留 {kept} 条)")
            else:
                ai_filtered += 1
                if ai_filtered % 50 == 0:
                    print(f"  [Qwen剔除] {i + 1}/{total_edges} (已过滤 {ai_filtered} 条)")
        if (i + 1) % BATCH_SIZE == 0:
            progress = {"last_index": i + 1, "kept_edges": kept_edges}
            save_progress(progress)
        if suspicious:
            time.sleep(0.5)

    filtered_graph = {
        "nodes": graph.get("nodes", {}),
        "edges": kept_edges,
        "original_edge_count": total_edges,
        "filtered_edge_count": len(kept_edges),
        "local_filtered_count": local_filtered,
        "ai_filtered_count": ai_filtered,
        "filtered_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    save_graph(filtered_graph)
    print(f"\n" + "=" * 50)
    print("筛选完成！")
    print(f"原始边数: {total_edges}")
    print(f"本地规则过滤: {local_filtered} 条")
    print(f"Qwen裁判过滤: {ai_filtered} 条")
    print(f"最终保留: {len(kept_edges)} 条")
    print(f"筛选结果已保存到 {OUTPUT_FILE}")

    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)


if __name__ == "__main__":
    main()