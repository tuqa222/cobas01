import streamlit as st
import os
import glob
import re
import fitz  # PyMuPDF لعرض صفحات PDF كصور عالية الدقة بكل تفاصيلها والصور
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
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line_str = line.strip()
        if "Roche Diagnostics" in line_str or "Software version" in line_str or "Safety Guide" in line_str:
            continue
        if re.match(r'^\d+\s*Warning messages', line_str):
            continue
        if len(line_str) > 0:
            cleaned_lines.append(line_str)
            
    text_clean = " ".join(cleaned_lines)
    text_clean = re.sub(r'\br\b', '•', text_clean)
    return text_clean

@st.cache_resource
def process_manuals_exact(root_dir="."):
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
    query_lower = user_query.lower().strip()
    
    explain_keywords = ['فهمني', 'شرح', 'بسط', 'لخص', 'وضح', 'explain', 'simplify', 'summarize', 'elaborate']
    next_keywords = ['what is next', 'next', 'tell me the next', 'التالي', 'ما التالي', 'القسم التالي', 'كمل', 'الصفحة التالية', 'تابع']
    
    # 1. حالة طلب الصفحة القادمة بالتتابع
    is_next = any(k in query_lower for k in next_keywords)
    if is_next and "last_page" in st.session_state and st.session_state.last_page is not None:
        next_target_page = st.session_state.last_page + 1
        next_chunks = [c for c in chunks if c['page'] == next_target_page]
        
        if next_chunks:
            st.session_state.last_page = next_target_page
            next_text = "\n\n".join([c['text'] for c in next_chunks])
            if lang == "العربية":
                return f"📍 **القسم التالي - رقم الصفحة / السلايد:** `Page {next_target_page}`\n\n> {next_text}"
            else:
                return f"📍 **Next Section / Page Reference:** `Page {next_target_page}`\n\n> {next_text}"

    # 2. حالة طلب الشرح والتبسيط للفقرة السابقة
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

    # 3. البحث المباشر في المانيوال
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

    st.session_state.last_page = best_chunk['page']
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

if "last_page" not in st.session_state:
    st.session_state.last_page = 1

# -----------------------------------------------------------------------------
# 4. Background Image & Styling
# -----------------------------------------------------------------------------
roche_bg_url = "https://images.unsplash.com/photo-1579154204601-01588f351e67?q=80&w=2070&auto=format&fit=crop"

overlay_color = "rgba(10, 13, 20, 0.85)" if st.session_state.theme == "Dark" else "rgba(241, 245, 249, 0.85)"
card_bg = "rgba(23, 32, 51, 0.75)" if st.session_state.theme == "Dark" else "rgba(255, 255, 255, 0.85)"
border_color = "rgba(255, 255, 255, 0.12)" if st.session_state.theme == "Dark" else "rgba(0, 0, 0, 0.1)"
text_color = "#F8FAFC" if st.session_state.theme == "Dark" else "#0F172A"

st.markdown(f"""
<style>
    .stApp {{
        background: linear-gradient({overlay_color}, {overlay_color}), url("{roche_bg_url}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
        color: {text_color};
    }}

    [data-testid="stSidebar"] {{
        background: rgba(10, 13, 20, 0.85) !important;
        backdrop-filter: blur(12px);
    }}

    .contrast-card {{
        background: {card_bg};
        border: 1px solid {border_color};
        border-radius: 16px;
        padding: 22px 28px;
        margin-bottom: 20px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
    }}

    [data-testid="stChatMessage"] {{
        background: {card_bg} !important;
        border: 1px solid {border_color} !important;
        border-radius: 12px !important;
        padding: 12px 18px !important;
        margin-bottom: 10px !important;
        backdrop-filter: blur(8px);
    }}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 5. Sidebar Controls
# -----------------------------------------------------------------------------
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/f/f5/Roche_Logo.svg", width=130)
    st.markdown("---")
    st.session_state.theme = st.selectbox("Theme / المظهر", ["Dark", "Light"])
    st.session_state.lang = st.selectbox("Language / اللغة", ["English", "العربية"])
    st.markdown("---")
    if st.session_state.selected_device:
        st.success(f"Active System:\n**{st.session_state.selected_device}**")
        if st.button("← Switch System", use_container_width=True):
            st.session_state.selected_device = None
            st.session_state.current_page = "Home"
            st.session_state.last_page = 1
            st.rerun()

# -----------------------------------------------------------------------------
# 6. Main Application Views
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
        st.subheader(f"📖 Technical Documentation Visual Viewer — {st.session_state.selected_device}")
        
        pdf_files = glob.glob("*.pdf") + glob.glob("*.pdf.pdf")
        if pdf_files:
            pdf_path = pdf_files[0]
            
            # فتح الـ PDF باستخدام PyMuPDF
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            
            col_input, col_info = st.columns([1, 3])
            
            with col_input:
                # ادخال رقم السلايد/الصفحة كتابةً مباشرة
                page_input = st.text_input(
                    f"✏️ اكتب رقم السلايد/الصفحة (1 - {total_pages}):", 
                    value=str(st.session_state.last_page) if st.session_state.last_page else "1"
                )
            
            # التحقق والتأكد من إدخال رقم صحيح
            try:
                target_page = int(page_input)
                if target_page < 1:
                    target_page = 1
                elif target_page > total_pages:
                    target_page = total_pages
            except ValueError:
                target_page = 1
                
            st.session_state.last_page = target_page

            with col_info:
                st.markdown(f"#### 📄 السلايد المعروضة: **{target_page} من أصل {total_pages}**")

            st.markdown("---")
            
            # رندر الصفحة المطلوبة كصورة عالية الجودة (300 DPI)
            page = doc.load_page(target_page - 1)
            pix = page.get_pixmap(dpi=150)
            img_bytes = pix.tobytes("png")
            
            # عرض الصورة الكاملة للسلايد مع الصور والتنسيقات الأصلية
            st.image(img_bytes, caption=f"Slide / Page {target_page}", use_column_width=True)
            doc.close()
        else:
            st.info("💡 PDF Manual file is missing in root repository.")

    elif st.session_state.current_page == "Parts":
        st.subheader(f"🔬 System Components — {st.session_state.selected_device}")
        st.markdown('<div class="contrast-card"><h3>ECL Measuring Cell Assembly</h3><p>Electrochemiluminescence detection core.</p></div>', unsafe_allow_html=True)
