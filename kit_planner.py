# kit_planner.py
import os
import time
import requests
import json
import re
from typing import Dict, Any
from kit_narrative_logic import NarrativeLogicKit

class PlannerKit:
    def __init__(self, base_url="https://api.deepseek.com", model: str = "deepseek-chat", max_retries: int = 3):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.model = model
        self.endpoint = f"{base_url}/chat/completions"
        self.max_retries = max_retries
        self.narrative_logic = NarrativeLogicKit()

    def generate_blueprint(
            self,
            topic: str,
            emotion: str,
            target_words: int,
            style: str = "prose",
            ending_type: str = "image",      # 保留向后兼容，但实际不再使用
            ending_style: str = "implicit",  # explicit / implicit / abrupt
            graph_context: str = ""
    ) -> Dict[str, Any]:
        # ================= 1. 句子数量估算（调整后，平均句长20-25字） =================
        if target_words > 1200:
            min_sentences = max(30, target_words // 25)
            max_sentences = max(45, target_words // 18)
        elif target_words > 1000:
            min_sentences = max(25, target_words // 22)
            max_sentences = max(40, target_words // 16)
        else:
            min_sentences = max(20, target_words // 20)
            max_sentences = max(35, target_words // 14)

        # ================= 2. 文体相关的段落结构指令 =================
        if style == "free":
            structure_guide = """
            - 结构紧凑：有一个核心意象（如“老钟”“旧琴”“废窑”），全篇围绕这个意象展开。
            - 叙事弧线：按照“童年-青年-中年-晚年”四个阶段，每个阶段用1-2个具体场景展现。
            - 禁止跳跃：每个段落之间必须有时间或事件上的明确衔接，不能出现突兀的场景切换。
            - 意象必须贯穿：核心意象在文章至少出现5次，每次服务于不同的叙事功能。
            - **意象多样化**：每次生成时必须选择与之前不同的核心意象，优先选择非机械类的物品（如植物、布料、器皿、乐器、农具等），禁止连续两次使用同一类或者同一个意象。
            """
            emotion_guide = "- 情感克制，用意象和动作代替直白抒情，结尾留白。"
        elif style in ("exam_junior", "exam_senior"):
            structure_guide = """
            - 结构严谨：引论 → 本论（2-3个分论点）→ 结论
            - 每个分论点必须搭配1个具体事例或论据，看看能不能跟实事结合一下或者结合历史"""
            emotion_guide = "- 情感曲线中性偏正，结尾点题升华"
        else:
            structure_guide = """
            - 结构自由：开篇 → 展开（2-3个场景或细节）→ 收束
            - 优先使用具体意象和感官细节，避免抽象议论"""
            emotion_guide = "- 情感曲线自然波动，结尾留白或意象收束"

        # ================= 3. 结尾风格指令（基于 ending_style） =================
        if ending_style == "explicit":
            ending_instruction = """
- 结尾必须直接点题、升华主题，可以使用总结性语句（例如“我终于明白……”）。
- 允许出现“因此”“总之”“这就是”等词，但要自然。
- 最后一句应明确传递文章的中心思想。
"""
        elif ending_style == "abrupt":
            ending_instruction = """
- 结尾要突然中断，不要解释，不要总结。
- 最后一句必须是动作描写、环境描写，或者一句看似无关的对话。
- 绝对不能出现“我明白了”“从此以后”“这就是”等收束性语句。
- 让读者感觉文章仿佛没有写完，但实际上深意已在不言中。
"""
        else:  # implicit (意犹未尽)
            ending_instruction = """
- 结尾用一个具体的视觉意象、动作细节或未完成的场景收束。
- 不要直接点题，不要说明道理。
- 让意象本身承载余味，例如“那本旧字典静静躺在书架上，月光下墨迹仿佛还在微微浮动。”
- 禁止出现“总之”“因此”“我终于明白”等总结词。
"""

        # ================= 4. 词云素材注入提示 =================
        graph_prompt = ""
        if graph_context:
            graph_prompt = f"""
[Injected Imagery Context]
The following unique details have been retrieved from a creative imagery database.
Please try to incorporate at least 1-2 of them naturally into the blueprint
as concrete sensory details or scene elements:

{graph_context}
"""

        # ================= 5. 叙事结构指南 =================
        narrative_guideline = self.narrative_logic.get_structure_guideline()
        narrative_rules = """
【叙事结构优先级规则】
1. 如果用户在主题或情感描述中暗示了某种叙事结构，以用户暗示为准，忽略上述随机建议。
   - “成绩逐渐变差”→“高开低走”
   - “从底层一步步爬上来”→“低开高走”
   - “人生大起大落”→“三起三落”
   - “回到原点才发现”→“环形结构”
   - “几代人的命运交织”→“多线并行”
2. 用户未暗示时，可采纳上述随机建议。
3. 你有权否决随机建议，自行选择更合适的结构。
4. 优先级：用户暗示 > 你的自主判断 > 随机建议
"""

        # ================= 6. 构建 system_prompt =================
        system_prompt = f"""You are a meticulous writing planner. Create a detailed blueprint for a {style} article.

【叙事结构建议】
{narrative_guideline}

{narrative_rules}

The blueprint must include:
- A title for the article.
- Overall emotional baseline (float from -1.0 to 1.0).
- A list of paragraphs with target_word_count and sentences.
{structure_guide}

Emotional arc requirements:
{emotion_guide}
{ending_instruction}

Output ONLY valid JSON, no extra text."""

        # ================= 7. 构建 user_prompt =================
        user_prompt = f"""
[Article Topic]
{topic}

[Desired Emotion]
{emotion}

[Target Total Length]
Approximately {target_words} Chinese characters.

[Style]
{style}

{graph_prompt}

**IMPORTANT**: A typical Chinese article of {target_words} characters contains about {min_sentences} to {max_sentences} sentences.
Please ensure your blueprint contains an appropriate number of sentences.
For a {target_words}-character article, a typical distribution is:
- Opening: 15-20%
- Body (1-2 paragraphs): 50-60%
- Climax/Turning point: 15-20%
- Closing: 10-15%

For sentences in the climax or turning point paragraphs, add an atmosphere_hint field.
Optionally, for sentences with type_tag inner_thought or reflection, you may add
a psychological_hint field with value inner_monologue or exclamation.

**CRITICAL**: The article MUST contain at least {min_sentences} sentences total.
Do NOT output fewer than {min_sentences} sentences.

[CRITICAL OUTPUT FORMAT]
Each sentence object MUST contain exactly these fields:
- "core_fact": a concise description of what this sentence is about
- "must_contain": a list of 3-5 Chinese keywords
- "sentiment": a float between -1.0 and 1.0
- "type_tag": one of the allowed sentence types

*Do NOT use "content" or any other field names!*
It's better for you to give a name for the characters in the articles, but not compulsory.
Only give out the blueprint to the json documents instead of thinking process.
Now generate the JSON blueprint.
"""

        # ================= 8. 追加补充指令 =================
        system_prompt += f"""
**CRITICAL**: For a {target_words}-character article, you must plan at least {min_sentences} sentences total. 
Each sentence MUST contribute meaningfully to the word count. 
Do NOT skip or condense any planned sentence.
"""
        system_prompt += """
**MANDATORY IMAGERY CONTROL**
The core imagery (e.g. "老钟") MUST appear at least once in every paragraph.
Each appearance should serve a different narrative function:
- Opening: introduce the imagery as the protagonist's origin.
- Body paragraphs: show how the imagery changes with each rise and fall.
- Climax: the protagonist physically interacts with the imagery one last time.
- Closing: the imagery transforms from a personal object into a symbol.
The imagery is NOT decorative — it IS the protagonist's life timeline.
"""
        system_prompt += """
**GENERATIONAL IMAGERY EXTENSION**
If the article spans the protagonist's entire life, the final paragraph SHOULD show 
the core imagery being passed on to the next generation (child, grandchild, apprentice).
This can be done through:
- A physical handover: the protagonist gives the object to someone.
- A discovered relic: a descendant finds the object and understands its meaning.
- An inherited action: someone repeats an action associated with the object.
This adds a sense of continuity and legacy to the ending.
"""
        system_prompt += """
可以尝试用一些时政类的东西或者历史，但是不要生硬了，主要保证故事衔接好，该加细节描写的时候加进去，不要每次都加，适合的时候可以使用
"""

        # ================= 9. 发送请求 =================
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.3,
            "response_format": {"type": "json_object"}
        }

        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self.endpoint,
                    headers=headers,
                    json=payload,
                    timeout=300
                )
                response.raise_for_status()
                result = response.json()
                content = result["choices"][0]["message"]["content"]

                # 清除思考链标签
                content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
                content = re.sub(r'[\x00-\x1f]', '', content)

                # 提取 JSON 对象
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    content = json_match.group()

                blueprint = json.loads(content)
                # 在蓝图中记录结尾风格，供生成时使用
                blueprint["ending_style"] = ending_style
                return blueprint

            except requests.exceptions.Timeout as e:
                last_error = e
                print(f"[Planner] 请求超时 (尝试 {attempt + 1}/{self.max_retries})")
            except requests.exceptions.RequestException as e:
                last_error = e
                print(f"[Planner] 请求失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")

            if attempt < self.max_retries - 1:
                wait_time = (attempt + 1) * 5
                print(f"[Planner] {wait_time}秒后重试...")
                time.sleep(wait_time)

        raise Exception(f"规划师API调用失败，已重试{self.max_retries}次。最后错误: {last_error}")