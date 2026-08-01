import streamlit as st
from pypdf import PdfReader
import os

# -----------------------------------------------------------------------------
# 1. Page Configuration & Theme Settings
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Roche Assistant",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# 2. State Initialization (Language, Theme, Device, Page Navigation)
# -----------------------------------------------------------------------------
if "lang" not in st.session_state:
    st.session_state.lang = "English"

if "theme" not in st.session_state:
    st.session_state.theme = "Dark"

if "selected_device" not in st.session_state:
    st.session_state.selected_device = None

if "current_page" not in st.session_state:
    st.session_state.current_page = "Home"

# Translations Dictionary
translations = {
    "English": {
        "title": "Roche Smart Assistant",
        "subtitle": "Next-Generation Medical Diagnostics & Technical Knowledge Platform",
        "select_device": "Select Diagnostic Analyzer",
        "change_device": "← Change Analyzer",
        "theme_label": "Appearance Theme",
        "lang_label": "Language / اللغة",
        "search_device_placeholder": "Enter analyzer name (e.g., cobas e 411)...",
        "option_ai": "AI Assistant & Troubleshooting",
        "option_manual": "Full Manual Viewer",
        "option_parts": "Component & Hardware Explorer",
        "ai_header": "AI Diagnostic Companion",
        "manual_header": "Official Device Manual",
        "parts_header": "Analyzer Components & Functions",
        "ask_placeholder": "Ask anything about errors, maintenance, or operations...",
        "no_pdf": "PDF Manual not found for this device. Please upload it in the data folder.",
        "parts_search": "Search for a specific component...",
    },
    "العربية": {
        "title": "مساعد روش الذكي | Roche Assistant",
        "subtitle": "منصة الجيل القادم للتشخيص الطبي والمعرفة التقنية",
        "select_device": "اختر جهاز التحليل الطبي",
        "change_device": "← تغيير الجهاز",
        "theme_label": "مظهر التطبيق",
        "lang_label": "اللغة / Language",
        "search_device_placeholder": "اكتب اسم الجهاز (مثال: cobas e 411)...",
        "option_ai": "المساعد الذكي وحل الأعطال (AI)",
        "option_manual": "استعراض الكتالوج الكامل (PDF)",
        "option_parts": "استكشاف قطع الجهاز ووظائفها",
        "ai_header": "المساعد الذكي للتشخيص",
        "manual_header": "الكتالوج والدليل الرسمي للجهاز",
        "parts_header": "مكونات الجهاز وقطع الغيار ووظائفها",
        "ask_placeholder": "اسأل عن الأعطال، الصيانة، أو تعليمات التشغيل...",
        "no_pdf": "ملف الكتالوج (PDF) غير متوفر لهذا الجهاز حالياً.",
        "parts_search": "ابحث عن قطعة أو جزء معين في الجهاز...",
    }
}

t = translations[st.session_state.lang]

# -----------------------------------------------------------------------------
# 3. Dynamic Custom CSS (Custom Branding, Dark/Light Themes)
# -----------------------------------------------------------------------------
dark_css = """
<style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    .device-card {
        background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
        border: 1px solid #374151;
        border-radius: 16px;
        padding: 24px;
        text-align: center;
        transition: transform 0.3s ease, border-color 0.3s ease;
    }
    .device-card:hover { transform: translateY(-5px); border-color: #0066CC; }
    .stButton>button { border-radius: 8px; font-weight: bold; }
</style>
"""

light_css = """
<style>
    .stApp { background-color: #F8FAFC; color: #0F172A; }
    .device-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 16px;
        padding: 24px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        transition: transform 0.3s ease;
    }
    .device-card:hover { transform: translateY(-5px); border-color: #0066CC; }
    .stButton>button { border-radius: 8px; font-weight: bold; }
</style>
"""

if st.session_state.theme == "Dark":
    st.markdown(dark_css, unsafe_allow_html=True)
