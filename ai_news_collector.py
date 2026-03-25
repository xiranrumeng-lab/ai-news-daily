import csv
import requests
import feedparser
import time
import re
from datetime import datetime

# ========== 配置 ==========
ENABLE_TRANSLATION = True

# ========== AI关键词（用于筛选内容）==========
# 只有标题或摘要中包含以下任一关键词，才保留
AI_KEYWORDS = [
    # AI核心领域
    "ai", "人工智能", "machine learning", "机器学习", "deep learning", "深度学习",
    "llm", "大模型", "foundation model", "基础模型",
    "gpt", "claude", "llama", "gemini", "deepseek", "chatgpt",
    "tts", "语音合成", "text-to-speech", "asr", "语音识别", "whisper",
    "speech", "语音技术", "语音交互", "voice",
    # 视频生成
    "video generation", "文生视频", "seedance", "sora", "vidu", "可灵", "kling",
    "图生视频", "image to video", "runway", "pika", "视频生成",
    # 开源与工具
    "开源", "open source", "hugging face", "github",
    # 技术词汇
    "模型", "算法", "训练", "推理", "参数", "benchmark", "评测", "leaderboard",
    "transformer", "diffusion", "多模态", "multimodal",
    # 公司（当公司名出现时，大概率是AI相关）
    "openai", "google ai", "deepmind", "anthropic", "字节", "百度", "腾讯", "阿里", 
    "科大讯飞", "快手", "可灵", "智谱", "百川", "月之暗面", "minimax",
    "fish audio", "elevenlabs", "hugging face",
    # 论文
    "paper", "arxiv", "论文"
]

