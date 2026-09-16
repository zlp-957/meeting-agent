import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.agent import chat
from core.config import DEEPSEEK_API_KEY

st.set_page_config(
    page_title="智能会议室预约助手",
    page_icon="🏢",
    layout="centered",
)

st.title("🏢 智能会议室预约助手")
st.caption("会前预约 · 会中管理 · 会后纪要 —— 会议全流程智能助手")

if not DEEPSEEK_API_KEY:
    st.error("⚠️ 未检测到大模型密钥，请复制 .env.example 为 .env 并填入你的密钥。")
    st.code("copy .env.example .env\n# 然后编辑 .env 文件，填入你的 DeepSeek 密钥", language="bash")
    st.stop()

with st.expander("💡 你可以这样问我", expanded=False):
    st.markdown("""
    **会前 · 智能推荐与预约**
    - "帮我推荐一个明天下午2点、能坐15人的会议室，要有投影仪"
    - "推荐个A座的10人会议室，后天上午用"
    - "帮我约 B202 明天下午2点到4点，我叫张三"

    **会中 · 查询与管理**
    - "我有哪些预约？"
    - "取消预约号 #000001"
    - "把预约#000003改到下午3点"

    **会后 · 会议纪要**
    - "帮我给预约#000002生成会议纪要，笔记如下：..."
    - "看看有哪些会议纪要"

    **规则问答**
    - "取消预约要提前多久？"
    - "会议室能带宠物吗？"
    """)

st.divider()

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("请输入你的需求，例如：帮我约明天下午2点的会议室"):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        with st.spinner("正在思考中…"):
            try:
                response = chat(prompt)
            except Exception as e:
                response = f"⚠️ 出错了：{e}\n\n请检查密钥是否正确，或稍后重试。"
        st.markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response})