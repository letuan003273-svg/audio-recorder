import streamlit as st
import speech_recognition as sr
from audio_recorder_streamlit import audio_recorder
import io

# 1. Cấu hình trang
st.set_page_config(page_title="Ghi Chú Giọng Nói", page_icon="🎙️")

st.title("🎙️ Ứng dụng Ghi Chú Bằng Giọng Nói")
st.write("Nhấn vào micro bên dưới để bắt đầu ghi âm, sau đó chờ hệ thống chuyển đổi thành văn bản.")

# 2. Khởi tạo danh sách ghi chú trong bộ nhớ tạm (Session State)
if 'notes' not in st.session_state:
    st.session_state.notes = []

# 3. Hàm xử lý chuyển đổi âm thanh thành văn bản
def transcribe_audio(audio_bytes):
    # Khởi tạo bộ nhận diện
    r = sr.Recognizer()
    
    # Chuyển đổi bytes thành dữ liệu âm thanh mà thư viện hiểu được
    audio_data = io.BytesIO(audio_bytes)
    
    try:
        with sr.AudioFile(audio_data) as source:
            audio = r.record(source)  # Đọc toàn bộ file âm thanh
            # Sử dụng Google Speech Recognition (cần kết nối internet)
            text = r.recognize_google(audio, language="vi-VN") 
            return text
    except sr.UnknownValueError:
        return "Không thể nghe rõ âm thanh."
    except sr.RequestError:
        return "Lỗi kết nối đến dịch vụ Google."
    except Exception as e:
        return f"Đã xảy ra lỗi: {e}"

# 4. Giao diện ghi âm
# Nút ghi âm sẽ trả về dữ liệu bytes khi người dùng dừng ghi
audio_bytes = audio_recorder(
    text="",
    recording_color="#e8b62c",
    neutral_color="#6aa36f",
    icon_name="microphone",
    icon_size="2x",
)

# 5. Xử lý khi có dữ liệu âm thanh
if audio_bytes:
    # Hiển thị thanh phát lại âm thanh vừa ghi
    st.audio(audio_bytes, format="audio/wav")
    
    with st.spinner("Đang chuyển đổi giọng nói thành văn bản..."):
        # Gọi hàm chuyển đổi
        transcript = transcribe_audio(audio_bytes)
        
        if transcript:
            st.success("Đã chuyển đổi thành công!")
            st.subheader("📝 Nội dung ghi chú:")
            st.info(transcript)
            
            # Thêm vào danh sách lịch sử
            st.session_state.notes.append(transcript)

# 6. Hiển thị lịch sử ghi chú
st.divider()
st.header("Lịch sử Ghi chú")
if st.session_state.notes:
    for i, note in enumerate(reversed(st.session_state.notes)):
        st.text_area(f"Ghi chú {len(st.session_state.notes) - i}", note, height=70)
else:
    st.write("Chưa có ghi chú nào.")
