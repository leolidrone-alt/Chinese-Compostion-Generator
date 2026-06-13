"""
深度词云构建脚本 - 最终版
融合基础意象关系与人类社会行为关系，捕捉人性化的微妙关联。
挂在CloudStudio里跑2-3天，Random触发AI发散。
"""
import json
import os
import time
import random
import requests
from typing import Optional

# ================= 配置 =================
API_KEY = "sk-b81960bbb02a4fa0b080b6d5e89e6e69"
API_URL = "https://api.deepseek.com/v1/chat/completions"
SEED_WORD = "父亲"

# 发散温度：1.5 脑洞较大，可激发古怪联想；1.2 更稳妥
DIVERGENT_TEMPERATURE = 1.25
CROSS_LINK_TEMPERATURE = 1.09

# 关系类型（基础意象 + 人类社会行为）
RELATION_TYPES = [
    # ===== 基础意象关系 =====
    "场景/空间共现",
    "感官/意象相似",
    "隐喻/象征映射",
    "对比/矛盾关系",

    # ===== 深层人类行为逻辑 =====
    "身份/炫耀关联",  # 拥有某物是为了在特定人面前展示
    "劳动力转移/省力",  # 将劳动巧妙地转移给他人
    "延迟满足/仪式感",  # 为更大回报推迟即时满足
    "情感/内疚补偿",  # 弥补内心亏欠的补偿性行为
    "互惠/心照不宣",  # 双方默契交换，都不点破
    "创造共同体验",  # 保留初次体验，为与特定人共享
    "压迫/反抗",  # 权力关系中的冲突与反制
    "隐秘的嫉妒/羡慕",  # 表面平静，内心暗自比较
    "牺牲/自我感动",  # 做出牺牲并从中获得道德满足
    "好奇心驱使的探索"
    # ===== 人类社会行为/认知逻辑 =====
    "所有权/未来产出",  # 拥有A即拥有其未来产出B，如母鸡→鸡蛋
    "规则歧义/漏洞利用",  # 利用规则的模糊地带获取利益
    "认知错位",  # 同一件事，不同人因角度不同产生完全不同的理解
    "主观期待/现实偏差",  # 主观想象与客观事实之间的差距
    "时间序列/惯性",  # A发生后，按惯性必然导致B
    "空间邻近/意外",  # 因物理空间上的靠近而发生的意外关联
    "经济/交换逻辑",  # 用A换取B的市场行为
    "生存/资源竞争",  # 在有限资源下的博弈关系
]

PROGRESS_FILE = "relation_graph.json"
OUTPUT_FILE = "relation_graph.json"


# ================= 进度管理 =================
def load_progress() -> dict:
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "nodes": {},
        "edges": [],
        "pending": [SEED_WORD],
        "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_api_calls": 0
    }


def save_progress(progress):
    progress["last_saved"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


# ================= API调用 =================
def call_llm(prompt: str, temperature: float = 1.5, max_tokens: int = 250) -> Optional[str]:
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "top_p": 0.85
          # 关闭思维链，直接输出JSON
    }
    for attempt in range(3):
        try:
            resp = requests.post(API_URL, headers=headers, json=payload, timeout=60)
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"].strip()
            else:
                print(f"  API错误 {resp.status_code}: {resp.text[:100]}")
        except Exception as e:
            print(f"  网络异常: {e}")
        time.sleep(5 * (attempt + 1))
    return None


# ================= 边去重 =================
def edge_exists(progress, word_a, word_b, relation):
    return any(
        (e["from"] == word_a and e["to"] == word_b and e["relation"] == relation) or
        (e["from"] == word_b and e["to"] == word_a and e["relation"] == relation)
        for e in progress["edges"]
    )


