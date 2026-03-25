import csv
import requests
import feedparser
import os
from datetime import datetime

# 配置信息源（已帮你配置好重点关注的领域）
SOURCES = [
    # arXiv 论文
    {"url": "http://export.arxiv.org/rss/cs.AI", "name": "arXiv AI论文", "type": "论文"},
    {"url": "http://export.arxiv.org/rss/cs.CL", "name": "arXiv 计算语言学", "type": "论文"},
    {"url": "http://export.arxiv.org/rss/cs.LG", "name": "arXiv 机器学习", "type": "论文"},
    
    # Hugging Face 热门论文
    {"url": "https://huggingface.co/papers.rss", "name": "HuggingFace论文", "type": "论文"},
    
    # GitHub Trending AI
    {"url": "https://github.com/trending/ai", "name": "GitHub AI热门", "type": "开源项目"},
]

# 公众号RSS（通过 RSSHub 免费获取）
WECHAT_SOURCES = [
    {"url": "https://rsshub.app/wechat/weixin/jizhi", "name": "机器之心", "type": "综合资讯"},
    {"url": "https://rsshub.app/wechat/weixin/qbitai", "name": "量子位", "type": "综合资讯"},
    {"url": "https://rsshub.app/wechat/weixin/AI_era", "name": "新智元", "type": "综合资讯"},
]

# 重点领域关键词（用于标记重要性）
IMPORTANT_WORDS = ["开源", "发布", "上线", "融资", "突破", "开源模型", "SOTA", "新模型", "release", "launch", "open source"]

# 分类关键词
CATEGORY_WORDS = {
    "TTS": ["tts", "语音合成", "text-to-speech", "fish", "elevenlabs", "端到端", "语音交互"],
    "ASR": ["asr", "语音识别", "whisper", "speech recognition"],
    "音视频生成": ["video generation", "文生视频","图生视频", "参考生视频","seedance", "sora", "runway", "pika", "vidu", "可灵", "skyreels", "数字人"],
    "论文": ["paper", "arxiv", "论文"],
    "数据集": ["dataset", "数据集", "benchmark"],
    "大模型": ["llm", "大模型", "gpt", "claude", "llama", "gemini"],
    "自动化评测": ["benchmark", "leaderboard", "评测", "eval", "arena"],
}

def get_category(title, summary):
    text = (title + " " + summary).lower()
    for cat, words in CATEGORY_WORDS.items():
        for w in words:
            if w in text:
                return cat
    return "其他"

def is_important(title, summary):
    text = (title + " " + summary).lower()
    for w in IMPORTANT_WORDS:
        if w in text:
            return "是"
    return "否"

def get_company(title, summary):
    companies = ["OpenAI", "Google", "Meta", "微软", "字节跳动", "阿里", "腾讯", "百度", "科大讯飞", "Fish Audio", "Hugging Face", "ElevenLabs"]
    text = (title + " " + summary).lower()
    for c in companies:
        if c.lower() in text:
            return c
    return "其他"

def fetch_rss(url):
    try:
        feed = feedparser.parse(url)
        items = []
        for entry in feed.entries[:15]:
            items.append({
                "title": entry.title,
                "link": entry.link,
                "summary": entry.summary[:200] if hasattr(entry, 'summary') else "",
                "published": datetime.now().strftime("%Y-%m-%d")
            })
        return items
    except:
        return []

print(f"🤖 AI资讯收集器启动 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*50)

all_news = []

# 抓取学术和开源源
for src in SOURCES:
    print(f"正在获取: {src['name']}...")
    items = fetch_rss(src["url"])
    for item in items:
        all_news.append({
            "时间": datetime.now().strftime("%Y-%m-%d"),
            "公司": get_company(item["title"], item["summary"]),
            "资讯标题": item["title"],
            "重点内容": item["summary"],
            "类型": get_category(item["title"], item["summary"]),
            "是否重要": is_important(item["title"], item["summary"]),
            "信息链接": item["link"]
        })
    print(f"  ✓ 获取 {len(items)} 条")

# 抓取公众号
for src in WECHAT_SOURCES:
    print(f"正在获取公众号: {src['name']}...")
    items = fetch_rss(src["url"])
    for item in items:
        all_news.append({
            "时间": datetime.now().strftime("%Y-%m-%d"),
            "公司": src["name"],
            "资讯标题": item["title"],
            "重点内容": item["summary"],
            "类型": get_category(item["title"], item["summary"]),
            "是否重要": is_important(item["title"], item["summary"]),
            "信息链接": item["link"]
        })
    print(f"  ✓ 获取 {len(items)} 条")

# 去重（去掉重复标题）
seen = set()
unique_news = []
for item in all_news:
    if item["资讯标题"] not in seen:
        seen.add(item["资讯标题"])
        unique_news.append(item)

# 保存到CSV
filename = f"ai_news_{datetime.now().strftime('%Y%m')}.csv"
file_exists = os.path.isfile(filename)

with open(filename, 'a', newline='', encoding='utf-8-sig') as f:
    writer = csv.writer(f)
    if not file_exists:
        writer.writerow(["时间", "公司", "资讯标题", "重点内容", "类型", "是否重要", "信息链接"])
    
    for item in unique_news:
        writer.writerow([
            item["时间"],
            item["公司"],
            item["资讯标题"],
            item["重点内容"][:150],
            item["类型"],
            item["是否重要"],
            item["信息链接"]
        ])

print("="*50)
print(f"✅ 完成！共收集 {len(unique_news)} 条资讯")
print(f"📊 已保存到: {filename}")
print("")
print("重要资讯汇总:")
for item in unique_news:
    if item["是否重要"] == "是":
        print(f"  🔥 [{item['类型']}] {item['资讯标题'][:60]}")
