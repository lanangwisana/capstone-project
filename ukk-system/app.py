import re

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Tren Ujian Kompetensi SMK", layout="wide")

# ---------- Rubrik ----------
KATEGORI = ["Belum Kompeten", "Cukup Kompeten", "Kompeten", "Sangat Kompeten"]
WARNA = {
    "Belum Kompeten": "#d62728",
    "Cukup Kompeten": "#ff9f1c",
    "Kompeten": "#2ca02c",
    "Sangat Kompeten": "#1f77b4",
}
BUCKET_NORM = {"91-100", "75-90", "61-74", "<60", "<61"}


def konversi(nilai: float) -> str:
    if nilai >= 91:
        return "Sangat Kompeten"
    if nilai >= 75:
        return "Kompeten"
    if nilai >= 61:
        return "Cukup Kompeten"
    return "Belum Kompeten"


# ---------- Helper baca & olah data ----------
@st.cache_data
def baca_file(file, header_row: int) -> pd.DataFrame:
    """header_row = -1 -> cari baris header otomatis (memuat 'nilai', 'nama', atau rentang nilai)."""
    if file.name.lower().endswith((".xlsx", ".xls")):
        mentah = pd.read_excel(file, header=None)
    else:
        mentah = pd.read_csv(file, header=None)
    if header_row < 0:
        header_row = 0
        for i in range(min(len(mentah), 15)):
            isi = [str(v).strip().lower() for v in mentah.iloc[i].tolist()]
            if any("nilai" in v or "nama" in v or v.replace(" ", "") in BUCKET_NORM for v in isi):
                header_row = i
                break
    df = mentah.iloc[header_row + 1:].copy()
    df.columns = [str(c).strip() for c in mentah.iloc[header_row].tolist()]
    df = df.dropna(how="all").dropna(axis=1, how="all").reset_index(drop=True)
    return df


def cari_kolom(cols, kata):
    for c in cols:
        if kata in c.lower():
            return c
    return None


def kolom_bucket(cols):
    return [c for c in cols if c.replace(" ", "") in BUCKET_NORM]


def ke_angka(seri):
    """Ubah ke angka; aman untuk teks seperti '85,5' atau ' 85 '."""
    return pd.to_numeric(seri.astype(str).str.strip().str.replace(",", ".", regex=False), errors="coerce")


POLA_TAHUN = r"(?<!\d)((?:19|20)\d{2})(?!\d)"


def ekstrak_tahun(seri):
    """Ambil angka tahun 4 digit dari kolom (mis. 'Kamis, 16 April 2026' atau 2024-04-16)."""
    return pd.to_numeric(seri.astype(str).str.extract(POLA_TAHUN)[0], errors="coerce")


def susun_data(df, nama_file, tahun_src, tahun_manual, mode, col_nilai, col_bucket, col_nama, col_paket):
    if mode == "Satu kolom nilai":
        nilai = ke_angka(df[col_nilai])
    else:
        nilai = df[col_bucket].apply(ke_angka).max(axis=1) if col_bucket else pd.Series(np.nan, index=df.index)
    tahun = tahun_manual if tahun_src == "Isi manual" else ekstrak_tahun(df[tahun_src])
    return pd.DataFrame(
        {
            "tahun": tahun,
            "nama": df[col_nama] if col_nama else None,
            "nilai": nilai,
            "paket": df[col_paket] if col_paket else None,
            "sumber": nama_file,
        }
    )


@st.cache_data
def data_contoh() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    rows = []
    for tahun, mu in {2022: 70, 2024: 76, 2026: 80}.items():
        for i, v in enumerate(np.clip(rng.normal(mu, 11, 200), 30, 100)):
            rows.append({"tahun": tahun, "nama": f"Siswa {tahun}-{i}", "nilai": round(v, 1),
                         "paket": f"Paket {i % 3 + 1}", "sumber": "contoh"})
    return pd.DataFrame(rows)


# ---------- Sidebar: upload ----------
st.title("Tren Hasil Ujian Kompetensi SMK")

