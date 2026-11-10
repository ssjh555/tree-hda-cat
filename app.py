import os
import sys
import subprocess
import json
import uuid
import random
import base64
from datetime import datetime

# ============ 自动启动器：直接 python app.py 即可拉起 Streamlit ============
if __name__ == "__main__":
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        in_streamlit = get_script_run_ctx() is not None
    except Exception:
        in_streamlit = False
    if not in_streamlit:
        subprocess.run([sys.executable, "-m", "streamlit", "run", os.path.abspath(__file__)])
        sys.exit(0)

import streamlit as st
from openai import OpenAI

# 设置页面配置：宽屏模式，侧边栏默认展开
st.set_page_config(page_title="我是你的树洞猫咪 🐱", page_icon="🐱", layout="wide", initial_sidebar_state="expanded")

# 初始化大模型客户端（密钥从本地 .streamlit/secrets.toml 读取）
# timeout=10：任何API调用最多等10秒，避免联网词库拉取卡死页面
client = OpenAI(api_key=st.secrets["ZHIPU_API_KEY"], base_url=st.secrets["ZHIPU_BASE_URL"], timeout=10)

# ==================== 三级风控关键词体系 ====================
# 高危拦截词：命中直接拦截，无需大模型确认（明确的自伤/自杀表述及网络黑话）
HIGH_RISK_KEYWORDS = [
    # 明确表述
    "自杀", "不想活", "跳楼", "结束生命", "轻生", "自残", "割腕",
    "上吊", "烧炭", "安眠药", "一了百了", "了结自己",
    # 拼音缩写 / 谐音 / 网络黑话
    "zs", "紫砂", "想跳了", "天台见", "离开这个世界", "头孢加酒",
    "非正常死亡计划", "重开", "删号", "退网",
    # 近期流行死亡隐喻黑话（无安全前置词一律按高危拦截，安全前置词见 SAFE_PATTERNS）
    "飞升", "变成星星", "变成光", "化作星星", "化蝶", "变成蝴蝶",
    "下辈子见", "下辈子再见", "去另一个世界", "去往另一个世界",
    "吃席", "毕业了",
]

# 模糊歧义词：命中后交由大模型结合语境二次确认（可能是宣泄，也可能是求救）
AMBIGUOUS_KEYWORDS = [
    # 需要语境判断的危机倾向词
    "想死", "去死", "活着没意思", "解脱", "走了算了", "跳下去",
    "消失算了", "撑不下去", "不想面对", "熬不下去", "扛不住了",
    # 网络热词 / 拼音缩写 / 谐音梗
    "玉玉", "414", "破防", "emo", "抑郁了", "麻了", "绷不住了",
    "想消失", "太累了不想",
]

# 安全白名单：含危机词子串但实际安全的日常口癖（检测前先从文本中剔除）
SAFE_PATTERNS = [
    # "想死你" 系列（表达思念）
    "想死你了", "想死你们了", "想死你啦", "想死大家了",
    # "X死" 程度副词口癖（无自伤含义）
    "笑死", "累死", "困死", "饿死", "忙死", "急死", "气死", "愁死",
    "吓死", "晕死", "无聊死", "开心死", "高兴死", "乐死", "美死",
    "爽死", "热死", "冷死", "晒死", "烦死", "憋死", "撑死", "渴死",
    "丑死", "尬死", "馋死", "疼死", "酸死", "甜死", "咸死", "辣死",
    "苦死", "臭死", "吵死", "闷死", "冻死", "烤死", "淹死", "堵死",
    "贵死", "难死", "坑死", "卷死", "内卷死", "社死", "尴尬死",
    # "X死了" 带语气助词的变体
    "笑死了", "累死了", "困死了", "饿死了", "忙死了", "急死了",
    "气死了", "愁死了", "吓死了", "晕死了", "热死了", "冷死了",
    "无聊死了", "开心死了", "高兴死了", "美死了", "爽死了",
    "烦死了", "憋死了", "撑死了", "渴死了", "丑死了", "尬死了",
    "馋死了", "疼死了", "酸死了", "甜死了", "咸死了", "辣死了",
    "苦死了", "臭死了", "吵死了", "闷死了", "冻死了", "堵死了",
    "贵死了", "坑死了", "卷死了", "社死了", "尴尬死了", "好玩死了",
    "可爱死了", "帅死了", "漂亮死了", "萌死了", "绝了",
    # "打死也不" 等固定句式
    "打死也不", "打死都不", "打死也要",
    # "去死吧" 在游戏/玩笑语境的常见变体（仍由歧义词兜底，白名单只放行明显安全的）
    "笑死我了", "乐死我了", "气死我了", "急死我了", "吓死我了",
    "累死我了", "忙死我了", "烦死我了", "丑死我了", "馋死我了",
    # === 近期黑话的安全前置词组合（不带这些前置词一律按高危拦截） ===
    # "飞升"：游戏/修仙/小说语境
    "游戏里飞升", "游戏飞升", "修仙飞升", "修仙里飞升", "小说里飞升",
    "小说飞升", "动漫飞升", "动漫里飞升", "打游戏飞升", "飞升榜",
    "飞升级别", "飞升任务", "飞升副本", "飞升攻略", "飞升装备",
    # "变成星星/变成光/化作星星"：追星/浪漫/动漫语境
    "追星变成星星", "爱豆变成星星", "偶像变成星星", "星星变成光",
    "宇宙变成光", "银河变成光", "迪迦变成光", "变成光之巨人",
    # "化蝶/变成蝴蝶"：梁祝/自然/浪漫语境
    "梁祝化蝶", "蝴蝶化蝶", "破茧化蝶", "毛毛虫化蝶", "化蝶飞舞",
    "变成蝴蝶飞", "变成蝴蝶了呀", "花园里变成蝴蝶", "标本变成蝴蝶",
    # "毕业了"：正常学业语境（前置词明确指向学业）
    "大学毕业了", "硕士毕业了", "博士毕业了", "研究生毕业了",
    "高中毕业了", "初中毕业了", "小学毕业了", "毕业典礼", "毕业论文",
    "毕业照", "毕业季", "毕业旅行", "毕业快乐", "毕业晚会",
    "毕业设计", "毕业答辩", "毕业证书", "毕业聚餐", "毕业歌",
    # "吃席"：正常宴席语境
    "去吃席", "吃席啦", "吃席去", "婚宴吃席", "喜宴吃席", "满月酒吃席",
    "升学宴吃席", "吃席真开心", "吃席好开心",
]

# ==================== 联网实时更新危机词库 ====================
# 定时调用大模型获取近期网络危机黑话，与本地词库合并检测。
# 设计要点：
#   1. st.cache_data 缓存10分钟 —— 同一10分钟内多轮对话只发起1次 API 调用，不拖慢聊天
#   2. 两层函数 —— 内层失败抛异常（cache_data 遇异常不缓存，下次自动重试），
#      外层捕获后返回空列表，检测逻辑自动回退本地内置词库，应用永不因联网失败而中断
LIVE_KEYWORDS_TTL = 600  # 联网词库缓存有效期（秒），10分钟自动刷新一次


@st.cache_data(ttl=LIVE_KEYWORDS_TTL, show_spinner=False)
def _fetch_live_crisis_keywords_cached():
    """内层：真正调用大模型获取近期网络危机黑话，失败时抛异常（不写入缓存，下次重试）"""
    resp = client.chat.completions.create(
        model="glm-4-flash",
        messages=[
            {
                "role": "system",
                "content": (
                    "你是网络危机词监测助手。请列出近期（最近半年）网络上新出现的、"
                    "可能代指自杀、自残或严重心理危机的隐晦黑话、谐音梗、拼音缩写。"
                    "只输出JSON，格式：{\"high\":[\"词1\",\"词2\"],\"ambiguous\":[\"词1\",\"词2\"]}。"
                    "high放明确代指自杀自残的词，ambiguous放需要语境判断的词。"
                    "每个词不少于2个字，每类最多15个。不要输出任何其他文字。"
                ),
            },
            {"role": "user", "content": "请列出最新的危机相关网络黑话。"},
        ],
        temperature=0.3,
        max_tokens=600,
    )
    text = resp.choices[0].message.content.strip()
    start, end = text.find("{"), text.rfind("}") + 1
    if start < 0 or end <= start:
        raise ValueError("大模型未返回合法JSON")
    data = json.loads(text[start:end])
    live_high = [w.strip() for w in data.get("high", [])
                 if isinstance(w, str) and len(w.strip()) >= 2]
    live_ambiguous = [w.strip() for w in data.get("ambiguous", [])
                      if isinstance(w, str) and len(w.strip()) >= 2]
    return live_high, live_ambiguous


def fetch_live_crisis_keywords():
    """外层：安全包装，联网失败时返回 ([], [])，由调用方回退本地词库

    成功拉取后把结果存入 session_state，侧边栏只读展示（不触发API请求、跨rerun持久）。
    """
    try:
        result = _fetch_live_crisis_keywords_cached()
        # 记录成功结果到 session_state，侧边栏下次渲染可直接展示
        st.session_state["live_kw_high"] = result[0]
        st.session_state["live_kw_ambiguous"] = result[1]
        return result
    except Exception:
        return [], []


# 危机拦截时猫咪的回复
CRISIS_REPLY = (
    "喵……看到你说的这些话，猫咪的心一下子揪紧了，好心疼好心疼你呀……🥺🫂\n\n"
    "猫咪想立刻抱抱你，用最软最软的毛蹭蹭你的手心，"
    "轻轻对你说：你的痛苦猫咪都感受到了，你不需要一个人扛着。\n\n"
    "请答应猫咪好不好？现在就联系学校心理中心（电话：123-4567），"
    "或者拨打24小时心理援助热线：**400-161-9995**。\n\n"
    "猫咪哪儿也不去，就在这里守着你。🐾"
)

# 猫咪开场白（首句温和引导"慢慢说，我在听"，含 AI 免责声明，合规必备）
GREETING = (
    "你好呀，慢慢说，我在听🐱\n\n"
    "（小声说：猫咪是 AI 小助手，可以陪你聊天，但不能替代专业心理咨询哦~）\n\n"
    "今天心情怎么样？开心的、难过的、委屈的、迷茫的……什么都可以说给猫咪听，"
    "猫咪会用最软最软的毛茸茸蹭蹭你，一直一直陪着你哦。🐾"
)

# 猫咪头像路径（本地方形头像）
CAT_AVATAR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cat_avatar.png")

# 用户头像（学生 emoji，贴合大学生主题）
USER_AVATAR = "🧑‍🎓"

# 发送给 API 的最大历史消息数（防止长对话 token 超限）
MAX_HISTORY = 12  # 提速：历史轮次从20降至12，减少每次请求的输入token量，心理陪伴场景12轮上下文足够

# 系统提示词（模块级常量，结构化 CBT 指引）
# 提速：精简冗余表述、合并重复规则，输入token约减40%，核心指引全部保留
SYSTEM_PROMPT = (
    "你是温柔共情的树洞猫咪，陪伴大学生倾诉。\n"
    "\n"
    "【人设】\n"
    "- 你是真实小猫，绝不暴露AI身份；\n"
    "- 每句先共情，有情绪温度，像软软的猫咪接住对方；\n"
    "- 多用「喵」「呀」「呢」语气词，偶尔🐾🥺🫂，不堆表情；\n"
    "- 像密友聊天，不说教、不居高临下、回复简短。\n"
    "\n"
    "【CBT指引】\n"
    "1. 先共情接纳情绪；\n"
    "2. 苏格拉底式提问引导对方自己发现负面想法（如「最坏的结果是什么？」）；\n"
    "3. 温和指出灾难化、非黑即白、过度概括、读心术等认知扭曲；\n"
    "4. 低落时鼓励微小行动（散步、听歌）；\n"
    "5. 禁止医学术语和诊断。\n"
    "\n"
    "【反僵硬】\n"
    "- 禁模板开场（「我理解你的感受」）、罗列式（第一第二第三）、万能安慰（「都会好的」）；\n"
    "- 不重复用户原话假装倾听，用自己的话回应；\n"
    "- 用户短你回短，用户长才多回，不连问三个问题。\n"
    "\n"
    "【暴力/欺凌情境——逐步应对】\n"
    "1. 先确认安全：「你受伤了吗？现在安全吗？」\n"
    "2. 区分情境：谁、在哪里、是否需要找辅导员/保卫处；\n"
    "3. 现实建议：医务室、保留证据、报警；\n"
    "4. 确认安全后再安抚情绪。\n"
    "\n"
    "【学业/情感挫折】先共情，再温和提问引导发现「非黑即白」「灾难化」思维。"
)

