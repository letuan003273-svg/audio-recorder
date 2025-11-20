import streamlit as st
from audio_recorder_streamlit import audio_recorder
import whisper
import tempfile
import os
import io
from docx import Document
import google.generativeai as genai

# 1. Cấu hình trang
st.set_page_config(page_title="AI Note Mobile", page_icon="🎙️", layout="centered") # Đổi layout thành centered để đẹp hơn trên mobile

# --- PHẦN CSS TÙY CHỈNH (RESPONSIVE) ---
st.markdown("""
    <style>
        /* Import Font */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        /* Style cho hộp ghi âm */
        .recording-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            background-color: #f0f2f6;
            border-radius: 20px;
            padding: 20px;
            margin-top: 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            border: 2px solid #e0e0e0;
        }

        /* Nhãn hướng dẫn trạng thái */
        .status-label {
            font-weight: bold;
            margin-bottom: 10px;
            color: #555;
            font-size: 1.1rem;
        }

        .instruction-text {
            font-size: 0.9rem;
            color: #888;
            margin-top: 5px;
            text-align: center;
        }

        /* --- MOBILE RESPONSIVE --- */
        /* Khi màn hình nhỏ hơn 600px (Điện thoại) */
        @media only screen and (max-width: 600px) {
            h1 {
                font-size: 1.8rem !important; /* Tiêu đề nhỏ lại */
            }
            .stButton > button {
                width: 100%; /* Nút bấm full màn hình */
                padding: 15px;
            }
            .recording-container {
                padding: 10px; /* Giảm padding để tiết kiệm chỗ */
            }
            /* Ẩn sidebar mặc định trên mobile để gọn (Streamlit tự làm, nhưng ta chỉnh padding) */
            .block-container {
                padding-top: 2rem;
                padding-left: 1rem;
                padding-right: 1rem;
            }
        }
    </style>
""", unsafe_allow_html=True)
# --------------------------

# 2. Xử lý API Key
api_key = None
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
else:
    st.error("⚠️ Vui lòng cấu hình GOOGLE_API_KEY trong Secrets.")
    st.stop()

# 3. Session State
if 'notes' not in st.session_state:
    st.session_state.notes = []

# 4. Hàm chức năng (Giữ nguyên)
@st.cache_resource
def load_whisper_model():
    return whisper.load_model("base")

model = load_whisper_model()

def transcribe_audio(audio_bytes):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
        temp_audio.write(audio_bytes)
        temp_filename = temp_audio.name
    try:
        result = model.transcribe(temp_filename, language="vi")
        return result["text"]
    except Exception as e:
        return f"Lỗi: {e}"
    finally:
        if os.path.exists(temp_filename): os.remove(temp_filename)

def summarize_text(text):
    try:
        model_gemini = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"Sửa lỗi chính tả, tóm tắt ý chính và liệt kê hành động từ văn bản sau: '{text}'"
        response = model_gemini.generate_content(prompt)
        return response.text
    except Exception as e:
        return str(e)

def create_docx(original, summary):
    doc = Document()
    doc.add_heading('Biên bản AI', 0)
    doc.add_heading('Tóm tắt', 1)
    doc.add_paragraph(summary)
    doc.add_heading('Chi tiết', 1)
    doc.add_paragraph(original)
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- GIAO DIỆN CHÍNH ---

st.title("🎙️ AI Ghi Chú")

# Hộp ghi âm (Custom HTML Wrapper)
st.markdown('<div class="recording-container">', unsafe_allow_html=True)

# Hiển thị trạng thái bằng màu sắc icon
# Lưu ý: Streamlit chạy lại code từ đầu khi có tương tác.
# audio_recorder tự quản lý trạng thái JS của nó.
st.markdown('<div class="status-label">Trạng thái Micro</div>', unsafe_allow_html=True)

# Component Ghi âm
# pause_threshold=10.0: Chỉ dừng nếu im lặng quá 10 giây (giúp tránh dừng đột ngột)
audio_bytes = audio_recorder(
    text="", # Không dùng text mặc định của thư viện để ta tự custom label
    recording_color="#ff2b2b", # Màu đỏ tươi khi đang ghi
    neutral_color="#3d3d3d",   # Màu đen xám khi chờ
    icon_name="microphone",
    icon_size="4x",            # Icon to dễ bấm trên điện thoại
    pause_threshold=10.0       # Tăng ngưỡng im lặng để không tự tắt
)

# Hướng dẫn dưới nút
st.markdown("""
    <div class="instruction-text">
    ⚫ Màu đen: Nhấn để BẮT ĐẦU<br>
    🔴 Màu đỏ: Đang ghi (Nhấn lại để DỪNG)
    </div>
    </div>
""", unsafe_allow_html=True)


# Xử lý kết quả
if audio_bytes:
    st.audio(audio_bytes, format="audio/wav")
    
    with st.status("⏳ Đang xử lý âm thanh...", expanded=True) as status:
        st.write("Whisper: Đang gỡ băng...")
        transcript = transcribe_audio(audio_bytes)
        
        st.write("Gemini: Đang tóm tắt...")
        summary = summarize_text(transcript)
        
        status.update(label="✅ Xử lý hoàn tất!", state="complete", expanded=False)

    # Hiển thị kết quả (Dùng Tabs cho gọn trên mobile)
    st.divider()
    tab1, tab2 = st.tabs(["📝 Tóm tắt", "📄 Chi tiết"])
    
    with tab1:
        st.info(summary)
    
    with tab2:
        st.write(transcript)

    # Nút tải về
    st.markdown("<br>", unsafe_allow_html=True)
    docx = create_docx(transcript, summary)
    st.download_button(
        label="📥 Tải Word (.docx)",
        data=docx,
        file_name="SmartNote_Mobile.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        use_container_width=True # Quan trọng: Nút rộng full trên mobile
    )

    # Lưu lịch sử
    note_data = {"original": transcript, "summary": summary}
    if not st.session_state.notes or st.session_state.notes[-1]["original"] != transcript:
        st.session_state.notes.append(note_data)

# Lịch sử (Rút gọn)
if st.session_state.notes:
    st.divider()
    st.caption(f"Lịch sử ({len(st.session_state.notes)} bản ghi)")
    with st.expander("Xem lại các ghi chú cũ"):
        for i, note in enumerate(reversed(st.session_state.notes)):
             st.markdown(f"**#{len(st.session_state.notes)-i}** - {note['summary'][:80]}...")
             st.markdown("---")
