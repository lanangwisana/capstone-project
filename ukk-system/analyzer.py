import io
import re
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd

KATEGORI = ["Belum Kompeten", "Cukup Kompeten", "Kompeten", "Sangat Kompeten"]
WARNA = {
    "Belum Kompeten": "#d62728",
    "Cukup Kompeten": "#ff9f1c",
    "Kompeten": "#2ca02c",
    "Sangat Kompeten": "#1f77b4",
}
BUCKET_NORM = {"91-100", "75-90", "61-74", "<60", "<61"}
POLA_TAHUN = r"(?<!\d)((?:19|20)\d{2})(?!\d)"


def konversi(nilai: float) -> str:
    if nilai >= 91:
        return "Sangat Kompeten"
    if nilai >= 75:
        return "Kompeten"
    if nilai >= 61:
        return "Cukup Kompeten"
    return "Belum Kompeten"


def baca_tabel(file_source: Union[bytes, io.BytesIO, Any], filename: str, header_row: int = -1) -> pd.DataFrame:
    """Membaca CSV/Excel menjadi DataFrame. header_row = -1 -> cari baris header otomatis."""
    source = io.BytesIO(file_source) if isinstance(file_source, (bytes, bytearray)) else file_source
    if filename.lower().endswith((".xlsx", ".xls")):
        mentah = pd.read_excel(source, header=None)
    else:
        mentah = pd.read_csv(source, header=None)

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


def cari_kolom(cols: List[str], kata: str) -> Optional[str]:
    for c in cols:
        if kata in str(c).lower():
            return c
    return None


def kolom_bucket(cols: List[str]) -> List[str]:
    return [c for c in cols if str(c).replace(" ", "") in BUCKET_NORM]


def ke_angka(seri: pd.Series) -> pd.Series:
    """Ubah ke angka; aman untuk teks seperti '85,5' atau ' 85 '."""
    return pd.to_numeric(seri.astype(str).str.strip().str.replace(",", ".", regex=False), errors="coerce")


def ekstrak_tahun(seri: pd.Series) -> pd.Series:
    """Ambil angka tahun 4 digit dari kolom (mis. 'Kamis, 16 April 2026' atau 2024-04-16)."""
    return pd.to_numeric(seri.astype(str).str.extract(POLA_TAHUN)[0], errors="coerce")


def susun_data(
    df: pd.DataFrame,
    nama_file: str,
    tahun_src: str,
    tahun_manual: Optional[int],
    mode: str,
    col_nilai: Optional[str],
    col_bucket: List[str],
    col_nama: Optional[str],
    col_paket: Optional[str],
) -> pd.DataFrame:
    if mode == "Satu kolom nilai":
        nilai = ke_angka(df[col_nilai]) if col_nilai else pd.Series(np.nan, index=df.index)
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


def proses_otomatis(
    raw: pd.DataFrame,
    filename: str,
    tahun_manual: Optional[int] = None,
) -> pd.DataFrame:
    """Deteksi otomatis kolom tahun, format nilai, nama, dan paket dari DataFrame mentah."""
    cols = [str(c) for c in raw.columns]
    tebak = re.search(POLA_TAHUN, filename)
    kol_th = cari_kolom(cols, "tahun") or (None if tebak else cari_kolom(cols, "tanggal"))

    if kol_th:
        src = kol_th
        th_val = tahun_manual
    else:
        src = "Isi manual"
        th_val = tahun_manual if tahun_manual is not None else (int(tebak.group(1)) if tebak else 2026)

    bkt = kolom_bucket(cols)
    if len(bkt) >= 2:
        mode = "Tersebar di kolom rentang"
        col_nilai, col_bucket = None, bkt
    else:
        mode = "Satu kolom nilai"
        col_nilai = cari_kolom(cols, "nilai") or (cols[0] if cols else None)
        col_bucket = []

    col_nama = cari_kolom(cols, "nama")
    col_paket = cari_kolom(cols, "paket")
    return susun_data(raw, filename, src, th_val, mode, col_nilai, col_bucket, col_nama, col_paket)


def data_contoh() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    rows = []
    for tahun, mu in {2022: 70, 2024: 76, 2026: 80}.items():
        for i, v in enumerate(np.clip(rng.normal(mu, 11, 200), 30, 100)):
            rows.append(
                {
                    "tahun": tahun,
                    "nama": f"Siswa {tahun}-{i}",
                    "nilai": round(float(v), 1),
                    "paket": f"Paket {i % 3 + 1}",
                    "sumber": "contoh",
                }
            )
    return pd.DataFrame(rows)