# ========== RSS源 ==========
SOURCES = [
    # 中文科技媒体
    {"url": "https://www.ithome.com/rss/", "name": "IT之家", "type": "中文资讯", "limit": 25},
    {"url": "https://36kr.com/feed", "name": "36氪", "type": "中文资讯", "limit": 25},
    {"url": "https://www.infoq.cn/feed", "name": "InfoQ", "type": "中文资讯", "limit": 20},
    
    # 官方博客
    {"url": "https://huggingface.co/blog/feed.xml", "name": "HuggingFace博客", "type": "官方资讯", "limit": 10},
    {"url": "https://techcrunch.com/category/artificial-intelligence/feed/", "name": "TechCrunch AI", "type": "科技资讯", "limit": 20},
    {"url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "name": "The Verge AI", "type": "科技资讯", "limit": 20},
    
    # 论文源
    {"url": "http://export.arxiv.org/rss/cs.AI", "name": "arXiv AI论文", "type": "论文", "limit": 10},
    {"url": "http://export.arxiv.org/rss/cs.CL", "name": "arXiv 计算语言学", "type": "论文", "limit": 10},
    {"url": "http://export.arxiv.org/rss/cs.LG", "name": "arXiv 机器学习", "type": "论文", "limit": 10},
    {"url": "http://export.arxiv.org/rss/cs.SD", "name": "arXiv 声音处理", "type": "论文", "limit": 10},
    {"url": "http://export.arxiv.org/rss/eess.AS", "name": "arXiv 音频语音处理", "type": "论文", "limit": 10},
]

# ========== 智能分类关键词 ==========
CATEGORY_MAP = {
    "语音技术": ["tts", "语音合成", "asr", "语音识别", "whisper", "text-to-speech", "speech", "语音交互", "语音技术", "fish audio", "elevenlabs"],
    "视频生成": ["video generation", "文生视频", "seedance", "sora", "vidu", "可灵", "kling", "图生视频", "runway", "pika", "视频生成"],
    "大模型": ["llm", "大模型", "gpt", "claude", "llama", "gemini", "deepseek", "foundation model", "chatgpt", "多模态"],
    "开源发布": ["开源", "open source", "代码开源", "模型开源", "hugging face"],
    "论文研究": ["paper", "arxiv", "论文", "技术报告", "research"],
    "产品发布": ["发布", "上线", "launch", "release", "正式版"],
    "融资并购": ["融资", "收购", "投资", "funding", "acquisition"],
    "技术突破": ["突破", "超越", "sota", "state of the art", "新纪录", "首个"],
    "评测榜单": ["benchmark", "leaderboard", "评测", "排行榜", "arena"],
    "公司动态": ["人事", "组织架构", "战略", "合作", "签约"],
}

# ========== 公司识别关键词 ==========
COMPANY_MAP = {
    "OpenAI": ["openai", "chatgpt", "gpt-4", "gpt-5", "sora"],
    "Google": ["google", "deepmind", "gemini", "bard"],
    "Meta": ["meta", "facebook", "llama"],
    "Microsoft": ["microsoft", "azure", "copilot"],
    "Anthropic": ["anthropic", "claude"],
    "字节跳动": ["字节", "字节跳动", "抖音", "豆包", "seedance"],
    "阿里巴巴": ["阿里", "阿里巴巴", "通义", "千问"],
    "腾讯": ["腾讯", "混元"],
    "百度": ["百度", "文心"],
    "科大讯飞": ["科大讯飞", "讯飞"],
    "快手": ["快手", "可灵", "kling"],
    "生数科技": ["生数", "vidu"],
    "智谱": ["智谱", "glm"],
    "百川": ["百川"],
    "月之暗面": ["月之暗面", "kimi"],
    "Minimax": ["minimax"],
    "零一万物": ["零一", "01.ai"],
    "Hugging Face": ["hugging face", "huggingface"],
    "ElevenLabs": ["elevenlabs"],
    "Fish Audio": ["fish audio", "fishaudio"],
}

# ========== 辅助函数 ==========
def contains_ai_keyword(title, summary):
    """判断是否包含AI关键词（只有包含才保留）"""
    text = (title + " " + summary).lower()
    for kw in AI_KEYWORDS:
        if kw.lower() in text:
            return True
    return False

def smart_category(title, summary):
    """智能分类"""
    text = (title + " " + summary).lower()
    for cat, keywords in CATEGORY_MAP.items():
        for kw in keywords:
            if kw.lower() in text:
                return cat
    return "AI相关"

def extract_company(title, summary):
    """识别公司名称"""
    text = (title + " " + summary).lower()
    for company, keywords in COMPANY_MAP.items():
        for kw in keywords:
            if kw.lower() in text:
                return company
    return "其他"

def clean_text(text, max_len=200):
    """清理文本，去除HTML标签和乱码"""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[&nbsp;]+', ' ', text)
    text = text.strip()
    if len(text) > max_len:
        text = text[:max_len] + "..."
    return text

def generate_summary(text, max_points=3):
    """生成要点列表（按序号）"""
    if not text:
        return ""
    text = clean_text(text, 300)
    sentences = re.split(r'[。！？；]', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
    points = sentences[:max_points]
    if points:
        result = ""
        for i, point in enumerate(points, 1):
            result += f"{i}. {point}。\n"
        return result.strip()
    return text[:150]

def is_english(text):
    if not text:
        return False
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    return len(text) > 0 and (chinese_chars / len(text)) < 0.1

def translate_text(text, max_length=400):
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

def fetch_rss(url, limit=15):
    try:
        feed = feedparser.parse(url)
        items = []
        for entry in feed.entries[:limit]:
            items.append({
                "title": entry.title,
                "link": entry.link,
                "summary": entry.summary[:500] if hasattr(entry, 'summary') else "",
            })
        return items
    except:
        return []

# ========== 主程序 ==========
print("="*60)
print(f"🤖 AI资讯收集器 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*60)

all_news = []
filtered_count = 0

for src in SOURCES:
    limit = src.get("limit", 15)
    print(f"📡 {src['name']}...", end=" ")
    items = fetch_rss(src["url"], limit)
    print(f"{len(items)}条", end="")
    
    src_items = 0
    for item in items:
        # 只保留包含AI关键词的内容
        if not contains_ai_keyword(item["title"], item["summary"]):
            filtered_count += 1
            continue
        
        src_items += 1
        
        # 翻译
        if src["type"] == "中文资讯":
            title_cn = item["title"]
            summary_cn = item["summary"]
        else:
            title_cn = translate_text(item["title"])
            summary_cn = translate_text(item["summary"])
        
        # 生成要点摘要
        key_points = generate_summary(summary_cn)
        
        all_news.append({
            "时间": datetime.now().strftime("%Y-%m-%d"),
            "公司": extract_company(item["title"], item["summary"]),
            "资讯标题": clean_text(title_cn, 100),
            "重点内容": key_points,
            "类型": smart_category(item["title"], item["summary"]),
            "是否重要": "是" if any(kw in (title_cn + summary_cn).lower() for kw in ["开源", "发布", "融资", "突破", "上线", "launch", "release"]) else "否",
            "信息链接": item["link"]
        })
    
    print(f" → AI相关 {src_items}条")
    time.sleep(0.3)

# 去重
seen = set()
unique_news = []
for item in all_news:
    if item["资讯标题"] not in seen:
        seen.add(item["资讯标题"])
        unique_news.append(item)

# 排序
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
print(f"✅ 收集完成！共 {len(unique_news)} 条AI相关资讯")
print(f"📊 已过滤 {filtered_count} 条（不含AI关键词）")
print(f"📁 已保存到: {filename}")
print("="*60)

# 分类统计
print("\n📋 今日分类统计：")
cat_count = {}
for item in unique_news:
    cat = item["类型"]
    cat_count[cat] = cat_count.get(cat, 0) + 1
for cat, cnt in sorted(cat_count.items(), key=lambda x: x[1], reverse=True):
    print(f"   {cat}: {cnt}条")

# 重要资讯预览
print("\n" + "="*60)
print("🔥 今日重要资讯：")
print("="*60)
important_items = [n for n in unique_news if n["是否重要"] == "是"]
if important_items:
    for i, item in enumerate(important_items[:10], 1):
        print(f"\n{i}. 【{item['类型']}】{item['资讯标题']}")
        print(f"   📍 公司：{item['公司']}")
        print(f"   📝 要点：")
        for line in item["重点内容"].split('\n'):
            if line.strip():
                print(f"      {line}")
        print(f"   🔗 {item['信息链接']}")
else:
    print("   今日暂无重要资讯")
