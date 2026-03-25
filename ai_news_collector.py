import csv
import requests
import feedparser
import time
from datetime import datetime

# ========== 配置 ==========
ENABLE_TRANSLATION = True

# ========== 所有已验证可用的RSS源 ==========
SOURCES = [
    # ----- 中文科技媒体（已验证可用）-----
    {"url": "https://www.ithome.com/rss/", "name": "IT之家", "type": "中文资讯", "limit": 10},
    {"url": "https://36kr.com/feed", "name": "36氪", "type": "中文资讯", "limit": 10},
    {"url": "https://www.infoq.cn/feed", "name": "InfoQ", "type": "中文资讯", "limit": 8},
    {"url": "https://www.huxiu.com/rss/0.xml", "name": "虎嗅", "type": "中文资讯", "limit": 8},
    {"url": "https://techcrunch.cn/feed/", "name": "TechCrunch中文", "type": "中文资讯", "limit": 8},
    
    # ----- 官方博客（英文，会自动翻译）-----
    {"url": "https://openai.com/blog/rss", "name": "OpenAI博客", "type": "官方资讯"},
    {"url": "https://ai.googleblog.com/feeds/posts/default", "name": "Google AI博客", "type": "官方资讯"},
    {"url": "https://deepmind.com/blog/rss", "name": "DeepMind博客", "type": "官方资讯"},
    {"url": "https://huggingface.co/blog/feed.xml", "name": "HuggingFace博客", "type": "官方资讯"},
    
    # ----- 国际科技媒体（英文，会自动翻译）-----
    {"url": "https://techcrunch.com/category/artificial-intelligence/feed/", "name": "TechCrunch AI", "type": "科技资讯"},
    {"url": "https://venturebeat.com/category/ai/feed/", "name": "VentureBeat AI", "type": "科技资讯"},
    {"url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "name": "The Verge AI", "type": "科技资讯"},
    
    # ----- 论文源（每个限制5条，避免太多）-----
    {"url": "http://export.arxiv.org/rss/cs.AI", "name": "arXiv AI论文", "type": "论文", "limit": 5},
    {"url": "http://export.arxiv.org/rss/cs.CL", "name": "arXiv 计算语言学", "type": "论文", "limit": 5},
    {"url": "http://export.arxiv.org/rss/cs.LG", "name": "arXiv 机器学习", "type": "论文", "limit": 5},
    {"url": "http://export.arxiv.org/rss/cs.SD", "name": "arXiv 声音处理", "type": "论文", "limit": 5},
    {"url": "http://export.arxiv.org/rss/eess.AS", "name": "arXiv 音频语音处理", "type": "论文", "limit": 5},
    {"url": "https://huggingface.co/papers.rss", "name": "HuggingFace论文", "type": "论文", "limit": 5},
]

# ========== 分类关键词 ==========
CATEGORY_WORDS = {
    "TTS": ["tts", "语音合成", "text-to-speech", "fish", "elevenlabs", "cosyvoice"],
    "ASR": ["asr", "语音识别", "whisper", "speech recognition"],
    "音视频生成": ["video generation", "文生视频", "seedance", "sora", "vidu", "可灵", "图生视频"],
    "大模型": ["llm", "大模型", "gpt", "claude", "llama", "gemini", "deepseek", "千问", "混元"],
    "产品发布": ["发布", "上线", "launch", "release", "正式版"],
    "融资并购": ["融资", "收购", "funding", "acquisition", "投资"],
    "开源": ["开源", "open source"],
    "论文": ["paper", "arxiv", "论文"],
}

# ========== 重要关键词 ==========
IMPORTANT_KEYWORDS = [
    "开源", "发布", "上线", "融资", "收购", "投资", "突破", 
    "SOTA", "launch", "release", "funding", "acquisition",
    "首个", "首次", "最强", "超越", "重磅"
]

# ========== 公司关键词 ==========
COMPANIES = [
    "OpenAI", "Google", "Meta", "Microsoft", "Anthropic", "DeepMind",
    "字节跳动", "阿里巴巴", "腾讯", "百度", "华为", "科大讯飞",
    "Fish Audio", "Hugging Face", "ElevenLabs", "快手", "可灵", "Vidu",
    "智谱", "百川", "月之暗面", "Minimax", "零一万物"
]

# ========== 辅助函数 ==========
def is_english(text):
    """判断是否为英文（中文字符占比<10%）"""
    if not text:
        return False
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    return len(text) > 0 and (chinese_chars / len(text)) < 0.1

def translate_text(text, max_length=500):
    """翻译英文为中文"""
    if not ENABLE_TRANSLATION or not text or not is_english(text):
        return text
    try:
        url = "https://api.mymemory.translated.net/get"
        params = {"q": text[:max_length], "langpair": "en|zh-CN"}
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        if data.get("responseData", {}).get("translatedText"):
            return data["responseData"]["translatedText"]
    except:
        pass
    return text

def get_category(title, summary):
    """判断资讯分类"""
    text = (title + " " + summary).lower()
    for cat, words in CATEGORY_WORDS.items():
        for w in words:
            if w.lower() in text:
                return cat
    return "其他"

def is_important(title, summary):
    """判断是否重要"""
    text = (title + " " + summary).lower()
    for kw in IMPORTANT_KEYWORDS:
        if kw.lower() in text:
            return "是"
    return "否"

def get_company(title, summary):
    """提取公司名称"""
    text = (title + " " + summary).lower()
    for c in COMPANIES:
        if c.lower() in text:
            return c
    return "其他"

def fetch_rss(url, limit=15):
    """获取RSS内容"""
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
        print(f"  ❌ 失败")
        return []

# ========== 主程序 ==========
print("="*60)
print(f"🤖 AI资讯收集器 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*60)

all_news = []
stats = {"中文资讯": 0, "官方资讯": 0, "科技资讯": 0, "论文": 0}

for src in SOURCES:
    limit = src.get("limit", 12)
    print(f"📡 {src['name']}...", end=" ")
    items = fetch_rss(src["url"], limit)
    print(f"{len(items)}条")
    
    # 统计
    src_type = src["type"]
    if src_type in stats:
        stats[src_type] += len(items)
    
    for item in items:
        # 中文源直接使用原文，英文源翻译
        if src_type == "中文资讯":
            title_cn = item["title"]
            summary_cn = item["summary"][:150]
        else:
            title_cn = translate_text(item["title"])
            summary_cn = translate_text(item["summary"])[:150]
        
        all_news.append({
            "时间": datetime.now().strftime("%Y-%m-%d"),
            "公司": get_company(item["title"], item["summary"]),
            "资讯标题": title_cn,
            "重点内容": summary_cn,
            "类型": get_category(item["title"], item["summary"]),
            "是否重要": is_important(item["title"], item["summary"]),
            "信息链接": item["link"],
            "原标题": item["title"]  # 保留原文用于去重
        })
    time.sleep(0.3)

# 去重（按标题）
seen = set()
unique_news = []
for item in all_news:
    key = item["原标题"][:50]  # 用前50字符去重
    if key not in seen:
        seen.add(key)
        unique_news.append(item)

# 排序：重要资讯在前
unique_news.sort(key=lambda x: 0 if x["是否重要"] == "是" else 1)

# 保存CSV
filename = "ai_news_latest.csv"
with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.writer(f)
    writer.writerow(["时间", "公司", "资讯标题", "重点内容", "类型", "是否重要", "信息链接"])
    for item in unique_news:
        writer.writerow([
            item["时间"], item["公司"], item["资讯标题"],
            item["重点内容"], item["类型"], item["是否重要"], item["信息链接"]
        ])

# 输出统计
print("="*60)
print(f"✅ 收集完成！共 {len(unique_news)} 条资讯")
print(f"📊 来源分布：中文资讯 {stats['中文资讯']} 条 | 官方资讯 {stats['官方资讯']} 条 | 科技资讯 {stats['科技资讯']} 条 | 论文 {stats['论文']} 条")
print(f"📁 已保存到: {filename}")
print("="*60)

# 重要资讯预览
print("\n🔥 今日重要资讯：")
important_items = [n for n in unique_news if n["是否重要"] == "是"]
if important_items:
    for i, item in enumerate(important_items[:8], 1):
        print(f"\n{i}. 【{item['类型']}】{item['资讯标题']}")
        print(f"   📍 公司：{item['公司']}")
        print(f"   📝 {item['重点内容'][:80]}..." if len(item['重点内容']) > 80 else f"   📝 {item['重点内容']}")
        print(f"   🔗 {item['信息链接']}")
else:
    print("   今日暂无重要资讯")

# 分类统计
print("\n📋 今日分类统计：")
cat_count = {}
for item in unique_news:
    cat = item["类型"]
    cat_count[cat] = cat_count.get(cat, 0) + 1
for cat, cnt in sorted(cat_count.items(), key=lambda x: x[1], reverse=True):
    print(f"   {cat}: {cnt}条")
