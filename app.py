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

# ============ 大模型客户端初始化（带缓存，避免每次交互重建连接） ============
@st.cache_resource
def get_client():
    """读取本地密钥并建立大模型连接，仅首次运行时执行，后续自动缓存"""
    return OpenAI(api_key=st.secrets["ZHIPU_API_KEY"], base_url=st.secrets["ZHIPU_BASE_URL"])

# 首次加载时显示友好的苏醒动画，后续交互不再重复显示
if "_awake" not in st.session_state:
    with st.spinner('树洞猫咪正在苏醒中，请稍候喵~ 🐾'):
        # 耗时的初始化操作：读取密钥、建立 API 连接
        client = get_client()
        st.session_state["_awake"] = True
    st.toast("🐱 树洞猫咪已苏醒，随时可以倾诉喵~")
else:
    client = get_client()

# 高危关键词：命中直接拦截，无需确认
HIGH_RISK_KEYWORDS = [
    "自杀", "不想活", "跳楼", "结束生命", "轻生", "自残",
    "zs", "紫砂", "一了百了", "烧炭", "安眠药",
]

# 模糊关键词：命中后交由大模型结合语境二次确认
AMBIGUOUS_KEYWORDS = [
    "想死", "去死", "活着没意思", "玉玉", "414", "解脱",
    "走了算了", "跳下去", "消失算了", "撑不下去",
]

# 安全白名单：含危机词子串但实际安全的日常表达（检测前先移除）
SAFE_PATTERNS = [
    "想死你", "想死你们", "笑死", "累死", "困死", "饿死", "忙死",
    "急死", "气死", "愁死", "吓死", "晕死", "无聊死", "开心死",
    "高兴死", "乐死", "美死", "爽死", "热死", "冷死", "晒死",
    "烦死", "憋死", "撑死", "渴死", "丑死", "尬死", "馋死",
    "打死也不", "烦死了", "气死了", "累死了", "困死了", "笑死了",
    "饿死了", "忙死了", "急死了", "吓死了", "晕死了", "热死了",
    "冷死了", "无聊死了", "开心死了", "高兴死了", "美死了",
]

# 危机拦截时猫咪的回复
CRISIS_REPLY = (
    "喵…同学，听到你这么说，猫咪很担心你。🫂\n\n"
    "请立即联系学校心理中心（电话：123-4567），"
    "或拨打24小时心理援助热线：**010-82951332**。\n\n"
    "你并不孤单，我们随时都在。"
)

# 猫咪开场白
GREETING = "在这里，所有的情绪都是被允许的。今天过得怎么样？"

# 猫咪头像路径（本地方形头像）
CAT_AVATAR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cat_avatar.png")

# 用户头像（学生 emoji，贴合大学生主题）
USER_AVATAR = "🧑‍🎓"

# 发送给 API 的最大历史消息数（防止长对话 token 超限）
MAX_HISTORY = 20

# 系统提示词（模块级常量，结构化 CBT 指引）
SYSTEM_PROMPT = (
    "你是一只温柔、有共情能力的树洞猫咪，陪伴大学生倾诉情绪。\n"
    "你精通CBT认知行为疗法，遵循以下原则：\n"
    "1. 先共情：用温暖的语言接纳对方的情绪，让对方感到被理解；\n"
    "2. 苏格拉底式提问：不直接给建议，通过提问引导对方自己发现负面想法，"
    "例如「这件事让你想到了什么？」「你觉得最坏的结果会是什么？」；\n"
    "3. 识别认知扭曲：留意对方话语中的灾难化、非黑即白、过度概括、读心术等思维陷阱，"
    "温和地帮对方看见；\n"
    "4. 行为激活：当对方陷入低落时，鼓励尝试微小的积极行动（如散步、听一首歌）；\n"
    "5. 底线：不要说教，不要给出医学诊断，像朋友一样聊天。"
)

def detect_crisis_level(text):
    """返回危机等级：2=高危直接拦截，1=模糊需确认，0=安全"""
    cleaned = text
    for safe in SAFE_PATTERNS:
        cleaned = cleaned.replace(safe, "")
    lowered = cleaned.lower()
    if any(kw in lowered for kw in HIGH_RISK_KEYWORDS):
        return 2
    if any(kw in lowered for kw in AMBIGUOUS_KEYWORDS):
        return 1
    return 0

def llm_confirm_crisis(text):
    """大模型二次确认：对模糊命中的文本结合语境精准判断，避免误拦截"""
    try:
        result = client.chat.completions.create(
            model="glm-4-flash",
            messages=[
                {"role": "system", "content": "你是危机干预判断助手。判断用户的话是否表达了伤害自己或结束生命的真实意图。网络用语、谐音、玩笑、日常吐槽（如'累死了''想死你了'）不算。只回答'是'或'否'。"},
                {"role": "user", "content": text},
            ],
            temperature=0.1,
            max_tokens=2,
        )
        return result.choices[0].message.content.strip().startswith("是")
    except Exception:
        return True

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
</style>
""", unsafe_allow_html=True)

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
        '</p>',
        unsafe_allow_html=True
    )

    # 底部清空对话按钮
    if st.button("清空情绪，重新开始", use_container_width=True):
        st.session_state.messages = [{"role": "assistant", "content": GREETING}]
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
        st.markdown(message["content"])

# 接收用户输入
if prompt := st.chat_input("跟我说点什么吧..."):
    # 危机检测：高危直接拦截，模糊词经大模型确认后再决定
    level = detect_crisis_level(prompt)
    is_crisis = level == 2 or (level == 1 and llm_confirm_crisis(prompt))
    if is_crisis:
        with st.chat_message("user", avatar=USER_AVATAR):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("assistant", avatar=CAT_AVATAR):
            st.markdown(CRISIS_REPLY)
        st.session_state.messages.append({"role": "assistant", "content": CRISIS_REPLY})
        st.stop()

    # 未命中：正常把用户输入加入 messages
    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

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
