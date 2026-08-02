import streamlit as st
import os
import glob
import re
from pypdf import PdfReader
import google.generativeai as genai

# -----------------------------------------------------------------------------
# 1. Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Roche Enterprise Assistant",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# 2. PDF Processing & Context Loading
# -----------------------------------------------------------------------------
@st.cache_resource
def load_full_manual_text(root_dir="."):
    """قراءة وحفظ المانيوال مقسماً حسب الصفحات لاستخدامه مع الذكاء الاصطناعي"""
    pdf_files = glob.glob(os.path.join(root_dir, "*.pdf")) + glob.glob(os.path.join(root_dir, "*.pdf.pdf"))
    if not pdf_files:
        return ""

    full_content = []
    for pdf_path in pdf_files:
        try:
            reader = PdfReader(pdf_path)
            doc_name = os.path.basename(pdf_path)
            for page_num, page in enumerate(reader.pages):
                text = page.extract_text()
                if text and len(text.strip()) > 10:
                    full_content.append(f"--- [Document: {doc_name} | Page {page_num + 1}] ---\n{text.strip()}")
        except Exception:
            pass

    return "\n\n".join(full_content)

def get_flexible_ai_response(user_prompt, chat_history, manual_context, api_key):
    """إرسال المحادثة والسياق بالكامل إلى Gemini API للإجابة بمرونة وفهم عميق"""
    if not api_key:
        return "⚠️ الرجاء إدخال مفتاح Gemini API في الشريط الجانبي لتفعيل الذكاء الاصطناعي المرن."

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')

        system_instruction = f"""
أنت مساعد ذكي متخصص لشركة Roche Diagnostics ومعدات cobas.
أمامك دليل الاستخدام/المانيوال التالي المكون من عدة صفحات:

{manual_context[:50000]}  # استخدام نص المانيوال المتاح

تعليمات التعامل مع المستخدم:
1. إذا طلب المستخدم معلومات من المانيوال: اذكر رقم الصفحة (Page Number) بدقة، واقتبس المقطع الحرفي أو الإجابة المباشرة.
2. إذا كان السؤال متابعة (مثل: "فهمني"، "لخص"، "ما التالي"، "what is next"، "بسطلي إياها"): افهم سياق المحادثة السابقة وأجب بمرونة وذكاء كامل دون التزام قسري بالاقتباس الحرفي إذا كان المطلوب الشرح.
3. كن مرناً، طبيعياً، ودقيقاً في جميع إجاباتك.
"""

        # بناء سجل المحادثة
        formatted_history = []
        for msg in chat_history:
            role = "user" if msg["role"] == "user" else "model"
            formatted_history.append({"role": role, "parts": [msg["content"]]})

        chat = model.start_chat(history=formatted_history)
        prompt_with_instructions = f"{system_instruction}\n\nUser Question: {user_prompt}"
        response = chat.send_message(prompt_with_instructions)
        return response.text

    except Exception as e:
        return f"❌ حدث خطأ أثناء الاتصال بالذكاء الاصطناعي: {str(e)}"

# -----------------------------------------------------------------------------
# 3. State Initialization
# -----------------------------------------------------------------------------
if "lang" not in st.session_state:
    st.session_state.lang = "English"

if "theme" not in st.session_state:
    st.session_state.theme = "Dark"

if "selected_device" not in st.session_state:
    st.session_state.selected_device = None

if "current_page" not in st.session_state:
    st.session_state.current_page = "Home"

if "messages" not in st.session_state:
    st.session_state.messages = []

if "api_key" not in st.session_state:
    st.session_state.api_key = ""

# -----------------------------------------------------------------------------
# 4. Styling & Light Contrast UI Setup
# -----------------------------------------------------------------------------
bg_color = "#0A0D14" if st.session_state.theme == "Dark" else "#F1F5F9"
card_bg = "rgba(23, 32, 51, 0.65)" if st.session_state.theme == "Dark" else "rgba(255, 255, 255, 0.85)"
border_color = "rgba(255, 255, 255, 0.08)" if st.session_state.theme == "Dark" else "rgba(0, 0, 0, 0.08)"
text_color = "#F8FAFC" if st.session_state.theme == "Dark" else "#0F172A"

