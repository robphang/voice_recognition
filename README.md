
# 🗣️ Voice Recognition with Grammar Check (Whisper + Gemini)

API untuk mengenali suara (speech-to-text) dan mengecek tata bahasa (grammar check) menggunakan **OpenAI Whisper** dan **Google Gemini API**.  
Mendukung berbagai bahasa seperti **Bahasa Indonesia**, **Bahasa Inggris**, dll.

---

## 🚀 Endpoint

### `POST /recognize`

#### 🧾 Form Data

| Field   | Tipe     | Keterangan                                  |
|---------|----------|---------------------------------------------|
| `audio` | file     | File audio (.mp3, .wav) **(wajib)**         |
| `lang`  | string   | Kode bahasa (opsional). Contoh: `id`, `en`, `auto` |

---

## 📥 Contoh Response

```json
{
  "transcript": "saya cinta kamu",
  "language": "id",
  "result": "❌ Salah. Koreksi yang disarankan: 'saya mencintaimu'"
}
```

---

## 📌 Cara Menjalankan Proyek Lengkap dari Awal

### 1. Clone / Download Project

```bash
git clone https://github.com/namauser/proyek-kamu.git
cd proyek-kamu
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

> Pastikan juga `ffmpeg` sudah terinstal (dibutuhkan oleh Whisper).  
> Install via `choco install ffmpeg` (Windows) atau `brew install ffmpeg` (macOS).

### 3. Siapkan file `.env`

Buat file `.env` di folder root dan isi dengan API key dari Google Cloud:

```env
GEMINI_API_KEY=AIzaSyDxxxxxxx
```

> Kamu bisa dapatkan key dari: https://console.cloud.google.com/apis/credentials  
> Pastikan API **Generative Language API** sudah diaktifkan.

### 4. Jalankan server Flask

```bash
python app.py
```

Server akan berjalan di: `http://localhost:5000`

---

## 🧪 Tes API via Postman / curl

### ✅ Postman (Form-Data)
- `audio`: pilih file audio (.mp3, .wav)
- `lang`: `id` / `en` / `auto` (opsional)

### ✅ Curl

```bash
curl -X POST http://localhost:5000/recognize \
  -F "audio=@contoh.wav" \
  -F "lang=id"
```

---

## ⚠️ Catatan

- Whisper memerlukan `torch` dan `ffmpeg`
- Gemini API menggunakan model **`models/gemini-1.5-flash`** (GRATIS)
- Harus pakai **Google Cloud API key**, bukan dari AI Studio
- Pastikan batas harian Google API tidak terlampaui (sekitar 60–100 request gratis/hari)

---

## 📦 Requirements

Tersimpan di `requirements.txt`, termasuk:

- `flask`
- `python-dotenv`
- `whisper`
- `torch`
- `google-generativeai`
- `werkzeug`

---

## 📄 Lisensi
Proyek ini bebas digunakan untuk pembelajaran atau pengembangan pribadi.
