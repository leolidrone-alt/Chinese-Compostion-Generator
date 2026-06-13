import os
import re


def split_articles(input_file, output_dir):
    """将包含多篇文章的大文件分割为独立的txt文件"""
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 按连续三个以上换行符分割（文章之间的分隔）
    articles = re.split(r'\n{3,}', content)

    saved_count = 0
    for i, article in enumerate(articles):
        article = article.strip()
        # 过滤过短的片段（标题、分隔符等）
        if len(article) > 300:
            filename = f"article_{i + 1:03d}.txt"
            filepath = os.path.join(output_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as out:
                out.write(article)
            saved_count += 1
            print(f"已保存: {filename} ({len(article)} 字符)")

    print(f"\n共分割出 {saved_count} 篇文章，保存在 '{output_dir}' 目录")


# 使用
split_articles("final_clean_articles.txt", "./corpus")