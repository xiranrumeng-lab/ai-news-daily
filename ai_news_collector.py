import csv
import requests
import feedparser
import time
from datetime import datetime

# ========== 配置 ==========
ENABLE_TRANSLATION = True

# ========== 信息源（重新排序：资讯优先，论文在后）==========
SOURCES = [
    # 1. 科技媒体（资讯类，优先获取）
    {"url": "https://techcrunch.com/category/artificial-intelligence/feed/", "name": "TechCrunch AI", "type": "科技资讯"},
    {"url": "https://venturebeat.com/category/ai/feed/", "name": "VentureBeat AI", "type": "科技资讯"},
    {"url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "name": "The Verge AI", "type": "科技资讯"},
    
    # 2. 官方博客（产品发布类）
    {"url": "https://openai.com/blog/rss", "name": "OpenAI博客", "type": "官方资讯"},
    {"url": "https://ai.googleblog.com/feeds/posts/default", "name": "Google AI博客", "type": "官方资讯"},
    {"url": "https://huggingface.co/blog/feed.xml", "name": "HuggingFace博客", "type": "官方资讯"},
    
    # 3. 中文媒体（官方RSS，如果失效会跳过）
    {"url": "https://www.jiqizhixin.com/rss", "name": "机器之心", "type": "中文资讯"},
    {"url": "https://www.qbitai.com/feed", "name": "量子位", "type": "中文资讯"},
    {"url": "https://www.geekpark.net/rss", "name": "极客公园", "type": "中文资讯"},
    
    # 4. 论文源（限制数量，只取最新5条）
    {"url": "http://export.arxiv.org/rss/cs.AI", "name": "arXiv AI论文", "type": "论文", "limit": 5},
    {"url": "http://export.arxiv.org/rss/cs.CL", "name": "arXiv 计算语言学", "type": "论文", "limit": 5},
    {"url": "http://export.arxiv.org/rss/cs.LG", "name": "arXiv 机器学习", "type": "论文", "limit": 5},
    {"url": "https://huggingface.co/papers.rss", "name": "HuggingFace论文", "type": "论文", "limit": 5},
]

# ========== 重要关键词 ==========
IMPORTANT_KEYWORDS = {
    "🚀 产品发布": ["发布", "上线", "launch", "release", "正式版", "首发"],
    "💰 融资并购": ["融资", "收购", "投资", "funding", "估值"],
    "🔥 技术突破": ["突破", "超越", "SOTA", "首个", "首次", "最强"],
    "📦 开源发布": ["开源", "open source"],
}

# 分类关键词
CATEGORY_WORDS = {
    "TTS": ["tts", "语音合成", "text-to-speech"],
    "ASR": ["asr", "语音识别", "whisper"],
    "音视频生成": ["video generation", "文生视频", "seedance", "sora", "vidu", "可灵"],
    "大模型": ["llm", "大模型", "gpt", "claude", "llama", "gemini"],
    "产品发布": ["发布", "上线", "launch"],
    "融资": ["融资", "收购", "投资"],
    "论文": ["paper", "arxiv"],
}

# ========== 翻译函数 ==========
def is_english(text):
    if not text:
        return False
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    total_chars = len(text)
    if total_chars == 0:
        return False
    return (chinese_chars / total_chars) < 0.1

def translate_text(text, max_length=500):
    if not ENABLE_TRANSLATION or not text:
        return text
    if not is_english(text):
        return text
    
    try:
        url = "https://api.mymemory.translated.net/get"
        params = {"q": text[:max_length], "langpair": "en|zh-CN"}
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        if data.get("responseData", {}).get("translatedText"):
            return data["responseData"]["translatedText"]
    except:
        pass
    return text

def get_category(title, summary):
    text = (title + " " + summary).lower()
    for cat, words in CATEGORY_WORDS.items():
        for w in words:
            if w.lower() in text:
                return cat
    return "其他"

def is_important(title, summary):
    text = (title + " " + summary).lower()
    for category, keywords in IMPORTANT_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text:
                return "是"
    return "否"

def get_company(title, summary):
    companies = ["OpenAI", "Google", "Meta", "微软", "字节跳动", "阿里", "腾讯", "百度",
                 "科大讯飞", "Fish Audio", "Hugging Face", "ElevenLabs", "快手", "Vidu"]
    text = (title + " " + summary).lower()
    for c in companies:
        if c.lower() in text:
            return c
    return "其他"

def fetch_rss(url, limit=15):
    try:
        feed = feedparser.parse(url)
        items = []
        for entry in feed.entries[:limit]:
            items.append({
                "title": entry.title,
                "link": entry.link,
                "summary": entry.summary[:300] if hasattr(entry, 'summary') else "",
            })
        return items
    except Exception as e:
        print(f"  获取失败: {e}")
        return []

# ========== 主程序 ==========
print(f"🤖 AI资讯收集器启动 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*50)

all_news = []
stats = {"资讯": 0, "论文": 0, "其他": 0}

for src in SOURCES:
    limit = src.get("limit", 15)
    print(f"正在获取: {src['name']}...")
    items = fetch_rss(src["url"], limit)
    
    for item in items:
        title_cn = translate_text(item["title"])
        summary_cn = translate_text(item["summary"])
        
        news_type = src["type"]
        if news_type == "论文":
            stats["论文"] += 1
        elif news_type in ["科技资讯", "官方资讯", "中文资讯"]:
            stats["资讯"] += 1
        else:
            stats["其他"] += 1
        
        all_news.append({
            "时间": datetime.now().strftime("%Y-%m-%d"),
            "公司": get_company(item["title"], item["summary"]),
            "资讯标题": title_cn,
            "重点内容": summary_cn[:150],
            "类型": get_category(item["title"], item["summary"]),
            "是否重要": is_important(item["title"], item["summary"]),
            "信息链接": item["link"],
            "原标题": item["title"]
        })
    print(f"  ✓ 获取 {len(items)} 条")
    time.sleep(0.5)

# 去重
seen = set()
unique_news = []
for item in all_news:
    if item["原标题"] not in seen:
        seen.add(item["原标题"])
        unique_news.append(item)

# 排序
unique_news.sort(key=lambda x: 0 if x["是否重要"] == "是" else 1)

# 保存
filename = "ai_news_latest.csv"
with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.writer(f)
    writer.writerow(["时间", "公司", "资讯标题", "重点内容", "类型", "是否重要", "信息链接"])
    for item in unique_news:
        writer.writerow([
            item["时间"], item["公司"], item["资讯标题"],
            item["重点内容"], item["类型"], item["是否重要"], item["信息链接"]
        ])

print("="*50)
print(f"✅ 完成！共收集 {len(unique_news)} 条")
print(f"📊 来源统计：资讯 {stats['资讯']} 条 | 论文 {stats['论文']} 条 | 其他 {stats['其他']} 条")
print(f"📊 已保存到: {filename}")

# 分类统计
print("\n📋 今日分类统计：")
cat_count = {}
for item in unique_news:
    cat = item["类型"]
    cat_count[cat] = cat_count.get(cat, 0) + 1
for cat, cnt in sorted(cat_count.items(), key=lambda x: x[1], reverse=True):
    print(f"  {cat}: {cnt}条")

# 重要资讯预览
print("\n" + "="*50)
print("🔥 今日重要资讯：")
print("="*50)
important = [n for n in unique_news if n["是否重要"] == "是"]
for i, item in enumerate(important[:10], 1):
    print(f"\n{i}. 【{item['类型']}】{item['资讯标题']}")
    print(f"   📍 公司：{item['公司']}")
    print(f"   📝 摘要：{item['重点内容'][:100]}...")
    print(f"   🔗 链接：{item['信息链接']}")
