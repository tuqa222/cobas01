import streamlit as st
import os
import glob
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from google import genai

# -----------------------------------------------------------------------------
# 1. Page Configuration & Optimizations
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Roche Diagnostic Assistant",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# 2. RAG Engine & Caching Functions (سرعة فائقة)
# -----------------------------------------------------------------------------
@st.cache_resource
def load_embedding_model():
    # نموذج خفيف وسريع جداً لعمل Embeddings محلياً
    return SentenceTransformer('all-MiniLM-L6-v2')

@st.cache_resource
def process_manuals_rag(data_dir="data"):
    """قراءة كل ملفات الـ PDF وتجزئتها وبناء فهرس FAISS للبحث اللحظي"""
    chunks = []
    if not os.path.exists(data_dir):
        return None, []
        
    pdf_files = glob.glob(os.path.join(data_dir, "*.pdf"))
    if not pdf_files:
        return None, []

    for pdf_path in pdf_files:
        try:
            reader = PdfReader(pdf_path)
            doc_name = os.path.basename(pdf_path)
            for page_num, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    # تقسيم النص لقطع صغيرة لرفع دقة استرجاع الإجابة
                    words = text.split()
                    for i in range(0, len(words), 200):
                        chunk_text = " ".join(words[i:i+250])
                        chunks.append({
                            "text": chunk_text,
                            "source": f"{doc_name} (Page {page_num+1})"
                        })
        except Exception as e:
            st.error(f"Error reading {pdf_path}: {e}")

    if not chunks:
        return None, []

    model = load_embedding_model()
    texts = [c["text"] for c in chunks]
    embeddings = model.encode(texts, convert_to_numpy=True)
    
    # بناء كشاف FAISS
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(np.array(embeddings).astype('float32'))
    
    return index, chunks

def query_rag(query_text, index, chunks, top_k=3):
    """البحث عن أكثر النصوص صلة بالسؤال داخل المانيوال"""
    if index is None or not chunks:
        return ""
    
    model = load_embedding_model()
    query_vector = model.encode([query_text], convert_to_numpy=True)
    distances, indices = index.search(np.array(query_vector).astype('float32'), top_k)
    
    retrieved_context = ""
    for idx in indices[0]:
        if idx < len(chunks):
            retrieved_context += f"\n--- Source: {chunks[idx]['source']} ---\n{chunks[idx]['text']}\n"
            
    return retrieved_context

def generate_ai_response(prompt, context, device_name, lang):
    """توليد الإجابة الكاملة من المانيوال باستخدام Gemini API"""
    api_key = os.environ.get("GEMINI_API_KEY")
    
    # في حال عدم وجود المفتاح أو ملفات المانيوال يتم استخدام نظام الإجابة التوليدية المستندة إلى سياق النظام
    if not api_key:
        return f"⚠️ **API Key Missing**: Please configure `GEMINI_API_KEY` in Streamlit Secrets.\n\n**Extracted Context from Manual:**\n{context}" if context else "Please upload manual PDFs to `/data` directory."
    
    try:
        client = genai.Client(api_key=api_key)
        
        system_instruction = f"""
        You are an expert technical support engineer for Roche Diagnostics specializing in {device_name}.
        Your goal is to provide full, comprehensive, detailed, step-by-step answers to technical queries.
        Never just quote section numbers. Provide the exact procedure, troubleshooting steps, and operational guidelines directly from the provided manual context.
        Language of response: {lang}.
        """
        
        user_message = f"""
        Device: {device_name}
        User Query: {prompt}
        
        Manual Context Retrieved:
        {context if context else 'No direct manual text found. Answer using general technical standards for this device.'}
        
        Please provide a detailed and complete technical answer based on the manual context above.
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_message,
            config={'system_instruction': system_instruction}
        )
        return response.text
    except Exception as e:
        return f"Error communicating with AI model: {str(e)}"

# -----------------------------------------------------------------------------
# 3. State Management Initialization
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

# -----------------------------------------------------------------------------
# 4. Dynamic Global Theme & Low-Contrast Background Styling
# -----------------------------------------------------------------------------
global_roche_bg = "https://images.unsplash.com/photo-1579154204601-01588f351e67?auto=format&fit=crop&w=1920&q=80"

if st.session_state.theme == "Dark":
    bg_color = "#070A10"
    text_color = "#F1F5F9"
    card_bg = "rgba(15, 23, 42, 0.80)"
    card_border = "rgba(255, 255, 255, 0.08)"
    overlay_color = "rgba(7, 10, 16, 0.94)"
else:
    bg_color = "#F8FAFC"
    text_color = "#0F172A"
    card_bg = "rgba(255, 255, 255, 0.88)"
    card_border = "rgba(0, 102, 204, 0.15)"
    overlay_color = "rgba(248, 250, 252, 0.94)"

custom_css = f"""
<style>
    .stApp {{
        background-color: {bg_color};
        background-image: linear-gradient({overlay_color}, {overlay_color}), url('{global_roche_bg}');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        color: {text_color};
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }}

    .glass-card {{
        background: {card_bg};
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid {card_border};
        border-radius: 16px;
        padding: 28px;
        margin-bottom: 20px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.15);
    }}
    
    .glass-card:hover {{
        transform: translateY(-4px);
        border-color: #0066CC;
        box-shadow: 0 20px 35px -10px rgba(0, 102, 204, 0.25);
    }}

    .stButton > button {{
        border-radius: 10px;
        font-weight: 600;
        letter-spacing: 0.3px;
        transition: all 0.2s ease;
    }}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 5. Translations Layer