elif st.session_state.theme == "Light":
    st.markdown(light_css, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 4. Sidebar Controls (Theme & Language Settings)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/f/f5/Roche_Logo.svg", width=140)
    st.title("⚙️ Settings")
    
    # Theme Selection
    st.session_state.theme = st.radio(
        t["theme_label"],
        ["Dark", "Light", "Default"],
        index=["Dark", "Light", "Default"].index(st.session_state.theme)
    )
    
    # Language Selection
    st.session_state.lang = st.selectbox(
        t["lang_label"],
        ["English", "العربية"],
        index=["English", "العربية"].index(st.session_state.lang)
    )
    
    st.divider()
    if st.session_state.selected_device:
        st.success(f"📌 Active: **{st.session_state.selected_device}**")
        if st.button(t["change_device"]):
            st.session_state.selected_device = None
            st.session_state.current_page = "Home"
            st.rerun()

# -----------------------------------------------------------------------------
# 5. Header Section
# -----------------------------------------------------------------------------
st.title(f"🧪 {t['title']}")
st.caption(t["subtitle"])
st.divider()

# -----------------------------------------------------------------------------
# 6. Page 1: Device Selection (الراوتر واختيار الجهاز)
# -----------------------------------------------------------------------------
if st.session_state.selected_device is None:
    st.subheader(f"🔍 {t['select_device']}")
    
    # Search Box for Devices
    search_query = st.text_input("", placeholder=t["search_device_placeholder"])
    
    # Sample Devices List (يمكنك إضافة أو تعديل الأجهزة من هنا)
    devices_database = [
        {
            "id": "cobas_e411",
            "name": "Roche cobas e 411",
            "category": "Immunochemistry Analyzer",
            "image": "https://images.unsplash.com/photo-1579154204601-01588f351e67?auto=format&fit=crop&w=600&q=80",
            "desc": "Fully automated, random-access analyzer for immunoassay analysis."
        },
        {
            "id": "cobas_c311",
            "name": "Roche cobas c 311",
            "category": "Clinical Chemistry Analyzer",
            "image": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=600&q=80",
            "desc": "Automated clinical chemistry analyzer designed for small to medium workloads."
        }
    ]
    
    cols = st.columns(2)
    for index, dev in enumerate(devices_database):
        if search_query.lower() in dev["name"].lower() or search_query == "":
            with cols[index % 2]:
                st.image(dev["image"], use_container_width=True)
                st.markdown(f"### {dev['name']}")
                st.caption(dev["category"])
                st.write(dev["desc"])
                if st.button(f"Select {dev['name']}", key=dev["id"]):
                    st.session_state.selected_device = dev["name"]
                    st.session_state.current_page = "AI"
                    st.rerun()

# -----------------------------------------------------------------------------
# 7. Page 2: Device Hub & Navigation Options (بعد اختيار الجهاز)
# -----------------------------------------------------------------------------
else:
    # Top Navigation Tabs for Options
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button(f"🤖 {t['option_ai']}", use_container_width=True):
            st.session_state.current_page = "AI"
    with col2:
        if st.button(f"📖 {t['option_manual']}", use_container_width=True):
            st.session_state.current_page = "Manual"
    with col3:
        if st.button(f"🔬 {t['option_parts']}", use_container_width=True):
            st.session_state.current_page = "Parts"

    st.divider()

    # -------------------------------------------------------------------------
    # Option A: AI Technical Assistant
    # -------------------------------------------------------------------------
    if st.session_state.current_page == "AI":
        st.subheader(f"🤖 {t['ai_header']} - {st.session_state.selected_device}")
        
        # Chat History Container
        if "messages" not in st.session_state:
            st.session_state.messages = []

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if user_prompt := st.chat_input(t["ask_placeholder"]):
            st.session_state.messages.append({"role": "user", "content": user_prompt})
            with st.chat_message("user"):
                st.markdown(user_prompt)

            # AI Logic (Response Generation Placeholder for local processing)
            with st.chat_message("assistant"):
                response_text = f"**[Roche AI System]**: Received query regarding `{st.session_state.selected_device}`: '{user_prompt}'. Analyzing local manual database..."
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})

    # -------------------------------------------------------------------------
    # Option B: Full Manual Viewer
    # -------------------------------------------------------------------------
    elif st.session_state.current_page == "Manual":
        st.subheader(f"📖 {t['manual_header']} - {st.session_state.selected_device}")
        
        # يمكنك وضع اسم ملف الـ PDF الخاص بالجهاز هنا
        pdf_path = "data/cobas_e411_manual.pdf"
        
        if os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                st.download_button(
                    label="📥 Download Full PDF Manual",
                    data=f,
                    file_name="cobas_e411_manual.pdf",
                    mime="application/pdf"
                )
            st.info("Interactive PDF Viewer integrated below:")
            # Simple Embedded PDF Viewer
            st.markdown(f'<iframe src="{pdf_path}" width="100%" height="800px"></iframe>', unsafe_allow_html=True)
        else:
            st.warning(t["no_pdf"])

    # -------------------------------------------------------------------------
    # Option C: Hardware Parts & Functions Explorer
    # -------------------------------------------------------------------------
    elif st.session_state.current_page == "Parts":
        st.subheader(f"🔬 {t['parts_header']} - {st.session_state.selected_device}")
        
        # بيانات القطع والصور (يمكنك إضافتها وتعديلها بسهولة من هنا)
        components_data = [
            {
                "name_en": "ECL Measuring Cell",
                "name_ar": "خلية القياس الكهروكيميائية (ECL)",
                "image": "https://images.unsplash.com/photo-1579154204601-01588f351e67?auto=format&fit=crop&w=400&q=80",
                "desc_en": "Core component where ElectrochemiLuminescence reaction occurs and light signal is detected.",
                "desc_ar": "القطعة الأساسية التي يتم فيها تفاعل التلألؤ الكهروكيميائي وقياس الإشارة الضوئية للتحليل."
            },
            {
                "name_en": "Sample & Reagent Pipettor Arm",
                "name_ar": "ذراع سحب العينات والمواصفات",
                "image": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=400&q=80",
                "desc_en": "Precision liquid handling system equipped with liquid level detection and clash protection.",
                "desc_ar": "نظام دقيق لنقل السوائل مزود بحساسات لمستوى السائل وحماية من الاصطدام."
            },
            {
                "name_en": "Incubator Incubator Assembly",
                "name_ar": "حاضنة التفاعلات (Incubator)",
                "image": "https://images.unsplash.com/photo-1532187863486-abf9dbad1b69?auto=format&fit=crop&w=400&q=80",
                "desc_en": "Maintains precise 37°C temperature control for optimal assay incubation time.",
                "desc_ar": "تحافظ على درجة حرارة دقيقة 37 درجة مئوية لضمان الوقت المثالي لحضن التفاعلات الطبية."
            }
        ]
        
        part_search = st.text_input(t["parts_search"])
        
        part_cols = st.columns(3)
        for idx, part in enumerate(components_data):
            name = part["name_ar"] if st.session_state.lang == "العربية" else part["name_en"]
            desc = part["desc_ar"] if st.session_state.lang == "العربية" else part["desc_en"]
            
            if part_search.lower() in name.lower() or part_search == "":
                with part_cols[idx % 3]:
                    st.image(part["image"], use_container_width=True)
                    st.markdown(f"#### {name}")
                    st.write(desc)