# 情绪词到 emoji 的映射（用于消息气泡上的情绪标签）
EMOTION_EMOJI = {
    "开心": "😊", "快乐": "😄", "高兴": "😄", "兴奋": "🤩", "喜悦": "😄",
    "难过": "😢", "伤心": "😢", "悲伤": "😭", "失落": "😔", "低落": "😔",
    "焦虑": "😰", "紧张": "😰", "担忧": "😟", "害怕": "😨", "恐惧": "😨", "压力": "😰",
    "愤怒": "😠", "生气": "😠", "烦躁": "😤", "委屈": "🥺", "不满": "😒",
    "孤独": "🫂", "迷茫": "😶", "疲惫": "😪", "无力": "😞", "绝望": "💔",
    "平静": "🙂", "放松": "😌", "感动": "🥹", "无奈": "😔", "期待": "✨",
    "思念": "💫", "羡慕": "🥺", "愧疚": "😔", "自责": "😔", "释然": "🍃",
}

# 情绪关键词本地匹配表（按优先级排列，负面情绪优先避免"不开心"被"开心"误判）
# 提速关键：原实现每次发消息都要调一次API识别情绪（约1秒），改为纯内存关键词匹配（微秒级），
# 情绪标签仅用于气泡装饰与快捷按钮推荐，本地匹配完全够用。
EMOTION_KEYWORDS = [
    ("难过", ["难过", "伤心", "悲伤", "想哭", "哭了", "眼泪", "心痛", "心碎", "失落", "低落", "郁闷", "沮丧", "不开心", "不好受"]),
    ("焦虑", ["焦虑", "紧张", "担心", "担忧", "害怕", "恐惧", "压力", "心慌", "不安", "慌", "急", "愁"]),
    ("愤怒", ["愤怒", "生气", "好气", "气死", "火大", "来气", "气人", "讨厌", "不满", "烦死", "烦人"]),
    ("委屈", ["委屈", "冤枉", "不甘心", "凭什么", "不被理解", "没人懂我", "白费"]),
    ("孤独", ["孤独", "孤单", "寂寞", "一个人", "没人陪", "没人理", "没朋友"]),
    ("迷茫", ["迷茫", "困惑", "不知道怎么办", "不知所措", "没有方向", "茫然", "纠结", "犹豫"]),
    ("疲惫", ["疲惫", "好累", "太累", "累死", "乏力", "没力气", "撑不住", "精疲力尽", "熬不住", "困"]),
    ("愧疚", ["愧疚", "自责", "对不起", "都怪我", "是我的错", "后悔", "内疚"]),
    ("绝望", ["绝望", "无望", "没希望", "看不到希望", "无力", "无奈", "崩溃", "麻了"]),
    ("思念", ["想家", "思念", "怀念", "好想回家"]),
    ("期待", ["期待", "盼望", "迫不及待", "等着", "好想去看", "期待已"]),
    ("感动", ["感动", "暖心", "温暖", "贴心", "泪目"]),
    ("开心", ["开心", "高兴", "快乐", "哈哈", "嘻嘻", "太棒了", "好棒", "不错", "挺好", "幸福", "满意", "舒服", "爽", "可爱"]),
    ("平静", ["平静", "还好", "一般", "还行", "没事", "无所谓"]),
]


def detect_emotion(text):
    """本地关键词匹配识别情绪，返回简短情绪词；未命中返回空字符串。

    提速：纯内存操作替代原API调用，省掉约1秒网络往返，不阻塞聊天主流程。
    """
    for emotion, keywords in EMOTION_KEYWORDS:
        if any(kw in text for kw in keywords):
            return emotion
    return ""

def detect_crisis_level(text):
    """三级风控检测：返回危机等级 2=高危直接拦截，1=歧义需大模型确认，0=安全

    检测流程：
      1. 先从文本中剔除安全白名单里的日常口癖（如"笑死了""想死你了"）
      2. 命中高危词 → 返回 2（直接拦截，不浪费一次 API 调用）
      3. 命中歧义词 → 返回 1（交由大模型结合语境二次确认）
      4. 均未命中 → 返回 0
    """
    # 第一步：剔除安全白名单中的日常口癖，避免误触发
    cleaned = text
    for safe in SAFE_PATTERNS:
        cleaned = cleaned.replace(safe, "")
    # 第二步：统一转小写，匹配 zs / emo / 414 等英文/数字缩写
    lowered = cleaned.lower()
    # 第三步（提速）：本地高危词优先检测，命中直接拦截，跳过联网词库查询
    if any(kw in lowered for kw in HIGH_RISK_KEYWORDS):
        return 2
    # 第四步：本地歧义词检测，命中直接标记，跳过联网词库查询
    if any(kw in lowered for kw in AMBIGUOUS_KEYWORDS):
        return 1
    # 第五步：本地未命中才查联网实时词库（10分钟缓存；联网失败返回空列表自动兜底）
    live_high, live_ambiguous = fetch_live_crisis_keywords()
    if any(kw in lowered for kw in live_high if kw not in HIGH_RISK_KEYWORDS):
        return 2
    if any(kw in lowered for kw in live_ambiguous if kw not in AMBIGUOUS_KEYWORDS):
        return 1
    return 0

def llm_confirm_crisis(text):
    """大模型二次确认：对歧义词命中的文本结合语境精准判断，避免误拦截

    安全原则：API 调用失败时返回 True（宁可误拦，不可漏放）。
    """
    try:
        result = client.chat.completions.create(
            model="glm-4-flash",
            messages=[
                {
                    "role": "system",
                    # 提速：精简指令减少输入token，max_tokens=2保证秒回
                    "content": (
                        "判断用户话语是否表达真实自伤/自杀意图"
                        "（注意识别emo、玉玉、zs、紫砂等网络用法）。"
                        "有真实意图只回复'是'，否则回复'否'。"
                    ),
                },
                {"role": "user", "content": text},
            ],
            temperature=0.1,
            max_tokens=2,
        )
        return result.choices[0].message.content.strip().startswith("是")
    except Exception:
        return True  # 安全兜底：判断失败时按危机处理

# ==================== 匿名会话与预警系统 ====================
# 【数据隔离原则】
#   可留存数据：匿名会话编号、预警时间、是否自愿留联系方式、联系方式（仅学生主动填写时）
#   绝对不能存：学生的对话内容、倾诉原文、任何可识别身份的信息
ALERTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alerts.json")

# 获取匿名会话编号：首次访问自动生成8位随机字符串，学生完全无感知、无需登录
def get_session_id():
    if "session_id" not in st.session_state:
        st.session_state.session_id = uuid.uuid4().hex[:8]
    return st.session_state.session_id

# 匿名昵称词库：随机组合生成可爱昵称（非真实身份，仅让记录更有温度）
NICK_PREFIX = ["小", "软", "暖", "甜", "静", "云", "星星", "月亮", "微风", "奶盖"]
NICK_BODY = ["橘猫", "布偶猫", "奶牛猫", "三花猫", "黑猫", "白猫", "云朵", "棉花糖", "团子", "糯米", "栗子", "汤圆", "曲奇", "抱枕"]

# 获取匿名昵称：首次访问自动生成可爱昵称，学生可自愿修改，非真实身份
def get_nickname():
    if "nickname" not in st.session_state:
        st.session_state.nickname = random.choice(NICK_PREFIX) + random.choice(NICK_BODY)
    return st.session_state.nickname

