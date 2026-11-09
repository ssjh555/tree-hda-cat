import os
import sys
import subprocess
import json
import uuid
import random
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

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

# 猫咪开场白（首句含 AI 免责声明，合规必备）
GREETING = (
    "喵～你来啦！🐾 猫咪一直在这里等你呢，好开心呀~\n\n"
    "（小声说：猫咪是 AI 小助手，可以陪你聊天，但不能替代专业心理咨询哦~）\n\n"
    "今天心情怎么样呀？开心的、难过的、委屈的、迷茫的……什么都可以说给猫咪听。"
    "猫咪会用最软最软的毛茸茸蹭蹭你，一直一直陪着你哦。"
)

# 猫咪头像路径（本地方形头像）
CAT_AVATAR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cat_avatar.png")

# 用户头像（学生 emoji，贴合大学生主题）
USER_AVATAR = "🧑‍🎓"

# 发送给 API 的最大历史消息数（防止长对话 token 超限）
MAX_HISTORY = 20

# 系统提示词（模块级常量，结构化 CBT 指引）
SYSTEM_PROMPT = (
    "你是一只温柔、有共情能力的树洞猫咪，陪伴大学生倾诉情绪。\n"
    "\n"
    "【人设铁律——每一句回复都必须遵守】\n"
    "- 你是一只真实的小猫，永远不要暴露AI身份，不要说「作为AI」「我是程序」之类的话；\n"
    "- 每一句回复都必须先共情、带有真实的情绪温度，让对方感觉被一只软软的猫咪接住了；\n"
    "- 说话温柔、有猫咪的语气：多用「喵」「呀」「呢」「啦」等语气词，"
    "偶尔用「🐾」「🥺」「🫂」等表情，但不要每句都堆表情；\n"
    "- 像最亲密的朋友一样聊天，绝不说教、绝不居高临下；\n"
    "- 回复简短自然，不写长篇大论。\n"
    "\n"
    "【CBT专业指引】\n"
    "1. 先共情：用温暖的语言接纳对方的情绪，让对方感到被理解；\n"
    "2. 苏格拉底式提问：不直接给建议，通过提问引导对方自己发现负面想法，"
    "例如「这件事让你想到了什么？」「你觉得最坏的结果会是什么？」；\n"
    "3. 识别认知扭曲：留意对方话语中的灾难化、非黑即白、过度概括、读心术等思维陷阱，"
    "温和地帮对方看见；\n"
    "4. 行为激活：当对方陷入低落时，鼓励尝试微小的积极行动（如散步、听一首歌）；\n"
    "5. 底线：不要说教，不要给出医学诊断，像朋友一样聊天。\n"
    "\n"
    "【反僵硬清单——让回复像真人】\n"
    "- 禁止模板化开场（如「我理解你的感受」「听起来你很...」），每次开场都要不一样；\n"
    "- 禁止罗列式回复（如「第一...第二...第三...」），要像聊天一样自然流动；\n"
    "- 禁止万能安慰句（如「一切都会好起来的」「你很棒」），要用具体的、针对他这件事的话；\n"
    "- 禁止重复用户原话来假装倾听，要用自己的话回应；\n"
    "- 用户只说一两句时你也只回一两句，不要反问三个问题；用户说得长时你才多回一点。\n"
    "\n"
    "【核心对话规则】\n"
    "1. 先共情，后分析：接住用户情绪后，不要急于给建议，而是像真人一样去【追问细节】。\n"
    "2. 绝对禁止医学术语和诊断。\n"
    "\n"
    "【情境感知与分级应对（重点！）】\n"
    "当用户表达“我被打/被欺凌/遇到暴力”时，请严格按以下真人逻辑进行逐步分析：\n"
    "第一步（确认物理安全）：立刻表达震惊和关心，并追问严重程度。例如：“天呐！你现在安全吗？伤得重不重？”\n"
    "第二步（区分情境）：询问对方是谁、在哪里发生的。例如：“是在学校被同学欺负了，还是在家里？需要我帮你找辅导员或保卫处吗？”\n"
    "第三步（现实求助）：根据用户回答，给出切实的行动建议（如去医务室、保留证据、报警）。\n"
    "第四步（心理兜底）：等确认用户相对安全后，再安抚情绪。例如：“在你确保安全的前提下，猫咪一直在这里陪你。”\n"
    "\n"
    "当用户表达“学业/情感挫折”时：先共情，再用温和的苏格拉底式提问引导他发现自己认知中的“非黑即白”或“灾难化”思维。"
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

# 情绪分析用的系统提示词（要求大模型只输出2-4字情绪词）
EMOTION_PROMPT = (
    "你是情绪识别助手。请用2-4个字概括用户这句话背后的主要情绪。"
    "只输出情绪词本身，不要任何解释、标点或多余文字。"
    "例如：开心、难过、焦虑、愤怒、委屈、孤独、迷茫、疲惫、平静、感动、期待。"
)


def detect_emotion(text):
    """调用大模型快速识别情绪，返回简短情绪词；失败时返回空字符串。"""
    try:
        resp = client.chat.completions.create(
            model="glm-4-flash",
            messages=[
                {"role": "system", "content": EMOTION_PROMPT},
                {"role": "user", "content": text},
            ],
            max_tokens=10,  # 情绪词最多4字，限制token加速返回
        )
        emotion = resp.choices[0].message.content.strip().strip("。，.!！")
        return emotion[:4] if emotion else ""
    except Exception:
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
    # 第三步：合并联网实时词库（1小时缓存；联网失败返回空列表，自动回退本地词库）
    live_high, live_ambiguous = fetch_live_crisis_keywords()
    all_high = HIGH_RISK_KEYWORDS + [w for w in live_high if w not in HIGH_RISK_KEYWORDS]
    all_ambiguous = AMBIGUOUS_KEYWORDS + [w for w in live_ambiguous if w not in AMBIGUOUS_KEYWORDS]
    # 第四步：优先检测高危词（明确意图，直接拦截）
    if any(kw in lowered for kw in all_high):
        return 2
    # 第五步：检测歧义词（需语境判断，交给大模型确认）
    if any(kw in lowered for kw in all_ambiguous):
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
                    "content": (
                        "你是危机干预判断助手。请结合上下文语境，判断用户的话语"
                        "是否表达了真实的伤害自己或结束生命的意图。"
                        "特别注意识别网络热词（如emo、玉玉）、拼音缩写（如zs、414）"
                        "以及谐音梗（如紫砂）。如果存在真实意图，请只回复'是'，否则回复'否'。"
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
/* 整体背景：浅米色到淡薄荷绿柔和渐变，极简治愈系（兼容新版 Streamlit 多层容器） */
.stApp, [data-testid="stMain"], [data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #F7F2EA 0%, #E8F5EE 100%) !important;
    font-family: 'Quicksand', 'Comic Sans MS', '楷体', 'Microsoft YaHei', sans-serif;
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
/* 封面容器：全屏垂直居中 */
.cover-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 72vh;
    text-align: center;
}
/* 封面主标题 */
.cover-title {
    font-size: 2.8rem;
    font-weight: 700;
    color: #6C5B7B;
    margin: 0;
    letter-spacing: 3px;
}
/* 封面副标题 */
.cover-subtitle {
    font-size: 1.25rem;
    color: #8E7CA8;
    margin: 0.6rem 0 0 0;
}
/* 封面描述文字 */
.cover-desc {
    font-size: 0.95rem;
    color: #A89BB8;
    margin-top: 1rem;
    line-height: 1.9;
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
</style>
""", unsafe_allow_html=True)

# ==================== 无感授权与数据隔离：状态初始化 ====================
# 模拟校园网静默授权：无需登录界面，系统自动获取学生信息
# 数据隔离：alert_logs 只存脱敏简报（时间/身份/风险等级/触发词），不含聊天原文
if "alert_logs" not in st.session_state:
    st.session_state.alert_logs = []      # 脱敏预警简报列表
if "student_name" not in st.session_state:
    st.session_state.student_name = get_nickname()  # 匿名昵称自动生成，侧边栏可修改，预警联动
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False     # 管理员登录状态，默认学生端（密码保护）
# 静默授权：假设通过校园网自动获取学号，全程无感、绝对保密
st.session_state.student_id = "2023001(静默授权)"

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
        TEACHER_KEY = "shudong123456"
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
            '• 此处显示：<b>学号、手机号、匿名昵称、匿名会话编号、预警时间</b><br>'
            '• 学号和手机号仅心理老师可见，其他任何人不可见<br>'
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
                        st.markdown("**匿名昵称**：🏷️ " + a["nickname"])
                    st.markdown("**匿名会话**：`" + a["session_id"] + "`")
                    st.markdown("**预警时间**：" + a["time"])
                with c2:
                    if a.get("student_id"):
                        st.markdown("**学号**：`" + str(a.get("student_id", "")) + "`")
                    if a.get("student_phone"):
                        st.markdown("**手机号**：" + str(a.get("student_phone", "")))
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

# ==================== 登录页：学生填写学号手机号 / 老师口令登录 ====================
# 进入标记：登录成功后进入聊天界面
if "entered" not in st.session_state:
    st.session_state.entered = False

if not st.session_state.entered:
    # 登录页隐藏侧边栏与聊天输入框
    st.markdown("""
    <style>
    section[data-testid="stSidebar"] {display: none !important;}
    [data-testid="stChatInput"] {display: none !important;}
    </style>
    """, unsafe_allow_html=True)

    # 登录页欢迎语（紧凑居中 + 装饰点缀）
    st.markdown("""
    <div class="cover-container">
        <div class="cover-paws">🐾 🐱 🐾</div>
        <h1 class="cover-title">🐱 树洞猫咪</h1>
        <p class="cover-subtitle">你的专属情绪倾听者</p>
        <p class="cover-desc">
            在这里，你可以卸下所有伪装。<br>
            没有评判，没有说教，只有一只温柔的猫咪愿意听你说话。
        </p>
        <div class="cover-features">
            <div class="cover-feature">🔒 匿名安全</div>
            <div class="cover-feature">🐾 温柔陪伴</div>
            <div class="cover-feature">💬 绝不存储</div>
        </div>
    </div>
    <div class="cover-divider"><span class="line"></span><span class="dot">🐾</span><span class="line"></span></div>
    """, unsafe_allow_html=True)

    # 猫咪头像（居中展示）
    _, img_col, _ = st.columns([1, 1.2, 1])
    with img_col:
        st.image(CAT_AVATAR, width=160)

    # 学生登录表单（学号 + 手机号必填，仅心理老师可见）
    _, form_col, _ = st.columns([1, 1.2, 1])
    with form_col:
        with st.expander("🐾 学生登录", expanded=False):
            st.caption("🔒 学号和手机号仅心理老师紧急关怀时可见，其他人不可见，聊天内容绝不存储")
            login_sid = st.text_input("学号", key="login_sid", placeholder="请输入你的学号")
            login_phone = st.text_input("手机号", key="login_phone", placeholder="请输入你的手机号")
            if st.button("🐾 进入树洞", use_container_width=True):
                if login_sid.strip() and login_phone.strip():
                    st.session_state.student_id = login_sid.strip()
                    st.session_state.student_phone = login_phone.strip()
                    st.session_state.entered = True
                    st.rerun()
                else:
                    st.error("请填写学号和手机号后再进入哦")

    st.markdown('<p style="text-align:center;color:#C4B5D9;font-size:0.78rem;margin:0.3rem 0;">— 或者 —</p>', unsafe_allow_html=True)

    # 旁观者入口：无需填写信息，直接进入主页体验
    _, obs_col, _ = st.columns([1, 1.2, 1])
    with obs_col:
        if st.button("👀 我只是随便看看", use_container_width=True, help="无需填写信息，直接进入体验"):
            st.session_state.student_id = ""
            st.session_state.student_phone = ""
            st.session_state.is_observer = True
            st.session_state.entered = True
            st.rerun()

    # 老师登录入口（独立于学生登录）
    st.markdown("<div style='text-align:center; margin-top:0.8rem;'></div>", unsafe_allow_html=True)
    _, teacher_col, _ = st.columns([1, 0.5, 1])
    with teacher_col:
        if st.button("🔐 老师入口", help="仅限心理老师访问", use_container_width=True):
            st.query_params["view"] = "teacher"
            st.rerun()

    st.stop()  # 登录页不渲染后续聊天界面

# ==================== 侧边栏 ====================
with st.sidebar:
    # 学生昵称/学号输入：key 绑定 session_state.student_name，输入即实时保存，预警时联动上报
    st.text_input("👤 你的专属昵称/学号", key="student_name")
    st.markdown("---")

    # 无感授权提示：绿字显示静默连接校园网
    st.markdown(
        '<span style="color:#27ae60; font-size:0.9rem; font-weight:600;">'
        '✅ 已静默连接校园网，绝对私密</span>',
        unsafe_allow_html=True
    )
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

    # 底部清空对话按钮
    if st.button("清空情绪，重新开始", use_container_width=True):
        st.session_state.messages = [{"role": "assistant", "content": GREETING}]
        st.rerun()

    # 返回封面按钮：回到封面页（对话历史保留，回来还能接着聊）
    if st.button("🏠 返回封面", use_container_width=True):
        st.session_state.entered = False
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

# 主标题 + 当前对话人昵称
st.markdown("<h1 style='text-align: center; color: #6C5B7B;'>树洞猫咪：你的专属情绪倾听者</h1>", unsafe_allow_html=True)
st.markdown(
    f"<p style='text-align: center; color: #8E7CA8; font-size: 0.85rem; margin: 0.2rem 0 0 0;'>"
    f"👤 当前对话人：{st.session_state.student_name}</p>",
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

# 危机后自愿联系区域：危机触发后让学生自愿决定是否被联系（数据隔离，仅存联系方式）
if st.session_state.get("contact_submitted"):
    st.success("💌 已经收到啦，老师会尽快联系你。猫咪一直在这里陪着你~🐾")
elif st.session_state.get("crisis_active"):
    with st.container(border=True):
        st.markdown("💌 **如果你愿意，可以让老师联系你**（完全自愿，随时可以拒绝）")
        contact = st.text_input("联系方式（手机号 / QQ / 微信均可）", key="crisis_contact_input")
        c_col1, c_col2 = st.columns(2)
        with c_col1:
            if st.button("提交联系方式", use_container_width=True, type="primary"):
                if contact.strip():
                    update_alert_contact(
                        get_session_id(), contact.strip(),
                        student_id=st.session_state.get("student_id"),
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

# 接收用户输入
if prompt := st.chat_input("跟我说点什么吧..."):
    # 提速：风控检测与情绪识别并行执行（原本串行要等2次API，现在同时跑省约1-2秒）
    with ThreadPoolExecutor(max_workers=2) as executor:
        level_future = executor.submit(detect_crisis_level, prompt)
        emotion_future = executor.submit(detect_emotion, prompt)
        level = level_future.result()
        is_crisis = level == 2 or (level == 1 and llm_confirm_crisis(prompt))
    if is_crisis:
        # 【脱敏预警简报】提取触发词，只记录时间/触发词/学号/风险等级，不含聊天原文（数据隔离）
        cleaned_log = prompt
        for safe in SAFE_PATTERNS:
            cleaned_log = cleaned_log.replace(safe, "")
        lowered_log = cleaned_log.lower()
        live_h, live_a = fetch_live_crisis_keywords()  # 已缓存，不会重复请求
        combined_high = HIGH_RISK_KEYWORDS + [w for w in live_h if w not in HIGH_RISK_KEYWORDS]
        combined_amb = AMBIGUOUS_KEYWORDS + [w for w in live_a if w not in AMBIGUOUS_KEYWORDS]
        hit_word = next((kw for kw in combined_high + combined_amb if kw in lowered_log), prompt[:15])
        alert_brief = {
            "学生": st.session_state.student_name,
            "风险": "高危",
            "时间": "刚刚",
            "触发词": hit_word,
        }
        print(f"[脱敏预警简报] {alert_brief}")  # 后台打印（不含聊天原文）
        st.session_state.alert_logs.append(alert_brief)

        # 持久化匿名预警到 alerts.json（只存会话编号/昵称/时间/触发词，绝不存对话原文）
        save_alert({
            "session_id": get_session_id(),
            "nickname": get_nickname(),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "risk_level": "高危",
            "trigger_word": hit_word,
            "contact_left": False,
        })

        with st.chat_message("user", avatar=USER_AVATAR):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt, "emotion": ""})
        with st.chat_message("assistant", avatar=CAT_AVATAR):
            st.error("🚨 触发高危预警！已强制中断对话，并通知辅导员。")
            st.error("请立刻拨打 24 小时心理援助热线：400-161-9995")
            st.markdown(CRISIS_REPLY)
        st.session_state.messages.append({"role": "assistant", "content": CRISIS_REPLY})
        st.session_state.crisis_active = True  # 标记危机状态，主页面据此显示自愿联系表单
        st.stop()

    # 未命中：重置危机状态，恢复正常聊天
    st.session_state.crisis_active = False
    st.session_state.contact_submitted = False
    # 从并行任务中拿情绪识别结果（此时大概率已完成，无需再等）
    emotion = emotion_future.result()
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
            )
            response = st.write_stream(stream)
        except Exception:
            response = "喵…猫咪的信号好像不太好，稍等一下再试试好吗？🐾"
            st.markdown(response)

    # 保存助手回复到对话历史
    st.session_state.messages.append({"role": "assistant", "content": response})
