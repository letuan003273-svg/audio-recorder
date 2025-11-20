import streamlit as st
from audio_recorder_streamlit import audio_recorder
import whisper
import tempfile
import os
import io
from docx import Document # Thư viện xử lý Word

# 1. Cấu hình trang
st.set_page_config(page_title="Whisper Note Pro", page_icon="📝")
st.title("📝 Ghi Chú & Xuất File Word")

# 2. Khởi tạo Session State
if 'notes' not in st.session_state:
    st.session_state.notes = []

# 3. Tải mô hình Whisper
@st.cache_resource
def load_whisper_model():
    # Sử dụng model "base"
    model = whisper.load_model("base")
    return model

with st.spinner("Đang tải hệ thống AI..."):
    model = load_whisper_model()

# 4. Hàm xử lý âm thanh
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
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

# 5. Hàm tạo file Word (MỚI)
def create_docx(text):
    doc = Document()
    doc.add_heading('Ghi chú giọng nói', 0)
    doc.add_paragraph(text)
    
    # Lưu file vào bộ nhớ đệm (RAM) thay vì ổ cứng
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0) # Đưa con trỏ về đầu file để sẵn sàng đọc
    return buffer

# 6. Giao diện chính
st.write("Nhấn micro để ghi âm:")
audio_bytes = audio_recorder(
    text="",
    recording_color="#ff4b4b",
    neutral_color="#333333",
    icon_name="microphone",
    icon_size="2x",
)

# 7. Xử lý kết quả và hiển thị nút tải xuống
if audio_bytes:
    st.audio(audio_bytes, format="audio/wav")
    
    with st.spinner("Đang chuyển đổi giọng nói..."):
        transcript = transcribe_audio(audio_bytes)
        
        if transcript:
            st.success("Đã xong!")
            st.subheader("Nội dung:")
            st.info(transcript)
            
            # --- PHẦN MỚI: CÁC NÚT TẢI XUỐNG ---
            col1, col2 = st.columns(2)
            
            # Nút tải file TXT
            with col1:
                st.download_button(
                    label="📥 Tải file .txt",
                    data=transcript,
                    file_name="ghi_chu.txt",
                    mime="text/plain"
                )
            
            # Nút tải file Word
            with col2:
                docx_file = create_docx(transcript)
                st.download_button(
                    label="📥 Tải file Word (.docx)",
                    data=docx_file,
                    file_name="ghi_chu.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            # -------------------------------------

            # Lưu vào lịch sử
            if not st.session_state.notes or st.session_state.notes[-1] != transcript:
                st.session_state.notes.append(transcript)

# 8. Lịch sử
st.divider()
st.header("Lịch sử gần đây")
if st.session_state.notes:
    for i, note in enumerate(reversed(st.session_state.notes)):
        st.text(f"Ghi chú {len(st.session_state.notes) - i}:")
        st.caption(note[:100] + "..." if len(note) > 100 else note) # Chỉ hiện 100 ký tự đầu
        st.markdown("---")
else:
    st.caption("Chưa có dữ liệu.")
