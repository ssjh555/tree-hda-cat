import os
import sys
import subprocess

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
client = OpenAI(api_key=st.secrets["ZHIPU_API_KEY"], base_url=st.secrets["ZHIPU_BASE_URL"])

# ==================== 三级风控关键词体系 ====================
# 高危拦截词：命中直接拦截，无需大模型确认（明确的自伤/自杀表述及网络黑话）
HIGH_RISK_KEYWORDS = [
    # 明确表述
    "自杀", "不想活", "跳楼", "结束生命", "轻生", "自残", "割腕",
    "上吊", "烧炭", "安眠药", "一了百了", "了结自己",
    # 拼音缩写 / 谐音 / 网络黑话
    "zs", "紫砂", "想跳了", "天台见", "离开这个世界", "头孢加酒",
    "非正常死亡计划", "重开", "删号", "退网",
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
]

# 危机拦截时猫咪的回复
CRISIS_REPLY = (
    "喵……看到你说的这些话，猫咪的心一下子揪紧了，好心疼好心疼你呀……🥺🫂\n\n"
    "猫咪想立刻抱抱你，用最软最软的毛蹭蹭你的手心，"
    "轻轻对你说：你的痛苦猫咪都感受到了，你不需要一个人扛着。\n\n"
    "请答应猫咪好不好？现在就联系学校心理中心（电话：123-4567），"
    "或者拨打24小时心理援助热线：**010-82951332**。\n\n"
    "猫咪哪儿也不去，就在这里守着你。🐾"
)

# 猫咪开场白
GREETING = (
    "喵~你来啦！🐾 猫咪一直在这里等你呢，好开心呀~\n\n"
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
    "5. 底线：不要说教，不要给出医学诊断，像朋友一样聊天。"
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
    # 第三步：优先检测高危词（明确意图，直接拦截）
    if any(kw in lowered for kw in HIGH_RISK_KEYWORDS):
        return 2
    # 第四步：检测歧义词（需语境判断，交给大模型确认）
    if any(kw in lowered for kw in AMBIGUOUS_KEYWORDS):
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

/* 聊天气泡：统一圆角与阴影 */
[data-testid="stChatMessage"] {
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
</style>
""", unsafe_allow_html=True)

# ==================== 封面页：点击进入主界面 ====================
# 进入标记：首次访问显示封面，点击后进入聊天界面
if "entered" not in st.session_state:
    st.session_state.entered = False

if not st.session_state.entered:
    # 封面页隐藏侧边栏（聊天输入框无需隐藏：st.stop() 已阻止其渲染）
    st.markdown("""
    <style>
    section[data-testid="stSidebar"] {display: none !important;}
    </style>
    """, unsafe_allow_html=True)

    # 封面欢迎语（垂直居中）
    st.markdown("""
    <div class="cover-container">
        <h1 class="cover-title">🐱 树洞猫咪</h1>
        <p class="cover-subtitle">你的专属情绪倾听者</p >
        <p class="cover-desc">
            在这里，你可以卸下所有伪装。<br>
            没有评判，没有说教，只有一只温柔的猫咪愿意听你说话。
        </p >
    </div>
    """, unsafe_allow_html=True)

    # 猫咪头像（居中展示）
    _, img_col, _ = st.columns([1, 1.2, 1])
    with img_col:
        st.image(CAT_AVATAR, width=260)

    # 进入按钮（居中）
    _, btn_col, _ = st.columns([1, 1, 1])
    with btn_col:
        if st.button("🐾 轻触进入树洞", use_container_width=True):
            st.session_state.entered = True
            st.rerun()

    st.stop()  # 封面页不渲染后续聊天界面

# ==================== 侧边栏 ====================
with st.sidebar:
    # 顶部标题
    st.markdown(
        '<div style="text-align:center; margin-bottom:12px;">'
        '<span style="font-size:1.3rem; font-weight:700; color:#6C5B7B;">🐱 你的专属树洞猫咪</span>'
        '</div>',
        unsafe_allow_html=True
    )

    # 猫咪头像图片（居中展示）
    st.image(CAT_AVATAR, width=200)

    # 中间免责声明（黄色小字）
    st.markdown(
        '<p style="color:#B8860B; font-size:0.78rem; line-height:1.7; margin:8px 0;">'
        '⚠️ 声明：本应用为 AI 助手，旨在提供情绪缓冲与陪伴。不能替代专业心理咨询。'
        '如遇严重心理危机，请务必联系专业医生或拨打援助热线。'
        '</p >',
        unsafe_allow_html=True
    )

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

# ==================== 主页面 ====================
st.markdown("<h1 style='text-align: center; color: #6C5B7B;'>树洞猫咪：你的专属情绪倾听者</h1>", unsafe_allow_html=True)

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

# 接收用户输入
if prompt := st.chat_input("跟我说点什么吧..."):
    # 三级风控检测：高危(2)直接拦截，歧义(1)经大模型确认，安全(0)正常对话
    level = detect_crisis_level(prompt)
    is_crisis = level == 2 or (level == 1 and llm_confirm_crisis(prompt))
    if is_crisis:
        with st.chat_message("user", avatar=USER_AVATAR):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt, "emotion": ""})
        with st.chat_message("assistant", avatar=CAT_AVATAR):
            st.markdown(CRISIS_REPLY)
        st.session_state.messages.append({"role": "assistant", "content": CRISIS_REPLY})
        st.stop()

    # 未命中：识别情绪后把用户输入加入 messages
    emotion = detect_emotion(prompt)
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
            )
            response = st.write_stream(stream)
        except Exception:
            response = "喵…猫咪的信号好像不太好，稍等一下再试试好吗？🐾"
            st.markdown(response)

    # 保存助手回复到对话历史
    st.session_state.messages.append({"role": "assistant", "content": response})
