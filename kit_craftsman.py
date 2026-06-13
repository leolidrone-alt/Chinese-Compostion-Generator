import os
import re
import json
import time
import random
from http import HTTPStatus
from dashscope import Generation
import dashscope


class CraftsmanKit:
    def __init__(self, api_key=os.getenv("DASHSCOPE_API_KEY"),
                 base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                 model="qwen-plus", temperature=1.3, top_p=0.85, max_tokens=400):
        self.base_url = base_url
        self.model = model
        self.base_temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens

        self.system_prompt = """You are a literary craftsman. Generate FIVE versions of the same Chinese sentence with different lengths and structures.

[Requirements]
1. All versions must convey the same core fact and include all mandatory keywords.
2. Version A (very_short): 4-8 characters.
3. Version B (short): 10-18 characters. Use a different sentence structure than Version A.
4. Version C (medium): 20-30 characters. Use a rhetorical device if appropriate.
5. Version D (long): 35-50 characters. Include one sensory detail.
6. Version E (very_long): 48-60 characters. Include MORE THAN ONE sensory detail (e.g., visual + auditory, or tactile + olfactory).
7. Ensure the five versions are clearly distinct in wording, rhythm, and detail.
8. Output ONLY a valid JSON object: {"very_short": "...", "short": "...", "medium": "...", "long": "...", "very_long": "..."}
9. Do not include any extra text, explanations, or markdown formatting.
10. MUST BE ALL CHINESE, DO NOT EXIST ANY ENGLISH WORDS OR ARROW, ECT.!!!!!!!!!
"""

        self.system_prompt += """
[Seamless Detail Integration]
When a divergent_detail from an external imagery database is provided:
- Weave it directly into the narrative action or sensory observation.
- Do NOT present it as a standalone interjection or a random metaphor.
- Ground it in the scene: Who is observing it? What triggers this observation?
- Ensure the sentence flows naturally from the previous one without a jarring context shift.
"""

        self.CLICHE_PATTERNS = [
            (r".{0,10}像.{1,5}(山|海|太阳|灯塔|明灯|指路|方向).{0,10}", "像XX一样伟大"),
            (r".{0,10}(教会了|让我明白|让我懂得|让我知道).{0,15}", "教会了我XX"),
            (r".{0,10}(永远|永远地|再也|再也无法).{1,10}(忘记|铭记|忘掉|释怀).{0,10}", "永远不能忘记"),
            (r".{0,10}心中.{1,5}(涌起|充满|泛起|升腾).{0,10}", "心中涌起一股暖流"),
            (r".{0,10}像.{1,5}(春风|阳光|雨露|甘霖|暖阳).{0,10}", "像春风一样温暖"),
            (r".{0,10}(岁月|时光|光阴).{0,5}(如梭|荏苒|似水|如歌).{0,10}", "岁月如梭"),
            (r".{0,10}(无私奉献|默默付出|含辛茹苦|任劳任怨).{0,10}", "无私奉献"),
            (r".{0,10}(最好的|最珍贵的|最难忘的|最宝贵的).{0,5}(礼物|回忆|财富).{0,10}", "最珍贵的礼物"),
        ]

    def _hit_cliche_pattern(self, sentence: str) -> bool:
        for pattern, _ in self.CLICHE_PATTERNS:
            if re.search(pattern, sentence):
                return True
        return False

    def _get_clean_length(self, sentence: str) -> int:
        clean = re.sub(r'[^\u4e00-\u9fa5]', '', sentence)
        return len(clean)

    def _similarity(self, a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        set_a = set(a)
        set_b = set(b)
        return len(set_a & set_b) / len(set_a | set_b)

    def _call_api(self, messages: list, temperature: float) -> tuple[bool, dict]:
        try:
            response = Generation.call(
                model=self.model,
                messages=messages,
                temperature=temperature,
                top_p=self.top_p,
                max_tokens=self.max_tokens,
                result_format='message',
            )
            if response.status_code == HTTPStatus.OK:
                content = response.output.choices[0].message.content.strip()
                content = re.sub(r'```json\s*', '', content, flags=re.IGNORECASE)
                content = re.sub(r'```\s*$', '', content, flags=re.IGNORECASE)
                match = re.search(r'\{.*\}', content, re.DOTALL)
                if match:
                    content = match.group()

                def extract_field(field_name):
                    pattern = rf'"{field_name}"\s*:\s*"((?:[^"\\]|\\.)*)"'
                    m = re.search(pattern, content)
                    if m:
                        return m.group(1).replace('\\"', '"').replace('\\n', '\n')
                    return ""

                very_short = extract_field("very_short")
                short = extract_field("short")
                medium = extract_field("medium")
                long_ = extract_field("long")
                very_long = extract_field("very_long")

                if not all([very_short, short, medium, long_, very_long]):
                    data = json.loads(content)
                    very_short = data.get("very_short", "")
                    short = data.get("short", "")
                    medium = data.get("medium", "")
                    long_ = data.get("long", "")
                    very_long = data.get("very_long", "")

                variants = {
                    "very_short": very_short,
                    "short": short,
                    "medium": medium,
                    "long": long_,
                    "very_long": very_long,
                }
                return True, variants
            else:
                return False, f"API Error: {response.code}"
        except Exception as e:
            return False, str(e)

    def _build_hint_prompt(self, atmosphere_hint: str) -> str:
        if not atmosphere_hint:
            return ""
        hints = {
            "dialogue_and_reaction": """
[Special Requirement]
Include a short line of dialogue and describe the other person's facial expression or body language.
""",
            "sensory_detail": """
[Special Requirement]
Include one sensory detail (sound, scent, or light). Weave it into the action.
""",
            "flashback_detail": """
[Special Requirement]
This is a flashback. Use "那时" or "记得" naturally, and include a sensory detail from memory.
""",
            "inner_monologue": """
[Special Requirement]
Reveal the narrator's inner thought subtly within the sentence. Do NOT use "心想：".
""",
            "exclamation": """
[Special Requirement]
Add a mild exclamation particle (e.g., "呢", "吧", "呀") at an appropriate place.
""",
            "seamless_divergent_detail": """
[Special Requirement]
Seamlessly weave the unique sensory clue into the action or observation of this sentence. The detail should feel like a natural part of the scene, not an inserted metaphor.
""",
            "vary_sentence_opening": """
[CRITICAL] Do NOT start this sentence with '我'. Use a different structure.
"""
        }
        # 如果传入的 hint 不在字典中，返回空字符串
        return hints.get(atmosphere_hint, "")

    def generate_sentence(
        self,
        core_fact: str,
        must_contain: list[str],
        sentiment: float,
        target_len_min: int,
        target_len_max: int,
        previous_sentences: list = None,
        atmosphere_hint: str = None,
        serendipity_prob: float = 0.05,
        paragraph_intent: str = ""
    ) -> str:
        # 处理 previous_sentences
        if previous_sentences is None:
            previous_sentences = []
        # 最近一句用于相似度比较
        last_sentence = previous_sentences[-1] if previous_sentences else ""
        # 取最近2句作为上下文显示
        context_sentences = previous_sentences[-2:] if len(previous_sentences) > 2 else previous_sentences

        # 动态调整 temperature
        if atmosphere_hint in ["dialogue_and_reaction", "flashback_detail"]:
            temperature = min(self.base_temperature + 0.3, 1.5)
        else:
            temperature = self.base_temperature

        # 构建 hint 提示
        hint_prompt = self._build_hint_prompt(atmosphere_hint)

        # 添加上下文
        context_block = ""
        if context_sentences:
            context_block = """
[Previous Context]
The following are the last {} sentence(s) of the article, written just before this one:
""".format(len(context_sentences))
            for i, s in enumerate(context_sentences, 1):
                context_block += f"{i}. {s}\n"
            context_block += "\nPlease continue naturally from this context, maintaining coherence in tone and action.\n"
        else:
            context_block = "[Previous Context]\nThis is the beginning of the article. Start naturally.\n\n"

        # 段落意图
        para_intent_block = ""
        if paragraph_intent:
            para_intent_block = f"\n[段落叙事意图]\n本段落的叙事目标是：{paragraph_intent}\n请确保本句的语调、节奏和细节与这个整体意图保持一致。"

        # 时间标记约束
        time_marker_block = "\n[Time Marker Usage]\n- Opening and body paragraphs: '记得' and '那时' are acceptable.\n- Climax and closing paragraphs: AVOID '记得' and '那时'. Emotional impact should feel immediate, not recalled."

        # 构建 user content
        user_content = f"""{context_block}
[Crafting Task]
Core fact: {core_fact}
Mandatory keywords: {', '.join(must_contain)}
Sentiment: {sentiment} (Range: -1.0 = highly negative, 1.0 = highly positive)
Previous sentence (for reference): "{last_sentence}"
{hint_prompt}
{para_intent_block}
{time_marker_block}

Generate FIVE versions (very_short, short, medium, long, very_long) as specified.
"""

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_content},
        ]

        max_attempts = 2
        for attempt in range(max_attempts):
            success, result = self._call_api(messages, temperature)
            if not success:
                print(f"[Craftsman] Attempt {attempt+1} failed: {result}")
                time.sleep(1)
                continue

            variants = result
            required_keys = ["very_short", "short", "medium", "long", "very_long"]
            if not all(k in variants and variants[k] for k in required_keys):
                print(f"[Craftsman] Incomplete variants, retrying...")
                continue

            lengths = {k: self._get_clean_length(variants[k]) for k in required_keys}
            target_mid = (target_len_min + target_len_max) / 2

            sorted_keys = sorted(required_keys, key=lambda k: abs(lengths[k] - target_mid))
            best_key = sorted_keys[0]
            best_sentence = variants[best_key]
            best_len = lengths[best_key]

            # 长度偏离检查
            if best_len < target_len_min * 0.5 or best_len > target_len_max * 1.8:
                if attempt < max_attempts - 1:
                    print(f"[Craftsman] Best length {best_len} far from target, retrying...")
                    continue

            # 相似度去重（与上一句比较）
            if last_sentence and self._similarity(best_sentence, last_sentence) > 0.45:
                found_alternative = False
                for next_key in sorted_keys[1:]:
                    if self._similarity(variants[next_key], last_sentence) <= 0.45:
                        best_sentence = variants[next_key]
                        found_alternative = True
                        break
                if not found_alternative and attempt < max_attempts - 1:
                    print(f"[Craftsman] All candidates too similar, retrying...")
                    continue

            # 陈词模式检查
            if self._hit_cliche_pattern(best_sentence):
                for next_key in sorted_keys[1:]:
                    if not self._hit_cliche_pattern(variants[next_key]):
                        best_sentence = variants[next_key]
                        break

            # 偶然性扰动
            if random.random() < serendipity_prob:
                other_keys = [k for k in required_keys if k != best_key]
                if other_keys:
                    best_sentence = variants[random.choice(other_keys)]

            return best_sentence

        # 重试耗尽，返回安全默认句
        return f"我{core_fact}。"