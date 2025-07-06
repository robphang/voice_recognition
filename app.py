
from flask import Flask, request, jsonify, send_from_directory
import whisper
import os
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import google.generativeai as genai
from gtts import gTTS

# Load environment variables
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Inisialisasi model Gemini
gemini_model = genai.GenerativeModel("gemini-2.5-flash-lite-preview-06-17")

# Inisialisasi Flask dan Whisper
app = Flask(__name__)
model = whisper.load_model("base")

# Folder untuk menyimpan file audio
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Fungsi grammar check pakai Gemini
def check_grammar_gemini(text, lang_code):
    prompt = f"""
    Anda adalah pemeriksa tata bahasa yang akurat dan ringkas.
    Periksa tata bahasa dari kalimat berikut dalam bahasa {lang_code.upper()}.
    Jika kalimat tersebut sudah benar, **ulangi saja kalimat aslinya**.
    Jika ada kesalahan, **berikan hanya versi kalimat yang sudah diperbaiki**.
    Jangan pernah memberikan penjelasan tambahan, awalan seperti 'Teks yang dikoreksi:', tanda kutip di awal/akhir, catatan, atau informasi lainnya.
    Berikan respons sesingkat mungkin dan hanya berupa teks yang diminta.

    Contoh Bahasa Indonesia:
    Input: Saya pergi ke toko
    Output: Saya pergi ke toko

    Input: Aku makan nasi
    Output: Aku makan nasi

    Input: Kami akan pergi toko kemarin
    Output: Kami akan pergi ke toko kemarin

    Input: Ani dan Budi bermain bola di lapangan mereka sangat senang
    Output: Ani dan Budi bermain bola di lapangan. Mereka sangat senang

    Input: Aku cinte kamo
    Output: Aku cinta kamu

    Contoh Bahasa Mandarin:
    Input: ni hao
    Output: 你好

    Input: wo shi zhongguo ren
    Output: 我是中国人

    Input: ta hen gaoxing
    Output: 他很高兴

    Input: wo chi guo fan
    Output: 我吃过饭了

    Input: ming tian qu nar
    Output: 明天去哪儿

    Kalimat untuk diperiksa:
    {text}
"""
    try:
        response = gemini_model.generate_content(prompt)
        suggestion = response.text.strip()
        return (suggestion == text), suggestion
    except Exception as e:
        return False, f"[Error Gemini] {str(e)}"

# Fungsi text-to-speech dengan gTTS
def text_to_speech(text, lang_code, output_path):
    # gTTS tidak terima lang seperti "id-ID", jadi kita ambil "id"
    tts = gTTS(text=text, lang=lang_code.split('-')[0])
    tts.save(output_path)

# Endpoint utama untuk proses voice recognition + grammar check + TTS
@app.route('/recognize', methods=['POST'])
def recognize():
    if 'audio' not in request.files:
        return jsonify({"error": "Mohon kirim file 'audio'"}), 400

    lang = request.form.get('lang', 'id')  # Default ke Bahasa Indonesia

    audio_file = request.files['audio']
    filename = secure_filename(audio_file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    audio_file.save(filepath)

    try:
        # Transkripsi suara
        result = model.transcribe(filepath, language="id" if lang.startswith("id") else None)
        transcript = result["text"].strip().lower()

        # Grammar check dengan Gemini
        is_correct, suggestion = check_grammar_gemini(transcript, lang)

        # Text-to-speech: hasil koreksi jika salah, atau transkrip asli jika benar
        tts_text = suggestion if not is_correct else transcript
        tts_filename = f"tts_{os.path.splitext(filename)[0]}.mp3"
        tts_path = os.path.join(UPLOAD_FOLDER, tts_filename)
        text_to_speech(tts_text, lang, tts_path)

        # Return response JSON dengan URL download TTS
        return jsonify({
            "transcript": transcript,
            "language": lang,
            "result": "✅ Benar (tidak ada kesalahan)" if is_correct else f"❌ Salah. Koreksi yang disarankan: '{suggestion}'",
            "audio_output_url": f"/download_audio/{tts_filename}"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        # Hapus file input setelah selesai (kecuali TTS)
        if os.path.exists(filepath):
            os.remove(filepath)

# Endpoint untuk download / play file TTS hasil
@app.route('/download_audio/<filename>', methods=['GET'])
def download_audio(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == '__main__':
    app.run(debug=True)
