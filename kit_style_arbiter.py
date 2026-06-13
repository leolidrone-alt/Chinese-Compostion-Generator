
class StyleArbiter:
    def __init__(self):
        # 中考信号词
        self.junior_signals = [
            "追梦路上", "这才是该有的样子", "我的青春", "成长中的一件事",
            "以……为题", "写一篇记叙文", "真情实感", "不少于600字",
            "中考", "初中", "初三"
        ]

        # 高考信号词
        self.senior_signals = [
            "材料作文", "自拟题目", "文体不限", "不少于800字", "议论文",
            "谈谈你的看法", "结合材料", "感悟", "思考",
            "高考", "高中", "高三"
        ]

        # 散文/随笔信号词
        self.prose_signals = [
            "背影", "味道", "声音", "那个夏天", "小时候", "记得",
            "想念", "温暖", "雨", "风", "月光", "忽然", "感觉",
            "写一篇散文", "随笔", "随写", "故事"
        ]

        # 讽刺/批判信号词
        self.satire_signals = [
            "讽刺", "贪婪", "小利", "精明", "算计", "短视"
        ]

        # 小说信号词
        self.novel_signals = [
            "小说", "虚构", "人物", "情节", "冲突", "悬念",
            "写一个故事", "编一个故事", "想象", "假如", "如果",
            "主人公", "主角", "反派", "世界观", "设定"
        ]

    def analyze(self, user_input: str) -> str:
        """
        根据用户输入自动判断文体。

        返回值：
            "exam_junior" - 中考作文
            "exam_senior" - 高考作文
            "prose"       - 散文/随笔
            "satire"      - 讽刺文学
            "novel"       - 小说
            "free"        - 自由创作（默认）
        """
        text = user_input.strip()

        # 空输入 → 自由创作
        if not text:
            return "free"

        # 1. 考试信号词检测
        junior_count = sum(1 for s in self.junior_signals if s in text)
        senior_count = sum(1 for s in self.senior_signals if s in text)

        if junior_count > 0:
            return "exam_junior"
        if senior_count > 0:
            return "exam_senior"

        # 2. 字数限制信号
        if "600字" in text or "700字" in text:
            return "exam_junior"
        if "800字" in text or "不少于" in text:
            return "exam_senior"

        # 3. 议论文/记叙文等文体指令
        if "议论文" in text or "谈谈你的看法" in text:
            return "exam_senior"
        if "记叙文" in text:
            return "exam_junior"

        # 4. 小说信号（优先级高于散文，因为小说可能包含散文信号词）
        novel_count = sum(1 for s in self.novel_signals if s in text)
        if novel_count >= 2:
            return "novel"

        # 5. 讽刺文学信号
        satire_count = sum(1 for s in self.satire_signals if s in text)
        if satire_count >= 1:
            return "satire"

        # 6. 散文/随笔信号
        prose_count = sum(1 for s in self.prose_signals if s in text)
        if prose_count >= 1:
            return "prose"

        # 7. 输入长度判断
        if len(text) <= 15:
            return "free"

        # 8. 默认 → 散文模式
        return "prose"