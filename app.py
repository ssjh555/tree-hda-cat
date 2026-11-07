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

# 危机关键词列表（精确组合词，避免"累死了""笑死"等日常表达误触发）
CRISIS_KEYWORDS = ["自杀", "不想活", "跳楼", "结束生命", "活着没意思", "想死", "去死", "轻生", "自残"]

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
    # 封面页隐藏侧边栏与聊天输入框
    st.markdown("""
    <style>
    section[data-testid="stSidebar"] {display: none !important;}
    [data-testid="stChatInput"] {display: none !important;}
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
    # 危机关键词检测：命中则以猫咪身份温柔回应并引导求助，存入历史后中断
    if any(keyword in prompt for keyword in CRISIS_KEYWORDS):
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
