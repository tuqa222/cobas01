import streamlit as st
import os
import glob
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import re

# -----------------------------------------------------------------------------
# 1. Page Configuration & Setup
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Roche Enterprise Assistant",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# 2. Advanced Local RAG & Flexible Smart Engine
# -----------------------------------------------------------------------------
@st.cache_resource
def load_embedding_model():
    return SentenceTransformer('all-MiniLM-L6-v2')

@st.cache_resource
def process_manuals_rag(root_dir="."):
    """قراءة كل ملفات الـ PDF وتخزين الصفحات والسلايدات برقم دقيق"""
    chunks = []
    pdf_files = glob.glob(os.path.join(root_dir, "*.pdf")) + glob.glob(os.path.join(root_dir, "*.pdf.pdf"))
    
    if not pdf_files:
        return None, []

    for pdf_path in pdf_files:
        try:
            reader = PdfReader(pdf_path)
            doc_name = os.path.basename(pdf_path)
            for page_num, page in enumerate(reader.pages):
                text = page.extract_text()
                if text and len(text.strip()) > 15:
                    chunks.append({
                        "text": text.strip(),
                        "source": doc_name,
                        "page": page_num + 1  # رقم السلايد / الصفحة
                    })
        except Exception:
            pass

    if not chunks:
        return None, []

    model = load_embedding_model()
    texts = [c["text"] for c in chunks]
    embeddings = model.encode(texts, convert_to_numpy=True)
    
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(np.array(embeddings).astype('float32'))
    
    return index, chunks

def summarize_text(raw_text, is_arabic):
    """خوارزمية محليّة ذكية لتلخيص واستخراج الأسباب والنقاط الجوهرية فقط"""
    # استخراج الجمل الأساسية
    sentences = re.split(r'(?<=[.!?\n])\s+', raw_text)
    important_sentences = []
    
    keywords = ['warning', 'caution', 'danger', 'shock', 'electric', 'cover', 'cause', 'risk', 'hazard', 'maintenance', 'step', 'note', 'حذر', 'صدمة', 'كهرباء', 'خطر', 'سبب']
    
    for s in sentences:
        s_clean = s.strip()
        if len(s_clean) > 15:
            # التحقق من وجود كلمات مفتاحية أو أسباب
            if any(k in s_clean.lower() for k in keywords) or len(important_sentences) < 2:
                if s_clean not in important_sentences:
                    important_sentences.append(s_clean)
                    
    if not important_sentences:
        important_sentences = sentences[:2]
        
    return " ".join(important_sentences[:3])

def query_flexible_ai(user_query, index, chunks, device_name, lang, top_k=2):
    """محرك AI مرن واحترافي: يحدد السلايد ويصيغ الرد (ملخص أم شرح) بنطاق محدد"""
    if index is None or not chunks:
        return "⚠️ لا توجد ملفات المانيوال في المستودع." if lang == "العربية" else "⚠️ Manual PDFs missing in repository."

    model = load_embedding_model()
    query_vector = model.encode([user_query], convert_to_numpy=True)
    distances, indices = index.search(np.array(query_vector).astype('float32'), top_k)
    
    matched = []
    for idx in indices[0]:
        if idx < len(chunks):
            matched.append(chunks[idx])
            
    if not matched:
        return "لم أجد معلومات مطابقة داخل المانيوال." if lang == "العربية" else "No matching information found in manual."

    # كشف هل المستخدم يطلب ملخص/اختصار أم لا
    is_summary = any(w in user_query.lower() for w in ['summary', 'summarize', 'brief', 'ملخص', 'اختصار', 'باختصار', 'موجز'])
    
    main_page = matched[0]['page']
    raw_content = matched[0]['text']
    
    if is_summary:
        processed_content = summarize_text(raw_content, lang == "العربية")
    else:
        # صياغة احترافية مركزة بدلاً من الإطالة
        sentences = re.split(r'(?<=[.!?\n])\s+', raw_content)
        processed_content = " ".join([s.strip() for s in sentences if len(s.strip()) > 10][:4])

    if lang == "العربية":
        header = f"📍 **الصفحة / السلايد:** `{main_page}`\n\n"
        if is_summary:
            reply = f"{header}📝 **الملخص التنفيذي:**\n{processed_content}"
        else:
            reply = f"{header}💡 **الإجابة:**\n{processed_content}"
    else:
        header = f"📍 **Slide / Page Reference:** `Page {main_page}`\n\n"
        if is_summary:
            reply = f"{header}📝 **Summary:**\n{processed_content}"
        else:
            reply = f"{header}💡 **Answer:**\n{processed_content}"

    return reply

# -----------------------------------------------------------------------------
# 3. State Management
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
# 4. Styling & CSS
# -----------------------------------------------------------------------------
bg_color = "#070A10" if st.session_state.theme == "Dark" else "#F8FAFC"
text_color = "#F1F5F9" if st.session_state.theme == "Dark" else "#0F172A"