frames = []
with st.sidebar:
    st.header("Upload data")
    st.caption("Boleh banyak file sekaligus, tahun apa saja (CSV / Excel). Tahun dibaca dari nama file, "
               "kolom di dalam file, atau diisi manual.")
    files = st.file_uploader("File data", type=["csv", "xlsx", "xls"], accept_multiple_files=True)

    for i, f in enumerate(files or []):
        k = f"{i}_{f.name}"
        with st.expander(f.name, expanded=len(files) <= 3):
            header_row = st.number_input(
                "Baris header (-1 = otomatis)", min_value=-1, value=-1, key=f"hdr_{k}",
                help="Biarkan -1 supaya dicari otomatis. Isi manual (mulai dari 0) kalau salah.",
            )
            raw = baca_file(f, int(header_row))
            cols = list(raw.columns)
            st.caption(f"{len(raw)} baris | kolom: {', '.join(cols[:8])}")

            # --- sumber tahun ---
            tebak = re.search(POLA_TAHUN, f.name)
            kol_th = cari_kolom(cols, "tahun") or (None if tebak else cari_kolom(cols, "tanggal"))
            opsi_th = ["Isi manual"] + cols
            src = st.selectbox("Sumber tahun", opsi_th,
                               index=opsi_th.index(kol_th) if kol_th else 0, key=f"src_{k}")
            tahun_manual = None
            if src == "Isi manual":
                tahun_manual = st.number_input("Tahun", 1990, 2100, int(tebak.group(1)) if tebak else 2026,
                                               key=f"th_{k}")

            # --- format nilai ---
            bkt = kolom_bucket(cols)
            mode = st.radio("Format nilai", ["Satu kolom nilai", "Tersebar di kolom rentang"],
                            index=1 if len(bkt) >= 2 else 0, key=f"mode_{k}",
                            help="'Tersebar' = nilai ditaruh di salah satu kolom 91-100 / 75-90 / 61-74 / <60.")
            col_nilai, col_bucket = None, []
            if mode == "Satu kolom nilai":
                d = cari_kolom(cols, "nilai")
                col_nilai = st.selectbox("Kolom nilai", cols, index=cols.index(d) if d else 0, key=f"nil_{k}")
            else:
                col_bucket = st.multiselect("Kolom rentang nilai", cols, default=bkt, key=f"bkt_{k}")

            # --- opsional ---
            col_nama = cari_kolom(cols, "nama")
            col_paket = cari_kolom(cols, "paket")

            hasil = susun_data(raw, f.name, src, tahun_manual, mode, col_nilai, col_bucket, col_nama, col_paket)
            valid = (hasil["nilai"].between(0, 100) & hasil["tahun"].notna()).sum()
            if valid == 0:
                st.error(f"0 nilai valid dari {len(raw)} baris. Cek sumber tahun, kolom nilai, atau baris header.")
            else:
                th = sorted(hasil.loc[hasil["nilai"].between(0, 100), "tahun"].dropna().astype(int).unique())
                st.success(f"{valid} nilai valid dari {len(raw)} baris | tahun: {', '.join(map(str, th))}")
            frames.append(hasil)

if frames:
    df = pd.concat(frames, ignore_index=True)
else:
    st.info("Belum ada file diupload, menampilkan data contoh. Upload file di sidebar untuk memakai datamu.")
    df = data_contoh()

df = df.dropna(subset=["nilai", "tahun"])
df = df[(df["nilai"] >= 0) & (df["nilai"] <= 100)].copy()
if df.empty:
    st.warning("Tidak ada nilai valid. Cek pengaturan tiap file di sidebar.")
    st.stop()
df["tahun"] = df["tahun"].astype(int)
df["tahun_str"] = df["tahun"].astype(str)
df["kesimpulan"] = pd.Categorical(df["nilai"].apply(konversi), categories=KATEGORI, ordered=True)

# ---------- Filter ----------
with st.sidebar:
    st.header("Filter")
    tahun_opsi = sorted(df["tahun"].unique())
    tahun_pilih = st.multiselect("Tahun", tahun_opsi, default=tahun_opsi)
df = df[df["tahun"].isin(tahun_pilih)]
if df.empty:
    st.warning("Pilih minimal satu tahun.")
    st.stop()
urut_tahun = [str(t) for t in sorted(df["tahun"].unique())]

# ---------- Ringkasan per tahun ----------
ringkas = (
    df.groupby("tahun")
    .agg(
        jumlah=("nilai", "size"),
        rata2=("nilai", "mean"),
        median=("nilai", "median"),
        minimum=("nilai", "min"),
        maksimum=("nilai", "max"),
        pct_kompeten=("nilai", lambda s: (s >= 75).mean() * 100),
        pct_belum=("nilai", lambda s: (s < 61).mean() * 100),
    )
    .reset_index()
)

st.subheader("Ringkasan")
prev = None
baris = [ringkas.iloc[i:i + 5] for i in range(0, len(ringkas), 5)]
for chunk in baris:
    kc = st.columns(5)
    for c, (_, r) in zip(kc, chunk.iterrows()):
        delta = None if prev is None else f"{r['rata2'] - prev:+.1f} vs sebelumnya"
        c.metric(f"Rata-rata {int(r['tahun'])}", f"{r['rata2']:.1f}", delta)
        c.caption(f"{int(r['jumlah'])} siswa | {r['pct_kompeten']:.0f}% Kompeten ke atas")
        prev = r["rata2"]

tab1, tab2, tab3, tab4 = st.tabs(["Tren", "Distribusi nilai", "Paket soal", "Data"])

