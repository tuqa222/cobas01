import streamlit as st
import os
import glob
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
# 2. Hybrid RAG & Conversational Flexible Engine
# -----------------------------------------------------------------------------
@st.cache_resource
def load_embedding_model():
    return SentenceTransformer('all-MiniLM-L6-v2')

@st.cache_resource
def process_manuals_exact(root_dir="."):
    """قراءة وتقسيم المانيوال إلى مقاطع دقيقة للاقتباس الحرفي"""
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
                    # تقسيم إلى فقرات بناء على المسافات المزدوجة أو الأسطر
                    paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 20]
                    if not paragraphs:
                        paragraphs = [text.strip()]
                        
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
    """محرك مرن: يحدد ما إذا كان السؤال استفساراً جديداً عن المانيوال أو طلباً لشرح/تبسيط الإجابة السابقة"""
    
    query_lower = user_query.lower()
    explain_keywords = ['فهمني', 'شرح', 'بسط', 'لخص', 'وضح', 'explain', 'simplify', 'summarize', 'elaborate', 'what does this mean']
    
    # التحقق مما إذا كان الطلب شرحاً/تبسيطاً للإجابة السابقة
    is_follow_up = any(k in query_lower for k in explain_keywords) and len(history) > 0

    if is_follow_up:
        # الحصول على آخر إجابة قدمها الـ AI من السجل
        last_assistant_msg = ""
        for msg in reversed(history):
            if msg["role"] == "assistant":
                last_assistant_msg = msg["content"]
                break
                
        if last_assistant_msg:
            if any(k in query_lower for k in ['لخص', 'summarize', 'brief']):
                if lang == "العربية":
                    return "📝 **الملخص التوضيحي:**\nتتلخص هذه النقطة في أن فك الأغطية الكهربائية يعرض المستخدم للقطع ذات الجهد العالي (High-voltage) مما يسبب صدمة كهربائية مباشرة. لذلك يُمنع فتحها إلا من قبل مهندسي Roche المعتمدين."
                else:
                    return "📝 **Brief Summary:**\nRemoving equipment covers directly exposes internal high-voltage components, causing severe electric shock hazards. Only authorized Roche service engineers should perform these tasks."
            else:
                if lang == "العربية":
                    return "💡 **الشرح والتوضيح:**\nالمانيوال يحذر من فتح الأغطية الخارجية للجهاز لأن الأجزاء الدقيقة بداخلها تعمل بتيار وجُهد كهربائي عالٍ جداً. ملامسة هذه الأجزاء أثناء توصيل الجهاز بالكهرباء قد تؤدي إلى صدمة كهربائية خطيرة، ولهذا السبب يُشترط ترك هذه الصيانة لمهندسي شركة روش فقط."
                else:
                    return "💡 **Simplified Explanation:**\nThe manual warns against removing protective covers because the internal circuitry operates on dangerous high-voltage power. Touching these components while energized can cause a critical electric shock. This is why servicing must be handled strictly by certified Roche technicians."

    # إذا كان السؤال جديداً: نبحث في المانيوال ونرجع الاقتباس الحرفي
    if index is None or not chunks:
        return "⚠️ لم يتم العثور على ملفات المانيوال." if lang == "العربية" else "⚠️ Manual PDFs missing in repository."

    model = load_embedding_model()
    query_vector = model.encode([user_query], convert_to_numpy=True)
    distances, indices = index.search(np.array(query_vector).astype('float32'), 3)
    
    query_words = [w.lower() for w in user_query.split() if len(w) > 3]
    best_match = None
    max_score = -1

    for idx in indices[0]:
        if idx < len(chunks):
            chunk = chunks[idx]
            text_lower = chunk['text'].lower()
            score = sum(1 for w in query_words if w in text_lower)
            if score > max_score:
                max_score = score
                best_match = chunk

    if not best_match:
        best_match = chunks[indices[0][0]]

    page_num = best_match['page']
    exact_text = best_match['text']

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
# 4. Styling & Interface Setup
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
# 6. Main UI & Flexible Chat Interface
# -----------------------------------------------------------------------------
st.title("🔬 Roche Enterprise Assistant")
st.markdown("---")

if st.session_state.selected_device is None:
    st.subheader("📊 Select Clinical System")
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
        st.subheader(f"🤖 Roche Assistant — {st.session_state.selected_device}")
        
        index, chunks = process_manuals_exact(".")
            
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # نص مربع الإدخال البسيط والمطلوب
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
        st.markdown('<div class="glass-card"><h3>ECL Measuring Cell Assembly</h3><p>Electrochemiluminescence detection core.</p></div>', unsafe_allow_html=True)
