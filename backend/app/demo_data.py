from datetime import date

from app.schemas import Evidence, Opportunity

_BASE = {
    "problem": "目标用户需要在关键任务前获得及时、可靠且个性化的支持。",
    "targetUser": "有明确任务目标、愿意尝试 AI 工作流的个人用户。",
    "jobToBeDone": "在高压场景中更快完成准备并建立信心。",
    "painPoints": ["准备成本高", "反馈不够具体", "现有工具不连续"],
    "workarounds": ["模板搜索", "人工咨询", "通用聊天机器人"],
    "aiAngle": "用多轮、情境化的 AI 工作流提供即时反馈。",
    "possibleMvp": "一个聚焦核心场景的 Web MVP：输入背景，生成任务并给出可执行反馈。",
}
_ITEMS = [
    ("AI 英文面试模拟", "China · Shanghai", "Career", "外企候选人希望进行更真实、可追问的英文面试练习。", 88, 72, "Surging", "外企岗位回暖，用户主动寻找按简历追问的模拟工具。"),
    ("AI 高校答辩模拟", "China · Beijing", "Education", "研究生需要在答辩前反复模拟评委问题。", 82, 68, "Rising", "毕业季临近，答辩焦虑相关讨论持续增多。"),
    ("PPT 限时讲稿生成", "China · Guangdong", "Productivity", "职场人士需要将 PPT 转成特定时长、自然的讲稿。", 79, 76, "Rising", "汇报周期密集，用户不只要提纲而是要能直接演讲的内容。"),
    ("AI 小学英语陪练", "China · Shanghai", "Education", "家长希望孩子每天获得低压力的英语口语练习。", 84, 70, "Surging", "家庭对陪练频率和真人外教成本的讨论升温。"),
    ("AI 租房合同检查", "Singapore", "Legal", "租客担心在签约前忽略押金、维修和提前解约风险。", 81, 64, "Rising", "租房换季和跨境居住让合同审阅需求更明显。"),
    ("AI 科研审稿助手", "USA", "Research", "研究者希望在投稿前发现论证、结构和表达问题。", 86, 75, "Surging", "投稿周期中，研究者正在寻找比语法检查更深入的反馈。"),
    ("AI 视频自动配音", "Japan", "Creator", "小团队希望低成本为短视频制作自然的多语言配音。", 83, 69, "Rising", "跨语言内容分发增加，对保留情绪和节奏的配音提出需求。"),
    ("AI 跨境商品图生成", "China · Guangdong", "Commerce", "跨境卖家需要快速生成符合区域审美的商品展示图。", 80, 66, "Rising", "卖家尝试更多市场，图片本地化成为上架瓶颈。"),
    ("AI 老年家庭助手", "China · Beijing", "Family", "异地子女希望更轻松地协助父母处理数字事务。", 77, 58, "Stable", "家庭照护讨论持续，但真实使用场景仍需验证。"),
    ("AI 简历面试一体助手", "USA", "Career", "求职者想让简历优化、岗位匹配和面试准备形成闭环。", 85, 73, "Surging", "求职周期拉长，用户表达了对多工具切换的疲惫。"),
]

DEMO_OPPORTUNITIES = [
    Opportunity(
        id=f"demo-{index}", title=title, region=region, category=category,
        oneLineSummary=summary, marketScore=score, confidenceScore=confidence,
        momentum=momentum, whyNow=why_now, **_BASE,
        evidence=[Evidence(query=title, excerpt=f"我正在寻找能解决「{summary}」的工具，现有方式太耗时间。", platform="Manual demo" if index % 2 == 0 else "Zhihu", observedAt=date(2026, 9, 2), region=region, sourceUrl="https://example.com/demo-signal")],
    )
    for index, (title, region, category, summary, score, confidence, momentum, why_now) in enumerate(_ITEMS, start=1)
]