def bersihkan_dan_kategorikan(df: pd.DataFrame, tahun_filter: Optional[List[int]] = None) -> pd.DataFrame:
    """Filter nilai valid (0-100), pastikan tahun integer, dan tambahkan kolom kesimpulan."""
    clean = df.dropna(subset=["nilai", "tahun"]).copy()
    clean = clean[(clean["nilai"] >= 0) & (clean["nilai"] <= 100)].copy()
    if clean.empty:
        return clean

    clean["tahun"] = clean["tahun"].astype(int)
    if tahun_filter:
        clean = clean[clean["tahun"].isin(tahun_filter)].copy()
        if clean.empty:
            return clean

    clean["tahun_str"] = clean["tahun"].astype(str)
    clean["kesimpulan"] = pd.Categorical(clean["nilai"].apply(konversi), categories=KATEGORI, ordered=True)
    return clean


def hitung_ringkasan(df: pd.DataFrame) -> pd.DataFrame:
    return (
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
        .sort_values("tahun")
    )


def hitung_analitik_json(df: pd.DataFrame) -> Dict[str, Any]:
    """Menghasilkan payload JSON lengkap untuk kebutuhan dashboard frontend."""
    ringkas = hitung_ringkasan(df)

    summary_rows = []
    prev_rata2 = None
    for _, r in ringkas.iterrows():
        rata2_val = round(float(r["rata2"]), 2)
        delta = None if prev_rata2 is None else round(rata2_val - prev_rata2, 2)
        summary_rows.append(
            {
                "tahun": int(r["tahun"]),
                "jumlah": int(r["jumlah"]),
                "rata2": rata2_val,
                "median": round(float(r["median"]), 2),
                "minimum": round(float(r["minimum"]), 2),
                "maksimum": round(float(r["maksimum"]), 2),
                "pct_kompeten": round(float(r["pct_kompeten"]), 2),
                "pct_belum": round(float(r["pct_belum"]), 2),
                "delta_rata2": delta,
            }
        )
        prev_rata2 = rata2_val

    prop = df.groupby(["tahun", "kesimpulan"], observed=False).size().reset_index(name="n")
    prop["persen"] = prop["n"] / prop.groupby("tahun")["n"].transform("sum") * 100
    category_proportions = [
        {
            "tahun": int(r["tahun"]),
            "kesimpulan": str(r["kesimpulan"]),
            "n": int(r["n"]),
            "persen": round(float(r["persen"]), 2),
            "warna": WARNA.get(str(r["kesimpulan"]), "#888888"),
        }
        for _, r in prop.iterrows()
    ]

    distribution_stats = []
    for tahun, grp in df.groupby("tahun"):
        q1, med, q3 = np.percentile(grp["nilai"], [25, 50, 75])
        distribution_stats.append(
            {
                "tahun": int(tahun),
                "min": round(float(grp["nilai"].min()), 2),
                "q1": round(float(q1), 2),
                "median": round(float(med), 2),
                "q3": round(float(q3), 2),
                "max": round(float(grp["nilai"].max()), 2),
            }
        )

    dp = df[df["paket"].notna()].copy()
    paket_summary = []
    paket_composition = []
    if not dp.empty:
        rp = dp.groupby(["paket", "tahun"])["nilai"].agg(["mean", "count"]).reset_index()
        paket_summary = [
            {
                "paket": str(r["paket"]),
                "tahun": int(r["tahun"]),
                "rata2": round(float(r["mean"]), 2),
                "jumlah": int(r["count"]),
            }
            for _, r in rp.iterrows()
        ]
        kp = dp.groupby(["tahun", "paket", "kesimpulan"], observed=False).size().reset_index(name="n")
        kp["persen"] = kp["n"] / kp.groupby(["tahun", "paket"])["n"].transform("sum") * 100
        paket_composition = [
            {
                "tahun": int(r["tahun"]),
                "paket": str(r["paket"]),
                "kesimpulan": str(r["kesimpulan"]),
                "n": int(r["n"]),
                "persen": round(float(r["persen"]), 2),
            }
            for _, r in kp.iterrows()
        ]

    records_df = df[["tahun", "nama", "nilai", "paket", "sumber", "kesimpulan"]].copy()
    records_df["kesimpulan"] = records_df["kesimpulan"].astype(str)
    records_df = records_df.where(pd.notnull(records_df), None)

    return {
        "total_records": int(len(df)),
        "years": [int(t) for t in sorted(df["tahun"].unique())],
        "rubrik_colors": WARNA,
        "summary_by_year": summary_rows,
        "category_proportions": category_proportions,
        "distribution_stats": distribution_stats,
        "paket_analysis": {
            "summary": paket_summary,
            "composition": paket_composition,
        },
        "students": records_df.to_dict(orient="records"),
    }
