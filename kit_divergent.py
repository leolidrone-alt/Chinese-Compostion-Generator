# kit_divergent.py
import random

class DivergentKit:
    def __init__(self):
        self.idle_trigger_prob = 0.25   # 闲笔跳跃概率
        self.intrusion_prob = 0.15      # 意象闯入概率
        self.breath_prob = 0.30         # 段落间呼吸句概率

    def should_insert_idle(self) -> bool:
        return random.random() < self.idle_trigger_prob

    def should_intrude(self) -> bool:
        return random.random() < self.intrusion_prob

    def should_breathe(self, para_word_count: int, threshold: int = 100) -> bool:
        return random.random() < self.breath_prob and para_word_count > threshold