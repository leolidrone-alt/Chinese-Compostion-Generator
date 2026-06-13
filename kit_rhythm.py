# kit_rhythm.py
import random
import re
import numpy as np
import requests


class RhythmKit:
    def __init__(
        self,
        target_mean: float = 27.3,
        target_std: float = 16.78,
        min_len: int = 4,
        max_len: int = 50,
        force_break_threshold: int = 150,
        rhythm_disrupt_prob: float = 0.08
    ):
        self.target_mean = target_mean
        self.target_std = target_std
        self.min_len = min_len
        self.max_len = max_len
        self.force_break_threshold = force_break_threshold
        self.rhythm_disrupt_prob = rhythm_disrupt_prob
        self.history = []          # 句长序列
        self.para_len = 0          # 当前段落累计字数
        self.total_words_generated = 0   # 全文已生成字数
        self.target_total_words = 800    # 目标总字数

    def set_target_total(self, target: int):
        """设定目标总字数，用于疲劳曲线计算"""
        self.target_total_words = max(target, 1)

        # kit_rhythm.py 的 get_target_range 方法签名增加 para_type 参数
    def get_target_range(self, para_type: str = "body", recent_sentiments: list = None) -> tuple[int, int]:

        # ... 原有的全部逻辑，计算出 base_min, base_max ...
        """
        根据已有句长序列、疲劳进度和最近的情感浓度，动态计算下一句的目标长度区间。

        Args:
            recent_sentiments: 最近几句的情感值 (可选)，用于留白检测
        """
        # 计算全文进度（0~1）
        progress = self.total_words_generated / max(self.target_total_words, 1)
        progress = min(progress, 1.0)

        # === 强制极短/极长句（保持原有的节奏波动）===
        if len(self.history) % 5 == 0 and len(self.history) > 0:
            base_min, base_max = 3, 8
        elif len(self.history) % 8 == 0 and len(self.history) > 0:
            base_min, base_max = 38, 52
        elif self.history and self.history[-1] > 40:
            base_min, base_max = 5, 12
        elif len(self.history) >= 2 and self.history[-1] > 35 and self.history[-2] > 35:
            base_min, base_max = 3, 8
        elif len(self.history) < 2:
            base_min, base_max = 15, 35
        else:
            r = random.random()
            if r < 0.4:
                base_min, base_max = 6, 14
            elif r < 0.7:
                base_min, base_max = 18, 30
            else:
                base_min, base_max = 32, 45

        # === 疲劳衰减：后30%篇幅句长缩减20% ===
        if progress > 0.7:
            shrink = 1.0 - (progress - 0.7) * 0.8
            base_min = max(3, int(base_min * shrink))
            base_max = max(6, int(base_max * shrink))

        # === 留白检测：最近3句情感浓度过高时，强制生成极短句 ===
        if recent_sentiments and len(recent_sentiments) >= 3:
            if all(abs(s) > 0.5 for s in recent_sentiments[-3:]):
                return (2, 6)

        # === 偶然性跳变：以一定概率生成完全不同的长度区间 ===
        if random.random() < self.rhythm_disrupt_prob:
            return (random.randint(3, 12), random.randint(25, 50))

        # === 段落感知节奏调整 ===
        if para_type == "opening":
            # 开场段：保持平稳，避免极端短句
            base_min = max(base_min, 8)
            base_max = min(base_max, 40)
        elif para_type in ("climax", "closing"):
            # 高潮/结尾段：增加极短句触发概率
            if random.random() < 0.3 and base_min > 5:
                base_min, base_max = 2, 6
            # 同时降低极长句概率
            if base_max > 40:
                base_max = 40

        # 疲劳衰减（原逻辑）
        if progress > 0.7:
            shrink = 1.0 - (progress - 0.7) * 0.8
            base_min = max(3, int(base_min * shrink))
            base_max = max(6, int(base_max * shrink))

        # 留白检测（原逻辑）
        if recent_sentiments and len(recent_sentiments) >= 3:
            if all(abs(s) > 0.5 for s in recent_sentiments[-3:]):
                return (2, 6)

        # 偶然性跳变（原逻辑）
        if random.random() < self.rhythm_disrupt_prob:
            return (random.randint(3, 12), random.randint(25, 50))

        return base_min, base_max

    def record(self, sentence: str):
        """记录一句已生成，更新句长历史、段落累计字数和全文累计字数"""
        clean = re.sub(r'[^\u4e00-\u9fa5]', '', sentence)
        length = len(clean)
        self.history.append(length)
        self.para_len += length
        self.total_words_generated += length

    def should_break_paragraph(self) -> bool:
        """判断当前段落是否需要强制分段"""
        return self.para_len >= self.force_break_threshold

    def reset_paragraph(self):
        """开始新段落时重置累计字数"""
        self.para_len = 0

    def get_final_std(self) -> float:
        """返回全文句长标准差"""
        if len(self.history) < 2:
            return 0.0
        return float(np.std(self.history))


class NarrativeArbiter:
    """叙事手法仲裁器：Random提议 + AI判断"""

    def __init__(self, api_key: str, model: str = "deepseek-chat"):
        self.api_key = api_key
        self.model = model
        self.endpoint = "https://api.deepseek.com/v1/chat/completions"

    def propose_technique(self) -> str:
        r = random.random()
        if r < 0.12:
            return "flashback"
        elif r < 0.25:
            return "interlude"
        else:
            return "linear"

    def is_suitable(
        self,
        technique: str,
        previous_sentences: list[str],
        core_fact: str,
        theme: str,
    ) -> bool:
        if technique == "linear":
            return True

        context_text = "\n".join(previous_sentences[-3:]) if previous_sentences else "（文章开头）"

        prompt = f"""
[Context]
Previous sentences:
{context_text}

Current planned core fact: {core_fact}
Article theme: {theme}

[Proposed Narrative Technique]
{technique}

[Judgment Criteria]
- Does inserting a {technique} here feel natural and not forced?
- Will it disrupt the emotional flow or confuse the reader?
- Can it be smoothly executed in a single sentence?

Answer ONLY "YES" or "NO".
"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 5
        }

        try:
            response = requests.post(self.endpoint, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            answer = result["choices"][0]["message"]["content"].strip().upper()
            return "YES" in answer
        except Exception as e:
            print(f"[NarrativeArbiter] AI judgment failed: {e}, defaulting to linear")
            return False