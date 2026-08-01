import streamlit as st
import os

# -----------------------------------------------------------------------------
# 1. Configuration & Performance Caching
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Roche Assistant",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# 2. Advanced Dynamic CSS (High-End Lab UI)
# -----------------------------------------------------------------------------
dark_theme = """
<style>
    /* Main Background & Text */
    .stApp {
        background: #0B0F19;
        color: #F3F4F6;
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }
    
    /* Modern Glassmorphic Cards */
    .device-card {
        background: rgba(17, 24, 39, 0.7);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 20px;
        padding: 24px;
        margin-bottom: 20px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 10px 30px -10px rgba(0,0,0,0.5);
    }
    .device-card:hover {
        transform: translateY(-6px);
        border-color: #0066CC;
        box-shadow: 0 20px 40px -15px rgba(0, 102, 204, 0.3);
    }
    
    /* Buttons Styling */
    .stButton > button {
        border-radius: 12px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
</style>
"""

light_theme = """
<style>
    .stApp {
        background: #F8FAFC;
        color: #0F172A;
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }
    .device-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 20px;
        padding: 24px;
        margin-bottom: 20px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.05);
    }
    .device-card:hover {
        transform: translateY(-6px);
        border-color: #0066CC;
        box-shadow: 0 12px 30px -10px rgba(0, 102, 204, 0.15);
    }
    .stButton > button {
        border-radius: 12px;
        font-weight: 600;
    }
</style>
"""

# State Management
if "lang" not in st.session_state:
    st.session_state.lang = "English"

if "theme" not in st.session_state:
    st.session_state.theme = "Dark"

if "selected_device" not in st.session_state:
    st.session_state.selected_device = None

if "current_page" not in st.session_state:
    st.session_state.current_page = "Home"

# Apply Theme CSS
if st.session_state.theme == "Dark":
    st.markdown(dark_theme, unsafe_allow_html=True)
