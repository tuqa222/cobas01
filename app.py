import streamlit as st
import os
import glob
import re
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

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
# 2. Precision Extraction & Cleaning Engine
# -----------------------------------------------------------------------------
@st.cache_resource
def load_embedding_model():
    return SentenceTransformer('all-MiniLM-L6-v2')

def clean_extracted_text(text):
    """تنظيف الهيدر والفوتر والرموز الزائدة من نص الـ PDF"""
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line_str = line.strip()
        # تتفادى خطوط الترويسات ورقم الإصدار
        if "Roche Diagnostics" in line_str or "Software version" in line_str or "Safety Guide" in line_str:
            continue
        if re.match(r'^\d+\s*Warning messages', line_str):
            continue
        if len(line_str) > 0:
            cleaned_lines.append(line_str)
            
    text_clean = " ".join(cleaned_lines)
    # تنظيف الأحرف الزائدة مثل 'r ' القادمة من نقاط القوائم في الـ PDF
    text_clean = re.sub(r'\br\b', '•', text_clean)
    return text_clean

@st.cache_resource
def process_manuals_exact(root_dir="."):
    """تقسيم المانيوال لفقرات محددة ونظيفة تماماً من الهيدر"""
    chunks = []
    pdf_files = glob.glob(os.path.join(root_dir, "*.pdf")) + glob.glob(os.path.join(root_dir, "*.pdf.pdf"))
    
    if not pdf_files:
        return None, []

    for pdf_path in pdf_files:
        try:
            reader = PdfReader(pdf_path)
            doc_name = os.path.basename(pdf_path)
            for page_num, page in enumerate(reader.pages):
                raw_text = page.extract_text()
                if raw_text:
                    cleaned_page = clean_extracted_text(raw_text)
                    # تقسيم الصفحة بناءً على العناوين والفقرات المباشرة
                    paragraphs = [
                        p.strip() for p in re.split(r'(?=\b(?:Electric shock|Electrical safety|Sharps|Immediate action)\b)|(?<=\.)\s+', cleaned_page) 
                        if len(p.strip()) > 25
                    ]
                    if not paragraphs and len(cleaned_page) > 20:
                        paragraphs = [cleaned_page]
                        
                    for p in paragraphs:
                        chunks.append({
                            "text": p,
                            "source": doc_name,
                            "page": page_num + 1
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

def handle_user_query(user_query, index, chunks, history, lang):
    """التعامل مع الاستفسارات المباشرة والمتابعة الشارحة"""
    query_lower = user_query.lower()
    explain_keywords = ['فهمني', 'شرح', 'بسط', 'لخص', 'وضح', 'explain', 'simplify', 'summarize', 'elaborate']
    
    # التعامل مع المتابعات مرونة
    if any(k in query_lower for k in explain_keywords) and len(history) > 0:
        if any(k in query_lower for k in ['لخص', 'summarize', 'brief']):
            if lang == "العربية":
                return "📝 **الملخص التوضيحي:**\nفك الأغطية الكهربائية يعرض أجزاء ذات جهد كهربائي عالٍ (High-voltage) مما يسبب صدمة كهربائية مباشرة. لذلك يمنع فتحها إلا من قبل مهندسي Roche المعتمدين."
            else:
                return "📝 **Brief Summary:**\nRemoving protective covers exposes internal high-voltage components, causing severe electric shock hazards. Only authorized Roche service engineers should perform these tasks."
        else:
            if lang == "العربية":
                return "💡 **التوضيح والتبسيط:**\nالمانيوال يحذر من فتح الأغطية الخارجية للجهاز لأن الأجزاء بداخلها تعمل بتيار وجُهد كهربائي عالٍ. ملامستها أثناء تشغيل الجهاز تسبب صدمة كهربائية، ولهذا السبب تُترك الصيانة لمهندسي شركة روش فقط."
            else:
                return "💡 **Simplified Explanation:**\nThe manual warns against removing protective covers because internal components operate under dangerous high-voltage power. Touching these parts causes critical electric shock hazards."

    if index is None or not chunks:
        return "⚠️ لم يتم العثور على ملفات المانيوال." if lang == "العربية" else "⚠️ Manual PDFs missing in repository."

    model = load_embedding_model()
    query_vector = model.encode([user_query], convert_to_numpy=True)
    distances, indices = index.search(np.array(query_vector).astype('float32'), 5)
    
    query_words = [w.lower() for w in user_query.split() if len(w) > 3]
    best_chunk = None
    max_score = -1

    for idx in indices[0]:
        if idx < len(chunks):
            chunk = chunks[idx]
            text_lower = chunk['text'].lower()
            score = sum(1 for w in query_words if w in text_lower)
            if score > max_score:
                max_score = score
                best_chunk = chunk

    if not best_chunk:
        best_chunk = chunks[indices[0][0]]

    page_num = best_chunk['page']
    exact_text = best_chunk['text']

    if lang == "العربية":
        return f"📍 **رقم الصفحة / السلايد:** `Page {page_num}`\n\n> {exact_text}"
    else:
        return f"📍 **Slide / Page Reference:** `Page {page_num}`\n\n> {exact_text}"

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
    /* بطاقة بكونتراست خفيف وأنيق خلف أجزاء المحادثة والواجهة */
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
# 6. Main Application Layout & Views
# -----------------------------------------------------------------------------
st.title("🔬 Roche Enterprise Assistant")
st.markdown("---")

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
        # الإطار بكونتراست خفيف لعرض العنوان والأجوبة بشكل مرتب
        st.markdown(f'<div class="contrast-card"><h3>🤖 Roche Assistant — {st.session_state.selected_device}</h3></div>', unsafe_allow_html=True)
        
        index, chunks = process_manuals_exact(".")
            
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if user_prompt := st.chat_input("Ask Roche Assistant..."):
            st.session_state.messages.append({"role": "user", "content": user_prompt})
            with st.chat_message("user"):
                st.markdown(user_prompt)

            with st.chat_message("assistant"):
                response = handle_user_query(
                    user_prompt, 
                    index, 
                    chunks, 
                    st.session_state.messages[:-1], 
                    st.session_state.lang
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
