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
        Platform analitik teks dan visualisasi komparatif pemicu stres teknologi. Didukung pemodelan <b>Fallback Hybrid</b> (Otomatis mendeteksi kuisioner berskala Likert atau mengekstrak leksikon sentimen teks bebas).
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
            "📋 Skenario 1: Kuisioner Lengkap (Likert + Esai)",
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
            st.sidebar.success(f"File `{uploaded_file.name}` dimuat!")
        except Exception as e:
            st.sidebar.error(f"Gagal membaca CSV: {e}")

elif data_source == "⚡ Realtime JSON (Payload)":
    st.markdown("#### ⚡ Masukkan Payload JSON Realtime")
    default_json = """[
  {
    "respondent_id": "REALTIME-001",
    "likert_scores": {"q1_overload": 5, "q2_invasion": 4, "q3_complexity": 5},
    "essay": "Notifikasi tugas masuk tengah malam dan aplikasi lemot sekali bikin lelah dan pusing"
  },
  {
    "respondent_id": "REALTIME-002",
    "likert_scores": {"q1_overload": 1, "q2_invasion": 1, "q3_complexity": 2},
    "essay": "Sistem sangat lancar, mudah dan cepat menyelesaikan semua urusan laporan kerja"
  }
]"""
    json_text = st.text_area("JSON Array / Object:", value=default_json, height=160)
    if st.button("🚀 Analisis Payload Sekarang", type="primary"):
        try:
            payload = json.loads(json_text)
            analysis_res = pipeline.process_json_payload(payload, ngram_mode=ngram_choice)
        except Exception as e:
            st.error(f"Gagal memproses JSON: {e}")

# --- PROSES ANALISIS JIKA DATA TERSEDIA ---
if raw_df is not None:
    with st.spinner("Menjalankan pipeline NLP & Hybrid Classifier..."):
        analysis_res = pipeline.process_dataframe(raw_df, ngram_mode=ngram_choice)

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
                Dihitung dari {len(summary['likert_columns_detected'])} kolom kuisioner: 
                <code>{', '.join(summary['likert_columns_detected'])}</code> | Kolom Teks: <code>{summary['text_column_used']}</code>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="status-badge status-fallback">
            <span>🟡</span>
            <div>
                <b>Mode Aktif: Fallback NLP Inferred (Estimasi Leksikon Teks Otomatis)</b> &mdash; 
                <i>Dataset tidak memiliki kolom skala Likert numerik.</i> Sistem mengevaluasi sentimen & indikator stres langsung dari teks esai. Kolom Teks: <code>{summary['text_column_used']}</code>
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
    tab_wc, tab_phrases, tab_dims, tab_data = st.tabs([
        "🎨 Word Cloud Komparatif",
        "📊 Peringkat Top Frasa (Bigram)",
        "🧩 Dimensi Technostress",
        "📋 Data Responden & Ekspor"
    ])

    # --- TAB 1: WORD CLOUD KOMPARATIF ---
    with tab_wc:
        st.markdown("#### 🔄 Visualisasi Komparatif Berdampingan")
        st.caption("Membandingkan secara visual kata/frasa dominan antara kelompok yang mengalami stres tinggi terhadap kelompok yang puas/stres rendah.")

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
                <b style="color: #ef4444;">🔴 Kelompok Technostress Tinggi (Keluhan & Frustrasi)</b>
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
                <b style="color: #10b981;">🟢 Kelompok Technostress Rendah (Kepuasan & Kemudahan)</b>
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
        st.caption("Distribusi frekuensi frasa 2 kata (Bigram) atau unigram yang paling sering diutarakan responden.")

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

    # --- TAB 3: DIMENSI TECHNOSTRESS ---
    with tab_dims:
        st.markdown("#### 🧩 Distribusi 5 Dimensi Technostress")
        st.caption("Pemetaan keluhan berdasarkan kerangka teoritis Technostress (Tarafdar et al., 2007).")

        all_dims = []
        for dims in processed_df["dimensions"]:
            all_dims.extend(dims)
        dim_series = pd.Series(all_dims).value_counts().reset_index()
        dim_series.columns = ["Dimensi", "Frekuensi"]

        chart_dim = alt.Chart(dim_series).mark_bar(cornerRadiusTopRight=6, cornerRadiusBottomRight=6).encode(
            x=alt.X('Frekuensi:Q', title="Jumlah Kemunculan dalam Esai"),
            y=alt.Y('Dimensi:N', sort='-x', title=None),
            color=alt.Color('Dimensi:N', scale=alt.Scale(scheme='tableau10'), legend=None),
            tooltip=['Dimensi', 'Frekuensi']
        ).properties(height=280)

        st.altair_chart(chart_dim, use_container_width=True)

        col_d1, col_d2, col_d3 = st.columns(3)
        with col_d1:
            st.info("**Techno-Overload**: Beban kerja berlebih, multitasking, dan kebanjiran tugas.")
        with col_d2:
            st.info("**Techno-Invasion**: Terhubung terus-menerus, diganggu saat libur/malam hari.")
        with col_d3:
            st.info("**Techno-Complexity**: Sistem membingungkan, error, dan minimnya pelatihan.")

    # --- TAB 4: DATA RESPONDEN & EKSPOR ---
    with tab_data:
        st.markdown("#### 📋 Data Responden Teranalisis")
        
        # Filter interaktif
        filter_level = st.multiselect(
            "Filter Tingkat Stres:",
            options=["Tinggi", "Sedang", "Rendah"],
            default=["Tinggi", "Sedang", "Rendah"]
        )

        display_df = processed_df[processed_df["stress_level"].isin(filter_level)][
            ["stress_level", "stress_score", "source_mode", "dimensions", "text"]
        ].copy()

        display_df.rename(columns={
            "stress_level": "Level Stres",
            "stress_score": "Skor (1-5)",
            "source_mode": "Sumber Penentuan",
            "dimensions": "Dimensi Terdeteksi",
            "text": "Teks Esai Responden"
        }, inplace=True)

        st.dataframe(display_df, use_container_width=True, height=360)

        # Download CSV hasil analisis
        csv_data = display_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Unduh Hasil Analisis Lengkap (CSV)",
            data=csv_data,
            file_name="hasil_analisis_technostress.csv",
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
