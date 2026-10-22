import streamlit as st
import pandas as pd
import json
import os
import altair as alt
import requests
from src.pipeline import TechnostressPipeline

# --- KONFIGURASI HALAMAN STREAMLIT ---
st.set_page_config(
    page_title="Technostress Visual Analytics & Word Cloud",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- MODERN CUSTOM CSS STYLING ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    .metric-card {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.02));
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 14px;
        padding: 18px 20px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
    }
    .metric-title {
        font-size: 0.82rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #8892b0;
        margin-bottom: 4px;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 800;
        line-height: 1.2;
    }
    .metric-sub {
        font-size: 0.8rem;
        font-weight: 500;
        margin-top: 4px;
        color: #a0aec0;
    }

    .section-card {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 28px;
    }
</style>
""", unsafe_allow_html=True)

# --- HEADER SECTION ---
st.markdown("""
<div style="padding: 10px 0 20px 0;">
    <h1 style="font-size: 2.2rem; font-weight: 800; margin-bottom: 6px; background: linear-gradient(90deg, #3b82f6, #8b5cf6, #ec4899); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
        🧠 Technostress Visual Analytics & Word Cloud
    </h1>
    <p style="font-size: 1.05rem; color: #94a3b8; margin: 0;">
        Sistem visualisasi analitik teks dan pemetaan tingkat stres teknologi berbasis konsumsi <b>API format JSON</b> dengan validasi kontrak skema yang ketat.
    </p>
