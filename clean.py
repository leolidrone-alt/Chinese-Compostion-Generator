import os
import time
import json
import math
from pathlib import Path
import dashscope
from dashscope import Generation


def split_articles(content: str, separator: str = '\n\n---\n\n') -> list:
    """按分隔符将文档拆分成文章列表，过滤空串"""
    articles = content.split(separator)
    return [art.strip() for art in articles if art.strip() and len(art.strip()) > 100]


def clean_single_article(article: str, api_key: str, idx: int, total: int, max_retries: int = 3) -> str:
    """
    清洗单篇文章（逐篇处理，更稳定）
    返回清洗后的正文，失败返回空字符串
    """
    dashscope.api_key = api_key

    prompt = f"""请清洗以下文章，只保留正文。

【清洗规则】
1. 删除广告、导航、页眉页脚、推荐阅读、扫码关注等噪音
2. 删除高考作文题目要求（如“阅读下面的材料...”、“要求：...”）
3. 删除作者简介、文章来源、版权声明
4. 删除文不对题的内容（新闻、科技、政治等非散文内容）
5. 只保留纯净的正文，不要标题，不要任何额外说明

【原始文章】
{article[:3000]}  # 限制输入长度，避免超token

【输出要求】
直接输出清洗后的正文，不要任何前缀后缀。
如果文章本身就是纯净正文，原样输出。
"""

    for attempt in range(max_retries):
        try:
            response = Generation.call(
                model='qwen-max',
                messages=[{'role': 'user', 'content': prompt}],
                result_format='message',
                temperature=0.1,  # 更低温度，更稳定
                max_tokens=2000
            )
            if response.status_code == 200:
                result = response.output.choices[0].message.content.strip()
                # 如果返回内容过短，可能是清洗失败，保留原文
                if len(result) < 100:
                    print(f"  ⚠️ 第 {idx}/{total} 篇清洗后过短，保留原文")
                    return article
                return result
            else:
                print(f"  ⚠️ 第 {idx}/{total} 篇第 {attempt+1} 次失败: {response.code}")
                time.sleep(2)
        except Exception as e:
            print(f"  ⚠️ 第 {idx}/{total} 篇第 {attempt+1} 次异常: {e}")
            time.sleep(2)

    # 重试耗尽，返回原文
    print(f"  ❌ 第 {idx}/{total} 篇清洗失败，保留原文")
    return article


def clean_articles_one_by_one(
    input_file: str,
    output_file: str,
    api_key: str,
    checkpoint_file: str = "clean_checkpoint.json"
):
    """
    逐篇清洗文章，支持断点续传
    """
    # 读取原始文章
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    articles = split_articles(content)
    total = len(articles)
    print(f"共 {total} 篇文章")

    # 检查是否有断点
    cleaned_articles = []
    start_idx = 0
    if os.path.exists(checkpoint_file):
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            checkpoint = json.load(f)
            cleaned_articles = checkpoint.get('cleaned', [])
            start_idx = checkpoint.get('last_idx', 0)
            print(f"从断点恢复，已完成 {start_idx} 篇")

    # 逐篇清洗
    for i in range(start_idx, total):
        print(f"清洗第 {i+1}/{total} 篇...")
        cleaned = clean_single_article(articles[i], api_key, i+1, total)

        if cleaned:
            cleaned_articles.append(cleaned)
        else:
            # 失败时保留原文
            cleaned_articles.append(articles[i])

        # 每10篇保存一次断点
        if (i + 1) % 10 == 0:
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump({'last_idx': i + 1, 'cleaned': cleaned_articles}, f)
            print(f"  💾 断点已保存 ({i+1}/{total})")

        time.sleep(1)  # 礼貌延迟

    # 最终保存
    final_output = '\n\n\n\n\n'.join(cleaned_articles)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(final_output)

    # 清理断点文件
    if os.path.exists(checkpoint_file):
        os.remove(checkpoint_file)

    print(f"✅ 全部完成！共 {len(cleaned_articles)} 篇文章，保存到 {output_file}")


if __name__ == "__main__":
    DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
    if not DASHSCOPE_API_KEY:
        DASHSCOPE_API_KEY = input("请输入 DashScope API Key: ").strip()

    clean_articles_one_by_one(
        input_file='formatted_articles.txt',
        output_file='final_clean_articles.txt',
        api_key=DASHSCOPE_API_KEY
    )