# MAIN.py
import os
import json
import re
import random
from datetime import datetime
from kit_planner import PlannerKit
from kit_craftsman import CraftsmanKit
from kit_rhythm import RhythmKit, NarrativeArbiter
from kit_style_arbiter import StyleArbiter
from kit_divergent import DivergentKit
from kit_judger import ask_if_human
from kit_coherence import CoherenceKit

def get_user_input():
    print("=" * 50)
    print("欢迎使用 AI 写作助手")
    print("=" * 50)
    topic = input("请输入文章主题（或直接回车让我自由发挥）：").strip()
    emotion = input("请输入情感倾向（如：怀念、温暖、感伤，可留空）：").strip()
    if not emotion:
        emotion = "中性"
    while True:
        try:
            target_words = input("请输入目标字数（建议500-1500字，直接回车默认800）：").strip()
            if not target_words:
                target_words = 800
                break
            target_words = int(target_words)
            if target_words < 300:
                print("字数太少，建议至少300字。")
            else:
                break
        except ValueError:
            print("请输入有效的数字。")
    return {"topic": topic, "emotion": emotion, "target_words": target_words}

def save_blueprint(blueprint: dict, user_input: dict, output_dir: str = "blueprints"):
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{output_dir}/blueprint_{timestamp}.json"
    data = {
        "user_input": user_input,
        "blueprint": blueprint,
        "generated_at": timestamp
    }
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n蓝图已保存至: {filename}")