</div>
""", unsafe_allow_html=True)

# --- SIDEBAR: KONSUMSI ENDPOINT JSON ---
with st.sidebar:
    st.markdown("### 🔌 Konsumsi Endpoint JSON")
    input_method = st.radio(
        "Metode Input JSON:",
        ["🧪 Gunakan Payload Demo (25 Siswa)", "📥 Upload / Paste JSON", "🌐 Tembak URL API"]
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

# --- PROSES PENGAMBILAN DATA JSON ---
json_data = None

if input_method == "🧪 Gunakan Payload Demo (25 Siswa)":
    sample_json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "sample_payload.json")
    if os.path.exists(sample_json_path):
        with open(sample_json_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)
    else:
        st.error("File sample_payload.json tidak ditemukan.")

elif input_method == "📥 Upload / Paste JSON":
    upload_tab1, upload_tab2 = st.tabs(["📄 Upload File .JSON", "✍️ Paste Teks JSON"])
    with upload_tab1:
        uploaded_json_file = st.file_uploader("Pilih file .json:", type=["json"])
        if uploaded_json_file is not None:
            try:
                json_data = json.load(uploaded_json_file)
                st.sidebar.success(f"File `{uploaded_json_file.name}` dimuat!")
            except Exception as e:
                st.sidebar.error(f"Format file JSON tidak valid: {e}")
    with upload_tab2:
        raw_json_str = st.text_area("Paste string JSON di sini:", height=200, placeholder="{\n  \"status\": \"success\",\n  \"data\": [...]\n}")
        if st.button("🚀 Proses JSON Teks", type="primary"):
            if raw_json_str.strip():
                try:
                    json_data = json.loads(raw_json_str)
                except Exception as e:
                    st.error(f"Gagal memparsing JSON: {e}")

elif input_method == "🌐 Tembak URL API":
    api_url = st.text_input("Masukkan URL Endpoint API (GET):", placeholder="https://api.sekolah.id/v1/technostress-responses")
    if st.button("📡 Tarik Data API", type="primary"):
        if api_url.strip():
            with st.spinner("Menghubungi endpoint API..."):
                try:
                    resp = requests.get(api_url.strip(), timeout=10)
                    if resp.status_code == 200:
                        json_data = resp.json()
                        st.sidebar.success("Berhasil mengambil data dari API!")
                    else:
                        st.error(f"API merespons status code: {resp.status_code}")
                except Exception as e:
                    st.error(f"Koneksi ke API gagal: {e}")

# --- PROSES VALIDASI & PIPELINE JIKA JSON TERSEDIA ---
if json_data is not None:
    result = pipeline.process_json_payload(json_data, ngram_mode=ngram_choice)

    if not result.get("success", False):
        st.error(result.get("error_message", "Gagal memproses payload JSON."))
    else:
        summary = result["summary"]
        processed_df = result["processed_df"]
        freqs = result["frequencies"]

        can_chart = summary["can_render_chart"]
        can_wc = summary["can_render_wordcloud"]

        # Status Banner
        if can_chart and can_wc:
            st.success(f"✅ **Kontrak Skema API Terverifikasi Lengkap**: {summary['total_records']} baris data responden berhasil diekstraksi.")
        else:
            st.info(f"ℹ️ **Data JSON Dimuat**: {summary['total_records']} baris data responden diterima ke dalam sistem.")

        # =====================================================================
        # VISUALISASI 1: GRAFIK TINGKAT TECHNOSTRESS SISWA
        # =====================================================================
        st.markdown("""
        <div class="section-card">
            <h2 style="font-size: 1.5rem; font-weight: 700; margin-bottom: 4px;">
                📊 1. Visualisasi Grafik Tingkat Technostress Siswa
            </h2>
            <p style="color: #94a3b8; font-size: 0.95rem; margin-bottom: 18px;">
                Menampilkan sebaran tingkat stres siswa berdasarkan nilai kalkulasi kuisioner numerik dan kategori.
            </p>
        </div>
        """, unsafe_allow_html=True)

        if not can_chart:
            missing_str = ", ".join([f"`{p}`" for p in summary["chart_missing_params"]])
            st.warning(f"""
            ⚠️ **Visualisasi Grafik Tidak Dapat Ditampilkan**  
            Data JSON tetap diterima, namun parameter wajib untuk visualisasi grafik tidak lengkap pada payload: **{missing_str}**.  
            *Pastikan endpoint API kelompok penyedia data menyertakan kolom identitas (`id`, `name`), `post_date`, `kalkulasi`, dan `kategori`.*
            """)
        else:
            # Metric Cards (4 Kolom Utama)
            total = summary["total_records"]
            counts = summary["stress_counts"]
            high_count = counts.get("Tinggi", 0)
            med_count = counts.get("Sedang", 0)
            low_count = counts.get("Rendah", 0)

            mc1, mc2, mc3, mc4 = st.columns(4)
            with mc1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Total Responden</div>
                    <div class="metric-value" style="color: #6366f1;">{total}</div>
                    <div class="metric-sub">Siswa terdaftar</div>
                </div>
                """, unsafe_allow_html=True)
            with mc2:
                high_pct = round(high_count / total * 100, 1) if total else 0
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Stres Tinggi</div>
                    <div class="metric-value" style="color: #ef4444;">{high_count}</div>
                    <div class="metric-sub" style="color: #f87171;">{high_pct}% (Skala 4–5)</div>
                </div>
                """, unsafe_allow_html=True)
            with mc3:
                med_pct = round(med_count / total * 100, 1) if total else 0
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Stres Sedang</div>
                    <div class="metric-value" style="color: #3b82f6;">{med_count}</div>
                    <div class="metric-sub" style="color: #60a5fa;">{med_pct}% (Skala 3)</div>
                </div>
                """, unsafe_allow_html=True)
            with mc4:
                low_pct = round(low_count / total * 100, 1) if total else 0
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Stres Rendah</div>
                    <div class="metric-value" style="color: #10b981;">{low_count}</div>
                    <div class="metric-sub" style="color: #34d399;">{low_pct}% (Skala 1–2)</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

            # Chart Controls
            chart_df = processed_df.copy()
            chart_df["Label Siswa"] = chart_df["name"] + " (" + chart_df["id"] + ")"

            col_ct1, col_ct2 = st.columns([2, 2])
            with col_ct1:
                sort_order = st.selectbox(
                    "Urutkan Siswa Berdasarkan:",
                    ["Skor Tertinggi ke Terendah", "Skor Terendah ke Tertinggi", "Berdasarkan Nama Siswa"]
                )
            with col_ct2:
                filter_chart_level = st.multiselect(
                    "Filter Kategori di Grafik:",
                    options=["Tinggi", "Sedang", "Rendah"],
                    default=["Tinggi", "Sedang", "Rendah"]
                )

            chart_df_filtered = chart_df[chart_df["kategori"].isin(filter_chart_level)]

            if not chart_df_filtered.empty:
                if sort_order == "Skor Tertinggi ke Terendah":
                    sort_arg = alt.EncodingSortField(field="kalkulasi", order="descending")
                elif sort_order == "Skor Terendah ke Tertinggi":
                    sort_arg = alt.EncodingSortField(field="kalkulasi", order="ascending")
                else:
                    sort_arg = alt.EncodingSortField(field="Label Siswa", order="ascending")

                bars = alt.Chart(chart_df_filtered).mark_bar(cornerRadiusTopRight=6, cornerRadiusBottomRight=6).encode(
                    x=alt.X('kalkulasi:Q', scale=alt.Scale(domain=[0, 5.2]), title="Skor Kalkulasi Likert (1.00 - 5.00)"),
                    y=alt.Y('Label Siswa:N', sort=sort_arg, title=None),
                    color=alt.Color(
                        'kategori:N',
                        scale=alt.Scale(
                            domain=['Tinggi', 'Sedang', 'Rendah'],
                            range=['#ef4444', '#3b82f6', '#10b981']
                        ),
                        legend=alt.Legend(title="Kategori", orient="top")
                    ),
                    tooltip=['Label Siswa', 'kategori', 'kalkulasi', 'rounded_scale', 'post_date']
                )

                rule_high = alt.Chart(pd.DataFrame({'x': [3.50]})).mark_rule(
                    color='#ef4444', strokeDash=[4, 4], size=1.5
                ).encode(x='x:Q')

                rule_low = alt.Chart(pd.DataFrame({'x': [2.50]})).mark_rule(
                    color='#10b981', strokeDash=[4, 4], size=1.5
                ).encode(x='x:Q')

                chart_height = max(350, len(chart_df_filtered) * 22)
                final_chart = (bars + rule_high + rule_low).properties(height=chart_height)
                st.altair_chart(final_chart, use_container_width=True)

                st.markdown("##### 👥 Daftar Siswa Berdasarkan Kategori Interpretasi Pembulatan")
                sc1, sc2, sc3 = st.columns(3)
                with sc1:
                    st.markdown("<b style='color: #ef4444;'>🔴 Stres Tinggi (Skala 4–5 | Rata-rata $\ge$ 3.50):</b>", unsafe_allow_html=True)
                    high_names = chart_df[chart_df["kategori"] == "Tinggi"]["Label Siswa"].tolist()
                    for n in high_names:
                        st.markdown(f"- {n}")
                with sc2:
                    st.markdown("<b style='color: #3b82f6;'>🔵 Stres Sedang (Skala 3 | Rata-rata 2.50 – 3.49):</b>", unsafe_allow_html=True)
                    med_names = chart_df[chart_df["kategori"] == "Sedang"]["Label Siswa"].tolist()
                    for n in med_names:
                        st.markdown(f"- {n}")
                with sc3:
                    st.markdown("<b style='color: #10b981;'>🟢 Stres Rendah (Skala 1–2 | Rata-rata < 2.50):</b>", unsafe_allow_html=True)
                    low_names = chart_df[chart_df["kategori"] == "Rendah"]["Label Siswa"].tolist()
                    for n in low_names:
                        st.markdown(f"- {n}")
            else:
                st.info("Tidak ada siswa pada filter kategori yang dipilih.")

        st.markdown("<div style='height: 35px;'></div>", unsafe_allow_html=True)

        # =====================================================================
        # VISUALISASI 2: WORD CLOUD KOMPARATIF & ANALISIS FRASA
        # =====================================================================
        st.markdown("""
        <div class="section-card">
            <h2 style="font-size: 1.5rem; font-weight: 700; margin-bottom: 4px;">
                🎨 2. Visualisasi Word Cloud Komparatif & Top Frasa
            </h2>
            <p style="color: #94a3b8; font-size: 0.95rem; margin-bottom: 18px;">
                Mengekstraksi narasi esai siswa secara komparatif untuk menonjolkan kata kunci kendala pada kelompok stres tinggi (merah) vs pengalaman belajar pada kelompok stres rendah (hijau).
            </p>
        </div>
        """, unsafe_allow_html=True)

        if not can_wc:
            missing_wc_str = ", ".join([f"`{p}`" for p in summary["wordcloud_missing_params"]])
            st.warning(f"""
            ⚠️ **Visualisasi Word Cloud Tidak Dapat Dibuat**  
            Parameter teks esai tidak ditemukan dalam payload JSON: **{missing_wc_str}**.  
            *Pastikan endpoint API kelompok penyedia data menyertakan kolom jawaban terbuka seperti `essay_1`, `essay_2`, dst.*
            """)
        else:
            wc_col1, wc_col2 = st.columns(2)

            img_high, img_low = pipeline.wc_generator.generate_comparative_images(
                freqs["Tinggi"],
                freqs["Rendah"],
                max_words=max_words,
                bg_color=cloud_theme
            )

            with wc_col1:
                st.markdown("""
                <div style="background: rgba(239, 68, 68, 0.08); border-left: 4px solid #ef4444; padding: 8px 14px; border-radius: 4px 8px 8px 4px; margin-bottom: 12px;">
                    <b style="color: #ef4444;">🔴 Kelompok Technostress Tinggi (Keluhan & Kendala Utama)</b>
                </div>
                """, unsafe_allow_html=True)
                if img_high:
                    st.image(img_high, use_container_width=True)
                    btn_bytes_high = pipeline.wc_generator.generate_wordcloud_bytes(freqs["Tinggi"], "Tinggi", max_words, cloud_theme)
                    if btn_bytes_high:
                        st.download_button("📥 Unduh Gambar Stres Tinggi (HD)", data=btn_bytes_high, file_name="wordcloud_stres_tinggi.png", mime="image/png")
                else:
                    st.info("Tidak ada kata kunci yang cukup untuk kategori ini.")

            with wc_col2:
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

            # Tabel Top Frasa (Bigram)
            st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
            st.markdown("##### 📊 Top 10 Frasa / Kata Kunci Paling Sering Muncul")

            df_top_high = pipeline.wc_generator.get_top_ngrams_df(freqs["Tinggi"], top_n=10)
            df_top_low = pipeline.wc_generator.get_top_ngrams_df(freqs["Rendah"], top_n=10)

            col_p1, col_p2 = st.columns(2)
            with col_p1:
                st.markdown("###### 🔴 Top Frasa Stres Tinggi")
                if not df_top_high.empty:
                    chart_high = alt.Chart(df_top_high).mark_bar(cornerRadiusTopRight=6, cornerRadiusBottomRight=6).encode(
                        x=alt.X('Frekuensi:Q', title="Jumlah Kemunculan"),
                        y=alt.Y('Frasa:N', sort='-x', title=None),
                        color=alt.value('#ef4444'),
                        tooltip=['Frasa', 'Frekuensi']
                    ).properties(height=260)
                    st.altair_chart(chart_high, use_container_width=True)
                else:
                    st.write("Belum ada data.")

            with col_p2:
                st.markdown("###### 🟢 Top Frasa Stres Rendah")
                if not df_top_low.empty:
                    chart_low = alt.Chart(df_top_low).mark_bar(cornerRadiusTopRight=6, cornerRadiusBottomRight=6).encode(
                        x=alt.X('Frekuensi:Q', title="Jumlah Kemunculan"),
                        y=alt.Y('Frasa:N', sort='-x', title=None),
                        color=alt.value('#10b981'),
                        tooltip=['Frasa', 'Frekuensi']
                    ).properties(height=260)
                    st.altair_chart(chart_low, use_container_width=True)
                else:
                    st.write("Belum ada data.")

        # =====================================================================
        # INSPEKSI DATA MENTAH DARI API (COLLAPSIBLE)
        # =====================================================================
        st.markdown("<div style='height: 25px;'></div>", unsafe_allow_html=True)
        with st.expander("📋 Inspeksi Data Lengkap yang Diterima dari Endpoint JSON"):
            display_cols = [c for c in ["id", "name", "post_date", "kalkulasi", "rounded_scale", "kategori", "essay_text"] if c in processed_df.columns]
            rename_dict = {
                "id": "ID",
                "name": "Nama Siswa",
                "post_date": "Waktu Submit",
                "kalkulasi": "Rata-rata Skor (Desimal)",
                "rounded_scale": "Skala Bulat (1-5)",
                "kategori": "Kategori",
                "essay_text": "Gabungan Esai"
            }
            view_df = processed_df[display_cols].rename(columns=rename_dict)
            st.dataframe(view_df, use_container_width=True, height=300)

else:
    st.markdown("""
    <div style="text-align: center; padding: 60px 20px; background: rgba(255, 255, 255, 0.02); border: 2px dashed rgba(255, 255, 255, 0.15); border-radius: 16px;">
        <div style="font-size: 3rem; margin-bottom: 12px;">⚡</div>
        <h3 style="margin-bottom: 8px;">Siap Mengonsumsi Endpoint JSON</h3>
        <p style="color: #94a3b8; max-width: 520px; margin: 0 auto 20px auto;">
            Pilih opsi <b>"🧪 Gunakan Payload Demo (25 Siswa)"</b> di bilah samping untuk simulasi instan, atau masukkan URL API / upload file JSON Anda.
        </p>
    </div>
    """, unsafe_allow_html=True)
