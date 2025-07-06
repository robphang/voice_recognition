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
# Menggunakan model yang lebih stabil, bukan preview
gemini_model = genai.GenerativeModel("gemini-1.5-flash-latest")

# Inisialisasi Flask dan Whisper
app = Flask(__name__)
# Ganti ke model yang lebih besar untuk akurasi yang lebih baik
model = whisper.load_model("medium") # <-- Perubahan disarankan: dari "base" ke "medium"

# Folder untuk menyimpan file audio
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Fungsi grammar check pakai Gemini
def check_grammar_gemini(text, lang_code):
    # Mapping sederhana untuk nama bahasa di prompt Gemini
    lang_name_map = {
        'id': 'Bahasa Indonesia',
        'en': 'English',
        'zh': 'Bahasa Mandarin',
        'ja': 'Japanese',
        'ko': 'Korean',
    }
    # Ambil bagian pertama sebelum '-' jika ada (misal 'id-ID' jadi 'id')
    clean_lang_code = lang_code.split('-')[0]
    target_lang_name = lang_name_map.get(clean_lang_code, clean_lang_code) 

    prompt = f"""
    Anda adalah pemeriksa tata bahasa yang akurat dan ringkas.
    Periksa tata bahasa dari kalimat berikut dalam {target_lang_name}.
    Jika kalimat tersebut sudah benar, **ulangi saja kalimat aslinya**.
    Jika ada kesalahan, **berikan hanya versi kalimat yang sudah diperbaiki**.
    Jangan pernah memberikan penjelasan tambahan, awalan seperti 'Teks yang dikoreksi:', tanda kutip di awal/akhir, catatan, atau informasi lainnya.
    Berikan respons sesingkat mungkin dan hanya berupa teks yang diminta.

    Contoh Bahasa Indonesia:
    Input: Saya pergi ke toko.
    Output: Saya pergi ke toko.

    Input: Aku makan nasi
    Output: Aku makan nasi.

    Input: Kami akan pergi toko kemarin.
    Output: Kami akan pergi ke toko kemarin.

    Input: Ani dan Budi bermain bola di lapangan mereka sangat senang.
    Output: Ani dan Budi bermain bola di lapangan. Mereka sangat senang.

    Input: Aku cinte kamo.
    Output: Aku cinta kamu.

    Contoh Bahasa Mandarin:
    Input: ni hao
    Output: 你好。

    Input: wo shi zhongguo ren
    Output: 我是中国人。

    Input: ta hen gaoxing
    Output: 他很高兴。

    Input: wo chi guo fan
    Output: 我吃过饭了。

    Input: ming tian qu nar
    Output: 明天去哪儿？

    Kalimat untuk diperiksa:
    {text}
    """
    try:
        response = gemini_model.generate_content(prompt)
        suggestion = response.text.strip()

        # --- PERBAIKAN DI SINI ---
        # Fungsi pembantu untuk membersihkan string (tetap generik tanpa parameter lang)
        def _strip_and_lower(s):
            return s.strip().lower()

        # Fungsi untuk menghapus tanda baca akhir berdasarkan bahasa
        def _remove_trailing_punctuation(s, lang):
            if lang in ['id', 'en']:
                return s.rstrip('.,?!')
            elif lang == 'zh':
                return s.rstrip('。？！')
            return s # Kembalikan string asli jika bahasa tidak dikenali untuk penghapusan punctuation

        # Normalisasi teks untuk perbandingan:
        # 1. Terapkan lower() dan strip()
        normalized_transcript = _strip_and_lower(text)
        normalized_suggestion = _strip_and_lower(suggestion)

        # 2. Hapus tanda baca di akhir berdasarkan clean_lang_code
        normalized_transcript = _remove_trailing_punctuation(normalized_transcript, clean_lang_code)
        normalized_suggestion = _remove_trailing_punctuation(normalized_suggestion, clean_lang_code)

        # Bandingkan setelah dinormalisasi
        is_correct = (normalized_transcript == normalized_suggestion)
        # --- AKHIR PERBAIKAN ---
        
        return is_correct, suggestion
    except Exception as e:
        print(f"Error calling Gemini: {e}")
        return False, f"[Error Gemini] {str(e)}"

# Fungsi text-to-speech dengan gTTS
def text_to_speech(text, lang_code, output_path):
    # gTTS tidak terima lang seperti "id-ID", jadi kita ambil "id"
    clean_lang = lang_code.split('-')[0]
    try:
        tts = gTTS(text=text, lang=clean_lang)
        tts.save(output_path)
    except Exception as e:
        print(f"Error generating TTS for text '{text}' in lang '{clean_lang}': {e}")
        tts = gTTS(text="Bahasa tidak didukung atau kesalahan TTS.", lang='id') # Fallback
        tts.save(output_path)

# Endpoint utama untuk proses voice recognition + grammar check + TTS
@app.route('/recognize', methods=['POST'])
def recognize():
    if 'audio' not in request.files:
        return jsonify({"error": "Mohon kirim file 'audio'"}), 400

    client_lang = request.form.get('lang', 'id')
    processed_lang_code = client_lang.split('-')[0]

    audio_file = request.files['audio']
    filename = secure_filename(audio_file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    audio_file.save(filepath)

    try:
        # Transkripsi suara
        # Gunakan processed_lang_code untuk Whisper
        result = model.transcribe(filepath, language=processed_lang_code)
        transcript = result["text"].strip() # <--- Jangan lower() di sini. Biarkan Gemini melihat kapitalisasi asli

        # Grammar check dengan Gemini
        is_correct, suggestion = check_grammar_gemini(transcript, client_lang)

        # Teks yang akan diubah menjadi suara HANYA berasal dari 'suggestion' Gemini
        # Karena prompt Gemini sudah diatur untuk hanya mengembalikan teks yang dikoreksi/asli.
        tts_text_to_speak = suggestion 
        
        tts_filename = f"tts_{os.path.splitext(filename)[0]}.mp3"
        tts_path = os.path.join(UPLOAD_FOLDER, tts_filename)
        
        # Panggil text_to_speech dengan teks yang bersih dan kode bahasa yang diproses
        text_to_speech(tts_text_to_speak, processed_lang_code, tts_path)

        # Siapkan pesan status untuk respons JSON (tertulis)
        grammar_status_message = ""
        if is_correct:
            grammar_status_message = "✅ Benar (tidak ada kesalahan)"
        else:
            grammar_status_message = f"❌ Salah. Koreksi yang disarankan: '{suggestion}'"


        # Return response JSON dengan URL download TTS
        return jsonify({
            "original_transcript": transcript,
            "language_requested": client_lang,
            "grammar_check_status": grammar_status_message,
            "corrected_text_for_tts": tts_text_to_speak,
            "audio_output_url": f"/download_audio/{tts_filename}"
        })

    except Exception as e:
        print(f"An error occurred in /recognize: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

# Endpoint untuk download / play file TTS hasil
@app.route('/download_audio/<filename>', methods=['GET'])
def download_audio(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == '__main__':
    app.run(debug=True)