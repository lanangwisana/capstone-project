# Technostress Word Cloud & Comparative NLP Analyzer

Aplikasi analisis NLP dan visualisasi Word Cloud komparatif khusus untuk mengukur dan mendeteksi tingkat **Technostress** responden.

## 🚀 Fitur Unggulan

1. **Arsitektur Fallback Hybrid**:
   - **Mode Utama (Skala Likert)**: Mengkalkulasi rata-rata skor kuisioner numerik (skala 1 - 5) dan mengelompokkan responden ke dalam tingkat stres (Rendah, Sedang, Tinggi).
   - **Mode Fallback (NLP Inferred)**: Jika data open-source tidak memiliki skala Likert, sistem secara otomatis mengevaluasi teks esai/komentar menggunakan leksikon indikator stres & sentimen tanpa menimbulkan error.
2. **Word Cloud Komparatif**:
   - Menampilkan perbandingan visual berdampingan: Kelompok Stres Tinggi (Palet Merah) vs Kelompok Stres Rendah (Palet Hijau).
3. **Ekstraksi Frasa (N-gram)**:
   - Mendukung kata tunggal (Unigram), frasa 2 kata (Bigram, misal: *notifikasi malam*, *sistem lambat*, *beban tugas*), atau gabungan keduanya.
4. **Pemetaan 5 Dimensi Technostress** (Tarafdar et al., 2007):
   - Mendeteksi pemicu stres: *Techno-Overload*, *Techno-Invasion*, *Techno-Complexity*, *Techno-Insecurity*, dan *Techno-Uncertainty*.
5. **Dual Input Mode**:
   - Upload file **CSV** (batch data kuisioner).
   - Input payload **JSON** (data realtime form/API).
   - Tersedia tombol demo 1-klik untuk pengujian instan.

---

## 📂 Struktur Proyek

```
capstone-project/
├── data/
│   ├── sample_questionnaire.csv          # Contoh kuisioner lengkap (Likert + Esai)
│   ├── sample_opensource_reviews.csv      # Contoh ulasan teks bebas (Fallback NLP)
│   └── sample_payload.json               # Contoh format JSON realtime
├── src/
│   ├── nlp_preprocessor.py               # Pembersihan teks, slang normalizer, n-gram, stopwords
│   ├── stress_classifier.py              # Klasifikasi Hybrid (Likert vs NLP Leksikon)
│   ├── wordcloud_generator.py            # Generator gambar Word Cloud & tabel frasa
│   └── pipeline.py                       # Orkes trasi pipeline terpadu
├── app.py                                # Antarmuka Web Interaktif (Streamlit)
├── requirements.txt                      # Dependensi library Python
└── README.md
```

---

## 💻 Cara Menjalankan Aplikasi

Jalankan perintah berikut di terminal:

```bash
streamlit run app.py
```

Aplikasi web akan terbuka otomatis di browser Anda di alamat `http://localhost:8501`.