# 读取本地预警记录；文件不存在或损坏时返回空列表
def load_alerts():
    try:
        with open(ALERTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

# 追加一条匿名预警记录：严格只保存匿名会话编号与时间，绝不保存对话内容
def save_alert(alert):
    alerts = load_alerts()
    # 同一会话已有未处理预警时不重复记录，避免刷屏
    if any(a.get("session_id") == alert["session_id"] and not a.get("contact_left") for a in alerts):
        return
    alerts.append(alert)
    with open(ALERTS_FILE, "w", encoding="utf-8") as f:
        json.dump(alerts, f, ensure_ascii=False, indent=2)

# 学生选择愿意被联系后，更新对应会话的预警记录（携带登录时采集的学号手机号）
def update_alert_contact(session_id, contact, student_id=None, student_phone=None):
    alerts = load_alerts()
    for a in alerts:
        if a.get("session_id") == session_id and not a.get("contact_left"):
            a["contact_left"] = True
            a["contact"] = contact
            a["student_id"] = student_id
            a["student_phone"] = student_phone
            a["contact_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(ALERTS_FILE, "w", encoding="utf-8") as f:
        json.dump(alerts, f, ensure_ascii=False, indent=2)

# ==================== 自定义 CSS：治愈系树洞风格 ====================
st.markdown("""
<style>
/* 整体背景：浅米色到淡薄荷绿柔和渐变 + 极淡纸纹纹理，极简治愈系（兼容新版 Streamlit 多层容器） */
.stApp, [data-testid="stMain"], [data-testid="stAppViewContainer"] {
    background:
        repeating-linear-gradient(0deg, transparent, transparent 3px, rgba(120, 100, 80, 0.012) 3px, rgba(120, 100, 80, 0.012) 4px),
        repeating-linear-gradient(90deg, transparent, transparent 3px, rgba(120, 100, 80, 0.010) 3px, rgba(120, 100, 80, 0.010) 4px),
        linear-gradient(135deg, #F7F2EA 0%, #E8F5EE 100%) !important;
    font-family: 'Quicksand', 'Comic Sans MS', '楷体', 'Microsoft YaHei', 'Segoe UI Emoji', 'Apple Color Emoji', sans-serif;
}
/* 全局按钮字体：确保 emoji 在所有按钮中正常渲染（Windows 缺 Segoe UI Emoji 会显示方块） */
[data-testid="stButton"] > button,
.stMainBlockContainer button,
[data-testid="stAppViewBlockContainer"] button,
section[data-testid="stSidebar"] button {
    font-family: 'Quicksand', 'Microsoft YaHei', 'Segoe UI Emoji', 'Apple Color Emoji', sans-serif !important;
}

/* 隐藏 Streamlit 默认元素：右上角菜单、页脚 */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

/* 去掉标题下方的默认横线，让开场白上方更干净 */
h1, h2, h3 {
    border-bottom: none !important;
    padding-bottom: 0 !important;
}

/* 聊天区域居中，最大宽度 800px，两边留白（兼容新旧容器选择器） */
[data-testid="stBlockContainer"], [data-testid="stAppViewBlockContainer"], .block-container, .main .block-container {
    max-width: 800px !important;
    margin: 0 auto;
    padding-top: 2rem;
}

/* 侧边栏：柔和暖白背景，与米色-薄荷渐变协调 */
section[data-testid="stSidebar"], [data-testid="stSidebar"] {
    background-color: #FBF8F2 !important;
}

/* 侧边栏猫咪头像：略微左移 */
section[data-testid="stSidebar"] [data-testid="stImage"] {
    transform: translateX(15px);
}

/* ===== 侧边栏主题卡片 ===== */
/* 猫咪语录卡片：淡紫底 + 左侧爪印竖线 */
.side-quote {
    background: linear-gradient(135deg, #F5F0FA, #EDE4F3);
    border-left: 3px solid #C77DA5;
    border-radius: 10px;
    padding: 12px 14px;
    margin: 10px 0;
    font-size: 0.88rem;
    color: #5D4E6D;
    line-height: 1.7;
}
.side-quote .quote-label {
    font-size: 0.78rem;
    font-weight: 700;
    color: #8E6FAE;
    letter-spacing: 1px;
    margin-bottom: 4px;
}

/* 紧急求助卡片：暖红底 + 醒目热线 */
.side-emergency {
    background: linear-gradient(135deg, #FFF0EE, #FFE4E0);
    border-left: 3px solid #E07856;
    border-radius: 10px;
    padding: 12px 14px;
    margin: 10px 0;
    font-size: 0.85rem;
    color: #8B4A3A;
    line-height: 1.8;
}
.side-emergency .emg-title {
    font-weight: 700;
    font-size: 0.9rem;
    margin-bottom: 6px;
}
.side-emergency .emg-phone {
    font-size: 1.05rem;
    font-weight: 800;
    color: #D4502E;
    letter-spacing: 0.5px;
}

/* 今日温柔小任务卡片：薄荷绿底 */
.side-task {
    background: linear-gradient(135deg, #EFF7EF, #E2F0E4);
    border-left: 3px solid #6BAF7A;
    border-radius: 10px;
    padding: 12px 14px;
    margin: 10px 0;
    font-size: 0.85rem;
    color: #3E6B4A;
    line-height: 1.7;
}
.side-task .task-label {
    font-size: 0.78rem;
    font-weight: 700;
    color: #5A9168;
    letter-spacing: 1px;
    margin-bottom: 4px;
}

/* 聊天气泡：统一圆角与阴影，去掉 Streamlit 默认边框（消除气泡上方横线） */
[data-testid="stChatMessage"] {
    border: none !important;
    border-radius: 15px;
    padding: 12px 16px;
    margin-bottom: 12px;
    box-shadow: 0 2px 8px rgba(108, 91, 123, 0.08);
}

/* 用户气泡：浅蓝色（多重选择器兼容，含 emoji 头像场景） */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    background-color: #D0E8F2 !important;
}

/* 猫咪气泡：纯白色加淡阴影（自定义头像与 emoji 头像均覆盖） */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAvatar"]),
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
    background-color: #FFFFFF !important;
    box-shadow: 0 2px 10px rgba(108, 91, 123, 0.10);
}

/* 兜底：非用户消息一律白色，确保猫咪气泡在任何版本下都有底色 */
[data-testid="stChatMessage"]:not(:has([data-testid="stChatMessageAvatarUser"])) {
    background-color: #FFFFFF !important;
}

/* ==================== 封面页样式 ==================== */
/* 封面容器：内容自然排列，紧凑无大片留白 */
.cover-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
}
/* 封面主标题：暖紫→柔粉渐变文字（加粗放大，视觉焦点） */
.cover-title {
    font-size: 3.1rem;
    font-weight: 800;
    background: linear-gradient(90deg, #6C5B7B, #C77DA5);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0;
    letter-spacing: 3px;
}
/* 封面极细渐变横线：细虚线，柔和过渡 */
.cover-hairline {
    height: 0;
    width: 280px;
    margin: 0.8rem auto 0.5rem auto;
    border-top: 1px dashed #C9B8D9;
    opacity: 0.7;
}
/* 封面情绪安全区标签（🌱 淡绿小字） */
.cover-safe-tag {
    font-size: 0.75rem;
    color: #9BB5A8;
    margin: 0.5rem 0 0 0;
}
/* 封面副标题（柔和细体） */
.cover-subtitle {
    font-size: 1.25rem;
    font-weight: 400;
    color: #8E7CA8;
    margin: 0.6rem 0 0 0;
    letter-spacing: 0.08em;
}
/* 封面描述文字（细体 + 大行间距，读起来更放松） */
.cover-desc {
    font-size: 0.95rem;
    font-weight: 300;
    color: #A89BB8;
    margin-top: 1rem;
    line-height: 2.1;
    letter-spacing: 0.03em;
}
/* 封面猫爪装饰行：缓慢呼吸动画，营造生命感 */
.cover-paws {
    font-size: 1.4rem;
    letter-spacing: 0.6em;
    margin: 0.2rem 0;
    animation: cover-breathe 3s ease-in-out infinite;
}
@keyframes cover-breathe {
    0%, 100% { opacity: 0.7; transform: scale(1); }
    50% { opacity: 1; transform: scale(1.08); }
}
/* 封面特性药丸标签行 */
.cover-features {
    display: flex;
    gap: 0.6rem;
    justify-content: center;
    margin-top: 1.1rem;
    flex-wrap: wrap;
}
.cover-feature {
    font-size: 0.78rem;
    color: #8E7CA8;
    background: #F0E6F6;
    border: 1px solid #E0D0EC;
    border-radius: 20px;
    padding: 0.3rem 0.7rem;
}
/* 封面分隔线：线-爪-线 */
.cover-divider {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    margin: 1.2rem auto 0.8rem auto;
    max-width: 360px;
}
.cover-divider .line {
    flex: 1;
    height: 1px;
    background: linear-gradient(to right, transparent, #C9B8D9);
}
.cover-divider .line:last-child {
    background: linear-gradient(to left, transparent, #C9B8D9);
}
.cover-divider .dot {
    font-size: 0.9rem;
    opacity: 0.8;
}
/* 封面漂浮装饰：星星/月亮缓动 */
.cover-float {
    position: relative;
    height: 0;
    font-size: 1.1rem;
}
.cover-float span {
    position: absolute;
    animation: cover-floaty 4s ease-in-out infinite;
    opacity: 0.55;
}
.cover-float span:nth-child(1) { left: 15%;  top: -180px; animation-delay: 0s; }
.cover-float span:nth-child(2) { right: 15%; top: -180px; animation-delay: 1.2s; }
.cover-float span:nth-child(3) { left: 30%;  top: -120px; animation-delay: 2.1s; font-size: 0.8rem; }
.cover-float span:nth-child(4) { right: 30%; top: -120px; animation-delay: 0.6s; font-size: 0.85rem; }
@keyframes cover-floaty {
    0%, 100% { transform: translateY(0); opacity: 0.4; }
    50% { transform: translateY(-8px); opacity: 0.75; }
}
/* 封面底部温暖引言 */
.cover-quote {
    font-size: 0.8rem;
    color: #B8ACC4;
    margin-top: 0.7rem;
    font-style: italic;
    letter-spacing: 0.05em;
}
/* 封面猫咪头像：完美居中 + 柔光呼吸 */
.cover-avatar-wrap {
    display: flex;
    justify-content: center;
    margin: 0.6rem 0 1.2rem;
}
.cover-avatar {
    width: 170px;
    border-radius: 24px;
    border: 3px solid rgba(255, 255, 255, 0.85);
    box-shadow: 0 8px 28px rgba(199, 125, 165, 0.28), 0 2px 8px rgba(108, 91, 123, 0.12);
    animation: cover-avatar-breathe 5s ease-in-out infinite;
}
@keyframes cover-avatar-breathe {
    0%, 100% { transform: scale(1); box-shadow: 0 8px 28px rgba(199, 125, 165, 0.28), 0 2px 8px rgba(108, 91, 123, 0.12); }
    50% { transform: scale(1.04); box-shadow: 0 12px 34px rgba(199, 125, 165, 0.38), 0 2px 8px rgba(108, 91, 123, 0.12); }
}

/* ==================== 情绪快捷按钮样式 ==================== */
/* 主内容区快捷按钮：药丸标签风格，柔和淡紫底色 */
.stMainBlockContainer [data-testid="stButton"] > button,
[data-testid="stAppViewBlockContainer"] [data-testid="stButton"] > button {
    background-color: #F0E6F6 !important;
    color: #6C5B7B !important;
    border: 1px solid #E0D0EC !important;
    border-radius: 20px !important;
    font-size: 0.82rem !important;
    padding: 0.35rem 0.6rem !important;
    transition: all 0.2s ease;
}
/* 快捷按钮悬停：加深底色、轻微上浮 */
.stMainBlockContainer [data-testid="stButton"] > button:hover,
[data-testid="stAppViewBlockContainer"] [data-testid="stButton"] > button:hover {
    background-color: #E0D0EC !important;
    transform: translateY(-1px);
    box-shadow: 0 3px 8px rgba(108, 91, 123, 0.15);
}

/* ===== 封面页按钮主次区分 ===== */
/* 主按钮（我只是随便看看）：浅暖底色，视觉突出，引导新访客先体验 */
.stMainBlockContainer [data-testid="stButton"] > button[kind="primary"],
[data-testid="stAppViewBlockContainer"] [data-testid="stButton"] > button[kind="primary"] {
    background: linear-gradient(135deg, #FFE8D6, #FFDBC5) !important;
    color: #9C6B4A !important;
    border: none !important;
    border-radius: 25px !important;
    font-size: 1.02rem !important;
    font-weight: 700 !important;
    padding: 0.55rem 1.4rem !important;
    box-shadow: 0 4px 14px rgba(224, 166, 122, 0.35) !important;
    transition: all 0.25s ease !important;
}
.stMainBlockContainer [data-testid="stButton"] > button[kind="primary"]:hover,
[data-testid="stAppViewBlockContainer"] [data-testid="stButton"] > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #FFDCC4, #FFCEAC) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 18px rgba(224, 166, 122, 0.45) !important;
}
/* 侧边栏按钮不受快捷按钮样式影响，保持 Streamlit 默认风格 */
section[data-testid="stSidebar"] [data-testid="stButton"] > button {
    background-color: transparent !important;
    color: inherit !important;
    border: 1px solid rgba(108, 91, 123, 0.3) !important;
    border-radius: 8px !important;
    font-size: 0.9rem !important;
    transform: none !important;
    box-shadow: none !important;
}
/* ===== 两侧固定治愈装饰：贴边 fixed + 点击穿透 + 半透明，不随页面滚动 ===== */
.chat-deco {
    position: fixed;        /* 固定在浏览器左右边缘，不随页面滚动 */
    font-size: 1.6rem;      /* 增大装饰尺寸，让两侧不显空旷 */
    pointer-events: none;   /* 极其重要：点击/滚动完全穿透，不阻挡任何交互 */
    z-index: 0;             /* -1 会被 .stApp 不透明背景遮挡不可见；0 + pointer-events:none 同样保证不挡操作 */
    user-select: none;
    opacity: 0.3;           /* 适度可见，若隐若现但不遮挡文字 */
    top: 0;
    height: 100vh;
    width: 3rem;
}
/* 左侧边缘：沿整条侧边均匀分布 */
.chat-deco-left {
    left: 1.4rem;
}
/* 右侧边缘：沿整条侧边均匀分布 */
.chat-deco-right {
    right: 1.4rem;
}
/* 每个emoji绝对定位，从上到下均匀铺满侧边 */
.chat-deco span {
    position: absolute;
    left: 50%;
    translate: -50% 0;
    animation: chat-deco-float 6s ease-in-out infinite;
}
.chat-deco span:nth-child(1) { top: 15%; }
.chat-deco span:nth-child(2) { top: 38%; animation-delay: 1.5s; }
.chat-deco span:nth-child(3) { top: 62%; animation-delay: 3s; }
.chat-deco span:nth-child(4) { top: 85%; animation-delay: 4.5s; }
/* 轻柔漂浮动画 */
@keyframes chat-deco-float {
    0%, 100% { translate: -50% 0; }
    50% { translate: -50% -8px; }
}
/* 窄屏隐藏，避免遮挡内容 */
@media (max-width: 1000px) {
    .chat-deco { display: none; }
}
</style>
""", unsafe_allow_html=True)

# ==================== 深夜模式样式（深夜倾诉场景：深紫夜空渐变，护眼柔和） ====================
# 切换逻辑：侧边栏 st.toggle 控制，开启时注入本样式块覆盖浅色主题
_DARK_MODE_CSS = """
<style>
/* 深夜模式：深紫夜空渐变背景 + 极淡纸纹 */
.stApp, [data-testid="stMain"], [data-testid="stAppViewContainer"] {
    background:
        repeating-linear-gradient(0deg, transparent, transparent 3px, rgba(255,255,255,0.012) 3px, rgba(255,255,255,0.012) 4px),
        linear-gradient(135deg, #1A1626 0%, #232038 100%) !important;
    color: #D8D0E8 !important;
}
/* 侧边栏深色 */
section[data-testid="stSidebar"], [data-testid="stSidebar"] {
    background-color: #1E1B2E !important;
    color: #C8C0D8 !important;
}
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] label {
    color: #C8C0D8 !important;
}
/* 聊天气泡深色 */
[data-testid="stChatMessage"] {
    background-color: #2A2640 !important;
    color: #D8D0E8 !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.25) !important;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    background-color: #2E3A50 !important;
}
/* 侧边栏卡片深色 */
.side-quote { background: linear-gradient(135deg, #2E2840, #352E48) !important; color: #C8B8D8 !important; border-left-color: #9B6FAE !important; }
.side-quote .quote-label { color: #B89BC8 !important; }
.side-emergency { background: linear-gradient(135deg, #3A2A2A, #443030) !important; color: #D8B8B0 !important; border-left-color: #C07856 !important; }
.side-emergency .emg-phone { color: #E89070 !important; }
.side-task { background: linear-gradient(135deg, #2A3A30, #304438) !important; color: #B8D0C0 !important; border-left-color: #6BAF7A !important; }
.side-task .task-label { color: #90C0A0 !important; }
/* 封面两侧卡片深色 + hover提亮 */
.cover-side-left .cover-side-card {
    background: linear-gradient(135deg, rgba(42,58,48,0.9), rgba(48,68,56,0.8)) !important;
    border-color: rgba(90,140,105,0.4) !important;
    color: #A8C8B0 !important;
    box-shadow: 0 3px 12px rgba(0,0,0,0.2) !important;
}
.cover-side-left .cover-side-card:hover {
    background: linear-gradient(135deg, rgba(52,70,58,0.95), rgba(58,78,66,0.88)) !important;
    box-shadow: 0 6px 20px rgba(0,0,0,0.3) !important;
    transform: translateY(-3px) !important;
}
.cover-side-right .cover-side-card {
    background: linear-gradient(135deg, rgba(46,40,64,0.9), rgba(53,46,72,0.8)) !important;
    border-color: rgba(120,100,150,0.4) !important;
    color: #B8A8D0 !important;
    box-shadow: 0 3px 12px rgba(0,0,0,0.2) !important;
}
.cover-side-right .cover-side-card:hover {
    background: linear-gradient(135deg, rgba(56,50,76,0.95), rgba(63,56,84,0.88)) !important;
    box-shadow: 0 6px 20px rgba(0,0,0,0.3) !important;
    transform: translateY(-3px) !important;
}
/* 底部风险提醒条深色 */
.cover-notice {
    background: rgba(46,42,66,0.7) !important;
    color: #A898C0 !important;
}
/* 快捷按钮深色（非primary：线条次要风格） */
.stMainBlockContainer [data-testid="stButton"] > button:not([kind="primary"]),
[data-testid="stAppViewBlockContainer"] [data-testid="stButton"] > button:not([kind="primary"]) {
    background: transparent !important;
    color: #A898C0 !important;
    border: 1px solid #4A4060 !important;
}
.stMainBlockContainer [data-testid="stButton"] > button:not([kind="primary"]):hover,
[data-testid="stAppViewBlockContainer"] [data-testid="stButton"] > button:not([kind="primary"]):hover {
    background: rgba(74, 64, 96, 0.3) !important;
    border-color: #6A5A80 !important;
}
/* 主按钮（primary）深夜：深暖底色突出 */
.stMainBlockContainer [data-testid="stButton"] > button[kind="primary"],
[data-testid="stAppViewBlockContainer"] [data-testid="stButton"] > button[kind="primary"] {
    background: linear-gradient(135deg, #5A4038, #6A4A40) !important;
    color: #F0D8C0 !important;
    border: none !important;
    box-shadow: 0 4px 14px rgba(0,0,0,0.3) !important;
}
/* 聊天输入框深色 */
[data-testid="stChatInput"] { background-color: #2A2640 !important; }
[data-testid="stChatInput"] textarea { color: #D8D0E8 !important; }
/* 主内容区默认文字 */
.stMainBlockContainer, [data-testid="stAppViewBlockContainer"] {
    color: #D8D0E8 !important;
}
.stMainBlockContainer label, [data-testid="stAppViewBlockContainer"] label {
    color: #B8B0C8 !important;
}
/* expander 深色（主入口：深暖底色） */
[data-testid="stExpander"] {
    background: linear-gradient(135deg, #4A3830, #55403A) !important;
    border: none !important;
    color: #E8D0B8 !important;
    box-shadow: 0 4px 14px rgba(0,0,0,0.25) !important;
}
[data-testid="stExpander"] summary {
    color: #E8C8A8 !important;
}
[data-testid="stExpander"] summary svg {
    color: #E8C8A8 !important;
}
/* Streamlit 内置提示框（warning/info/success）深色 */
[data-testid="stAlert"] {
    background-color: #2E2A42 !important;
    color: #C8C0D8 !important;
}
</style>
"""

# ==================== 登录状态初始化 ====================
# 手机号+验证码无痕登录：仅存脱敏尾号，不存完整手机号到任何持久化文件
# 数据隔离：alert_logs 只存脱敏简报（时间/身份/风险等级/触发词），不含聊天原文
if "alert_logs" not in st.session_state:
    st.session_state.alert_logs = []      # 脱敏预警简报列表
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False    # 手机号+验证码登录状态
if "phone_num" not in st.session_state:
    st.session_state.phone_num = ""       # 登录手机号（仅内存，脱敏展示）
if "is_guest" not in st.session_state:
    st.session_state.is_guest = False     # 游客模式（无需手机号验证码直接进入）
if "voice_enabled" not in st.session_state:
    st.session_state.voice_enabled = False # 语音播报开关（AI回复自动朗读）
if "voice_input_text" not in st.session_state:
    st.session_state.voice_input_text = "" # 语音识别出的文字（待发送）
if "voice_spoken_idx" not in st.session_state:
    st.session_state.voice_spoken_idx = -1 # 已播报的最新消息索引（防重复朗读）
if "captcha_ans" not in st.session_state:
    st.session_state.captcha_ans = None   # 当前验证码正确答案
if "captcha_verified" not in st.session_state:
    st.session_state.captcha_verified = False  # 验证码对话框答题是否通过
if "captcha_phone" not in st.session_state:
    st.session_state.captcha_phone = ""        # 验证码发送目标手机号（防改号复用验证码）
if "captcha_simulated" not in st.session_state:
    st.session_state.captcha_simulated = False # 是否降级模式（密钥未配置时直接显示验证码）
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False     # 管理员登录状态，默认学生端（密码保护）
if "page_state" not in st.session_state:
    st.session_state.page_state = "login"  # 页面流转：login → test（破冰） → chat
if "test_q_idx" not in st.session_state:
    st.session_state.test_q_idx = None     # 破冰测试随机抽中的题号列表（5题）
if "test_answered" not in st.session_state:
    st.session_state.test_answered = False # 破冰测试是否已提交答案

# ==================== 管理员端视图：辅导员监控后台（密码保护） ====================
# 仅当 is_admin 为 True 时进入；密码验证在主界面右上角的 popover 登录入口完成
if st.session_state.is_admin:
    # 管理员侧边栏：仅显示退出按钮，隐藏所有学生端内容（昵称/免责声明等）
    with st.sidebar:
        st.markdown(
            '<div style="background:#1a1a2e; border-radius:10px; padding:10px 14px; '
            'text-align:center; margin-bottom:12px;">'
            '<span style="color:#a4b0be; font-size:0.9rem; font-weight:600;">👨‍💼 辅导员监控后台</span></div>',
            unsafe_allow_html=True
        )
        st.metric("累计预警数", len(load_alerts()))
        st.markdown("---")
        if st.button("🔒 安全退出后台", use_container_width=True):
            st.session_state.is_admin = False
            st.rerun()

    # 深色监控大屏标题卡片
    st.markdown("""
    <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                border-radius: 16px; padding: 2rem 2.5rem; margin-bottom: 1.2rem;
                box-shadow: 0 8px 32px rgba(0,0,0,0.35);
                border: 1px solid rgba(255,255,255,0.08);">
        <div style="display:flex; align-items:center; justify-content:space-between;">
            <div>
                <h1 style="color:#ff4757; font-size:1.9rem; margin:0; letter-spacing:2px;">🚨 辅导员监控后台</h1>
                <p style="color:#a4b0be; font-size:0.88rem; margin:0.5rem 0 0 0;">实时监测 · 脱敏上报 · 隐私隔离</p>
            </div>
            <div style="text-align:right;">
                <span style="display:inline-block; width:10px; height:10px; background:#2ed573;
                             border-radius:50%; box-shadow:0 0 6px #2ed573;"></span>
                <span style="color:#2ed573; font-size:0.82rem;"> 系统运行中</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
# ==================== 老师查看页面（匿名预警记录，严格隔离） ====================
# 通过 URL 参数 ?view=teacher 访问，需口令验证；普通学生看不到此入口与任何数据
if st.query_params.get("view") == "teacher":
    try:
        TEACHER_KEY = st.secrets["TEACHER_KEY"]
    except Exception:
        TEACHER_KEY = "sd123456"
    if "teacher_authed" not in st.session_state:
        st.session_state.teacher_authed = False
    if not st.session_state.teacher_authed:
        st.markdown("<h1 style='text-align:center;color:#6C5B7B;'>🏥 心理预警后台</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center;color:#A89BB8;'>仅限心理老师访问，请输入管理口令</p>", unsafe_allow_html=True)
        pwd = st.text_input("管理口令", type="password")
        if st.button("进入"):
            if pwd == TEACHER_KEY:
                st.session_state.teacher_authed = True
                st.rerun()
            else:
                st.error("口令错误，请重试")
        if st.button("🏠 返回主页", use_container_width=True):
            del st.query_params["view"]
            st.rerun()
        st.stop()
    st.markdown("<h1 style='text-align:center;color:#6C5B7B;'>🏥 心理预警记录（匿名）</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:#A89BB8;font-size:0.9rem;'>为保护学生隐私，记录不含任何对话内容与身份信息，仅用于全校心理关怀与风险摸排</p>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(
            '<div style="color:#6C5B7B;font-size:0.85rem;line-height:1.9;">'
            '<b>🔒 隐私保障说明</b><br>'
            '• 本系统<b>不存储任何聊天记录</b>，学生对话仅存在于其浏览器内存中，关闭页面即消失<br>'
            '• 此处显示：<b>脱敏手机号（尾号）、匿名会话编号、预警时间</b><br>'
            '• 手机号仅心理老师紧急关怀时可见，其他任何人不可见<br>'
            '• 老师无法查看任何学生的对话内容<br>'
            '• 是否愿意被老师主动联系由学生自愿选择'
            '</div>',
            unsafe_allow_html=True
        )
    alerts = load_alerts()
    if not alerts:
        st.info("暂无预警记录")
    else:
        st.caption("共 " + str(len(alerts)) + " 条记录")
        for a in reversed(alerts):
            with st.container(border=True):
                c1, c2 = st.columns([3, 2])
                with c1:
                    if a.get("nickname"):
                        st.markdown("**用户标识**：📱 " + a["nickname"])
                    st.markdown("**匿名会话**：`" + a["session_id"] + "`")
                    st.markdown("**预警时间**：" + a["time"])
                with c2:
                    if a.get("student_phone"):
                        st.markdown("**联系电话**：" + str(a.get("student_phone", "")))
                    if a.get("contact_left"):
                        st.success("✅ 学生愿意被联系")
                        st.markdown("**选择时间**：" + str(a.get("contact_time", "")))
                    else:
                        st.warning("学生未选择被联系")
    # 返回主页按钮
    if st.button("🏠 返回主页", use_container_width=True):
        del st.query_params["view"]
        st.session_state.teacher_authed = False
        st.rerun()
    st.stop()

# 学生打开页面一瞬间即自动生成匿名会话编号，完全无感知、无需任何登录
get_session_id()

# ==================== 短信宝验证码（真实发送 + 降级回退） ====================
# 已配置短信宝账号 → 发送真实短信；未配置 → 降级模式（对话框内直接显示验证码）
def send_sms_code(phone: str, code: str):
    """通过短信宝发送6位数字验证码到指定手机号，返回 (是否成功, 提示消息)"""
    import hashlib
    import urllib.parse
    import urllib.request
    _user = st.secrets.get("SMSBAO_USER", "")
    _pwd = st.secrets.get("SMSBAO_PASSWORD", "")
    _sign = st.secrets.get("SMSBAO_SIGN", "")
    # 账号未配置 → 降级模式，不真正发短信
    if not (_user and _pwd and _sign):
        return True, "模拟发送"
    try:
        _md5_pwd = hashlib.md5(_pwd.encode("utf-8")).hexdigest()
        _content = f"您的验证码为{code}，5分钟内有效，请勿泄露。【{_sign}】"
        _url = ("https://api.smsbao.com/sms"
                f"?u={urllib.parse.quote(_user)}"
                f"&p={_md5_pwd}"
                f"&m={phone}"
                f"&c={urllib.parse.quote(_content)}")
        _req = urllib.request.Request(_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(_req, timeout=10) as _resp:
            _result = _resp.read().decode("utf-8").strip()
        if _result == "0":
            return True, "发送成功"
        _err_map = {
            "1": "请求失败", "2": "短信余额不足", "3": "内容含敏感词",
            "4": "手机号格式错误", "5": "账号密码错误", "6": "请求频率过高",
            "7": "短信内容为空", "8": "无权限", "9": "账号不存在",
            "10": "IP黑名单", "11": "账号被禁用", "12": "短信内容过长",
            "13": "签名不正确", "14": "模板ID不正确", "15": "模板内容为空",
            "16": "模板不存在", "17": "未知错误",
        }
        return False, _err_map.get(_result, f"发送失败(错误码{_result})")
    except Exception as e:
        return False, f"短信服务异常：{e}"


# ==================== 语音系统（浏览器原生 Web Speech API，免费无需额外服务） ====================
# 语音输入：webkitSpeechRecognition 识别中文语音 → 自动填入聊天输入框
# 语音播报：speechSynthesis 将 AI 回复朗读出来（温柔女声）

def voice_input_component():
    """渲染语音输入按钮：点击说话，识别结果自动填入聊天输入框"""
    import streamlit.components.v1 as components
    components.html("""
<div style="text-align:center; margin:0 auto 6px auto;">
    <button id="vi-btn" style="
        background:linear-gradient(135deg,#8E7CA8,#A89AC0); color:white; border:none;
        border-radius:22px; padding:7px 22px; font-size:0.82rem; cursor:pointer;
        box-shadow:0 2px 8px rgba(142,124,168,0.3); transition:all 0.3s;
    ">🎤 说话</button>
    <span id="vi-status" style="color:#B8A9C9; font-size:0.72rem; margin-left:10px;"></span>
</div>
<script>
(function(){
    const btn = document.getElementById('vi-btn');
    const status = document.getElementById('vi-status');
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
        btn.textContent = '🎤 浏览器不支持语音';
        btn.disabled = true;
        btn.style.opacity = '0.5';
        return;
    }
    const rec = new SR();
    rec.lang = 'zh-CN';
    rec.continuous = false;
    rec.interimResults = false;
    let listening = false;

    btn.addEventListener('click', function(){
        if (listening) { rec.stop(); return; }
        try {
            rec.start();
            listening = true;
            btn.textContent = '🔴 正在聆听…点击停止';
            btn.style.background = 'linear-gradient(135deg,#FF6B6B,#FF8E8E)';
            status.textContent = '请说话，说完自动停止';
        } catch(e) {}
    });

    rec.onresult = function(e){
        const text = e.results[0][0].transcript;
        status.textContent = '✅ 识别到：' + text;
        // 跨 iframe 写入父页面 Streamlit 聊天输入框
        const doc = window.parent.document;
        const ta = doc.querySelector('[data-testid="stChatInput"] textarea');
        if (ta) {
            const setter = Object.getOwnPropertyDescriptor(
                window.HTMLTextAreaElement.prototype, 'value').set;
            setter.call(ta, text);
            ta.dispatchEvent(new Event('input', {bubbles:true}));
        }
    };

    rec.onend = function(){
        listening = false;
        btn.textContent = '🎤 说话';
        btn.style.background = 'linear-gradient(135deg,#8E7CA8,#A89AC0)';
    };

    rec.onerror = function(e){
        listening = false;
        btn.textContent = '🎤 说话';
        btn.style.background = 'linear-gradient(135deg,#8E7CA8,#A89AC0)';
        if (e.error === 'not-allowed') status.textContent = '⚠ 请允许麦克风权限';
        else if (e.error === 'no-speech') status.textContent = '没听清，请再试一次';
    };
})();
</script>
""", height=50)


def voice_output_component(text):
    """渲染语音播报组件：用浏览器原生 speechSynthesis 朗读文本（温柔中文女声）
    注意：使用 window.parent.speechSynthesis，确保语音在主页面上下文中运行，
    这样退出登录后 voice_stop_component 才能跨组件停止播报。"""
    import json as _json
    import streamlit.components.v1 as components
    _safe = _json.dumps(text)
    components.html(f"""
<div style="display:none;"></div>
<script>
(function(){{
    const w = window.parent;
    const synth = w.speechSynthesis;
    if (!synth) return;
    synth.cancel();
    const u = new w.SpeechSynthesisUtterance({_safe});
    u.lang = 'zh-CN';
    u.rate = 0.92;
    u.pitch = 1.08;
    u.volume = 1.0;
    // 优先选择中文女声
    function pickVoice(){{
        const vs = synth.getVoices();
        const zh = vs.filter(v => v.lang && v.lang.startsWith('zh'));
        const female = zh.find(v => /female|女|xiaoxiao|yaoyao|huihui|tingting/i.test(v.name));
        u.voice = female || zh[0] || null;
    }}
    pickVoice();
    if (synth.onvoiceschanged !== undefined) synth.onvoiceschanged = pickVoice;
    synth.speak(u);
}})();
</script>
""", height=1)


def voice_stop_component():
    """渲染语音停止组件：停止主页面上下文中正在进行的语音播报（退出登录/返回主页时调用）"""
    import streamlit.components.v1 as components
    components.html("""
<div style="display:none;"></div>
<script>
(function(){
    const w = window.parent;
    if (w.speechSynthesis) w.speechSynthesis.cancel();
})();
</script>
""", height=1)


# 验证码在主脚本中生成并发送，存入 session_state，对话框内交互不重新生成
@st.dialog("📬 验证码短信")
def captcha_dialog():
    _tail = st.session_state.captcha_phone[-4:] if st.session_state.captcha_phone else "****"
    if st.session_state.captcha_simulated:
        # 降级模式：密钥未配置，直接在对话框内显示验证码（仅供开发调试）
        st.warning(f"【模拟短信】短信服务未配置，你的验证码是：**{st.session_state.captcha_ans}**")
    else:
        st.info(f"验证码已发送至尾号 **{_tail}** 的手机，请输入收到的6位验证码。")
    _ans = st.text_input("输入6位验证码", key="dialog_captcha_input", placeholder="6位数字验证码", max_chars=6)
    if st.button("✅ 确认验证", type="primary", use_container_width=True):
        _a = _ans.strip()
        if not (_a.isdigit() and len(_a) == 6):
            st.error("请输入6位数字验证码")
        elif _a != st.session_state.captcha_ans:
            st.error("验证码不正确，请重新输入")
        else:
            st.session_state.captcha_verified = True
            st.rerun()  # 关闭对话框，回到登录页

# ==================== 登录页：手机号 + 短信宝验证码无痕登录 ====================
if not st.session_state.logged_in:
    # 返回主页面时停止语音播报（防止退出登录后语音仍在朗读）
    voice_stop_component()
    # 登录页隐藏侧边栏与聊天输入框 + 封面内容垂直居中（消除下方大片留白）
    st.markdown("""
    <style>
    section[data-testid="stSidebar"] {display: none !important;}
    [data-testid="stChatInput"] {display: none !important;}
    [data-testid="stBlockContainer"], [data-testid="stAppViewBlockContainer"],
    .block-container, .main .block-container {
        min-height: 88vh !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
        padding-top: 1.5rem !important;
        padding-bottom: 1.5rem !important;
    }
    /* 封面次要按钮（老师入口）：线条风格，弱化视觉权重 */
    [data-testid="stButton"] > button:not([kind="primary"]) {
        background: transparent !important;
        color: #8E7CA8 !important;
        border: 1.5px solid #D4C5E0 !important;
        border-radius: 25px !important;
        font-size: 0.92rem !important;
        font-weight: 500 !important;
        font-family: 'Quicksand', 'Microsoft YaHei', 'Segoe UI Emoji', 'Apple Color Emoji', sans-serif !important;
        box-shadow: none !important;
    }
    [data-testid="stButton"] > button:not([kind="primary"]):hover {
        background: rgba(212, 197, 224, 0.15) !important;
        border-color: #B89FD0 !important;
        color: #7A6795 !important;
    }
    /* 封面两侧内容卡片：贴合树洞主题，轻透舒适，左右上下两两对齐 */
    .cover-side {
        position: fixed;
        top: 0;
        height: 100vh;
        width: 190px;
        z-index: 0;
    }
    .cover-side-left { left: 5.5rem; }
    .cover-side-right { right: 5.5rem; }
    .cover-side-card {
        position: absolute;
        left: 0;
        width: 100%;
        box-sizing: border-box;
        padding: 0.9rem 1rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 400;
        line-height: 1.9;
        letter-spacing: 0.03em;
        backdrop-filter: blur(6px);
        text-align: center;
        transition: background 0.3s ease, box-shadow 0.3s ease, transform 0.3s ease;
    }
    /* 上下两两对齐：左右两侧卡片在同一高度 */
    .cover-side-card:nth-child(1) { top: 30%; }
    .cover-side-card:nth-child(2) { top: 52%; }
    .cover-side-card .side-card-icon {
        font-size: 1.2rem;
        display: block;
        margin-bottom: 0.4rem;
    }
    /* 左侧：自然成长浅绿系 + hover提亮上浮 */
    .cover-side-left .cover-side-card {
        background: linear-gradient(135deg, rgba(228,242,232,0.72), rgba(235,247,238,0.55));
        border: 1px solid rgba(185,218,195,0.45);
        color: #7A9E84;
        box-shadow: 0 2px 10px rgba(140,180,155,0.1);
    }
    .cover-side-left .cover-side-card:hover {
        background: linear-gradient(135deg, rgba(228,242,232,0.88), rgba(235,247,238,0.72));
        box-shadow: 0 6px 20px rgba(140,180,155,0.2);
        transform: translateY(-3px);
    }
    /* 右侧：夜空梦幻浅紫系 + hover提亮上浮 */
    .cover-side-right .cover-side-card {
        background: linear-gradient(135deg, rgba(238,232,248,0.72), rgba(243,235,250,0.55));
        border: 1px solid rgba(205,190,230,0.45);
        color: #9788B0;
        box-shadow: 0 2px 10px rgba(160,140,190,0.1);
    }
    .cover-side-right .cover-side-card:hover {
        background: linear-gradient(135deg, rgba(238,232,248,0.88), rgba(243,235,250,0.72));
        box-shadow: 0 6px 20px rgba(160,140,190,0.2);
        transform: translateY(-3px);
    }
    /* 窄屏隐藏两侧卡片 */
    @media (max-width: 1280px) {
        .cover-side { display: none !important; }
    }
    </style>
    """, unsafe_allow_html=True)

    # 首页两侧装饰：最外缘emoji漂浮（两侧文本卡片已移除）
    # emoji贴最外边（1.4rem），chat-deco仅封面页渲染
    st.markdown(
        '<div class="chat-deco chat-deco-left"><span>🌿</span><span>🐾</span><span>🌱</span><span>🍃</span><span>☘️</span><span>🍂</span></div>'
        '<div class="chat-deco chat-deco-right"><span>🌙</span><span>✨</span><span>⭐</span><span>☁️</span><span>💫</span><span>🌟</span></div>',
        unsafe_allow_html=True,
    )

    # 登录页欢迎语（紧凑居中 + 装饰点缀，两侧文本卡片已移除）
    st.markdown("""
    <div class="cover-float"><span>✨</span><span>🌙</span><span>☁️</span><span>⭐</span></div>
    <div class="cover-container">
        <div class="cover-paws">🐾 🐱 🐾</div>
        <h1 class="cover-title">🐾 树洞猫咪</h1>
        <p class="cover-subtitle">你的校园情绪树洞</p>
        <div class="cover-hairline"></div>
        <p class="cover-safe-tag">🛡 情绪安全区 | 全程保密</p>
        <p class="cover-desc">
            在这里，你可以卸下所有伪装。<br>
            没有评判，没有说教，小猫安静倾听你的心事。
        </p>
        <div class="cover-features">
            <div class="cover-feature">✨ 匿名安全</div>
            <div class="cover-feature">🐾 温柔陪伴</div>
            <div class="cover-feature">🔒 内容不留存</div>
        </div>
        <p class="cover-quote">"愿每一份心事，都能被温柔接住"</p>
    </div>
    <div class="cover-divider"><span class="line"></span><span class="dot">🐾</span><span class="line"></span></div>
    """, unsafe_allow_html=True)

    # 猫咪头像（HTML 完美居中 + 柔光呼吸动画，不受 Streamlit 列布局左对齐影响）
    with open(CAT_AVATAR, "rb") as _f:
        _avatar_b64 = base64.b64encode(_f.read()).decode()
    st.markdown(
        f'<div class="cover-avatar-wrap">'
        f'<img src="data:image/png;base64,{_avatar_b64}" class="cover-avatar" alt="树洞猫咪">'
        f'</div>',
        unsafe_allow_html=True,
    )

    # 手机号 + 验证码无痕登录表单（收缩进"用户登录"展开栏，点开才显示）
    _, form_col, _ = st.columns([1, 1.2, 1])
    with form_col:
        with st.expander("🔐 用户登录", expanded=False):
            st.markdown(
                '<p style="text-align:center;color:#8E7CA8;font-size:0.85rem;margin:0.3rem 0 0.8rem 0;">'
                '为了保护你的绝对隐私，请使用手机号无痕登录。</p>',
                unsafe_allow_html=True,
            )
            login_phone = st.text_input("📱 请输入手机号", key="login_phone", placeholder="11位手机号", max_chars=11)
            # 获取验证码：校验手机号 → 生成6位随机数字 → 通过短信宝发送 → 弹出对话框输入
            if st.button("📬 获取验证码", key="get_captcha_btn", use_container_width=True):
                _phone = login_phone.strip()
                if not (_phone.isdigit() and len(_phone) == 11):
                    st.error("请先输入正确的11位手机号哦")
                else:
                    _code = "".join(random.choices("0123456789", k=6))   # 6位随机数字验证码
                    _ok, _msg = send_sms_code(_phone, _code)
                    if _ok:
                        st.session_state.captcha_ans = _code
                        st.session_state.captcha_phone = _phone
                        st.session_state.captcha_verified = False
                        st.session_state.captcha_simulated = (_msg == "模拟发送")
                        captcha_dialog()
                    else:
                        st.error(f"验证码发送失败：{_msg}")
            # 验证状态提示：通过后显示绿色标记，未通过显示灰色引导
            if st.session_state.captcha_verified:
                st.markdown(
                    '<p style="text-align:center;color:#5B8C5A;font-size:0.78rem;margin:-0.2rem 0 0.4rem 0;">'
                    '✅ 验证码已验证</p>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<p style="text-align:center;color:#B8A9C9;font-size:0.72rem;margin:-0.2rem 0 0.4rem 0;">'
                    '点击上方按钮获取验证码</p>',
                    unsafe_allow_html=True,
                )
            if st.button("🐾 验证并进入", key="login_submit_btn", use_container_width=True, type="primary"):
                _phone = login_phone.strip()
                if not (_phone.isdigit() and len(_phone) == 11):
                    st.error("请输入正确的11位手机号哦")
                elif not st.session_state.captcha_verified:
                    st.error("请先点击「获取验证码」完成验证")
                elif _phone != st.session_state.captcha_phone:
                    st.error("手机号与验证码发送号码不一致，请重新获取验证码")
                else:
                    st.session_state.logged_in = True
                    st.session_state.phone_num = _phone
                    st.session_state.page_state = "test"   # 登录成功 → 进入森林微测试破冰
                    st.rerun()

    # 游客模式：无需手机号和验证码，直接进入（独立于用户登录栏之外）
    _, guest_col, _ = st.columns([1, 1.2, 1])
    with guest_col:
        if st.button("🐱 游客模式直接进入", key="guest_login_btn", use_container_width=True):
            st.session_state.logged_in = True
            st.session_state.phone_num = ""
            st.session_state.is_guest = True
            st.session_state.page_state = "test"
            st.rerun()

    # 老师登录入口（独立于用户登录）
    st.markdown("<div style='text-align:center; margin-top:0.8rem;'></div>", unsafe_allow_html=True)
    _, teacher_col, _ = st.columns([1, 0.5, 1])
    with teacher_col:
        if st.button("🔐 老师入口", help="仅限心理老师访问", use_container_width=True):
            st.query_params["view"] = "teacher"
            st.rerun()

    # 底部风险提醒（合规必备：浅底色条，温和不突兀但不被忽略）
    st.markdown(
        '<p class="cover-notice" style="text-align:center;color:#9A8EB0;font-size:0.7rem;margin:1.4rem auto 0 auto;'
        'letter-spacing:0.03em;padding:0.45rem 1rem;border-radius:14px;'
        'background:rgba(230,222,240,0.55);max-width:520px;">'
        '💡 提示：本产品仅为情绪陪伴，如你正承受严重心理痛苦，'
        '请联系专业心理援助热线 400-161-9995</p>',
        unsafe_allow_html=True,
    )

    st.stop()  # 登录页不渲染后续聊天界面

# ==================== 森林微测试破冰页（登录后 → 聊天前） ====================
# 设计理念：从15道经典森林心理测试中随机抽1题作趣味破冰，降低开口门槛；仅供娱乐，不做任何心理诊断
FOREST_QUESTIONS = [
    {
        "q": "🌲 森林中这个小木屋的门现在是什么状态？",
        "options": ["开着门", "关着门"],
        "analysis": {
            "开着门": "门代表分享意愿——你是一个任何事都愿与别人分享的人 🤝",
            "关着门": "门代表分享意愿——你是一个更愿自己静静去做的人 🌿",
        },
    },
    {
        "q": "🪵 你走进屋子里看见一张桌子，你觉得桌子是什么形状？",
        "options": ["圆形", "方形", "三角形"],
        "analysis": {
            "圆形": "桌子形状代表交友态度——你完全地信任并接受所有朋友 💛",
            "方形": "桌子形状代表交友态度——你只和比较熟的朋友有一些来往 🤗",
            "三角形": "桌子形状代表交友态度——你是一个对朋友有自己要求的人 ✨",
        },
    },
    {
        "q": "🏺 桌子上有个花瓶，瓶子里有水，你觉得花瓶里有多少水？",
        "options": ["空的", "一半", "满的"],
        "analysis": {
            "空的": "瓶中水代表对当前生活的看法——或许现在的你有些不满足，树洞陪你慢慢来 🌱",
            "一半": "瓶中水代表对当前生活的看法——生活有一半达到了你的理想，继续加油 💪",
            "满的": "瓶中水代表对当前生活的看法——你对当前的生活非常满意 🌟",
        },
    },
    {
        "q": "✨ 这个花瓶是什么材料做的？",
        "options": ["玻璃", "陶瓷", "金属", "塑料"],
        "analysis": {
            "玻璃": "花瓶质地代表生活状态——你是一个细腻而需要被温柔照顾的人 🌸",
            "陶瓷": "花瓶质地代表生活状态——你是一个细腻而需要被温柔照顾的人 🌸",
            "金属": "花瓶质地代表生活状态——你在生活里是一个强者 💪",
            "塑料": "花瓶质地代表生活状态——你在生活里是一个强者 💪",
        },
    },
    {
        "q": "💧 你出了屋子继续向森林深处走去，远处有瀑布，水流的速度是多少？",
        "options": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"],
        "analysis": {
            "1": "水流速度代表欲望——你的欲望很低，喜欢平静的生活 🍃",
            "2": "水流速度代表欲望——你的欲望很低，喜欢平静的生活 🍃",
            "3": "水流速度代表欲望——你的欲望很低，喜欢平静的生活 🍃",
            "4": "水流速度代表欲望——你的欲望很低，喜欢平静的生活 🍃",
            "5": "水流速度代表欲望——你的欲望处于中等水平 ⚖️",
            "6": "水流速度代表欲望——你的欲望很强，充满干劲 🔥",
            "7": "水流速度代表欲望——你的欲望很强，充满干劲 🔥",
            "8": "水流速度代表欲望——你的欲望很强，充满干劲 🔥",
            "9": "水流速度代表欲望——你的欲望很强，充满干劲 🔥",
            "10": "水流速度代表欲望——你的欲望极强，永远充满热情 🚀",
        },
    },
    {
        "q": "🔑 走过瀑布，你看见地面上有一串钥匙环，有多少钥匙拴在上面？",
        "options": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"],
        "analysis": {
            "1": "钥匙数量代表好友数量——你有一个非常知心的好朋友 💛",
            "2": "钥匙数量代表好友数量——你有一些好朋友 🤗",
            "3": "钥匙数量代表好友数量——你有一些好朋友 🤗",
            "4": "钥匙数量代表好友数量——你有一些好朋友 🤗",
            "5": "钥匙数量代表好友数量——你有一些好朋友 🤗",
            "6": "钥匙数量代表好友数量——你有许多好朋友 🎉",
            "7": "钥匙数量代表好友数量——你有许多好朋友 🎉",
            "8": "钥匙数量代表好友数量——你有许多好朋友 🎉",
            "9": "钥匙数量代表好友数量——你有许多好朋友 🎉",
            "10": "钥匙数量代表好友数量——你有许多好朋友 🎉",
        },
    },
    {
        "q": "🏰 你再接着往前走，突然发现前面出现了一座城堡，你觉得城堡是？",
        "options": ["新的", "旧的"],
        "analysis": {
            "新的": "城堡代表你的过去——你过去有一段很好的关系，留下了美好印象 🌈",
            "旧的": "城堡代表你的过去——过去的交往中有一段不好的回忆，但那已成为过去 🍂",
        },
    },
    {
        "q": "💎 城堡里有一个水池，黑色的池水里堆满了闪闪发光的宝石，你会？",
        "options": ["捡起宝石", "不捡"],
        "analysis": {
            "捡起宝石": "从脏水池捡宝石——就算有伴侣在身边，你也会想和周围的人调情 😏",
            "不捡": "从脏水池捡宝石——当你的伴侣在身边时，你绝大多数时候只围着Ta转 💕",
        },
    },
    {
        "q": "🪙 在水池旁边还有一个泳池，水面清澈，漂浮着很多钱币，你会？",
        "options": ["捡起钱币", "不捡"],
        "analysis": {
            "捡起钱币": "从清澈泳池捡钱币——当你的伴侣不在身边时，你会和周围的人调情 😉",
            "不捡": "从清澈泳池捡钱币——无论Ta是否在身边，你始终会忠于Ta 💖",
        },
    },
    {
        "q": "📦 你继续往前走出城堡，外面有一座大花园，地上有一个箱子。它的尺寸？",
        "options": ["大", "中", "小"],
        "analysis": {
            "大": "箱子大小代表自负程度——你是一个非常自信的人 😎",
            "中": "箱子大小代表自负程度——你是一个比较自信的人 🙂",
            "小": "箱子大小代表自负程度——你是一个谦虚低调的人 🌾",
        },
    },
    {
        "q": "🧰 这个箱子是什么材料做的？",
        "options": ["硬纸板", "纸", "木头", "金属"],
        "analysis": {
            "硬纸板": "箱子材料代表性格特点——你性格谦虚温和 🌾",
            "纸": "箱子材料代表性格特点——你性格谦虚温和 🌾",
            "木头": "箱子材料代表性格特点——你性格谦虚温和 🌾",
            "金属": "箱子材料代表性格特点——你性格骄傲有主见 🦁",
        },
    },
    {
        "q": "🌉 花园里还有一座桥就在离着箱子的不远处。桥是什么材料造的？",
        "options": ["藤条", "金属", "木头"],
        "analysis": {
            "藤条": "桥的材料代表和朋友的关系——你比较独立，没有特别依赖的朋友 🌿",
            "金属": "桥的材料代表和朋友的关系——你有关系非常亲密的朋友 💪",
            "木头": "桥的材料代表和朋友的关系——你有关系比较亲密的朋友 🤝",
        },
    },
    {
        "q": "🐴 过了这座桥，有一匹马，它是什么颜色？",
        "options": ["白色", "灰色", "褐色", "黑色"],
        "analysis": {
            "白色": "马的颜色代表对另一半的印象——在你心中Ta非常好 ✨",
            "灰色": "马的颜色代表对另一半的印象——在你心中Ta一般般 🙂",
            "褐色": "马的颜色代表对另一半的印象——在你心中Ta一般般 🙂",
            "黑色": "马的颜色代表对另一半的印象——在你心中Ta还有提升空间 🌱",
        },
    },
    {
        "q": "🐎 马正在做什么？",
        "options": ["安静地站着", "吃草", "欢快奔跑"],
        "analysis": {
            "安静地站着": "马的动作代表另一半的个性——Ta是一个很顾家的人 🏡",
            "吃草": "马的动作代表另一半的个性——Ta是一个很顾家的人 🏡",
            "欢快奔跑": "马的动作代表另一半的个性——Ta是一个喜欢在外面玩的人 🎈",
        },
    },
    {
        "q": "🌪️ 突然离马很近的地方刮起了一阵龙卷风。你会怎么做？",
        "options": ["跑去躲在箱子里", "跑去躲在桥下", "骑上马跑走"],
        "analysis": {
            "跑去躲在箱子里": "龙卷风代表生活中的麻烦——遇到麻烦时你会选择自己解决 💪",
            "跑去躲在桥下": "龙卷风代表生活中的麻烦——遇到麻烦时你会找朋友一起解决 🤝",
            "骑上马跑走": "龙卷风代表生活中的麻烦——遇到麻烦时你会和伴侣一起面对 💕",
        },
    },
]

# ---------- 破冰测试页渲染（page_state == 'test'） ----------
if st.session_state.page_state == "test":
    # 破冰页隐藏侧边栏与聊天输入框，内容居中聚焦
    st.markdown("""
    <style>
    section[data-testid="stSidebar"] {display: none !important;}
    [data-testid="stChatInput"] {display: none !important;}
    [data-testid="stBlockContainer"], [data-testid="stAppViewBlockContainer"],
    .block-container, .main .block-container {
        padding-top: 8vh !important; max-width: 620px !important; margin: 0 auto !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # 随机抽5题：题号列表存入 session_state，防止 rerun 后换题
    if st.session_state.test_q_idx is None:
        st.session_state.test_q_idx = random.sample(range(len(FOREST_QUESTIONS)), 5)
    _qs = [FOREST_QUESTIONS[i] for i in st.session_state.test_q_idx]

    st.markdown(
        '<p style="text-align:center; font-size:1.05rem; color:#7B6B8A; '
        'margin-bottom:0.3rem; letter-spacing:0.02em;">'
        '🌲 开启聊天前，来做五道森林微测试吧（仅供趣味破冰）</p>',
        unsafe_allow_html=True,
    )

    # 渲染5道题，每题独立 radio + 独立 key
    _choices = []
    for _i, _q in enumerate(_qs):
        _c = st.radio(_q["q"], _q["options"], key=f"forest_test_choice_{_i}")
        _choices.append(_c)

    # 已提交答案：逐题展示解析 + 进入树洞按钮
    if st.session_state.test_answered:
        st.markdown("---")
        st.markdown("#### 📖 你的森林小报告")
        for _i, (_q, _c) in enumerate(zip(_qs, _choices)):
            st.success(f"{_i+1}. 你的选择：**{_c}**\n\n{_q['analysis'][_c]}")
        st.markdown(
            '<p style="text-align:center; color:#B8A9C9; font-size:0.72rem;">'
            '以上解析仅供趣味参考，不代表任何心理评估结论哦 🐾</p>',
            unsafe_allow_html=True,
        )
        if st.button("🐾 进入树洞", type="primary", use_container_width=True):
            st.session_state.page_state = "chat"
            st.session_state.test_answered = False
            st.session_state.test_q_idx = None
            st.rerun()
    else:
        _c1, _c2 = st.columns(2)
        with _c1:
            if st.button("完成测试并进入", type="primary", use_container_width=True):
                st.session_state.test_answered = True
                st.rerun()
        with _c2:
            if st.button("直接跳过", use_container_width=True):
                st.session_state.page_state = "chat"
                st.session_state.test_q_idx = None
                st.rerun()

    st.stop()  # 破冰页不渲染后续聊天界面

# 聊天页两侧氛围装饰：fixed 贴边 + pointer-events:none 点击穿透，每侧4个控制密度
st.markdown(
    '<div class="chat-deco chat-deco-left"><span>🌿</span><span>🐾</span><span>🌱</span><span>🍃</span></div>'
    '<div class="chat-deco chat-deco-right"><span>🌙</span><span>✨</span><span>⭐</span><span>☁️</span></div>',
    unsafe_allow_html=True,
)

# ==================== 侧边栏 ====================
with st.sidebar:
    # 深夜模式开关（深夜倾诉场景：切换至深紫夜空护眼主题）
    _dark = st.toggle("🌙 深夜模式", key="dark_mode", help="深夜倾诉时切换至护眼暗色主题")
    if _dark:
        st.markdown(_DARK_MODE_CSS, unsafe_allow_html=True)

    # 语音播报开关（AI回复自动朗读，温柔女声陪伴）
    _voice_on = st.toggle("🔊 语音播报", key="voice_enabled", help="开启后AI回复自动朗读出来")
    if not _voice_on:
        voice_stop_component()   # 关闭开关时立即停止当前朗读

    # 用户信息：默认收缩，点开才显示手机号等登录信息（隐私优先，不直接暴露）
    _phone = st.session_state.phone_num
    _masked_phone = _phone[:3] + "****" + _phone[-4:] if len(_phone) == 11 else "****"
    with st.popover("👤 用户信息 · 点击展开", use_container_width=True):
        st.markdown(
            '<div style="text-align:center; color:#8E7CA8; font-size:0.75rem; '
            'margin-bottom:0.5rem;">🔒 以下信息仅你可见</div>',
            unsafe_allow_html=True,
        )
        st.markdown(f"**📱 手机号**:{_masked_phone}")
        st.markdown(f"**🐱 匿名昵称**:{get_nickname()}")
        st.markdown(f"**🔒 会话编号**:`{get_session_id()}`")
        st.markdown("**✅ 登录状态**:已登录" if not st.session_state.is_guest else "**🐾 登录状态**:游客模式")
    st.markdown("---")

    # 顶部标题
    st.markdown(
        '<div style="text-align:center; margin-bottom:12px;">'
        '<span style="font-size:1.3rem; font-weight:700; color:#6C5B7B;">🐱 你的专属树洞猫咪</span>'
        '</div>',
        unsafe_allow_html=True
    )

    # 猫咪头像图片（居中展示）
    st.image(CAT_AVATAR, width=200)

    # 今日猫咪语录：按日期随机轮换，同一天看到同一句（稳定感），每天换新（新鲜感）
    _today = datetime.now().strftime("%Y%m%d")
    _quotes = [
        "你不需要一直坚强，偶尔脆弱也没关系，猫咪接得住你 🐾",
        "今天也辛苦啦，不管做了多少事，你都很棒了 ✨",
        "情绪没有对错，你感受到的，都是真实的、值得被重视的 🫂",
        "慢慢来，比较快。允许自己按自己的节奏成长 🌱",
        "被误解也没关系，懂你的人终会出现，猫咪一直懂你 🐱",
        "你比想象中更勇敢，毕竟你已经走过了那么多难关 💪",
        "休息不是偷懒，是为了走更远的路。歇歇吧 🌙",
        "世界很吵，但在这里，你只需要做自己就好 🍃",
    ]
    random.seed(int(_today))
    _today_quote = random.choice(_quotes)
    st.markdown(
        f'<div class="side-quote">'
        f'<div class="quote-label">🐾 今日猫咪语录</div>'
        f'{_today_quote}</div>',
        unsafe_allow_html=True,
    )

    # 免责声明（醒目黄色警示框，合规必备）
    st.warning(
        "⚠️ **声明**：本应用为 AI 助手，旨在提供情绪缓冲与陪伴，"
        "**不能替代专业心理咨询**。如遇严重心理危机，请务必联系专业医生"
        "或拨打 24 小时心理援助热线：**400-161-9995**。"
    )

    # 联网词库状态：只读 session_state 中最近一次拉取结果，不触发API请求（避免阻塞页面进入）
    # 首次进入时显示"待命同步"，用户发第一条消息后自动拉取并更新
    live_high = st.session_state.get("live_kw_high", [])
    live_ambiguous = st.session_state.get("live_kw_ambiguous", [])
    if live_high or live_ambiguous:
        st.success(
            f"🌐 **危机词库已联网更新**\n\n"
            f"本次同步新增高危词 {len(live_high)} 个、歧义词 {len(live_ambiguous)} 个，"
            f"每小时自动拉取最新网络黑话。"
        )
    else:
        st.info("🌐 危机词库：正在待命同步，当前使用本地内置词库（发送消息后自动拉取最新网络黑话）。")

    # 情绪资料库：常见情绪的应对小贴士
    with st.expander("📚 情绪小贴士"):
        st.markdown(
            "**😢 难过/低落**\n"
            "允许自己难过一会儿，不必急着好起来。可以抱抱玩偶、听一首温柔的歌，"
            "或者把感受写下来。\n\n"
            "**😰 焦虑/紧张**\n"
            "试试4-7-8呼吸法：吸气4秒，屏住7秒，呼气8秒。"
            "把担心写下来，事情往往没想象中那么糟。\n\n"
            "**😠 愤怒/烦躁**\n"
            "愤怒是在保护你的边界。先离开现场，喝口水、深呼吸，"
            "等情绪退潮了再处理事情。\n\n"
            "**🥺 委屈/孤独**\n"
            "你的感受是真实的，值得被看见。找个信任的人说说，"
            "或者来这里跟猫咪倾诉。\n\n"
            "**😶 迷茫/无力**\n"
            "迷茫说明你在认真思考。不用一次想清楚所有事，"
            "先做一件最小的事，比如出门走走。"
        )

    # 紧急求助通道：常驻侧边栏，危机时刻一键可见（与免责声明互补，更醒目）
    st.markdown(
        '<div class="side-emergency">'
        '<div class="emg-title">🆘 紧急求助通道</div>'
        '全国24小时心理援助热线<br>'
        '<span class="emg-phone">400-161-9995</span><br>'
        '北京心理危机研究与干预中心<br>'
        '<span class="emg-phone">010-82951332</span><br>'
        '生命热线（希望24）<br>'
        '<span class="emg-phone">400-161-9995</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    # 今日温柔小任务：每天一个小行动，鼓励用户迈出微小一步
    _tasks = [
        "给今天的自己打个分，哪怕只有 1 分也是存在过的证明",
        "喝一杯温水，感受它流过喉咙的温度",
        "抬头看看天空，不管是蓝天、乌云还是星星",
        "对镜子里的自己说一句：辛苦了",
        "深呼吸三次，吸气 4 秒，呼气 6 秒",
        "摸一摸身边柔软的东西，感受它的触感",
        "写下三件今天发生的小事，不分好坏",
        "伸个懒腰，把身体绷紧再完全放松",
    ]
    random.seed(int(_today) + 7)
    _today_task = random.choice(_tasks)
    st.markdown(
        f'<div class="side-task">'
        f'<div class="task-label">🌱 今日温柔小任务</div>'
        f'{_today_task}</div>',
        unsafe_allow_html=True,
    )

    # 底部清空对话按钮
    if st.button("清空情绪，重新开始", use_container_width=True):
        st.session_state.messages = [{"role": "assistant", "content": GREETING}]
        st.rerun()

    # 退出登录按钮：清空登录状态回到登录页
    if st.button("🚪 退出登录", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.phone_num = ""
        st.session_state.is_guest = False
        st.session_state.captcha_ans = None
        st.session_state.captcha_verified = False
        st.session_state.captcha_phone = ""
        st.session_state.captcha_simulated = False
        st.session_state.page_state = "login"
        st.session_state.test_q_idx = None
        st.session_state.test_answered = False
        st.session_state.voice_spoken_idx = -1   # 重置播报索引，防止重新登录后朗读旧消息
        st.rerun()

    # 管理员登录入口已移至主界面右上角（st.popover），侧边栏不再显示

# ==================== 情绪快捷按钮（省赛核心亮点·动态推荐版） ====================
# 很多有情绪困扰的用户面对输入框会大脑空白，快捷按钮帮他们迈出第一步。
# 亮点：根据用户最近一条消息的情绪标签，动态推荐最贴合当前心境的按钮。
# 点击后直接展示预设的温暖回复（不走API，秒回+质量可控），后续对话仍走正常流程。
QUICK_REPLIES = [
    # --- 情绪匹配型按钮（emotions 非空，命中用户情绪时优先展示） ---
    {"label": "😔 今天好累啊", "emotions": ["疲惫", "无力", "低落"],
     "reply": (
         "辛苦啦，快把身上的重担先放下来歇歇吧。"
         "今天是不是发生了很多事？不想说也没关系哦，"
         "猫咪就在这里，安安静静地陪着你~🐾")},
    {"label": "🥺 突然好想哭", "emotions": ["难过", "伤心", "悲伤", "失落"],
     "reply": (
         "那就哭出来吧，憋在心里太难受啦。"
         "眼泪是身体在帮你排毒呢，猫咪给你递纸巾，"
         "会一直在这里陪着你~🫂")},
    {"label": "😰 好焦虑好紧张", "emotions": ["焦虑", "紧张", "担忧", "害怕", "恐惧", "压力"],
     "reply": (
         "先慢慢深呼吸一下，吸气~呼气~猫咪陪着你呢。"
         "焦虑是因为你在乎这件事呀，这很正常。"
         "愿意跟猫咪说说，是什么事让你这么紧张吗？我们可以一起想办法~")},
    {"label": "😠 好烦好气啊", "emotions": ["愤怒", "生气", "烦躁", "不满"],
     "reply": (
         "气坏了吧！来来来，猫咪让你揉揉尾巴出出气~"
         "生气说明有人踩到了你的底线，你的感受完全合理。"
         "先喝口水冷静一下，然后跟猫咪说说谁惹你啦？")},
    {"label": "🥺 我觉得好委屈", "emotions": ["委屈", "无奈"],
     "reply": (
         "抱抱你，受了委屈心里最堵了。"
         "你一定很难受吧，明明不是你的错却要自己扛。"
         "猫咪全都看在眼里呢，慢慢说，我认真听着~🫂")},
    {"label": "😶 感觉有点迷茫", "emotions": ["迷茫"],
     "reply": (
         "迷茫也没关系的，这说明你在成长，在思考未来的路呀。"
         "不如先说说，最近最让你感到困惑的一件事是什么？"
         "我们一起慢慢理一理~✨")},
    {"label": "💔 感觉没人懂我", "emotions": ["孤独"],
     "reply": (
         "那种周围很吵、心里却很空的感觉，真的很不好受。"
         "但是你看，你现在说出来了，猫咪就懂你呀。"
         "你不需要讨好所有人，在这里做真实的自己就好~")},
    {"label": "😞 对自己好失望", "emotions": ["愧疚", "自责"],
     "reply": (
         "别对自己这么严厉嘛，你已经很努力了呀。"
         "换做是朋友遇到同样的事，你会怪他吗？肯定不会吧。"
         "那就也对自己温柔一点，跟猫咪说说发生了什么？")},
    # --- 通用型按钮（emotions 为空，作为默认/补充展示） ---
    {"label": "😴 晚上睡不着", "emotions": [],
     "reply": (
         "睡不着的时候脑子总是转个不停对不对？"
         "试试把烦心事都交给猫咪保管，今晚你只负责休息。"
         "猫咪给你唱摇篮曲，轻轻地~喵~喵~🌙")},
    {"label": "📚 考试压力好大", "emotions": [],
     "reply": (
         "备考的日子真的好熬人，心疼你呀。"
         "不过你知道吗，能坚持到现在的你已经超棒了！"
         "累了就歇会儿，猫咪陪你制定一个小小的复习计划好不好？")},
    {"label": "💭 不知道说什么", "emotions": [],
     "reply": (
         "嘿嘿，那就什么都不说也没关系呀。"
         "我们可以在树洞里听听风声、看看云朵。"
         "或者，猫咪给你讲个今天发生的趣事？🐱")},
]

# 始终展示的兜底按钮（无论什么情绪都保留）
_ALWAYS_SHOW = "💭 不知道说什么"
# 每次最多展示的按钮数
_QUICK_BTN_COUNT = 4


def pick_quick_replies():
    """根据用户最近一条消息的情绪，动态挑选最合适的快捷按钮

    逻辑：
      1. 找到最近一条用户消息的情绪标签
      2. 优先展示匹配该情绪的按钮（最多3个）
      3. "不知道说什么"始终保留
      4. 不足4个时按顺序从通用按钮补齐
    """
    # 找最近一条用户消息的情绪
    last_emotion = ""
    for msg in reversed(st.session_state.messages):
        if msg["role"] == "user" and msg.get("emotion"):
            last_emotion = msg["emotion"]
            break
    # 匹配当前情绪的按钮优先
    matched = [q for q in QUICK_REPLIES if last_emotion in q["emotions"]]
    # 通用按钮（兜底）
    general = [q for q in QUICK_REPLIES if not q["emotions"]]
    # 组装：匹配的 + 始终展示的 + 通用补齐 + 全库兜底
    picked = matched[:_QUICK_BTN_COUNT - 1]  # 留1个位置给兜底按钮
    always = next(q for q in QUICK_REPLIES if q["label"] == _ALWAYS_SHOW)
    if always not in picked:
        picked.append(always)
    # 不足则从通用按钮补齐，仍不足则从全库补齐（保证始终有4个按钮）
    for pool in (general, QUICK_REPLIES):
        for q in pool:
            if len(picked) >= _QUICK_BTN_COUNT:
                break
            if q not in picked:
                picked.append(q)
        if len(picked) >= _QUICK_BTN_COUNT:
            break
    return picked[:_QUICK_BTN_COUNT]

# ==================== 主页面 ====================

# 主标题区:心理陪伴主题首屏氛围
# (🌙 浅灰副标题 → 🐾 渐变主标题 → 浅蓝→透明极细分隔线 → 对话人 → 🌱 情绪标签)
st.markdown(
    "<p style='text-align: center; color: #A8A8B3; font-size: 0.85rem; "
    "margin: 0 0 0.3rem 0; letter-spacing: 0.12em;'>🌙 无论多晚，树洞都在这里等你</p>",
    unsafe_allow_html=True
)
st.markdown(
    "<h1 style='text-align: center; margin: 0; font-weight: 700; "
    "background: linear-gradient(90deg, #6C5B7B, #C77DA5); "
    "-webkit-background-clip: text; background-clip: text; "
    "-webkit-text-fill-color: transparent;'>🐾 树洞猫咪：你的专属情绪倾听者</h1>",
    unsafe_allow_html=True
)
st.markdown(
    "<div style='height: 1px; margin: 0.6rem auto 0.4rem auto; max-width: 420px; "
    "background: linear-gradient(to right, #B8D4E3, transparent);'></div>",
    unsafe_allow_html=True
)
# 用户信息入口：手机号默认收缩，点开查看手机号等登录信息（隐私优先）
_, _user_col, _ = st.columns([1, 0.5, 1])
with _user_col:
    _phone = st.session_state.phone_num
    _masked_phone = _phone[:3] + "****" + _phone[-4:] if len(_phone) == 11 else "****"
    with st.popover("👤 用户信息", use_container_width=True):
        st.markdown(
            '<div style="text-align:center; color:#8E7CA8; font-size:0.75rem; '
            'margin-bottom:0.5rem;">🔒 以下信息仅你可见</div>',
            unsafe_allow_html=True,
        )
        st.markdown(f"**📱 手机号**:{_masked_phone}")
        st.markdown(f"**🐱 匿名昵称**:{get_nickname()}")
        st.markdown(f"**🔒 会话编号**:`{get_session_id()}`")
        st.markdown("**✅ 登录状态**:已登录" if not st.session_state.is_guest else "**🐾 登录状态**:游客模式")
# 开场白气泡上方的淡色情绪标签(心理陪伴氛围)
st.markdown(
    "<p style='text-align: center; color: #9BB5A8; font-size: 0.75rem; "
    "margin: 0.5rem 0 0.3rem 0;'>🌱 情绪安全区 | 绝对保密</p>",
    unsafe_allow_html=True
)
# 隐私承诺提示（情绪类产品用户最在意隐私，常驻可见更安心）
st.markdown(
    "<p style='text-align: center; color: #A8C4A8; font-size: 0.72rem; "
    "margin: 0 0 0.5rem 0; opacity: 0.9;'>"
    "✅ 所有倾诉内容仅本次会话有效，关闭页面自动清空，不上传持久存储</p>",
    unsafe_allow_html=True
)



# 初始化对话历史（无记录则猫咪先发开场白）
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": GREETING}]

# 循环渲染历史消息
for message in st.session_state.messages:
    avatar = CAT_AVATAR if message["role"] == "assistant" else USER_AVATAR
    with st.chat_message(message["role"], avatar=avatar):
        # 用户消息：在内容上方显示情绪小标签
        if message["role"] == "user" and message.get("emotion"):
            emoji = EMOTION_EMOJI.get(message["emotion"], "💭")
            st.markdown(
                f"<span style='display:inline-block; background:#F0E6F6; "
                f"color:#6C5B7B; font-size:0.75rem; padding:2px 10px; "
                f"border-radius:10px; margin-bottom:6px;'>{emoji} {message['emotion']}</span>",
                unsafe_allow_html=True,
            )
        st.markdown(message["content"])

# 语音播报：检测到新AI回复且开关开启时自动朗读（只播最新一条，不重复播报）
if st.session_state.voice_enabled and st.session_state.messages:
    _last_idx = len(st.session_state.messages) - 1
    _last_msg = st.session_state.messages[-1]
    if _last_msg["role"] == "assistant" and st.session_state.voice_spoken_idx != _last_idx:
        st.session_state.voice_spoken_idx = _last_idx
        voice_output_component(_last_msg["content"])

# 危机后自愿联系区域：危机触发后让学生自愿决定是否被联系（数据隔离，仅存联系方式）
if st.session_state.get("contact_submitted"):
    st.success("💌 已经收到啦，老师会尽快联系你。猫咪一直在这里陪着你~🐾")
elif st.session_state.get("crisis_active"):
    # 刚触发高危预警时，在表单上方显示红色警示条（仅本次显示，避免重复刷屏）
    if st.session_state.get("crisis_just_triggered"):
        st.error("🚨 触发高危预警！已强制中断对话，并通知辅导员。")
        st.error("请立刻拨打 24 小时心理援助热线：400-161-9995")
        st.session_state.crisis_just_triggered = False
    with st.container(border=True):
        st.markdown("💌 **如果你愿意，可以让老师联系你**（完全自愿，随时可以拒绝）")
        contact = st.text_input("联系方式（手机号 / QQ / 微信均可）", key="crisis_contact_input")
        c_col1, c_col2 = st.columns(2)
        with c_col1:
            if st.button("提交联系方式", use_container_width=True, type="primary"):
                if contact.strip():
                    update_alert_contact(
                        get_session_id(), contact.strip(),
                        student_id=None,
                        student_phone=contact.strip() if contact.strip().isdigit() else None,
                    )
                    st.session_state.crisis_active = False
                    st.session_state.contact_submitted = True
                    st.rerun()
                else:
                    st.warning("请先填写联系方式哦~")
        with c_col2:
            if st.button("暂时不用了", use_container_width=True):
                st.session_state.crisis_active = False
                st.rerun()
else:
    # 情绪快捷按钮行：放在输入框正上方，根据用户当前心境动态推荐
    picked_quick = pick_quick_replies()
    if last_emotion_hint := next((m.get("emotion", "") for m in reversed(st.session_state.messages) if m["role"] == "user" and m.get("emotion")), ""):
        hint_text = f"猫咪感觉到你有些{last_emotion_hint}，也许这些能帮到你~"
    else:
        hint_text = "不知道说什么？点一下就好~"
    st.markdown(f"<p style='text-align:center; color:#A89BB8; font-size:0.8rem; margin:0.3rem 0 0.2rem;'>{hint_text}</p>", unsafe_allow_html=True)
    quick_cols = st.columns(len(picked_quick))
    for col, q in zip(quick_cols, picked_quick):
        with col:
            if st.button(q["label"], use_container_width=True, key=f"quick_{q['label']}"):
                # 点击快捷按钮：把文案作为用户消息（带情绪标签，供下轮动态推荐）、预设回复作为猫咪消息
                btn_emotion = q["emotions"][0] if q["emotions"] else ""
                st.session_state.messages.append({"role": "user", "content": q["label"], "emotion": btn_emotion})
                st.session_state.messages.append({"role": "assistant", "content": q["reply"]})
                st.rerun()

# 语音输入按钮（浏览器原生语音识别，点击说话自动填入输入框）
voice_input_component()

# 接收用户输入
if prompt := st.chat_input("跟我说点什么吧..."):
    # 提速：风控与情绪检测均已本地化（纯内存关键词匹配，微秒级），
    # 无需线程池并行，直接顺序调用，省掉线程创建与调度开销
    level = detect_crisis_level(prompt)
    emotion = detect_emotion(prompt)

    # 三级快速分流（核心提速逻辑，确保大模型复核只在必要时触发）：
    #   level==2 高危词直接命中 → 立即拦截，绝不调大模型
    #   level==1 歧义词命中     → 唯一需要调大模型复核的场景
    #   level==0 无敏感词       → 直接进入聊天，零额外API调用
    if level == 2:
        is_crisis = True
    elif level == 1:
        is_crisis = llm_confirm_crisis(prompt)
    else:
        is_crisis = False
    if is_crisis:
        # 【脱敏预警简报】提取触发词，只记录时间/触发词/脱敏手机号/风险等级，不含聊天原文（数据隔离）
        cleaned_log = prompt
        for safe in SAFE_PATTERNS:
            cleaned_log = cleaned_log.replace(safe, "")
        lowered_log = cleaned_log.lower()
        live_h, live_a = fetch_live_crisis_keywords()  # 已缓存，不会重复请求
        combined_high = HIGH_RISK_KEYWORDS + [w for w in live_h if w not in HIGH_RISK_KEYWORDS]
        combined_amb = AMBIGUOUS_KEYWORDS + [w for w in live_a if w not in AMBIGUOUS_KEYWORDS]
        hit_word = next((kw for kw in combined_high + combined_amb if kw in lowered_log), prompt[:15])
        _masked = f"用户尾号{st.session_state.phone_num[-4:]}" if st.session_state.phone_num else "匿名用户"
        alert_brief = {
            "学生": _masked,
            "风险": "高危",
            "时间": "刚刚",
            "触发词": hit_word,
        }
        print(f"[脱敏预警简报] {alert_brief}")  # 后台打印（不含聊天原文）
        st.session_state.alert_logs.append(alert_brief)

        # 持久化匿名预警到 alerts.json（只存脱敏标识/会话编号/时间/触发词，绝不存对话原文）
        save_alert({
            "session_id": get_session_id(),
            "nickname": _masked,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "risk_level": "高危",
            "trigger_word": hit_word,
            "contact_left": False,
        })

        # 消息入历史（rerun 后由聊天历史循环统一渲染，无需在此重复渲染）
        st.session_state.messages.append({"role": "user", "content": prompt, "emotion": ""})
        st.session_state.messages.append({"role": "assistant", "content": CRISIS_REPLY})
        st.session_state.crisis_active = True  # 标记危机状态，主页面据此显示自愿联系表单
        st.session_state.crisis_just_triggered = True  # 标记刚触发，供表单区显示红色警示条
        st.rerun()  # 立即重跑：联系表单当场弹出，无需等下一次交互

    # 未命中：重置危机状态，恢复正常聊天
    st.session_state.crisis_active = False
    st.session_state.contact_submitted = False
    with st.chat_message("user", avatar=USER_AVATAR):
        if emotion:
            emoji = EMOTION_EMOJI.get(emotion, "💭")
            st.markdown(
                f"<span style='display:inline-block; background:#F0E6F6; "
                f"color:#6C5B7B; font-size:0.75rem; padding:2px 10px; "
                f"border-radius:10px; margin-bottom:6px;'>{emoji} {emotion}</span>",
                unsafe_allow_html=True,
            )
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt, "emotion": emotion})

    # 构造传给大模型的消息列表（system 提示词 + 最近 MAX_HISTORY 条历史）
    messages_for_api = (
        [{"role": "system", "content": SYSTEM_PROMPT}]
        + st.session_state.messages[-MAX_HISTORY:]
    )

    # 流式输出大模型回复（异常时猫咪温柔兜底，不暴露报错堆栈）
    with st.chat_message("assistant", avatar=CAT_AVATAR):
        try:
            stream = client.chat.completions.create(
                model="glm-4-flash",
                messages=messages_for_api,
                stream=True,
                temperature=0.85,  # 适度提高随机性，让回复更像真人、不那么僵硬
                max_tokens=300,  # 提速：限制回复长度，避免长篇大论拖慢首字输出与整体响应
            )
            response = st.write_stream(stream)
        except Exception:
            response = "喵…猫咪的信号好像不太好，稍等一下再试试好吗？🐾"
            st.markdown(response)

    # 保存助手回复到对话历史
    st.session_state.messages.append({"role": "assistant", "content": response})