st.markdown(f"""
<style>
    .stApp {{
        background-color: {bg_color};
        color: {text_color};
    }}
    .contrast-card {{
        background: {card_bg};
        border: 1px solid {border_color};
        border-radius: 12px;
        padding: 18px 24px;
        margin-bottom: 20px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
        backdrop-filter: blur(10px);
    }}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 5. Sidebar Controls
# -----------------------------------------------------------------------------
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/f/f5/Roche_Logo.svg", width=120)
    st.markdown("---")
    st.session_state.api_key = st.text_input("🔑 Gemini API Key", value=st.session_state.api_key, type="password")
    st.markdown("---")
    st.session_state.theme = st.selectbox("Theme / المظهر", ["Dark", "Light"])
    st.session_state.lang = st.selectbox("Language / اللغة", ["English", "العربية"])
    st.markdown("---")
    if st.session_state.selected_device:
        st.success(f"Active System:\n**{st.session_state.selected_device}**")
        if st.button("← Switch System", use_container_width=True):
            st.session_state.selected_device = None
            st.session_state.current_page = "Home"
            st.rerun()

# -----------------------------------------------------------------------------
# 6. Main Application Views
# -----------------------------------------------------------------------------
st.title("🔬 Roche Enterprise Assistant")
st.markdown("---")

manual_text = load_full_manual_text(".")

if st.session_state.selected_device is None:
    st.subheader("📊 Select Clinical System")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="contrast-card"><h2>cobas e 411 analyzer</h2><p>Immunochemistry Platform</p></div>', unsafe_allow_html=True)
        if st.button("Select cobas e 411", key="btn_e411", use_container_width=True, type="primary"):
            st.session_state.selected_device = "cobas e 411 analyzer"
            st.session_state.current_page = "AI"
            st.rerun()
    with col2:
        st.markdown('<div class="contrast-card"><h2>cobas c 311 analyzer</h2><p>Clinical Chemistry System</p></div>', unsafe_allow_html=True)
        if st.button("Select cobas c 311", key="btn_c311", use_container_width=True, type="primary"):
            st.session_state.selected_device = "cobas c 311 analyzer"
            st.session_state.current_page = "AI"
            st.rerun()
else:
    nav1, nav2, nav3 = st.columns(3)
    with nav1:
        if st.button("🤖 Roche Flexible AI", use_container_width=True, type="primary" if st.session_state.current_page == "AI" else "secondary"):
            st.session_state.current_page = "AI"
            st.rerun()
    with nav2:
        if st.button("📖 Technical Documentation", use_container_width=True, type="primary" if st.session_state.current_page == "Manual" else "secondary"):
            st.session_state.current_page = "Manual"
            st.rerun()
    with nav3:
        if st.button("🔬 System Components", use_container_width=True, type="primary" if st.session_state.current_page == "Parts" else "secondary"):
            st.session_state.current_page = "Parts"
            st.rerun()

    st.markdown("---")

    if st.session_state.current_page == "AI":
        st.markdown(f'<div class="contrast-card"><h3>🤖 Flexible Assistant — {st.session_state.selected_device}</h3></div>', unsafe_allow_html=True)
        
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if user_prompt := st.chat_input("Ask Roche Assistant..."):
            st.session_state.messages.append({"role": "user", "content": user_prompt})
            with st.chat_message("user"):
                st.markdown(user_prompt)

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = get_flexible_ai_response(
                        user_prompt,
                        st.session_state.messages[:-1],
                        manual_text,
                        st.session_state.api_key
                    )
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})

    elif st.session_state.current_page == "Manual":
        st.subheader(f"📖 Technical Documentation — {st.session_state.selected_device}")
        target_keyword = "e411" if "e 411" in st.session_state.selected_device else "c311"
        found_files = glob.glob(f"*{target_keyword}*")
        if found_files:
            pdf_path = found_files[0]
            with open(pdf_path, "rb") as f:
                st.download_button("📥 Download Official Technical Manual (PDF)", f, file_name=os.path.basename(pdf_path), use_container_width=True)
        else:
            st.info("💡 PDF file is missing.")

    elif st.session_state.current_page == "Parts":
        st.subheader(f"🔬 System Components — {st.session_state.selected_device}")
        st.markdown('<div class="contrast-card"><h3>ECL Measuring Cell Assembly</h3><p>Electrochemiluminescence detection core.</p></div>', unsafe_allow_html=True)