def load_word_graph(graph_path: str = "relation_graph_filtered.json"):
    if not os.path.exists(graph_path):
        print(f"警告：词云文件 {graph_path} 未找到，将使用内置素材。")
        return {"edges": []}
    with open(graph_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def theme_consistency(detail: str, sentiment: float) -> float:
    """计算词云细节与当前句子情感的匹配度"""
    strong_positive = ["欢快", "明亮", "温暖", "笑容", "盛开", "灿烂", "耀眼", "甜", "绽放", "轻盈"]
    strong_negative = ["冰冷", "凋零", "枯黄", "黯淡", "沉默", "锈迹", "灰", "腐朽", "破碎", "苍凉"]
    pos_count = sum(1 for w in strong_positive if w in detail)
    neg_count = sum(1 for w in strong_negative if w in detail)
    if sentiment < -0.3:
        return neg_count - pos_count
    elif sentiment > 0.3:
        return pos_count - neg_count
    else:
        return -abs(pos_count - neg_count)

def find_related_detail(keyword: str, graph: dict, context: str = "", n: int = 5, sentiment: float = 0.0) -> list:
    """检索并过滤词云细节"""
    candidates = []
    for edge in graph.get("edges", []):
        if edge["from"] == keyword or edge["to"] == keyword:
            candidates.append(edge["detail"])
    if not candidates:
        return []

    # 上下文关键词过滤
    if context:
        context_words = set(re.findall(r'[\u4e00-\u9fa5]{2,}', context))
        filtered = [d for d in candidates if set(re.findall(r'[\u4e00-\u9fa5]{2,}', d)) & context_words]
        if filtered:
            candidates = filtered

    # 情感极性过滤
    if sentiment != 0.0:
        positive_words = ["快乐", "美好", "温暖", "甜蜜", "开心", "欢笑", "轻快", "灿烂", "明媚", "喜悦"]
        negative_words = ["悲伤", "痛苦", "苦涩", "冰冷", "绝望", "黑暗", "沉重", "枯萎", "凋零", "凄凉"]
        polarity_filtered = []
        for detail in candidates:
            pos_count = sum(1 for w in positive_words if w in detail)
            neg_count = sum(1 for w in negative_words if w in detail)
            if sentiment < -0.3 and pos_count > neg_count:
                continue
            if sentiment > 0.3 and neg_count > pos_count:
                continue
            polarity_filtered.append(detail)
        if polarity_filtered:
            candidates = polarity_filtered

    # 主题一致性评分
    if sentiment != 0.0:
        scored = [(d, theme_consistency(d, sentiment)) for d in candidates]
        scored.sort(key=lambda x: x[1], reverse=True)
        keep_count = max(2, int(len(scored) * 0.7))
        candidates = [d for d, _ in scored[:keep_count]]

    return random.sample(candidates, min(n, len(candidates)))

def generate_article_from_blueprint(blueprint, craftsman, arbiter, rhythm, divergent, graph, style="prose", coherence_kit=None):
    """根据蓝图生成文章，支持各种控制模块，并可选进行一致性校正"""
    article_parts = []
    previous_sentences = []          # 存储最近3句，用于工匠上下文
    consecutive_wo_start = 0
    seen_hashes = set()              # 全局去重
    ending_style = blueprint.get("ending_style", "implicit")  # 从蓝图中获取结尾风格

    for para in blueprint["paragraphs"]:
        rhythm.reset_paragraph()
        para_sentences = []
        para_word_count = 0
        para_atmosphere_used = False
        para_narrative_used = False
        paragraph_intent = para.get("paragraph_intent", "")
        # 如果是结尾段落，附加结尾风格提示
        if para.get("type") == "closing":
            paragraph_intent += f" 结尾风格要求：{ending_style}"

        # 段落前可能插入呼吸句
        if divergent.should_breathe(para.get("target_word_count", 120)):
            if previous_sentences:
                last_text = previous_sentences[-1]
                words = re.findall(r'[\u4e00-\u9fa5]{2,4}', last_text)
                if words:
                    breath_word = random.choice(words)
                    breath_sentence = f"{breath_word}。"
                    para_sentences.append(breath_sentence)
                    rhythm.record(breath_sentence)
                    para_word_count += len(re.sub(r'[^\u4e00-\u9fa5]', '', breath_sentence))

        for sent_plan in para["sentences"]:
            context = ""
            if "core_fact" not in sent_plan:
                if "must_contain" in sent_plan and sent_plan["must_contain"]:
                    sent_plan["core_fact"] = "、".join(sent_plan["must_contain"][:3])
                else:
                    continue
            if "must_contain" not in sent_plan:
                sent_plan["must_contain"] = []
            if "sentiment" not in sent_plan:
                sent_plan["sentiment"] = 0.0
            if "type_tag" not in sent_plan:
                sent_plan["type_tag"] = "action"

            # 叙事手法仲裁（考试文体强制线性）
            if style in ("exam_junior", "exam_senior"):
                technique = "linear"
            else:
                technique = arbiter.propose_technique()
                if not arbiter.is_suitable(technique, previous_sentences, sent_plan["core_fact"], blueprint.get("title", "")):
                    technique = "linear"
            adjusted_plan = sent_plan.copy()

            # 标签熔断
            if technique != "linear":
                para_narrative_used = True
                adjusted_plan["atmosphere_hint"] = None
            else:
                hint = sent_plan.get("atmosphere_hint")
                if hint == "third_person_glimpse":
                    hint = None
                if hint and not para_atmosphere_used:
                    para_atmosphere_used = True
                else:
                    hint = None
                adjusted_plan["atmosphere_hint"] = hint

            # 叙事手法调整（仅非线性时添加时间标记）
            if technique == "flashback":
                must_contain = sent_plan.get("must_contain", []) + ["那时", "记得"]
                adjusted_plan["must_contain"] = list(set(must_contain))
            elif technique == "interlude":
                must_contain = sent_plan.get("must_contain", []) + ["记得"]
                adjusted_plan["must_contain"] = list(set(must_contain))

            # 段落意图传递
            if paragraph_intent:
                adjusted_plan["paragraph_intent"] = paragraph_intent

            # 闲笔跳跃（仅非结尾段落，结尾段落已禁用）
            if divergent.should_insert_idle() and para_word_count > 30 and para.get("type") not in ("climax", "closing"):
                core_nouns = [w for w in sent_plan.get("must_contain", []) if len(w) >= 2]
                if core_nouns:
                    context = " ".join(sent_plan.get("must_contain", [])) + " " + (previous_sentences[-1] if previous_sentences else "")
                    details = find_related_detail(core_nouns[0], graph, context=context, n=1)
                    if details:
                        extra_clue = details[0][:12]
                        adjusted_plan["must_contain"] = list(set(adjusted_plan.get("must_contain", []) + [extra_clue]))
                        adjusted_plan["atmosphere_hint"] = "seamless_divergent_detail"
                        idle_sentence = details[0]
                        para_sentences.append(idle_sentence)
                        rhythm.record(idle_sentence)
                        para_word_count += len(re.sub(r'[^\u4e00-\u9fa5]', '', idle_sentence))
                        previous_sentences.append(idle_sentence)
                        if len(previous_sentences) > 3:
                            previous_sentences.pop(0)

            # 句首“我”控制（仅第一人称文章启用）
            # 这里简化：如果文章第一人称代词多，则启用；否则忽略。具体可由 coherence_kit 检测
            if consecutive_wo_start >= 2:
                adjusted_plan["atmosphere_hint"] = "vary_sentence_opening"

            # 获取目标长度
            recent_sentiments = [sent_plan.get("sentiment", 0) for sent_plan in para["sentences"][-5:]]
            target_min, target_max = rhythm.get_target_range(
                para_type=para.get("type", "body"),
                recent_sentiments=recent_sentiments
            )

            # 词云素材注入
            if not adjusted_plan.get("atmosphere_hint"):
                core_keyword = None
                for w in sent_plan.get("must_contain", []):
                    if len(w) >= 2:
                        core_keyword = w
                        break
                if core_keyword:
                    if style == "free" and random.random() > 0.11:
                        pass
                    else:
                        details = find_related_detail(core_keyword, graph, context=context, n=1, sentiment=sent_plan.get("sentiment", 0))
                        if details:
                            extra_clue = details[0][:12]
                            adjusted_plan["must_contain"] = list(set(adjusted_plan.get("must_contain", []) + [extra_clue]))
                            adjusted_plan["atmosphere_hint"] = "divergent_detail"

            # 动态扰动概率
            dynamic_serendipity = 0.05
            if para.get("type") in ("climax", "closing"):
                dynamic_serendipity = 0.0
            elif abs(sent_plan.get("sentiment", 0)) > 0.7:
                dynamic_serendipity = 0.01

            # 高潮/结尾禁用闲笔和闯入
            if para.get("type") in ("climax", "closing"):
                divergent.idle_trigger_prob = 0.0
                divergent.intrusion_prob = 0.0

            # ========== 工匠生成（传入 previous_sentences） ==========
            sentence = craftsman.generate_sentence(
                core_fact=adjusted_plan["core_fact"],
                must_contain=adjusted_plan["must_contain"],
                sentiment=sent_plan.get("sentiment", 0),
                target_len_min=target_min,
                target_len_max=target_max,
                previous_sentences=previous_sentences,
                atmosphere_hint=adjusted_plan.get("atmosphere_hint"),
                serendipity_prob=dynamic_serendipity,
                paragraph_intent=adjusted_plan.get("paragraph_intent", "")
            )

            # 全局文本哈希去重
            sentence_hash = hash(sentence[:15])
            if sentence_hash in seen_hashes:
                sentence = craftsman.generate_sentence(
                    core_fact=adjusted_plan["core_fact"],
                    must_contain=adjusted_plan["must_contain"],
                    sentiment=sent_plan.get("sentiment", 0),
                    target_len_min=target_min,
                    target_len_max=target_max,
                    previous_sentences=previous_sentences,
                    atmosphere_hint=adjusted_plan.get("atmosphere_hint"),
                    serendipity_prob=0.1,
                    paragraph_intent=adjusted_plan.get("paragraph_intent", "")
                )
            seen_hashes.add(hash(sentence[:15]))

            rhythm.record(sentence)
            para_sentences.append(sentence)

            # 更新“我”开头计数
            if sentence.startswith("我"):
                consecutive_wo_start += 1
            else:
                consecutive_wo_start = 0

            previous_sentences.append(sentence)
            if len(previous_sentences) > 3:
                previous_sentences.pop(0)
            para_word_count += len(re.sub(r'[^\u4e00-\u9fa5]', '', sentence))

            if rhythm.should_break_paragraph():
                break

        # 清理标点，拼接段落
        cleaned = [s.rstrip("。！？!?") for s in para_sentences]
        para_text = "。".join(cleaned) + "。"
        article_parts.append(para_text)

    # 后处理：如果提供了 coherence_kit，对整个文章进行统一修正（而非分段）
    if coherence_kit:
        full_article = "\n\n".join(article_parts)
        # 注意：full_correct 会重新分句，可能改变换行，但不影响意义
        fixed_article = coherence_kit.full_correct(full_article)
        return fixed_article, rhythm
    else:
        return "\n\n".join(article_parts), rhythm

def main():
    user_input = get_user_input()

    style_arbiter = StyleArbiter()
    style = style_arbiter.analyze(user_input["topic"])
    print(f"\n系统判断文体：{style}")

    # 随机选择结尾风格（意犹未尽45%，升华45%，烂尾10%）
    rand = random.random()
    if rand < 0.45:
        ending_style = "implicit"      # 意犹未尽（意象结尾）
    elif rand < 0.9:
        ending_style = "explicit"      # 明显升华（点题总结）
    else:
        ending_style = "abrupt"        # 看似烂尾（突然中断）
    print(f"本次结尾风格：{ending_style}")

    # 根据文体设置参数
    if style in ("exam_junior", "exam_senior"):
        craftsman_temp, craftsman_top_p, rhythm_target_std, ending_type = 1.0, 0.9, 13, "summary"
        # 考试文体强制使用“明显升华”结尾（避免烂尾风险）
        ending_style = "explicit"
    else:
        craftsman_temp, craftsman_top_p, rhythm_target_std = 1.3, 0.85, 16
        ending_type = random.choice(["image", "dialogue", "action"])

    # 初始化组件
    planner = PlannerKit()
    craftsman = CraftsmanKit(
        temperature=craftsman_temp,
        top_p=craftsman_top_p
    )
    arbiter = NarrativeArbiter(api_key=os.environ.get("DEEPSEEK_API_KEY"))
    rhythm = RhythmKit(target_std=rhythm_target_std)
    rhythm.set_target_total(user_input["target_words"])
    divergent = DivergentKit()
    graph = load_word_graph()
    # 初始化 CoherenceKit：默认第三人称，开启代词替换为人名
    coherence = CoherenceKit(default_person="他", resolve_pronouns_to_nouns=True)

    # 生成词云摘要（用于注入细节）
    try:
        import jieba
        words = list(jieba.cut(user_input["topic"]))
    except ImportError:
        words = re.findall(r'[\u4e00-\u9fa5]{2,}', user_input["topic"])
    stopwords = {"的", "了", "是"}   # 简化，可补充完整列表
    core_words = [w for w in words if len(w) >= 2 and w not in stopwords][:5]
    details_list = []
    for w in core_words:
        details_list.extend(find_related_detail(w, graph, n=2))
    unique_details = list(set(details_list))[:5]
    graph_summary = "; ".join(unique_details)

    print("\n正在生成写作蓝图...")
    blueprint = planner.generate_blueprint(
        topic=user_input["topic"],
        emotion=user_input["emotion"],
        target_words=user_input["target_words"],
        style=style,
        ending_type=ending_type,      # 保留兼容，实际不再使用具体值
        ending_style=ending_style,    # 新增参数
        graph_context=graph_summary
    )

    save_blueprint(blueprint, user_input)

    choice = input("\n是否立即生成文章？(y/n): ").strip().lower()
    if choice != 'y':
        return

    print("\n正在生成文章...")
    article, rhythm_obj = generate_article_from_blueprint(
        blueprint, craftsman, arbiter, rhythm, divergent, graph, style,
        coherence_kit=coherence
    )
    print("\n" + "=" * 50)
    print(article)
    print("=" * 50)
    print(f"全文实际字数: {len(re.sub(r'[^\u4e00-\u9fa5]', '', article))} 字")
    print(f"句长标准差: {rhythm_obj.get_final_std():.2f}")

    score, reason = ask_if_human(article, os.getenv("DASHSCOPE_API_KEY"))
    print("\n" + "=" * 50)
    print(f"像人指数：{score}/5 - {reason}")

if __name__ == "__main__":
    main()