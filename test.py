import time

import requests
import os

def baidu_search(query: str):
    api_key = "bce-v3/ALTAK-R2ZicdyyJmNxBVfp2PhXS/0e38dd752d47b028e17d3c7102e13b1dd06e0809"
    if not api_key:
        raise ValueError("请设置环境变量 BAIDU_AI_SEARCH_API_KEY")

    url = "https://qianfan.baidubce.com/v2/ai_search/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "messages": [{"role": "user", "content": query}],
        "model": "ernie-4.5-turbo-128k",
        "stream": False,
        "search_source": "baidu_search_v2"  # 推荐使用 v2
    }

    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    data = response.json()

    return {
        "answer": data["choices"][0]["message"]["content"],
        "references": data.get("references", [])
    }

# 使用示例
# 准备多样化的搜索查询（覆盖不同年份、文体、主题等，并加入好作家文章）
search_queries = [
    "中考满分作文 原文 记叙文 600字",
    "高考优秀作文 原文 议论文 800字",
    "2024年中考作文 原文 范文 网址",
    "2023年高考作文 优秀范文 原文 链接",
    "中高考作文 写人 原文 文章链接",
    "中高考作文 写事 原文 全文 不含赏析",
    "中考作文 成长类 优秀范文 原文",
    "高考作文 家国情怀 满分原文 网址",
    "中考作文 议论文 范文 原文 无解析",
    "高考作文 材料作文 优秀原文 链接",
    "中考作文 命题作文 原文 具体网址",
    "高考作文 话题作文 满分原文 不含点评",
    "中考作文 半命题 优秀范文 原文",
    "高考作文 任务驱动型 原文 文章地址",
    "中考作文 想象类 优秀原文 网页",
    "高考作文 哲理类 满分原文 无赏析",
    "中考作文 读后感 原文 范文链接",
    "高考作文 演讲稿 优秀原文 网址",
    "中考作文 书信体 范文 原文 地址",
    "中考作文 说明文 优秀原文 文章链接",
    "高考作文 微写作 原文 范例 网址",
    "中考作文 散文 优秀范文 原文 无评析",
    "高考作文 小说体 满分原文 链接",
    "中考作文 游记 优秀原文 具体文章",
    "高考作文 时评类 原文 范文 网址",
    "中考作文 应用文 原文 优秀范文",
    "高考作文 文学评论 原文 满分链接",
    "中考作文 童话 优秀原文 范文地址",
    "高考作文 寓言 原文 满分作文网址",
    "中考作文 诗歌除外 优秀原文 链接",
    # ----- 增加好作家文章搜索 -----
    "好作家 优秀文章 原文 网址 无赏析",
    "著名作家 散文 原文 全文 链接",
    "名家 记叙文 范文 原文 不含点评",
    "鲁迅 文章 原文 全文 网址",
    "朱自清 散文 原文 全文 链接",
    "老舍 经典文章 原文 无解析"
]

website = []
for query in search_queries:
    try:
        result = baidu_search(query)
        for ref in result["references"]:
            print(f"- {ref['url']}")
            website.append(ref['url'])
    except Exception as e:
        print(f"搜索 '{query}' 出错: {e}")
    time.sleep(2.5)  # 避免请求过快

# 去重
website = list(set(website))
print(f"\n共获取到 {len(website)} 个不同的文章链接")





import requests
from bs4 import BeautifulSoup
import chardet


def extract_text_from_url(url):

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        # 自动检测编码
        encoding = chardet.detect(resp.content)['encoding'] or 'utf-8'
        resp.encoding = encoding
        soup = BeautifulSoup(resp.text, 'lxml')

        # 移除 script, style 等标签
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()

        # 尝试多种常见正文容器
        text = None
        for selector in ['article', '.content', '#content', '.post-content', '.article-content', 'main']:
            elem = soup.select_one(selector)
            if elem:
                text = elem.get_text('\n', strip=True)
                break
        if not text:
            # 回退：取 body 内文本
            text = soup.body.get_text('\n', strip=True) if soup.body else ''

        # 清理多余空行
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return '\n'.join(lines)
    except Exception as e:
        print(f"提取失败 {url}: {e}")
        return None


def extract_all_articles(urls):
    """批量提取文章，返回成功的内容列表"""
    articles = []
    for i, url in enumerate(urls):
        print(f"正在提取 ({i + 1}/{len(urls)}): {url[:80]}...")
        content = extract_text_from_url(url)
        if content:
            articles.append(content)
    return articles


# 使用（假设 website 是你的 URL 列表）
articles = extract_all_articles(website)

# 保存到文件
with open('collected_articles.txt', 'w', encoding='utf-8') as f:
    f.write('\n\n---\n\n'.join(articles))

import dashscope
from dashscope import Generation

# ========== 排版函数（同前） ==========
def reformat_text_with_qwen(raw_text: str, api_key: str) -> str:
    dashscope.api_key = api_key
    prompt = f"""请对以下文章内容进行重新排版，要求：
1. 只保留文章正文，删除页眉、页脚、导航栏、广告、版权声明、无关链接等噪音。
2. 每个段落内部不要有多余空格。
3. 如果文章有标题和作者，请单独放在正文之前，格式为“标题：xxx\n作者：xxx”。
4. 正文使用清晰的分段，每段开头不需要缩进，段落之间空一行。
5. 输出内容不要包含任何额外的解释说明，直接输出排版后的文章。
6.如果原来文章有空行不当的，要适当加以空行
以下是需要排版的原始内容：
---
{raw_text}
---
"""
    try:
        response = Generation.call(
            model='qwen-turbo',
            messages=[{'role': 'user', 'content': prompt}],
            result_format='message'
        )
        if response.status_code == 200:
            return response.output.choices[0].message.content
        else:
            print(f"排版失败: {response.code} - {response.message}")
            return raw_text
    except Exception as e:
        print(f"调用Qwen异常: {e}")
        return raw_text

# ========== 读取已保存的文件，逐篇排版 ==========
input_file = 'collected_articles.txt'
output_file = 'formatted_articles.txt'

# 读取整个文件内容
with open(input_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 按分隔符 "---" 分割成文章列表（注意前后可能有空串）
articles_raw = content.split('\n\n---\n\n')
# 过滤掉空字符串
articles_raw = [art.strip() for art in articles_raw if art.strip()]

print(f"共读取 {len(articles_raw)} 篇文章，开始排版...")

# 设置你的 API Key（最好从环境变量读取）
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")

formatted_articles = []
for i, raw in enumerate(articles_raw):
    print(f"正在排版第 {i+1}/{len(articles_raw)} 篇...")
    cleaned = reformat_text_with_qwen(raw, DASHSCOPE_API_KEY)
    formatted_articles.append(cleaned)

# 保存排版后的文章
with open(output_file, 'w', encoding='utf-8') as f:
    f.write('\n\n---\n\n'.join(formatted_articles))

print(f"排版完成！结果保存到 {output_file}")