# ---------- Tab 1: Tren ----------
with tab1:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Rata-rata & median nilai per tahun**")
        long = ringkas.melt(id_vars="tahun", value_vars=["rata2", "median"], var_name="metrik", value_name="nilai")
        long["metrik"] = long["metrik"].map({"rata2": "Rata-rata", "median": "Median"})
        long["tahun"] = long["tahun"].astype(str)
        fig = px.line(long, x="tahun", y="nilai", color="metrik", markers=True,
                      category_orders={"tahun": urut_tahun})
        fig.update_yaxes(range=[0, 100])
        for batas in (61, 75, 91):
            fig.add_hline(y=batas, line_dash="dot", line_color="grey", opacity=0.5)
        st.plotly_chart(fig, use_container_width=True)

    prop = df.groupby(["tahun_str", "kesimpulan"], observed=False).size().reset_index(name="n")
    prop["persen"] = prop["n"] / prop.groupby("tahun_str")["n"].transform("sum") * 100
    with c2:
        st.markdown("**Proporsi kesimpulan per tahun (100%)**")
        fig = px.bar(
            prop, x="tahun_str", y="persen", color="kesimpulan",
            color_discrete_map=WARNA,
            category_orders={"kesimpulan": KATEGORI, "tahun_str": urut_tahun},
            text=prop["persen"].round(1).astype(str) + "%",
        )
        fig.update_layout(xaxis_title="tahun", yaxis_title="% siswa", barmode="stack")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("**Persentase tiap kategori antar tahun**")
    pivot = prop.pivot(index="kesimpulan", columns="tahun_str", values="persen").reindex(KATEGORI[::-1])
    pivot = pivot[urut_tahun]
    fig = px.imshow(pivot, text_auto=".1f", color_continuous_scale="Blues", aspect="auto",
                    labels=dict(color="% siswa", x="tahun"))
    st.plotly_chart(fig, use_container_width=True)

# ---------- Tab 2: Distribusi ----------
with tab2:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Sebaran nilai (box plot)**")
        fig = px.box(df, x="tahun_str", y="nilai", color="tahun_str", points="outliers",
                     category_orders={"tahun_str": urut_tahun})
        fig.update_layout(showlegend=False, xaxis_title="tahun")
        for batas in (61, 75, 91):
            fig.add_hline(y=batas, line_dash="dot", line_color="grey", opacity=0.5)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.markdown("**Histogram nilai per tahun**")
        fig = px.histogram(df, x="nilai", color="tahun_str", barmode="overlay", nbins=30, opacity=0.6,
                           category_orders={"tahun_str": urut_tahun})
        fig.update_layout(legend_title="Tahun")
        for batas in (61, 75, 91):
            fig.add_vline(x=batas, line_dash="dot", line_color="grey")
        st.plotly_chart(fig, use_container_width=True)

# ---------- Tab 3: Paket soal ----------
with tab3:
    dp = df[df["paket"].notna()]
    if dp.empty:
        st.info("Belum ada data dengan kolom 'paket soal' (kolom yang namanya memuat kata 'paket').")
    else:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Rata-rata nilai per paket soal**")
            rp = dp.groupby(["paket", "tahun_str"])["nilai"].agg(["mean", "count"]).reset_index()
            fig = px.bar(rp, x="paket", y="mean", color="tahun_str", barmode="group",
                         text=rp["mean"].round(1), hover_data=["count"],
                         category_orders={"tahun_str": urut_tahun})
            fig.update_yaxes(range=[0, 100], title="Rata-rata nilai")
            fig.update_layout(legend_title="Tahun")
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            th_paket = sorted(dp["tahun"].unique())
            th_pilih = st.selectbox("Komposisi kesimpulan per paket, tahun:", th_paket, key="th_paket")
            sub = dp[dp["tahun"] == th_pilih]
            kp = sub.groupby(["paket", "kesimpulan"], observed=False).size().reset_index(name="n")
            kp["persen"] = kp["n"] / kp.groupby("paket")["n"].transform("sum") * 100
            fig = px.bar(kp, x="paket", y="persen", color="kesimpulan",
                         color_discrete_map=WARNA, category_orders={"kesimpulan": KATEGORI})
            fig.update_layout(yaxis_title="% siswa")
            st.plotly_chart(fig, use_container_width=True)

# ---------- Tab 4: Data ----------
with tab4:
    st.markdown("**Tabel ringkasan per tahun**")
    tampil = ringkas.rename(columns={
        "tahun": "Tahun", "jumlah": "Jumlah siswa", "rata2": "Rata-rata", "median": "Median",
        "minimum": "Min", "maksimum": "Maks", "pct_kompeten": "% Kompeten ke atas",
        "pct_belum": "% Belum Kompeten",
    }).round(1)
    st.dataframe(tampil, use_container_width=True, hide_index=True)
    st.download_button("Download ringkasan (CSV)", tampil.to_csv(index=False).encode("utf-8"),
                       "ringkasan_tren.csv", "text/csv")
    st.markdown("**Data siswa gabungan (setelah filter)**")
    st.dataframe(df.drop(columns=["tahun_str"]), use_container_width=True)