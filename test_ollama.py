# test_single_model.py
"""
单模型测试脚本：用 qwen3.5:4b 同时承担规划师和工匠的角色。
模拟完整的写作流程：生成蓝图 → 逐句生成文章。
"""
import json
import re
from ollama import chat


def clean_response(text: str) -> str:
    """清洗模型输出，移除可能的 <think> 标签和控制字符"""
    # 移除 <think>...</think> 标签
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    # 移除控制字符
    text = re.sub(r'[\x00-\x1f\x7f]', '', text)
    return text.strip()


def generate_blueprint(topic: str, emotion: str, target_words: int = 800) -> dict:
    """
    规划师：根据主题和情感生成写作蓝图（JSON格式）。
    """
    system_prompt = """你是一个细致的写作规划师。请根据用户提供的主题和情感，生成一份详细的写作蓝图。

输出必须是一个有效的JSON对象，格式如下：
{
  "title": "文章标题",
  "paragraphs": [
    {
      "type": "opening/body/climax/closing",
      "sentences": [
        {
          "core_fact": "这一句的核心事件（简短描述）",
          "must_contain": ["关键词1", "关键词2"],
          "sentiment": 0.0
        }
      ]
    }
  ]
}

要求：
- 总共约4-5个段落，每个段落2-4个句子。
- 情感值在-1.0（极度负面）到1.0（极度正面）之间。
- 直接输出JSON，不要输出任何其他文字。"""

    user_prompt = f"""主题：{topic}
情感基调：{emotion}
目标字数：约{target_words}字

请生成蓝图。"""

    response = chat(
        model='qwen3.5:4b',
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt}
        ],
        options={
            'temperature': 0.3,
            "thinking":False
            }
    )

    content = clean_response(response.message.content)
    print(content)
    # 尝试提取JSON对象
    json_match = re.search(r'\{.*\}', content, re.DOTALL)
    if json_match:
        content = json_match.group()

    try:
        blueprint = json.loads(content)
        return blueprint
    except json.JSONDecodeError as e:
        print(f"蓝图解析失败: {e}")
        print(f"原始输出: {content[:500]}...")
        return None


def generate_sentence(core_fact: str, must_contain: list, sentiment: float,
                      previous_sentence: str = "") -> str:
    """
    工匠：根据核心事实和约束生成单句。
    """
    system_prompt = """你是一个文学工匠。请根据提供的核心事实和约束，生成一句优美的中文句子。

要求：
- 必须包含所有关键词。
- 长度在15-40字之间。
- 情感与给定值匹配。
- 如果提供了前一句，请确保句子自然衔接。
- 直接输出句子，不要任何解释。"""

    user_prompt = f"""核心事实：{core_fact}
必须包含的关键词：{', '.join(must_contain)}
情感值：{sentiment}（-1.0为极度负面，1.0为极度正面）
前一句："{previous_sentence}"（如果没有则为空）

请生成句子："""

    response = chat(
        model='qwen3.5:4b',
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt}
        ],
        options={'temperature': 1.1, 'top_p': 0.9}
    )

    sentence = clean_response(response.message.content)
    # 去掉可能的多余引号和首尾空白
    sentence = sentence.strip('"''').strip()
    return sentence


def test_full_pipeline():
    """测试完整流水线"""
    topic = input("请输入文章主题（直接回车使用默认'老王'）: ").strip()
    if not topic:
        topic = "老王"
    emotion = input("请输入情感倾向（直接回车使用'温暖、怀念'）: ").strip()
    if not emotion:
        emotion = "温暖、怀念"

    print(f"\n{'='*50}")
    print(f"测试主题: {topic}")
    print(f"情感倾向: {emotion}")
    print(f"{'='*50}\n")

    # 1. 生成蓝图
    print("正在生成蓝图...")
    blueprint = generate_blueprint(topic, emotion)
    if blueprint is None:
        print("蓝图生成失败，测试终止。")
        return

    print(f"蓝图生成成功！标题: {blueprint.get('title', '未命名')}")
    print(f"段落数: {len(blueprint.get('paragraphs', []))}\n")

    # 2. 逐句生成文章
    article = ""
    previous_sentence = ""
    total_chars = 0

    for para in blueprint.get('paragraphs', []):
        para_text = ""
        for sent in para.get('sentences', []):
            core_fact = sent.get('core_fact', '')
            must_contain = sent.get('must_contain', [])
            sentiment = sent.get('sentiment', 0.0)

            sentence = generate_sentence(core_fact, must_contain, sentiment,
                                         previous_sentence)
            para_text += sentence
            previous_sentence = sentence
            total_chars += len(sentence)
        article += para_text + "\n\n"

    print(f"{'='*50}")
    print(f"【生成文章】")
    print(f"{'='*50}")
    print(article)
    print(f"全文字数（含标点）: {total_chars}")


if __name__ == "__main__":
    test_full_pipeline()