# -----------------------------------------------------------------------------
translations = {
    "English": {
        "title": "Roche Enterprise Assistant",
        "subtitle": "Global Technical Diagnostics & RAG Manual Assistant",
        "select_device": "Select Clinical System",
        "change_device": "← Switch System",
        "theme_label": "Theme / المظهر",
        "lang_label": "Language / اللغة",
        "option_ai": "AI Assistant & Full Manual Diagnostics",
        "option_manual": "Technical Documentation",
        "option_parts": "System Components",
        "ask_placeholder": "Ask any question (e.g., How to fix error E-04? What is the daily maintenance steps?)...",
        "no_pdf": "Official PDF manual is missing in /data folder.",
    },
    "العربية": {
        "title": "منصة روش التشخيصية العالمية",
        "subtitle": "المنظمة المتقدمة للذكاء الاصطناعي والدليل التشغيلي المباشر للأجهزة",
        "select_device": "اختر نظام التحليل الطبي",
        "change_device": "← تغيير الجهاز",
        "theme_label": "المظهر / Theme",
        "lang_label": "اللغة / Language",
        "option_ai": "المساعد الذكي وحل الأعطال من المانيوال",
        "option_manual": "الدليل المباشر (PDF)",
        "option_parts": "مكونات النظام وقطع الغيار",
        "ask_placeholder": "اسأل عن أي خطوة تفصيلية (مثال: ما هي خطوات الصيانة اليومية؟ كيف نعالج كود الخطأ E-04؟)...",
        "no_pdf": "ملف PDF الكتالوج غير متوفر في مجلد البيانات حالياً.",
    }
}
t = translations[st.session_state.lang]

# -----------------------------------------------------------------------------
# 6. Sidebar Controls
# -----------------------------------------------------------------------------
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/f/f5/Roche_Logo.svg", width=120)
    st.markdown("---")
    st.markdown("### ⚙️ System Settings")
    
    st.session_state.theme = st.selectbox(
        t["theme_label"],
        ["Dark", "Light"],
        index=["Dark", "Light"].index(st.session_state.theme)
    )
    
    st.session_state.lang = st.selectbox(
        t["lang_label"],
        ["English", "العربية"],
        index=["English", "العربية"].index(st.session_state.lang)
    )
    
    st.markdown("---")
    if st.session_state.selected_device:
        st.success(f" Active System:\n**{st.session_state.selected_device}**")
        if st.button(t["change_device"], use_container_width=True):
            st.session_state.selected_device = None
            st.session_state.current_page = "Home"
            st.rerun()

# -----------------------------------------------------------------------------
# 7. Global Header
# -----------------------------------------------------------------------------
st.title(f"🔬 {t['title']}")
st.caption(t["subtitle"])
st.markdown("---")

