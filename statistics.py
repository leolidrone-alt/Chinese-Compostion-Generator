
import os
import re
import json
import numpy as np
from pathlib import Path

# 如果没有安装以下库，先运行：pip install jieba snownlp
import jieba
from snownlp import SnowNLP


class CorpusAnalyzer:
    def __init__(self, corpus_path):
        self.corpus_path = corpus_path
        self.articles = []
        self.results = {
            "sentence_stats": {"lengths": [], "mean": 0, "std": 0},
            "paragraph_stats": {"lengths": [], "mean": 0, "std": 0, "p90": 0},
            "sentiment_curves": [],
            "golden_sentences": [],
            "concrete_word_ratio": [],
        }

    def load_articles(self):
        """加载语料库中的所有txt文件"""
        corpus_dir = Path(self.corpus_path)
        for file_path in corpus_dir.glob("*.txt"):
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
                # 简单清洗：移除多余空行，但保留段落结构
                text = re.sub(r'\n{3,}', '\n\n', text)
                if len(text) > 300:  # 过滤过短的文本
                    self.articles.append(text)
        print(f"已加载 {len(self.articles)} 篇文章")

    def analyze_sentences(self, text):
        """分析单篇文章的句子长度"""
        # 按句号、问号、感叹号分句
        sentences = re.split(r'[。！？!?]', text)
        lengths = []
        for s in sentences:
            s = s.strip()
            if s:
                # 去除空格和换行后计算字符数
                clean_s = re.sub(r'\s+', '', s)
                if clean_s:
                    lengths.append(len(clean_s))
        return lengths

    def analyze_paragraphs(self, text):
        """分析单篇文章的段落长度"""
        # 按两个换行分段
        paragraphs = re.split(r'\n\n+', text)
        lengths = []
        for p in paragraphs:
            p = p.strip()
            if p:
                clean_p = re.sub(r'\s+', '', p)
                if len(clean_p) > 20:  # 过滤过短的段落（可能是标题或分隔符）
                    lengths.append(len(clean_p))
        return lengths

    def analyze_sentiment_curve(self, text, segments=10):
        """分析情感曲线：将文章等分为N段，计算每段的情感得分"""
        clean_text = re.sub(r'\s+', '', text)
        if len(clean_text) < 500:
            return None

        segment_size = len(clean_text) // segments
        curve = []
        for i in range(segments):
            start = i * segment_size
            end = (i + 1) * segment_size if i < segments - 1 else len(clean_text)
            segment = clean_text[start:end]
            if segment:
                try:
                    score = SnowNLP(segment).sentiments
                    curve.append(round(score, 3))
                except:
                    curve.append(0.5)
        return curve

    def find_golden_sentences(self, text):
        """识别可能的金句：长度适中、位于段尾、包含修辞特征"""
        paragraphs = re.split(r'\n\n+', text)
        golden = []
        for para in paragraphs:
            sentences = re.split(r'[。！？!?]', para)
            if len(sentences) >= 2:
                # 取每段的最后一句
                last_sent = sentences[-1].strip()
                clean_sent = re.sub(r'\s+', '', last_sent)
                # 金句特征：长度在10-30字之间，或包含比喻词
                if 10 <= len(clean_sent) <= 35:
                    golden.append(clean_sent)
                elif any(word in last_sent for word in ['像', '如', '似', '是', '仿佛']):
                    if len(clean_sent) <= 50:
                        golden.append(clean_sent)
        return golden[:20]  # 每篇最多取20句

    def analyze_concrete_ratio(self, text):
        """计算实词密度：名词和动词占总词数的比例"""
        words = list(jieba.cut(text))  # 改这里
        if len(words) < 50:
            return None

        import jieba.posseg as pseg
        word_flags = list(pseg.cut(text))  # 改这里

        concrete_count = 0
        total_count = 0
        for pair in word_flags:  # 注意：pseg.cut返回的是pair对象，不是元组
            word = pair.word
            flag = pair.flag
            if len(word.strip()) > 1:  # 忽略单字词
                total_count += 1
                if flag.startswith(('n', 'v')):  # 名词或动词
                    concrete_count += 1

        if total_count > 0:
            return concrete_count / total_count
        return None

    def run_full_analysis(self):
        """执行完整分析"""
        self.load_articles()

        all_sent_lens = []
        all_para_lens = []
        all_curves = []
        all_golden = []
        concrete_ratios = []

        for article in self.articles:
            # 句子分析
            sent_lens = self.analyze_sentences(article)
            all_sent_lens.extend(sent_lens)

            # 段落分析
            para_lens = self.analyze_paragraphs(article)
            all_para_lens.extend(para_lens)

            # 情感曲线
            curve = self.analyze_sentiment_curve(article)
            if curve:
                all_curves.append(curve)

            # 金句收集
            golden = self.find_golden_sentences(article)
            all_golden.extend(golden)

            # 实词密度
            ratio = self.analyze_concrete_ratio(article)
            if ratio:
                concrete_ratios.append(ratio)

        # 汇总统计
        self.results["sentence_stats"]["lengths"] = all_sent_lens
        self.results["sentence_stats"]["mean"] = round(np.mean(all_sent_lens), 2)
        self.results["sentence_stats"]["std"] = round(np.std(all_sent_lens), 2)

        self.results["paragraph_stats"]["lengths"] = all_para_lens
        self.results["paragraph_stats"]["mean"] = round(np.mean(all_para_lens), 2)
        self.results["paragraph_stats"]["std"] = round(np.std(all_para_lens), 2)
        self.results["paragraph_stats"]["p90"] = round(np.percentile(all_para_lens, 90), 2)

        # 平均情感曲线
        if all_curves:
            avg_curve = np.mean(all_curves, axis=0).tolist()
            self.results["sentiment_curves"] = [round(x, 3) for x in avg_curve]

        self.results["golden_sentences"] = all_golden[:50]  # 保留前50句作为示例
        self.results["concrete_word_ratio"] = {
            "mean": round(np.mean(concrete_ratios), 3) if concrete_ratios else 0,
            "std": round(np.std(concrete_ratios), 3) if concrete_ratios else 0
        }

        return self.results

    def save_results(self, output_path):
        """保存结果到JSON文件"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        print(f"分析结果已保存至 {output_path}")

    def print_summary(self):
        """打印摘要报告"""
        print("\n" + "=" * 50)
        print("【语料库分析报告】")
        print("=" * 50)
        print(f"分析文章数: {len(self.articles)}")
        print(f"\n【句子长度规律】")
        print(f"  平均句长: {self.results['sentence_stats']['mean']} 字")
        print(f"  句长标准差: {self.results['sentence_stats']['std']} (人类写作通常>10)")
        print(f"\n【段落长度规律】")
        print(f"  平均段落: {self.results['paragraph_stats']['mean']} 字")
        print(f"  段落标准差: {self.results['paragraph_stats']['std']}")
        print(f"  90%的段落不超过: {self.results['paragraph_stats']['p90']} 字")
        print(f"\n【情感曲线】(10等分)")
        if self.results['sentiment_curves']:
            curve = self.results['sentiment_curves']
            print(f"  {curve}")
            print(f"  最低点位置: 第{curve.index(min(curve)) + 1}段 ({min(curve):.3f})")
            print(f"  最高点位置: 第{curve.index(max(curve)) + 1}段 ({max(curve):.3f})")
        print(f"\n【实词密度】(名词+动词占比)")
        print(f"  均值: {self.results['concrete_word_ratio']['mean']}")
        print(f"  标准差: {self.results['concrete_word_ratio']['std']}")
        print(f"\n【金句示例】(前3句)")
        for i, sent in enumerate(self.results['golden_sentences'][:3], 1):
            print(f"  {i}. {sent}")
        print("=" * 50)


if __name__ == "__main__":
    CORPUS_PATH = "./corpus_cleaned"

    analyzer = CorpusAnalyzer(CORPUS_PATH)
    results = analyzer.run_full_analysis()
    analyzer.print_summary()
    analyzer.save_results("corpus_analysis_result3.json")