# kit_coherence.py
import re
from typing import List, Tuple, Optional

class CoherenceKit:
    """人称一致性与逻辑衔接校验器（增强版）"""

    def __init__(self, default_person: str = "我", resolve_pronouns_to_nouns: bool = False):
        """
        default_person: 全文默认使用的第一人称代词（备用）
        resolve_pronouns_to_nouns: 是否将所有第三人称代词（他/她）替换为具体人名（避免指代模糊）
        """
        self.default_person = default_person
        self.resolve_pronouns_to_nouns = resolve_pronouns_to_nouns
        self.first_person_set = {"我", "我们", "咱", "咱俩"}
        self.third_person_male = {"他", "他们"}
        self.third_person_female = {"她", "她们"}
        self.third_person_neutral = {"它", "它们"}
        self.all_third = self.third_person_male | self.third_person_female | self.third_person_neutral
        self.all_persons = self.first_person_set | self.all_third
        # 常见的主语缺失触发词
        self.subject_missing_pattern = re.compile(r'^(?:然后|接着|却|便|就|也|还|终于|忽然|突然|渐渐|悄悄|慢慢|匆匆)', re.UNICODE)
        self.pronoun_pattern = re.compile(r'(他|她|它|他们|她们|它们)')
        # 人物名词（用于指代消解）
        self.person_noun_pattern = re.compile(
            r'(?:[小老大]?[明伟华建国强]|阿\w|父亲|母亲|爷爷|奶奶|外公|外婆|祖父|祖母|儿子|女儿|孙子|孙女|老师|同学|朋友|邻居|王爷爷|李老师)'
        )

    def detect_primary_person(self, sentences: List[str]) -> str:
        """检测文章的主要人称（第一人称或第三人称），具体人名不干扰判断"""
        has_first = any(any(p in sent for p in self.first_person_set) for sent in sentences)
        if has_first:
            return "我"
        else:
            # 没有第一人称，默认为第三人称（用“他”代表）
            return "他"

    def extract_person_nouns(self, text: str) -> List[str]:
        """提取文本中出现的人物名词（人名、称谓），按出现顺序返回"""
        # 简单规则：匹配常见姓氏+名，或者称谓词
        # 实际可扩展
        found = re.findall(self.person_noun_pattern, text)
        # 去重保留顺序
        seen = set()
        ordered = []
        for n in found:
            if n not in seen:
                seen.add(n)
                ordered.append(n)
        return ordered

    def resolve_pronoun_to_noun(self, sentence: str, last_noun: str) -> str:
        """将句子中的‘他’‘她’替换为最近出现的人物名词"""
        if not last_noun:
            return sentence
        def repl(m):
            p = m.group(0)
            if p in {"他", "她"}:
                return last_noun
            elif p in {"他们", "她们"}:
                return last_noun + "们"
            return p
        return self.pronoun_pattern.sub(repl, sentence)

    def check_person_consistency(self, sentences: List[str], primary_person: str = None) -> Tuple[bool, List[int], List[str]]:
        """
        检测人称一致性（仅检测人称代词冲突，不替换具体人名）
        返回 (是否一致, 问题句子索引, 建议修改的句子列表)
        """
        if primary_person is None:
            primary_person = self.detect_primary_person(sentences)

        problematic = []
        suggestions = []
        for idx, sent in enumerate(sentences):
            if primary_person == "我":
                # 第一人称视角，不允许出现第三人称代词
                if any(p in sent for p in self.all_third):
                    problematic.append(idx)
                    new_sent = sent
                    for p in self.all_third:
                        new_sent = new_sent.replace(p, "我")
                    suggestions.append(new_sent)
            else:
                # 第三人称视角，不允许出现第一人称代词
                if any(p in sent for p in self.first_person_set):
                    problematic.append(idx)
                    new_sent = sent
                    for p in self.first_person_set:
                        new_sent = new_sent.replace(p, "他")
                    suggestions.append(new_sent)
        return len(problematic) == 0, problematic, suggestions

    def fix_subject_missing(self, sentence: str, previous_sentence: str = "", default_subject: str = None, context_nouns: List[str] = None) -> str:
        """
        检查句子是否缺少主语，并尝试从上一句或上下文名词中继承主语
        context_nouns: 已出现的人物名词列表（按顺序），用于查找合适的主语
        """
        if not sentence:
            return sentence
        # 如果句子已有主语（以名词、代词或称谓开头）
        if re.match(r'^[\u4e00-\u9fa5]{1,3}[，]', sentence):
            return sentence
        if sentence[0] in "我他她它你您咱" or (len(sentence) > 1 and sentence[0] in "大小阿" and sentence[1] in "明伟华"):  # 简单人名
            return sentence
        if self.subject_missing_pattern.match(sentence):
            subject = default_subject or self.default_person
            if previous_sentence:
                # 从上一句中提取主语
                prev_match = re.search(r'^([\u4e00-\u9fa5]+)', previous_sentence)
                if prev_match and prev_match.group(1) in self.all_persons:
                    subject = prev_match.group(1)
                elif "父亲" in previous_sentence:
                    subject = "父亲"
                elif "母亲" in previous_sentence:
                    subject = "母亲"
                elif "爷爷" in previous_sentence:
                    subject = "爷爷"
                elif "小明" in previous_sentence:
                    subject = "小明"
                elif context_nouns and len(context_nouns) > 0:
                    # 使用最近出现的人物名词
                    subject = context_nouns[-1]
                elif re.search(r'[他她]', previous_sentence):
                    match = re.search(r'(父亲|母亲|爷爷|奶奶|外公|外婆|祖父|祖母|他|她)', previous_sentence)
                    if match:
                        subject = match.group(1)
            return f"{subject}{sentence}"
        return sentence

    def full_correct(self, article: str, primary_person: str = None) -> str:
        """
        对整篇文章进行全套修正（人称一致性 + 指代消解 + 主语补全）
        """
        # 分句
        raw_sentences = article.split("。")
        sentences = [s.strip() for s in raw_sentences if s.strip()]
        if not sentences:
            return article

        # 1. 提取全文中出现的人物名词
        full_text = "。".join(sentences)
        person_nouns = self.extract_person_nouns(full_text)
        # 为每个句子记录当前已知的人物名词（按顺序累积）
        context_nouns = []

        # 2. 检测主要人称
        if primary_person is None:
            primary_person = self.detect_primary_person(sentences)
        if primary_person not in ["我", "他", "她", "它"]:
            primary_person = "我"

        # 3. 先处理人称一致性（代词冲突）
        _, _, suggestions = self.check_person_consistency(sentences, primary_person)
        for idx, new_sent in zip(range(len(sentences)), suggestions):
            sentences[idx] = new_sent

        # 4. 代词指代消解（如果启用，将“他/她”替换为具体人名）
        if self.resolve_pronouns_to_nouns:
            last_noun = None
            for i, sent in enumerate(sentences):
                # 更新最近出现的人物名词
                nouns_in_sent = re.findall(self.person_noun_pattern, sent)
                if nouns_in_sent:
                    last_noun = nouns_in_sent[-1]
                if last_noun:
                    sentences[i] = self.resolve_pronoun_to_noun(sent, last_noun)
        else:
            # 仅做基本的代词消解（不清除代词，但确保指代明确）
            # 这里简单处理：如果“他”出现且前文有人名，不修改；否则替换为第一个人名
            first_person_name = person_nouns[0] if person_nouns else None
            for i, sent in enumerate(sentences):
                if first_person_name and re.search(r'\b他\b', sent) and not re.search(r'(?:小明|阿发|父亲|母亲)', sent[:20]):
                    # 无前文指代的“他”，替换为第一人名称谓
                    sentences[i] = re.sub(r'\b他\b', first_person_name, sent)

        # 5. 修复缺失主语（逐句，并传递上下文名词列表）
        new_sentences = []
        for i, sent in enumerate(sentences):
            prev = new_sentences[-1] if new_sentences else ""
            # 累积已出现的人物名词
            if new_sentences:
                ctx = self.extract_person_nouns("。".join(new_sentences[-3:]))
                context_nouns = ctx if ctx else context_nouns
            new_sent = self.fix_subject_missing(sent, prev, default_subject=primary_person, context_nouns=context_nouns)
            new_sentences.append(new_sent)

        # 6. 重新拼接
        return "。".join(new_sentences) + "。"