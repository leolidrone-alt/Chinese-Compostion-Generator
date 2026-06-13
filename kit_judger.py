import json
import requests
from typing import Tuple, Optional

def ask_if_human(article: str, api_key: str, model: str = "qwen-max") -> Tuple[int, str]:
    """让AI判断文章是否像人写的。返回 (1-5分, 理由)"""
    prompt = f"""请像一个中学语文老师一样，凭直觉判断下面这篇文章是否像真人写的。

评分标准：
5分 - 完全像人写的，有细节、有情感、不套话
4分 - 比较像人，个别地方稍显生硬
3分 - 有明显的AI痕迹，但还能读
2分 - 套话多、细节空泛
1分 - 典型AI生成，毫无人味

文章：
{article[:1500]}

请返回JSON：{{"score": 5, "reason": "一句话理由"}}"""

    try:
        resp = requests.post(
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 100
            },
            timeout=30
        )
        resp.raise_for_status()
        data = resp.json()["choices"][0]["message"]["content"]

        # 尝试从返回内容中提取JSON
        import re
        json_match = re.search(r'\{.*\}', data, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            return result.get("score", 3), result.get("reason", "AI判断完成")
        else:
            return 3, "AI返回格式异常，默认3分"

    except Exception as e:
        return 3, f"评估失败: {e}"