elif st.session_state.theme == "Light":
    st.markdown(light_theme, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. Language Dictionary
# -----------------------------------------------------------------------------
translations = {
    "English": {
        "title": "Roche Assistant Portal",
        "subtitle": "Advanced Medical Diagnostics & Interactive Technical Intelligence Hub",
        "select_device": "Select Clinical Analyzer",
        "change_device": "← Back to Analyzers",
        "theme_label": "Theme / المظهر",
        "lang_label": "Language / اللغة",
        "option_ai": "AI Diagnostics & Support",
        "option_manual": "Full Manual Viewer",
        "option_parts": "Component Explorer",
        "ask_placeholder": "Ask about error codes, maintenance steps, or system operations...",
        "no_pdf": "Catalog PDF not found in /data directory.",
    },
    "العربية": {
        "title": "منصة روش الذكية | Roche Assistant",
        "subtitle": "المركز التفاعلي للتشخيص الطبي المتقدم والمعرفة التقنية للأجهزة",
        "select_device": "اختر جهاز التحليل الطبي",
        "change_device": "← العودة لجميع الأجهزة",
        "theme_label": "المظهر / Theme",
        "lang_label": "اللغة / Language",
        "option_ai": "المساعد الذكي وحل الأعطال (AI)",
        "option_manual": "استعراض الكتالوج (PDF)",
        "option_parts": "مكونات الجهاز وقطع الغيار",
        "ask_placeholder": "اسأل عن رموز الأعطال، خطة الصيانة، أو تعليمات التشغيل...",
        "no_pdf": "ملف الكتالوج (PDF) غير متوفر في مجلد البيانات حالياً.",
    }
}

t = translations[st.session_state.lang]

# -----------------------------------------------------------------------------
# 4. Sidebar Controls
# -----------------------------------------------------------------------------
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/f/f5/Roche_Logo.svg", width=130)
    st.markdown("### ⚙️ Preference Control")
    
    st.session_state.theme = st.selectbox(
        t["theme_label"],
        ["Dark", "Light", "Default"],
        index=["Dark", "Light", "Default"].index(st.session_state.theme)
    )
    
    st.session_state.lang = st.selectbox(
        t["lang_label"],
        ["English", "العربية"],
        index=["English", "العربية"].index(st.session_state.lang)
    )
    
    st.divider()
    if st.session_state.selected_device:
        st.info(f"📍 Active Device:\n**{st.session_state.selected_device}**")
        if st.button(t["change_device"], use_container_width=True):
            st.session_state.selected_device = None
            st.session_state.current_page = "Home"
            st.rerun()

# -----------------------------------------------------------------------------
# 5. Header
# -----------------------------------------------------------------------------
st.title(f"🔬 {t['title']}")
st.caption(t["subtitle"])
st.divider()

# -----------------------------------------------------------------------------
# 6. Page 1: Device Selection (الرئيسية)
# -----------------------------------------------------------------------------
if st.session_state.selected_device is None:
    st.subheader(f"📊 {t['select_device']}")
    
    # قائمة الأجهزة المحترفة
    devices = [
        {
            "id": "e411",
            "name": "cobas e 411 analyzer",
            "type": "Immunochemistry Testing",
            "image": "https://images.unsplash.com/photo-1579154204601-01588f351e67?auto=format&fit=crop&w=600&q=80",
            "desc": "Automated system for immunoassay analysis with ECL technology."
        },
        {
            "id": "c311",
            "name": "cobas c 311 analyzer",
            "type": "Clinical Chemistry",
            "image": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=600&q=80",
            "desc": "High-efficiency clinical chemistry analyzer for medium-sized laboratories."
        }
    ]
    
    col1, col2 = st.columns(2)
    for idx, dev in enumerate(devices):
        target_col = col1 if idx % 2 == 0 else col2
        with target_col:
            st.markdown(f"""
            <div class="device-card">
                <h3>{dev['name']}</h3>
                <p style="color: #0066CC; font-weight: 600;">{dev['type']}</p>
                <p>{dev['desc']}</p>
            </div>
            """, unsafe_allow_html=True)
            st.image(dev['image'], use_container_width=True)
            if st.button(f"Select {dev['name']}", key=dev['id'], use_container_width=True):
                st.session_state.selected_device = dev['name']
                st.session_state.current_page = "AI"
                st.rerun()

# -----------------------------------------------------------------------------
# 7. Page 2: Device Portal Options
# -----------------------------------------------------------------------------
else:
    nav_col1, nav_col2, nav_col3 = st.columns(3)
    with nav_col1:
        if st.button(f"🤖 {t['option_ai']}", use_container_width=True):
            st.session_state.current_page = "AI"
    with nav_col2:
        if st.button(f"📖 {t['option_manual']}", use_container_width=True):
            st.session_state.current_page = "Manual"
    with nav_col3:
        if st.button(f"🔬 {t['option_parts']}", use_container_width=True):
            st.session_state.current_page = "Parts"

    st.divider()

    # Option A: AI Assistant
    if st.session_state.current_page == "AI":
        st.subheader(f"🤖 {t['option_ai']} — {st.session_state.selected_device}")
        
        if "messages" not in st.session_state:
            st.session_state.messages = []

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if user_prompt := st.chat_input(t["ask_placeholder"]):
            st.session_state.messages.append({"role": "user", "content": user_prompt})
            with st.chat_message("user"):
                st.markdown(user_prompt)

            with st.chat_message("assistant"):
                ans = f"**[Roche AI]**: Query processed for `{st.session_state.selected_device}`: '{user_prompt}'. Searching device manuals..."
                st.markdown(ans)
                st.session_state.messages.append({"role": "assistant", "content": ans})

    # Option B: Manual Viewer
    elif st.session_state.current_page == "Manual":
        st.subheader(f"📖 {t['option_manual']} — {st.session_state.selected_device}")
        pdf_file = "data/cobas_e411_manual.pdf"
        
        if os.path.exists(pdf_file):
            with open(pdf_file, "rb") as f:
                st.download_button("📥 Download Official Manual (PDF)", f, file_name="manual.pdf")
        else:
            st.warning(t["no_pdf"])

    # Option C: Hardware Components
    elif st.session_state.current_page == "Parts":
        st.subheader(f"🔬 {t['option_parts']} — {st.session_state.selected_device}")
        
        parts = [
            {
                "name": "ECL Measuring Cell" if st.session_state.lang == "English" else "خلية قياس ECL",
                "img": "https://images.unsplash.com/photo-1579154204601-01588f351e67?auto=format&fit=crop&w=400&q=80",
                "desc": "Electrochemiluminescence detection system." if st.session_state.lang == "English" else "نظام قياس التلألؤ الكهروكيميائي لقياس العينات بدقة."
            },
            {
                "name": "Sample Pipettor Arm" if st.session_state.lang == "English" else "ذراع سحب العينات",
                "img": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=400&q=80",
                "desc": "Precision robotic arm for liquid handling." if st.session_state.lang == "English" else "ذراع روبوتية دقيقة لسحب ونقل السوائل والمواصفات."
            }
        ]
        
        p_cols = st.columns(2)
        for i, p in enumerate(parts):
            with p_cols[i % 2]:
                st.image(p["img"], use_container_width=True)
                st.markdown(f"#### {p['name']}")
                st.write(p["desc"])