st.markdown(f"""
<style>
    .stApp {{
        background-color: {bg_color};
        color: {text_color};
    }}
    .glass-card {{
        background: rgba(15, 23, 42, 0.75);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 15px;
    }}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 5. Translations
# -----------------------------------------------------------------------------
translations = {
    "English": {
        "title": "Roche Enterprise Assistant",
        "subtitle": "Global Technical Diagnostics & Flexible AI Engine",
        "select_device": "Select Clinical System",
        "change_device": "← Switch System",
        "option_ai": "Roche Flexible AI",
        "option_manual": "Technical Documentation",
        "option_parts": "System Components",
        "ask_placeholder": "Ask a question or request a summary (e.g., summarize shock risks)...",
    },
    "العربية": {
        "title": "منصة روش التشخيصية العالمية",
        "subtitle": "محرك الذكاء الاصطناعي المرن والدعم الفني المباشر",
        "select_device": "اختر نظام التحليل الطبي",
        "change_device": "← تغيير الجهاز",
        "option_ai": "المساعد الذكي (Roche AI)",
        "option_manual": "الدليل المباشر (PDF)",
        "option_parts": "مكونات النظام",
        "ask_placeholder": "اسأل سؤالاً أو اطلب ملخصاً (مثال: ملخص خطورة الكهرباء)...",
    }
}
t = translations[st.session_state.lang]

# -----------------------------------------------------------------------------
# 6. Sidebar Controls
# -----------------------------------------------------------------------------
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/f/f5/Roche_Logo.svg", width=120)
    st.markdown("---")
    
    st.session_state.theme = st.selectbox("Theme / المظهر", ["Dark", "Light"])
    st.session_state.lang = st.selectbox("Language / اللغة", ["English", "العربية"])
    
    st.markdown("---")
    if st.session_state.selected_device:
        st.success(f"Active System:\n**{st.session_state.selected_device}**")
        if st.button(t["change_device"], use_container_width=True):
            st.session_state.selected_device = None
            st.session_state.current_page = "Home"
            st.rerun()

# -----------------------------------------------------------------------------
# 7. UI Layout & Logic
# -----------------------------------------------------------------------------
st.title(f"🔬 {t['title']}")
st.caption(t["subtitle"])
st.markdown("---")

if st.session_state.selected_device is None:
    st.subheader(f"📊 {t['select_device']}")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="glass-card"><h2>cobas e 411 analyzer</h2><p>Immunochemistry Platform</p></div>', unsafe_allow_html=True)
        if st.button("Select cobas e 411", key="btn_e411", use_container_width=True, type="primary"):
            st.session_state.selected_device = "cobas e 411 analyzer"
            st.session_state.current_page = "AI"
            st.rerun()
    with col2:
        st.markdown('<div class="glass-card"><h2>cobas c 311 analyzer</h2><p>Clinical Chemistry System</p></div>', unsafe_allow_html=True)
        if st.button("Select cobas c 311", key="btn_c311", use_container_width=True, type="primary"):
            st.session_state.selected_device = "cobas c 311 analyzer"
            st.session_state.current_page = "AI"
            st.rerun()
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

    if st.session_state.current_page == "AI":
        st.subheader(f"🤖 {t['option_ai']} — {st.session_state.selected_device}")
        
        with st.spinner("Processing & indexing manual slides..."):
            index, chunks = process_manuals_rag(".")
            
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if user_prompt := st.chat_input(t["ask_placeholder"]):
            st.session_state.messages.append({"role": "user", "content": user_prompt})
            with st.chat_message("user"):
                st.markdown(user_prompt)

            with st.chat_message("assistant"):
                with st.spinner("Analyzing slide & generating smart response..."):
                    response = query_flexible_ai(
                        user_prompt, 
                        index, 
                        chunks, 
                        st.session_state.selected_device, 
                        st.session_state.lang
                    )
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

    elif st.session_state.current_page == "Manual":
        st.subheader(f"📖 {t['option_manual']} — {st.session_state.selected_device}")
        target_keyword = "e411" if "e 411" in st.session_state.selected_device else "c311"
        found_files = glob.glob(f"*{target_keyword}*")
        if found_files:
            pdf_path = found_files[0]
            with open(pdf_path, "rb") as f:
                st.download_button("📥 Download Official Technical Manual (PDF)", f, file_name=os.path.basename(pdf_path), use_container_width=True)
        else:
            st.info("💡 PDF file is missing.")

    elif st.session_state.current_page == "Parts":
        st.subheader(f"🔬 {t['option_parts']} — {st.session_state.selected_device}")
        st.markdown('<div class="glass-card"><h3>ECL Measuring Cell Assembly</h3><p>Electrochemiluminescence detection core.</p></div>', unsafe_allow_html=True)
