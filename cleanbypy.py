import re
import os
from pathlib import Path


def should_keep_article(text):
    """判断一篇文章是否应该保留"""
    # 1. 长度过滤：太短的不是完整文章
    clean_text = re.sub(r'\s+', '', text)
    if len(clean_text) < 200:
        return False, "too_short"

    # 2. 关键词过滤：明显非文学文本
    exclude_keywords = [
        "教学设计", "教学目标", "教学过程", "评析" # 教案
         "疫情","核酸",  # 新闻
        #"回复", "投稿", "自诉", "网友",  # 网络投稿体（可选）
        "赏析","假条","请假","应用文","说明文"
        "亲爱的"
    ]
    for kw in exclude_keywords:
        if kw in text:
            return False, f"keyword_{kw}"

    return True, "ok"


def clean_corpus(input_dir, output_dir):
    """清洗语料库"""
    os.makedirs(output_dir, exist_ok=True)

    seen_hashes = set()  # 用于去重
    stats = {"kept": 0, "filtered": 0, "reasons": {}}

    for file_path in Path(input_dir).glob("*.txt"):
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()

        keep, reason = should_keep_article(text)

        if keep:
            # 去重：计算文本hash
            text_hash = hash(re.sub(r'\s+', '', text)[:500])  # 取前500字做hash
            if text_hash in seen_hashes:
                stats["filtered"] += 1
                stats["reasons"]["duplicate"] = stats["reasons"].get("duplicate", 0) + 1
                continue

            seen_hashes.add(text_hash)

            # 繁转简（可选）
            # text = zhconv.convert(text, 'zh-cn')  # 需要 pip install zhconv

            # 保存清洗后的文章
            output_path = os.path.join(output_dir, file_path.name)
            with open(output_path, 'w', encoding='utf-8') as out:
                out.write(text)
            stats["kept"] += 1
        else:
            stats["filtered"] += 1
            stats["reasons"][reason] = stats["reasons"].get(reason, 0) + 1

    print(f"清洗完成：保留 {stats['kept']} 篇，过滤 {stats['filtered']} 篇")
    print(f"过滤原因统计：{stats['reasons']}")


# 使用
clean_corpus("./corpus", "./corpus_cleaned")