import streamlit as st
from audio_recorder_streamlit import audio_recorder
import whisper
import tempfile
import os
import io
from docx import Document
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 1. Cấu hình trang
st.set_page_config(page_title="AI Note Pro", page_icon="🔐", layout="centered")

# --- CSS ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
        html, body, [class*="css"] {font-family: 'Inter', sans-serif;}
        .recording-container {
            border: 2px dashed #e0e0e0; border-radius: 20px; padding: 20px;
            text-align: center; background-color: #f9f9f9; margin: 20px 0;
        }
    </style>
""", unsafe_allow_html=True)

# --- CHỨC NĂNG ĐĂNG NHẬP ---
def check_password():
    """Trả về True nếu đăng nhập thành công"""
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if st.session_state.password_correct:
        return True

    st.title("🔒 Đăng nhập")
    pwd = st.text_input("Nhập mật khẩu truy cập:", type="password")
    
    if st.button("Đăng nhập"):
        # So sánh với mật khẩu trong secrets
        if pwd == st.secrets["APP_PASSWORD"]:
            st.session_state.password_correct = True
            st.rerun()
        else:
            st.error("Sai mật khẩu!")
    return False

# Nếu chưa đăng nhập thì dừng chương trình tại đây
if not check_password():
    st.stop()

# --- SAU KHI ĐĂNG NHẬP THÀNH CÔNG ---

# 2. Kết nối Database (Google Sheets)
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. Cấu hình API
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("Thiếu API Key")
    st.stop()

# 4. Các hàm xử lý (Whisper, Gemini, Docx)
@st.cache_resource
def load_whisper_model():
    return whisper.load_model("base")

model = load_whisper_model()

def transcribe_audio(audio_bytes):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
        temp_audio.write(audio_bytes)
        temp_filename = temp_audio.name
    try:
        return model.transcribe(temp_filename, language="vi")["text"]
    finally:
        if os.path.exists(temp_filename): os.remove(temp_filename)

def summarize_text(text):
    model_gemini = genai.GenerativeModel('gemini-2.5-flash')
    prompt = f"Tóm tắt và liệt kê hành động: '{text}'"
    return model_gemini.generate_content(prompt).text

def create_docx(original, summary):
    doc = Document()
    doc.add_paragraph(summary)
    doc.add_paragraph(original)
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# Hàm lưu vào Google Sheets
def save_to_drive(summary, original):
    try:
        # Lấy dữ liệu hiện tại
        existing_data = conn.read(worksheet="Sheet1", usecols=[0, 1, 2], ttl=0)
        
        # Tạo dòng dữ liệu mới
        new_row = pd.DataFrame([{
            "Thời gian": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Tóm tắt": summary,
            "Chi tiết": original
        }])
        
        # Gộp dữ liệu cũ và mới
        updated_data = pd.concat([existing_data, new_row], ignore_index=True)
        
        # Cập nhật lên Google Sheet
        conn.update(worksheet="Sheet1", data=updated_data)
        st.toast("✅ Đã lưu vào Google Sheets thành công!", icon="☁️")
        
    except Exception as e:
        st.error(f"Lỗi lưu Database: {e}")

# --- GIAO DIỆN CHÍNH ---
st.title("🎙️ AI Voice Notes (Cloud Sync)")
st.caption(f"Xin chào, bạn đã đăng nhập thành công!")

# Khu vực ghi âm
st.markdown('<div class="recording-container">', unsafe_allow_html=True)
st.write("Bấm vào micro để bắt đầu")
audio_bytes = audio_recorder(text="", recording_color="#ff2b2b", neutral_color="#333", icon_size="4x", pause_threshold=10.0)
st.markdown('</div>', unsafe_allow_html=True)

if audio_bytes:
    st.audio(audio_bytes, format="audio/wav")
    
    with st.status("Đang xử lý dữ liệu...", expanded=True):
        st.write("Whisper: Gỡ băng...")
        transcript = transcribe_audio(audio_bytes)
        st.write("Gemini: Tóm tắt...")
        summary = summarize_text(transcript)
        
        # Tự động lưu vào Database
        st.write("Cloud: Đang đồng bộ Google Sheets...")
        save_to_drive(summary, transcript)

    # Hiển thị
    col1, col2 = st.columns(2)
    with col1:
        st.info(summary)
    with col2:
        st.write(transcript)
        
    docx = create_docx(transcript, summary)
    st.download_button("📥 Tải Word", docx, "Note.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)

# --- HIỂN THỊ LỊCH SỬ TỪ DATABASE ---
st.divider()
st.subheader("🗄️ Dữ liệu trên Cloud (Google Sheets)")

# Nút làm mới dữ liệu
if st.button("🔄 Tải lại danh sách"):
    st.cache_data.clear()
    st.rerun()

try:
    # Đọc dữ liệu từ Google Sheets (ttl=5: cache trong 5 giây)
    df = conn.read(worksheet="Sheet1", usecols=[0, 1, 2], ttl=5)
    
    if not df.empty:
        # Sắp xếp mới nhất lên đầu
        df = df.sort_values(by="Thời gian", ascending=False)
        
        for index, row in df.iterrows():
            with st.expander(f"{row['Thời gian']} - {str(row['Tóm tắt'])[:50]}..."):
                st.write(f"**Tóm tắt:** {row['Tóm tắt']}")
                st.write(f"**Chi tiết:** {row['Chi tiết']}")
    else:
        st.info("Chưa có dữ liệu nào trên Cloud.")
except Exception as e:
    st.warning("Chưa kết nối được Database hoặc bảng trống.")