def add_edge(progress, word_a, word_b, relation, detail):
    if not edge_exists(progress, word_a, word_b, relation):
        progress["edges"].append({
            "from": word_a,
            "to": word_b,
            "relation": relation,
            "detail": detail,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        return True
    return False


# ================= 核心扩展（发散） =================
def expand_word(word: str, progress: dict) -> bool:
    relation = random.choice(RELATION_TYPES)

    prompt = f"""我们正在构建一个涵盖人类全部生活经验的语义网络，核心是「{word}」。
请从「{relation}」这个角度，联想一个具体词语，并用一句极其生动、富有画面感的描述来揭示它们之间的联系。

要求：
1. 联想词语必须是具体名词、动词或形容意象，不要太抽象。
2. 描述要像电影台词或小说片段，包含一个微妙的心理细节或荒诞但合理的逻辑。
3. 格式严格为JSON：
{{
  "word": "联想到的词语",
  "detail": "用一句通顺、完整、有画面感的中文短句，清晰具体地描述这个联系（约20-40字），句子一定要是有逻辑的不能太无厘头
  *****同时句子中词语对于人类来说是熟悉的不要晦涩难懂,要是日常生活中能见到常见的搭配以及词语，胡乱搭配不要出现*********"
}}
如果实在想不出，输出 {{"word": null}}.
"""
    response = call_llm(prompt, temperature=DIVERGENT_TEMPERATURE)
    if not response:
        return False

    progress["total_api_calls"] += 1

    try:
        data = json.loads(response)
        new_word = data.get("word")
        if not new_word:
            return False
        detail = data.get("detail", "")
    except:
        # JSON解析失败，尝试提取关键信息
        print(f"  ⚠️ JSON解析失败，原始返回: {response[:100]}")
        return False

    now = time.strftime("%Y-%m-%d %H:%M:%S")
    if word not in progress["nodes"]:
        progress["nodes"][word] = {"first_seen": now}
    if new_word not in progress["nodes"]:
        progress["nodes"][new_word] = {"first_seen": now}
        if new_word not in progress["pending"]:
            progress["pending"].append(new_word)

    if add_edge(progress, word, new_word, relation, detail):
        print(f"  [{relation}] {word} → {new_word}: {detail}")

    return True


# ================= 核心：侧枝连接（古怪联想探测器） =================
def try_cross_link(new_word: str, progress: dict) -> bool:
    all_nodes = list(progress["nodes"].keys())
    if len(all_nodes) <= 2:
        return False

    other_nodes = [n for n in all_nodes if n != new_word]
    target = random.choice(other_nodes)
    relation = random.choice(RELATION_TYPES)

    prompt = f"""我们正在构建一个涵盖人类全部生活经验的语义网络。
请仔细想想，「{new_word}」和「{target}」这两个词，是否可能从「{relation}」这个角度产生某种古怪、真实、又不常被提及的联系。

例如“母鸡”和“鸡蛋”可以通过“所有权/未来产出”联系起来；“乐高”和“同学”可以通过“劳动力转移/省力”联系起来。

如果存在，请用一句既荒诞又合理的描述概括，要有细节。输出JSON：
{{"exists": true, "detail":  "用一句通顺、完整、有画面感的中文句子，清晰具体地描述这个联系（约20-40字），同时词语对于人类来说是熟悉的不要晦涩难懂，要是日常生活中能见到常见的搭配以及词语，胡乱搭配不要出现"}}
如果实在没有，输出：{{"exists": false}}.
"""
    response = call_llm(prompt, temperature=CROSS_LINK_TEMPERATURE, max_tokens=150)
    if not response:
        return False

    progress["total_api_calls"] += 1

    try:
        data = json.loads(response)
        if data.get("exists") and data.get("detail"):
            if add_edge(progress, new_word, target, relation, data["detail"]):
                print(f"  🔗 古怪连接 [{relation}] {new_word} ↔ {target}: {data['detail']}")
                return True
    except:
        pass
    return False


# ================= 主循环 (持续发散) =================
def main():
    if API_KEY == "你的key":
        print("请先设置环境变量 DEEPSEEK_API_KEY")
        return

    progress = load_progress()
    print(f"种子词: {SEED_WORD} (温度: {DIVERGENT_TEMPERATURE})")
    print(f"初始节点: {len(progress['nodes'])}, 边: {len(progress['edges'])}, 待扩展: {len(progress['pending'])}")

    start_time = time.time()
    target_seconds = 100 * 3600  # 可随时手动停止

    while time.time() - start_time < target_seconds:
        if not progress["pending"]:
            print("词穷，尝试在已有词之间建立古怪关联...")
            all_nodes = list(progress["nodes"].keys())
            if len(all_nodes) >= 2 and random.random() < 0.5:
                a = random.choice(all_nodes)
                b = random.choice([n for n in all_nodes if n != a])
                if not any(
                        e["from"] == a and e["to"] == b or e["from"] == b and e["to"] == a for e in progress["edges"]):
                    try_cross_link(a, progress)
            time.sleep(10)
            continue

        word = random.choice(progress["pending"])
        times_expanded = progress["nodes"].get(word, {}).get("times_expanded", 0)
        if times_expanded >= 3 and random.random() < 0.7:
            continue

        print(f"\n[{time.strftime('%H:%M:%S')}] 发散「{word}」")

        if expand_word(word, progress):
            if random.random() < 0.35:
                try_cross_link(word, progress)

        if progress["total_api_calls"] % 5 == 0:
            save_progress(progress)
            print(
                f"  📊 节点: {len(progress['nodes'])}, 边: {len(progress['edges'])}, 待扩展: {len(progress['pending'])}")

        time.sleep(random.randint(4, 7))

    save_progress(progress)
    final_graph = {
        "seed": SEED_WORD,
        "nodes": {word: {"first_seen": info["first_seen"]} for word, info in progress["nodes"].items()},
        "edges": progress["edges"],
        "total_nodes": len(progress["nodes"]),
        "total_edges": len(progress["edges"]),
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_graph, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 深度关系图已生成: {OUTPUT_FILE}")
    print(f"节点数: {len(progress['nodes'])}, 边数: {len(progress['edges'])}")


if __name__ == "__main__":
    main()