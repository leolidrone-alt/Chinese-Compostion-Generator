import os
import re
import shutil
from pathlib import Path


def is_poem(text: str,
            max_avg_line_len: int = 18,
            min_line_density: float = 0.03) -> tuple[bool, dict]:
    """
    判断一篇文章是否为诗歌。

    返回: (是否为诗歌, 特征字典)
    """
    # 去除空行，按换行分割
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if not lines:
        return False, {}

    total_chars = sum(len(line) for line in lines)
    line_count = len(lines)

    avg_line_len = total_chars / line_count
    line_density = line_count / total_chars if total_chars > 0 else 0

    # 句长标准差（辅助判断）
    line_lengths = [len(line) for line in lines]
    std_line_len = (sum((l - avg_line_len) ** 2 for l in line_lengths) / line_count) ** 0.5

    features = {
        "avg_line_len": round(avg_line_len, 1),
        "line_density": round(line_density, 4),
        "line_count": line_count,
        "total_chars": total_chars,
        "std_line_len": round(std_line_len, 1)
    }

    # 诗歌判定条件
    is_poem = (avg_line_len < max_avg_line_len) and (line_density > min_line_density)

    return is_poem, features


def filter_poems_from_corpus(
        corpus_dir: str,
        output_dir: str = None,  # 如果不为None，诗歌将被移动到此目录而非删除
        max_avg_line_len: int = 18,
        min_line_density: float = 0.03,
        dry_run: bool = False
):
    """
    遍历语料库，过滤掉诗歌。

    Args:
        corpus_dir: 语料库文件夹路径
        output_dir: 若提供，诗歌移入此文件夹；否则直接删除
        dry_run: 若为True，只统计不实际删除/移动
    """
    corpus_path = Path(corpus_dir)
    if not corpus_path.exists():
        print(f"错误：文件夹 {corpus_dir} 不存在")
        return

    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

    stats = {
        "total": 0,
        "poems": 0,
        "kept": 0,
        "poem_files": []
    }

    for txt_file in corpus_path.glob("*.txt"):
        stats["total"] += 1

        try:
            with open(txt_file, 'r', encoding='utf-8') as f:
                text = f.read()
        except Exception as e:
            print(f"读取失败 {txt_file.name}: {e}")
            continue

        is_poem_flag, features = is_poem(text, max_avg_line_len, min_line_density)

        if is_poem_flag:
            stats["poems"] += 1
            stats["poem_files"].append({
                "name": txt_file.name,
                "features": features
            })

            if not dry_run:
                if output_dir:
                    # 移动到诗歌专用文件夹
                    shutil.move(str(txt_file), str(output_path / txt_file.name))
                else:
                    # 直接删除
                    os.remove(txt_file)
        else:
            stats["kept"] += 1

    # 打印统计报告
    print("\n" + "=" * 50)
    print("【诗歌过滤报告】")
    print("=" * 50)
    print(f"总文章数: {stats['total']}")
    print(f"识别为诗歌: {stats['poems']} 篇")
    print(f"保留散文: {stats['kept']} 篇")

    if stats["poems"] > 0:
        print(f"\n被过滤的诗歌示例（前5篇）:")
        for item in stats["poem_files"][:5]:
            f = item["features"]
            print(
                f"  - {item['name']}: 平均行字符={f['avg_line_len']}, 行密度={f['line_density']}, 行数={f['line_count']}")

    if dry_run:
        print("\n⚠️ 此为模拟运行，未实际删除/移动文件。")
    else:
        if output_dir:
            print(f"\n✅ 诗歌已移动到: {output_dir}")
        else:
            print("\n✅ 诗歌已删除。")

    return stats


if __name__ == "__main__":
    # 配置区
    CORPUS_DIR = "./corpus_cleaned"  # 你的语料库文件夹
    POEM_OUTPUT_DIR = "./corpus_poems"  # 诗歌存放处（若为None则直接删除）
    DRY_RUN = False  # 先设为True模拟运行，确认无误后再改为False

    # 可调参数
    MAX_AVG_LINE_LEN = 22  # 平均每行最大字符数，低于此值倾向诗歌
    MIN_LINE_DENSITY = 0.02  # 最小行密度，高于此值倾向诗歌

    filter_poems_from_corpus(
        corpus_dir=CORPUS_DIR,
        output_dir=POEM_OUTPUT_DIR,
        max_avg_line_len=MAX_AVG_LINE_LEN,
        min_line_density=MIN_LINE_DENSITY,
        dry_run=DRY_RUN
    )