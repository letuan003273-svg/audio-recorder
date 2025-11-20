import streamlit as st
from audio_recorder_streamlit import audio_recorder
import whisper
import tempfile
import os

# 1. Cấu hình trang
st.set_page_config(page_title="Whisper Note", page_icon="🧠")
st.title("🧠 Ghi Chú Thông Minh với OpenAI Whisper")

# 2. Khởi tạo Session State
if 'notes' not in st.session_state:
    st.session_state.notes = []

# 3. Tải mô hình Whisper (QUAN TRỌNG: Dùng Cache)
# Chúng ta dùng @st.cache_resource để chỉ tải mô hình 1 lần duy nhất
# giúp ứng dụng không bị chậm khi tải lại trang.
@st.cache_resource
def load_whisper_model():
    # "base" là mô hình cân bằng giữa tốc độ và độ chính xác.
    # Bạn có thể đổi thành "tiny" (nhanh hơn, kém hơn) hoặc "small" (chậm hơn, tốt hơn)
    model = whisper.load_model("base")
    return model

# Hiển thị thông báo đang tải model (chỉ hiện lần đầu)
with st.spinner("Đang tải mô hình AI... Vui lòng đợi giây lát"):
    model = load_whisper_model()

# 4. Hàm xử lý âm thanh với Whisper
def transcribe_audio(audio_bytes):
    # Whisper cần đọc từ file, không đọc trực tiếp từ bytes được
    # Nên ta tạo một file tạm thời
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
        temp_audio.write(audio_bytes)
        temp_filename = temp_audio.name

    try:
        # Gọi mô hình để nhận diện
        result = model.transcribe(temp_filename, language="vi")
        return result["text"]
    except Exception as e:
        return f"Lỗi: {e}"
    finally:
        # Dọn dẹp: Xóa file tạm sau khi dùng xong
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

# 5. Giao diện ghi âm
st.write("Nhấn micro để ghi âm (Mô hình Base có thể mất vài giây để xử lý).")
audio_bytes = audio_recorder(
    text="",
    recording_color="#ff4b4b",
    neutral_color="#333333",
    icon_name="microphone",
    icon_size="2x",
)

# 6. Xử lý logic khi có âm thanh
if audio_bytes:
    st.audio(audio_bytes, format="audio/wav")
    
    with st.spinner("AI đang nghe và phân tích..."):
        transcript = transcribe_audio(audio_bytes)
        
        if transcript:
            st.success("Hoàn tất!")
            st.subheader("📝 Nội dung:")
            st.info(transcript)
            
            # Lưu vào lịch sử (tránh lưu trùng lặp nếu app reload)
            if not st.session_state.notes or st.session_state.notes[-1] != transcript:
                st.session_state.notes.append(transcript)

# 7. Hiển thị lịch sử
st.divider()
st.header("Lịch sử Ghi chú")
if st.session_state.notes:
    for i, note in enumerate(reversed(st.session_state.notes)):
        st.markdown(f"**Ghi chú {len(st.session_state.notes) - i}:**")
        st.write(note)
        st.markdown("---")
else:
    st.caption("Chưa có ghi chú nào.")
