import streamlit as st
from audio_recorder_streamlit import audio_recorder
import whisper
import tempfile
import os
import io
from docx import Document
import google.generativeai as genai

# 1. Cấu hình trang
st.set_page_config(page_title="AI Smart Note Pro", page_icon="🔐", layout="wide")
st.title("🔐 Ghi Chú & Tóm Tắt (Secure Mode)")

# 2. Xử lý API Key từ Secrets
# Kiểm tra xem key có tồn tại trong secrets không
api_key = None
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
else:
    st.error("⚠️ Chưa tìm thấy API Key. Vui lòng cấu hình trong secrets.toml (Local) hoặc App Settings (Cloud).")
    st.stop() # Dừng ứng dụng nếu không có key

# Cấu hình Gemini ngay lập tức
genai.configure(api_key=api_key)

# 3. Khởi tạo Session State
if 'notes' not in st.session_state:
    st.session_state.notes = []

# 4. Tải mô hình Whisper (Cache để không load lại)
@st.cache_resource
def load_whisper_model():
    model = whisper.load_model("base")
    return model

with st.spinner("Đang khởi động hệ thống AI..."):
    model = load_whisper_model()

# 5. Hàm xử lý âm thanh (Whisper)
def transcribe_audio(audio_bytes):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
        temp_audio.write(audio_bytes)
        temp_filename = temp_audio.name

    try:
        result = model.transcribe(temp_filename, language="vi")
        return result["text"]
    except Exception as e:
        return f"Lỗi Whisper: {e}"
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

# 6. Hàm tóm tắt nội dung (Gemini)
def summarize_text(text):
    try:
        model_gemini = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        Bạn là thư ký chuyên nghiệp. Nhiệm vụ:
        1. Sửa lỗi chính tả/ngữ pháp.
        2. Tóm tắt ý chính.
        3. Trích xuất danh sách việc cần làm (Action Items).
        
        Văn bản gốc: "{text}"
        """
        response = model_gemini.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Không thể tóm tắt: {e}"

# 7. Hàm tạo file Word
def create_docx(original_text, summary_text):
    doc = Document()
    doc.add_heading('Biên bản ghi chú AI', 0)
    
    doc.add_heading('1. Tóm tắt & Hành động', level=1)
    doc.add_paragraph(summary_text)
    
    doc.add_heading('2. Gỡ băng chi tiết', level=1)
    doc.add_paragraph(original_text)
    
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# 8. Giao diện chính
col_left, col_right = st.columns([1, 2])

with col_left:
    st.info("🎙️ Nhấn micro để bắt đầu:")
    audio_bytes = audio_recorder(
        text="",
        recording_color="#ff4b4b",
        neutral_color="#333333",
        icon_name="microphone",
        icon_size="3x",
    )

if audio_bytes:
    st.audio(audio_bytes, format="audio/wav")
    
    # Bước 1: Whisper
    with st.spinner("Đang gỡ băng ghi âm..."):
        transcript = transcribe_audio(audio_bytes)
    
    if transcript:
        st.success("Đã nghe xong!")
        
        # Bước 2: Gemini (Đã có key từ secrets)
        with st.spinner("AI đang phân tích và tóm tắt..."):
            summary = summarize_text(transcript)

        # Hiển thị kết quả
        tab1, tab2 = st.tabs(["📝 Tóm tắt AI", "📄 Văn bản gốc"])
        with tab1:
            st.markdown(summary)
        with tab2:
            st.write(transcript)

        # Nút tải về
        st.divider()
        docx_file = create_docx(transcript, summary)
        st.download_button(
            label="📥 Tải biên bản Word (.docx)",
            data=docx_file,
            file_name="bien_ban_ai.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

        # Lưu lịch sử
        note_data = {"original": transcript, "summary": summary}
        if not st.session_state.notes or st.session_state.notes[-1]["original"] != transcript:
            st.session_state.notes.append(note_data)

# 9. Lịch sử
st.divider()
with st.expander("Xem lịch sử"):
    if st.session_state.notes:
        for i, note in enumerate(reversed(st.session_state.notes)):
            st.markdown(f"**Ghi chú {len(st.session_state.notes) - i}**")
            st.caption(note["summary"][:150] + "...")
            st.markdown("---")
