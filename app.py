import streamlit as st
from audio_recorder_streamlit import audio_recorder
import whisper
import tempfile
import os
import io
from docx import Document
import google.generativeai as genai # Thư viện Google Gemini

# 1. Cấu hình trang
st.set_page_config(page_title="AI Smart Note", page_icon="🧠", layout="wide")
st.title("🧠 Ghi Chú & Tóm Tắt Tự Động")

# 2. Sidebar: Cấu hình API
with st.sidebar:
    st.header("Cài đặt AI")
    api_key = st.text_input("Nhập Google Gemini API Key:", type="password")
    st.caption("Lấy key miễn phí tại: [Google AI Studio](https://aistudio.google.com/)")
    if not api_key:
        st.warning("Vui lòng nhập API Key để dùng tính năng Tóm tắt.")

# 3. Khởi tạo Session State
if 'notes' not in st.session_state:
    st.session_state.notes = []

# 4. Tải mô hình Whisper
@st.cache_resource
def load_whisper_model():
    model = whisper.load_model("base")
    return model

with st.spinner("Đang khởi động AI..."):
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

# 6. Hàm tóm tắt nội dung (Gemini) - MỚI
def summarize_text(text, api_key):
    try:
        genai.configure(api_key=api_key)
        model_gemini = genai.GenerativeModel('gemini-2.5-flash') # Model nhanh và rẻ (free tier)
        
        prompt = f"""
        Bạn là một trợ lý thư ký chuyên nghiệp. Hãy thực hiện các việc sau với văn bản bên dưới:
        1. Sửa lỗi chính tả nếu có.
        2. Tóm tắt nội dung chính thành các gạch đầu dòng ngắn gọn.
        3. Trích xuất danh sách công việc cần làm (nếu có).
        
        Văn bản: "{text}"
        """
        response = model_gemini.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Không thể tóm tắt: {e}"

# 7. Hàm tạo file Word (Cập nhật thêm phần tóm tắt)
def create_docx(original_text, summary_text):
    doc = Document()
    doc.add_heading('Biên bản ghi chú', 0)
    
    doc.add_heading('1. Tóm tắt & Hành động', level=1)
    doc.add_paragraph(summary_text)
    
    doc.add_heading('2. Nội dung chi tiết (Gỡ băng)', level=1)
    doc.add_paragraph(original_text)
    
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# 8. Giao diện chính
col_left, col_right = st.columns([1, 2])

with col_left:
    st.write("🎙️ **Ghi âm tại đây:**")
    audio_bytes = audio_recorder(
        text="",
        recording_color="#ff4b4b",
        neutral_color="#333333",
        icon_name="microphone",
        icon_size="3x",
    )

if audio_bytes:
    st.audio(audio_bytes, format="audio/wav")
    
    # Bước 1: Chuyển đổi giọng nói (Whisper)
    with st.spinner("Whisper đang nghe..."):
        transcript = transcribe_audio(audio_bytes)
    
    if transcript:
        st.success("Đã nghe xong!")
        
        # Bước 2: Tóm tắt (Gemini)
        summary = ""
        if api_key:
            with st.spinner("Gemini đang đọc và tóm tắt..."):
                summary = summarize_text(transcript, api_key)
        else:
            summary = "Bạn chưa nhập API Key nên không có tóm tắt."

        # Hiển thị kết quả chia 2 cột
        tab1, tab2 = st.tabs(["📝 Tóm tắt & Sửa lỗi", "📄 Văn bản gốc"])
        
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
            file_name="bien_ban_hop.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

        # Lưu lịch sử
        note_data = {"original": transcript, "summary": summary}
        if not st.session_state.notes or st.session_state.notes[-1]["original"] != transcript:
            st.session_state.notes.append(note_data)

# 9. Hiển thị lịch sử
st.divider()
with st.expander("Xem lịch sử các bản ghi trước"):
    if st.session_state.notes:
        for i, note in enumerate(reversed(st.session_state.notes)):
            st.markdown(f"**Ghi chú {len(st.session_state.notes) - i}**")
            st.text("Tóm tắt:")
            st.caption(note["summary"][:200] + "...") # Hiện 1 phần tóm tắt
            st.markdown("---")
    else:
        st.write("Chưa có dữ liệu.")