# -----------------------------------------------------------------------------
# 8. Main Device Selection View
# -----------------------------------------------------------------------------
if st.session_state.selected_device is None:
    st.subheader(f"📊 {t['select_device']}")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div class="glass-card">
            <h2 style="color: #0066CC; margin-top:0;">cobas e 411 analyzer</h2>
            <p style="font-weight: 500; opacity: 0.8;">Immunochemistry & ECL Technology Platform</p>
            <hr style="border:0; border-top: 1px solid rgba(255,255,255,0.1); margin: 15px 0;">
            <p>Fully automated, random-access immunoassay system for fast and highly accurate clinical diagnostics.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Select cobas e 411", key="btn_e411", use_container_width=True, type="primary"):
            st.session_state.selected_device = "cobas e 411 analyzer"
            st.session_state.current_page = "AI"
            st.rerun()

    with col2:
        st.markdown("""
        <div class="glass-card">
            <h2 style="color: #0066CC; margin-top:0;">cobas c 311 analyzer</h2>
            <p style="font-weight: 500; opacity: 0.8;">Clinical Chemistry Analysis System</p>
            <hr style="border:0; border-top: 1px solid rgba(255,255,255,0.1); margin: 15px 0;">
            <p>High-efficiency automated system designed for consolidated clinical chemistry workload processing.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Select cobas c 311", key="btn_c311", use_container_width=True, type="primary"):
            st.session_state.selected_device = "cobas c 311 analyzer"
            st.session_state.current_page = "AI"
            st.rerun()

# -----------------------------------------------------------------------------
# 9. Active System Navigation & Full RAG AI Integration
# -----------------------------------------------------------------------------
else:
    nav1, nav2, nav3 = st.columns(3)
    with nav1:
        if st.button(f"🤖 {t['option_ai']}", use_container_width=True, type="primary" if st.session_state.current_page == "AI" else "secondary"):
            st.session_state.current_page = "AI"
            st.rerun()
    with nav2:
        if st.button(f"📖 {t['option_manual']}", use_container_width=True, type="primary" if st.session_state.current_page == "Manual" else "secondary"):
            st.session_state.current_page = "Manual"
            st.rerun()
    with nav3:
        if st.button(f"🔬 {t['option_parts']}", use_container_width=True, type="primary" if st.session_state.current_page == "Parts" else "secondary"):
            st.session_state.current_page = "Parts"
            st.rerun()

    st.markdown("---")

    # Module 1: AI Assistant (Full Manual RAG)
    if st.session_state.current_page == "AI":
        st.subheader(f"🤖 {t['option_ai']} — {st.session_state.selected_device}")
        
        # تحميل وتجهيز بيانات المانيوال بالخلفية
        with st.spinner("Indexing manuals for real-time extraction..."):
            index, chunks = process_manuals_rag("data")
            
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if user_prompt := st.chat_input(t["ask_placeholder"]):
            st.session_state.messages.append({"role": "user", "content": user_prompt})
            with st.chat_message("user"):
                st.markdown(user_prompt)

            with st.chat_message("assistant"):
                with st.spinner("Searching manual & generating step-by-step solution..."):
                    context = query_rag(user_prompt, index, chunks)
                    response = generate_ai_response(
                        user_prompt, 
                        context, 
                        st.session_state.selected_device, 
                        st.session_state.lang
                    )
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

    # Module 2: Document Manual Viewer
    elif st.session_state.current_page == "Manual":
        st.subheader(f"📖 {t['option_manual']} — {st.session_state.selected_device}")
        
        pdf_path = "data/cobas_e411_manual.pdf" if "e 411" in st.session_state.selected_device else "data/cobas_c311_manual.pdf"
        
        if os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                st.download_button("📥 Download Official Technical Manual (PDF)", f, file_name=os.path.basename(pdf_path), use_container_width=True)
        else:
            st.info(f"💡 {t['no_pdf']} Path searched: `{pdf_path}`")

    # Module 3: Hardware Components Viewer
    elif st.session_state.current_page == "Parts":
        st.subheader(f"🔬 {t['option_parts']} — {st.session_state.selected_device}")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("""
            <div class="glass-card">
                <h3>ECL Measuring Cell Assembly</h3>
                <p>Electrochemiluminescence detection core engineered for high sensitivity and precision measurement.</p>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown("""
            <div class="glass-card">
                <h3>Robotic Micro-Pipettor Arm</h3>
                <p>High-precision liquid handler with integral level sensing and clot detection sensors.</p>
            </div>
            """, unsafe_allow_html=True)
