import streamlit as st
import pandas as pd
import json
import os
import altair as alt
from src.pipeline import TechnostressPipeline

# --- KONFIGURASI HALAMAN STREAMLIT ---
st.set_page_config(
    page_title="Technostress NLP & Word Cloud Analytics",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- MODERN CUSTOM CSS STYLING ---
st.markdown("""
<style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    /* Container Card */
    .metric-card {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.02));
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 14px;
        padding: 20px 22px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: rgba(99, 102, 241, 0.4);
    }
    .metric-title {
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #8892b0;
        margin-bottom: 6px;
    }
    .metric-value {
        font-size: 1.85rem;
        font-weight: 800;
        line-height: 1.2;
    }
    .metric-sub {
        font-size: 0.82rem;
        font-weight: 500;
        margin-top: 6px;
        color: #a0aec0;
    }

    /* Status Mode Banner */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 10px 18px;
        border-radius: 10px;
        font-size: 0.92rem;
        font-weight: 600;
        margin-bottom: 20px;
        width: 100%;
    }
    .status-likert {
        background: rgba(34, 197, 94, 0.12);
        color: #16a34a;
        border: 1px solid rgba(34, 197, 94, 0.3);
    }
    .status-fallback {
        background: rgba(245, 158, 11, 0.12);
        color: #d97706;
        border: 1px solid rgba(245, 158, 11, 0.3);
    }

    /* Image Wrapper Card */
    .cloud-card {
        border-radius: 14px;
        overflow: hidden;
        border: 1px solid rgba(255, 255, 255, 0.12);
        background: rgba(255, 255, 255, 0.02);
        padding: 14px;
        margin-bottom: 15px;
    }

    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 18px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# --- HEADER SECTION ---
st.markdown("""
<div style="padding: 10px 0 24px 0;">
    <h1 style="font-size: 2.2rem; font-weight: 800; margin-bottom: 8px; background: linear-gradient(90deg, #3b82f6, #8b5cf6, #ec4899); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
        🧠 Technostress Comparative Word Cloud
    </h1>
    <p style="font-size: 1.05rem; color: #94a3b8; margin: 0; max-width: 850px;">
        Platform analitik teks dan visualisasi komparatif pemicu stres teknologi. Didukung pemodelan <b>Fallback Hybrid</b> (Otomatis mendeteksi kuisioner berskala Likert 1–10 butir atau mengekstrak leksikon sentimen teks bebas).
    </p>
</div>
""", unsafe_allow_html=True)

# --- SIDEBAR: KONFIGURASI DATA & PARAMETER NLP ---
with st.sidebar:
    st.markdown("### ⚙️ Sumber Data")
    data_source = st.radio(
        "Pilih Format Masukan:",
        ["🧪 Demo Instan (1-Click)", "📁 Upload CSV (Batch)", "⚡ Realtime JSON (Payload)"]
    )

    st.markdown("---")
    st.markdown("### 🎛️ Pengaturan Ekstraksi")
    
    ngram_choice = st.selectbox(
        "Mode N-gram:",
        ["both", "bigram", "unigram"],
        format_func=lambda x: {
            "both": "🔤 Gabungan (Kata + Frasa)",
            "bigram": "🔗 Frasa 2 Kata (Bigram Saja)",
            "unigram": "📝 Kata Tunggal (Unigram Saja)"
        }[x]
    )

    cloud_theme = st.selectbox(
        "Tema Kanvas Word Cloud:",
        ["white", "#0f172a"],
        format_func=lambda x: "☀️ Terang (Clean White)" if x == "white" else "🌙 Gelap (Dark Slate)"
    )

    max_words = st.slider("Maksimal Kata/Frasa:", min_value=20, max_value=120, value=60, step=10)

    st.markdown("---")
    st.markdown("### 🛑 Kustomisasi Stopwords")
    custom_stopwords_input = st.text_input(
        "Tambah Stopwords Tambahan:",
        placeholder="contoh: aplikasi, sistem, kantor"
    )
    custom_stopwords_set = set([s.strip().lower() for s in custom_stopwords_input.split(",") if s.strip()])

# Inisialisasi Pipeline
pipeline = TechnostressPipeline(additional_stopwords=custom_stopwords_set)

# --- MEMUAT DATA BERDASARKAN PILIHAN ---
raw_df = None

if data_source == "🧪 Demo Instan (1-Click)":
    demo_type = st.sidebar.radio(
        "Pilih Skenario Demo:",
        [
            "📋 Skenario 1: Kuisioner Lengkap (25 Siswa, 10 Likert, 2 Esai)",
            "🌐 Skenario 2: Ulasan Terbuka (Fallback NLP - Tanpa Likert)"
        ]
    )
    if "Kuisioner" in demo_type:
        sample_path = os.path.join("data", "sample_questionnaire.csv")
    else:
        sample_path = os.path.join("data", "sample_opensource_reviews.csv")
    
    if os.path.exists(sample_path):
        raw_df = pd.read_csv(sample_path)
    else:
        st.error("File demo tidak ditemukan.")

elif data_source == "📁 Upload CSV (Batch)":
    uploaded_file = st.sidebar.file_uploader("Pilih file CSV:", type=["csv"])
    if uploaded_file is not None:
        try:
            raw_df = pd.read_csv(uploaded_file)
            st.sidebar.success(f"File `{uploaded_file.name}` dimuat ({len(raw_df)} baris)!")
        except Exception as e:
            st.sidebar.error(f"Gagal membaca CSV: {e}")

elif data_source == "⚡ Realtime JSON (Payload)":
    st.markdown("#### ⚡ Masukkan Payload JSON Realtime")
    default_json = """[
  {
    "respondent_id": "REALTIME-001",
    "nama_siswa": "Rian Ardiansyah",
    "likert_scores": {
      "pertanyaan_1": 5, "pertanyaan_2": 5, "pertanyaan_3": 4, "pertanyaan_4": 4, "pertanyaan_5": 5,
      "pertanyaan_6": 4, "pertanyaan_7": 4, "pertanyaan_8": 5, "pertanyaan_9": 4, "pertanyaan_10": 4
    },
    "pertanyaan_essay_1": "Notifikasi tugas masuk tengah malam dan aplikasi lemot sekali bikin lelah dan pusing",
    "pertanyaan_essay_2": "Waktu tidur jadi tidak tenang dan selalu cemas ketinggalan tugas"
  },
  {
    "respondent_id": "REALTIME-002",
    "nama_siswa": "Dina Marlina",
    "likert_scores": {
      "pertanyaan_1": 1, "pertanyaan_2": 2, "pertanyaan_3": 1, "pertanyaan_4": 1, "pertanyaan_5": 2,
      "pertanyaan_6": 1, "pertanyaan_7": 1, "pertanyaan_8": 2, "pertanyaan_9": 1, "pertanyaan_10": 1
    },
    "pertanyaan_essay_1": "Aplikasi belajar sangat lancar, mudah dan cepat menyelesaikan semua urusan laporan kerja",
    "pertanyaan_essay_2": "Sangat membantu dan membuat proses belajar mandiri lebih menyenangkan"
  }
]"""
    json_text = st.text_area("JSON Array / Object:", value=default_json, height=180)
    if st.button("🚀 Analisis Payload Sekarang", type="primary"):
        try:
            payload = json.loads(json_text)
            analysis_res = pipeline.process_json_payload(payload, ngram_mode=ngram_choice)
        except Exception as e:
            st.error(f"Gagal memproses JSON: {e}")

# --- FILTER FOKUS ESAI (JIKA TERDAPAT MULTI-KOLOM ESAI) ---
selected_essay_focus = None
if raw_df is not None:
    detected_essays = pipeline.find_essay_columns(raw_df)
    if len(detected_essays) > 1:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📝 Fokus Analisis Esai")
        essay_options = ["ALL_COMBINED"] + detected_essays
        def format_essay_choice(x):
            if x == "ALL_COMBINED":
                return f"🔀 Semua Esai Gabungan ({len(detected_essays)} Kolom)"
            elif "1" in x:
                return f"1️⃣ {x} (Kendala & Stres)"
            elif "2" in x:
                return f"2️⃣ {x} (Pengaruh & Kenyamanan)"
            return f"📄 {x}"
        selected_essay_focus = st.sidebar.selectbox(
            "Pilih Kolom Esai untuk Word Cloud:",
            essay_options,
            format_func=format_essay_choice
        )

# --- PROSES ANALISIS JIKA DATA TERSEDIA ---
if raw_df is not None:
    with st.spinner("Menjalankan pipeline NLP & Hybrid Classifier..."):
        analysis_res = pipeline.process_dataframe(
            raw_df,
            text_col=selected_essay_focus,
            ngram_mode=ngram_choice
        )

# --- TAMPILAN DASHBOARD UTAMA ---
if "analysis_res" in locals() and "error" not in analysis_res:
    summary = analysis_res["summary"]
    processed_df = analysis_res["processed_df"]
    freqs = analysis_res["frequencies"]

    # 1. Status Mode Banner
    if summary["mode_used"] == "LIKERT":
        st.markdown(f"""
        <div class="status-badge status-likert">
            <span>🟢</span>
            <div>
                <b>Mode Aktif: Skala Likert Terdeteksi (Kuantitatif Akurat)</b> &mdash; 
                Dihitung dari <b>{len(summary['likert_columns_detected'])} butir pertanyaan Likert</b>: 
                <code>{', '.join(summary['likert_columns_detected'][:5])}...</code> | Sumber Teks: <code>{summary['text_column_used']}</code>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="status-badge status-fallback">
            <span>🟡</span>
            <div>
                <b>Mode Aktif: Fallback NLP Inferred (Estimasi Leksikon Teks Otomatis)</b> &mdash; 
                <i>Dataset tidak memiliki kolom skala Likert numerik.</i> Sistem mengevaluasi sentimen & indikator stres langsung dari teks esai. Sumber Teks: <code>{summary['text_column_used']}</code>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 2. Metric Cards
    total = summary["total_respondents"]
    counts = summary["stress_counts"]
    high_count = counts.get("Tinggi", 0)
    med_count = counts.get("Sedang", 0)
    low_count = counts.get("Rendah", 0)
    avg_score = summary["average_score"]

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Total Responden</div>
            <div class="metric-value" style="color: #6366f1;">{total}</div>
            <div class="metric-sub">Data teranalisis</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        high_pct = round(high_count / total * 100, 1) if total else 0
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Stres Tinggi</div>
            <div class="metric-value" style="color: #ef4444;">{high_count}</div>
            <div class="metric-sub" style="color: #f87171;">{high_pct}% dari total</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        med_pct = round(med_count / total * 100, 1) if total else 0
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Stres Sedang</div>
            <div class="metric-value" style="color: #3b82f6;">{med_count}</div>
            <div class="metric-sub" style="color: #60a5fa;">{med_pct}% dari total</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        low_pct = round(low_count / total * 100, 1) if total else 0
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Stres Rendah</div>
            <div class="metric-value" style="color: #10b981;">{low_count}</div>
            <div class="metric-sub" style="color: #34d399;">{low_pct}% dari total</div>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Rata-rata Skor</div>
            <div class="metric-value" style="color: #f59e0b;">{avg_score} <span style="font-size: 1rem; color: #94a3b8;">/ 5.0</span></div>
            <div class="metric-sub">Indeks Technostress</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 25px;'></div>", unsafe_allow_html=True)

    # 3. Visual Tabs
    tab_wc, tab_phrases, tab_chart, tab_data = st.tabs([
        "🎨 Word Cloud Komparatif",
        "📊 Peringkat Top Frasa (Bigram)",
        "📈 Grafik Tingkat Stres Siswa",
        "📋 Data Responden & Ekspor"
    ])

    # --- TAB 1: WORD CLOUD KOMPARATIF ---
    with tab_wc:
        st.markdown("#### 🔄 Visualisasi Komparatif Berdampingan")
        st.caption(f"Menampilkan visualisasi kata/frasa dominan berdasarkan teks: **{summary['text_column_used']}**.")

        col_w1, col_w2 = st.columns(2)

        img_high, img_low = pipeline.wc_generator.generate_comparative_images(
            freqs["Tinggi"],
            freqs["Rendah"],
            max_words=max_words,
            bg_color=cloud_theme
        )

        with col_w1:
            st.markdown("""
            <div style="background: rgba(239, 68, 68, 0.08); border-left: 4px solid #ef4444; padding: 8px 14px; border-radius: 4px 8px 8px 4px; margin-bottom: 12px;">
                <b style="color: #ef4444;">🔴 Kelompok Technostress Tinggi (Keluhan & Frustrasi Siswa)</b>
            </div>
            """, unsafe_allow_html=True)
            if img_high:
                st.image(img_high, use_container_width=True)
                btn_bytes_high = pipeline.wc_generator.generate_wordcloud_bytes(freqs["Tinggi"], "Tinggi", max_words, cloud_theme)
                if btn_bytes_high:
                    st.download_button("📥 Unduh Gambar Stres Tinggi (HD)", data=btn_bytes_high, file_name="wordcloud_stres_tinggi.png", mime="image/png")
            else:
                st.info("Tidak ada kata kunci yang cukup untuk kategori ini.")

        with col_w2:
            st.markdown("""
            <div style="background: rgba(16, 185, 129, 0.08); border-left: 4px solid #10b981; padding: 8px 14px; border-radius: 4px 8px 8px 4px; margin-bottom: 12px;">
                <b style="color: #10b981;">🟢 Kelompok Technostress Rendah (Kepuasan & Kemudahan Belajar)</b>
            </div>
            """, unsafe_allow_html=True)
            if img_low:
                st.image(img_low, use_container_width=True)
                btn_bytes_low = pipeline.wc_generator.generate_wordcloud_bytes(freqs["Rendah"], "Rendah", max_words, cloud_theme)
                if btn_bytes_low:
                    st.download_button("📥 Unduh Gambar Stres Rendah (HD)", data=btn_bytes_low, file_name="wordcloud_stres_rendah.png", mime="image/png")
            else:
                st.info("Tidak ada kata kunci yang cukup untuk kategori ini.")

        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        with st.expander("🌐 Lihat Word Cloud Keseluruhan Responden (Semua Kategori)"):
            img_all = pipeline.wc_generator.generate_wordcloud_image(freqs["Semua"], "Semua", max_words, cloud_theme)
            if img_all:
                st.image(img_all, use_container_width=True)

    # --- TAB 2: TOP FRASA ALTAIR CHARTS ---
    with tab_phrases:
        st.markdown("#### 📊 Peringkat Top Frasa & Kata Kunci")
        st.caption("Distribusi frekuensi frasa 2 kata (Bigram) atau kata tunggal yang paling sering diutarakan responden.")

        col_p1, col_p2 = st.columns(2)

        df_top_high = pipeline.wc_generator.get_top_ngrams_df(freqs["Tinggi"], top_n=10)
        df_top_low = pipeline.wc_generator.get_top_ngrams_df(freqs["Rendah"], top_n=10)

        with col_p1:
            st.markdown("##### 🔴 10 Frasa Terbanyak pada Stres Tinggi")
            if not df_top_high.empty:
                chart_high = alt.Chart(df_top_high).mark_bar(cornerRadiusTopRight=6, cornerRadiusBottomRight=6).encode(
                    x=alt.X('Frekuensi:Q', title="Jumlah Kemunculan"),
                    y=alt.Y('Frasa:N', sort='-x', title=None),
                    color=alt.value('#ef4444'),
                    tooltip=['Frasa', 'Frekuensi']
                ).properties(height=320)
                st.altair_chart(chart_high, use_container_width=True)
            else:
                st.write("Belum ada data.")

        with col_p2:
            st.markdown("##### 🟢 10 Frasa Terbanyak pada Stres Rendah")
            if not df_top_low.empty:
                chart_low = alt.Chart(df_top_low).mark_bar(cornerRadiusTopRight=6, cornerRadiusBottomRight=6).encode(
                    x=alt.X('Frekuensi:Q', title="Jumlah Kemunculan"),
                    y=alt.Y('Frasa:N', sort='-x', title=None),
                    color=alt.value('#10b981'),
                    tooltip=['Frasa', 'Frekuensi']
                ).properties(height=320)
                st.altair_chart(chart_low, use_container_width=True)
            else:
                st.write("Belum ada data.")

    # --- TAB 3: GRAFIK TINGKAT STRES SISWA ---
    with tab_chart:
        st.markdown("#### 📈 Grafik Tingkat Technostress Setiap Siswa")
        st.caption("Visualisasi perbandingan skor stres individual yang dikelompokkan ke dalam kategori Tinggi (Merah: Skala 4–5), Sedang (Biru: Skala 3), dan Rendah (Hijau: Skala 1–2). Garis batas merah berada pada nilai 3.50 (pembulatan ke skala 4) dan hijau pada nilai 2.50 (pembulatan ke skala 3).")

        # Buat dataframe khusus visualisasi grafik
        chart_df = processed_df.copy()
        if "nama_siswa" in chart_df.columns:
            chart_df["Label Siswa"] = chart_df["nama_siswa"] + " (" + chart_df["respondent_id"] + ")"
        else:
            chart_df["Label Siswa"] = chart_df["respondent_id"]

        chart_df["Skor Rata-rata"] = chart_df["stress_score"]
        chart_df["Skala Bulat"] = chart_df.get("rounded_scale", chart_df["stress_score"].round().astype(int))
        chart_df["Tingkat Stres"] = chart_df["stress_level"]

        # Kontrol Pengurutan & Filter
        col_c1, col_c2 = st.columns([2, 2])
        with col_c1:
            sort_order = st.selectbox(
                "Urutkan Grafik Berdasarkan:",
                ["Skor Tertinggi ke Terendah", "Skor Terendah ke Tertinggi", "Berdasarkan Nama Siswa"]
            )
        with col_c2:
            filter_chart_level = st.multiselect(
                "Filter Kategori di Grafik:",
                options=["Tinggi", "Sedang", "Rendah"],
                default=["Tinggi", "Sedang", "Rendah"]
            )

        chart_df_filtered = chart_df[chart_df["Tingkat Stres"].isin(filter_chart_level)]

        if not chart_df_filtered.empty:
            if sort_order == "Skor Tertinggi ke Terendah":
                sort_arg = alt.EncodingSortField(field="Skor Rata-rata", order="descending")
            elif sort_order == "Skor Terendah ke Tertinggi":
                sort_arg = alt.EncodingSortField(field="Skor Rata-rata", order="ascending")
            else:
                sort_arg = alt.EncodingSortField(field="Label Siswa", order="ascending")

            bars = alt.Chart(chart_df_filtered).mark_bar(cornerRadiusTopRight=6, cornerRadiusBottomRight=6).encode(
                x=alt.X('Skor Rata-rata:Q', scale=alt.Scale(domain=[0, 5.2]), title="Skor Rata-rata Likert (1.00 - 5.00)"),
                y=alt.Y('Label Siswa:N', sort=sort_arg, title=None),
                color=alt.Color(
                    'Tingkat Stres:N',
                    scale=alt.Scale(
                        domain=['Tinggi', 'Sedang', 'Rendah'],
                        range=['#ef4444', '#3b82f6', '#10b981']
                    ),
                    legend=alt.Legend(title="Kategori", orient="top")
                ),
                tooltip=['Label Siswa', 'Tingkat Stres', 'Skor Rata-rata', 'Skala Bulat', 'source_mode']
            )

            # Garis batas referensi pembulatan skala (Threshold Lines: 3.50 dan 2.50)
            rule_high = alt.Chart(pd.DataFrame({'x': [3.50]})).mark_rule(
                color='#ef4444', strokeDash=[4, 4], size=1.5
            ).encode(x='x:Q')

            rule_low = alt.Chart(pd.DataFrame({'x': [2.50]})).mark_rule(
                color='#10b981', strokeDash=[4, 4], size=1.5
            ).encode(x='x:Q')

            chart_height = max(350, len(chart_df_filtered) * 22)
            final_chart = (bars + rule_high + rule_low).properties(height=chart_height)
            st.altair_chart(final_chart, use_container_width=True)

            st.markdown("---")
            st.markdown("##### 👥 Daftar Nama Siswa per Kategori Interpretasi Pembulatan")
            sc1, sc2, sc3 = st.columns(3)
            with sc1:
                st.markdown("<b style='color: #ef4444;'>🔴 Stres Tinggi (Skala 4–5 | Rata-rata $\ge$ 3.50):</b>", unsafe_allow_html=True)
                high_names = chart_df[chart_df["Tingkat Stres"] == "Tinggi"]["Label Siswa"].tolist()
                for name in high_names:
                    st.markdown(f"- {name}")
            with sc2:
                st.markdown("<b style='color: #3b82f6;'>🔵 Stres Sedang (Skala 3 | Rata-rata 2.50 – 3.49):</b>", unsafe_allow_html=True)
                med_names = chart_df[chart_df["Tingkat Stres"] == "Sedang"]["Label Siswa"].tolist()
                for name in med_names:
                    st.markdown(f"- {name}")
            with sc3:
                st.markdown("<b style='color: #10b981;'>🟢 Stres Rendah (Skala 1–2 | Rata-rata < 2.50):</b>", unsafe_allow_html=True)
                low_names = chart_df[chart_df["Tingkat Stres"] == "Rendah"]["Label Siswa"].tolist()
                for name in low_names:
                    st.markdown(f"- {name}")
        else:
            st.warning("Tidak ada data untuk kategori yang difilter.")

    # --- TAB 4: DATA RESPONDEN & EKSPOR ---
    with tab_data:
        st.markdown("#### 📋 Data Responden Siswa & Hasil Klasifikasi")
        
        # Filter interaktif
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            filter_level = st.multiselect(
                "Filter Tingkat Stres:",
                options=["Tinggi", "Sedang", "Rendah"],
                default=["Tinggi", "Sedang", "Rendah"]
            )
        with col_f2:
            search_query = st.text_input("🔍 Cari Berdasarkan Nama Siswa / ID:", placeholder="Ketik nama atau ID...")

        # Persiapan kolom tampilan
        cols_to_display = []
        rename_map = {
            "respondent_id": "ID",
            "nama_siswa": "Nama Siswa",
            "stress_level": "Level Stres",
            "rounded_scale": "Skala Bulat (1-5)",
            "stress_score": "Rata-rata Skor (Desimal)",
            "source_mode": "Sumber Penentuan",
            "dimensions": "Dimensi Terdeteksi"
        }

        for c in ["respondent_id", "nama_siswa", "stress_level", "rounded_scale", "stress_score", "source_mode", "dimensions"]:
            if c in processed_df.columns:
                cols_to_display.append(c)

        for ec in summary.get("essay_columns_detected", []):
            if ec in processed_df.columns:
                cols_to_display.append(ec)
                rename_map[ec] = "Pertanyaan Esai 1 (Kendala)" if "1" in ec else ("Pertanyaan Esai 2 (Pengaruh)" if "2" in ec else ec)

        filtered_df = processed_df[processed_df["stress_level"].isin(filter_level)].copy()

        if search_query:
            mask = filtered_df["respondent_id"].astype(str).str.contains(search_query, case=False, na=False)
            if "nama_siswa" in filtered_df.columns:
                mask = mask | filtered_df["nama_siswa"].astype(str).str.contains(search_query, case=False, na=False)
            filtered_df = filtered_df[mask]

        display_df = filtered_df[cols_to_display].copy()
        display_df.rename(columns=rename_map, inplace=True)

        st.dataframe(display_df, use_container_width=True, height=400)

        # Download CSV hasil analisis
        csv_data = display_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Unduh Hasil Analisis Lengkap (CSV)",
            data=csv_data,
            file_name="hasil_analisis_technostress_siswa.csv",
            mime="text/csv",
            type="primary"
        )

else:
    if raw_df is None:
        st.markdown("""
        <div style="text-align: center; padding: 60px 20px; background: rgba(255, 255, 255, 0.02); border: 2px dashed rgba(255, 255, 255, 0.15); border-radius: 16px;">
            <div style="font-size: 3rem; margin-bottom: 12px;">📊</div>
            <h3 style="margin-bottom: 8px;">Belum Ada Data yang Dimuat</h3>
            <p style="color: #94a3b8; max-width: 500px; margin: 0 auto 20px auto;">
                Pilih opsi <b>"🧪 Demo Instan (1-Click)"</b> di bilah samping untuk melihat hasil analisis seketika, atau unggah file CSV kuisioner Anda.
            </p>
        </div>
        """, unsafe_allow_html=True)
