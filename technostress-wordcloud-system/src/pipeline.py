import re
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
from .nlp_preprocessor import NLPPreprocessor
from .wordcloud_generator import WordCloudGenerator

class TechnostressPipeline:
    """
    Pipeline khusus untuk konsumsi API format JSON dengan validasi skema ketat (Strict Contract).
    Menangani:
    1. Validasi parameter Grafik Siswa (id, name, kalkulasi, kategori, post_date).
    2. Validasi parameter Word Cloud (id, name, essay_1 ... essay_N, post_date).
    3. Normalisasi kategori dan ekstraksi NLP/Bigram.
    """

    def __init__(self, additional_stopwords: Optional[set] = None):
        self.preprocessor = NLPPreprocessor(additional_stopwords=additional_stopwords)
        self.wc_generator = WordCloudGenerator()

    def normalize_kategori(self, val: Any) -> str:
        """Menstandarkan variasi penulisan kategori ke 'Tinggi', 'Sedang', 'Rendah'."""
        if not val or not isinstance(val, str):
            return "Sedang"
        val_lower = val.lower().strip()
        if "tinggi" in val_lower:
            return "Tinggi"
        elif "rendah" in val_lower:
            return "Rendah"
        elif "sedang" in val_lower:
            return "Sedang"
        return val.capitalize()

    def process_json_payload(
        self,
        payload: Any,
        ngram_mode: str = "both"
    ) -> Dict[str, Any]:
        """
        Memproses payload JSON dengan validasi ketat (Strict Schema Validation).
        """
        # 1. Parsing payload wrapper (misal envelope key: 'data')
        raw_list = []
        if isinstance(payload, dict):
            if "data" in payload and isinstance(payload["data"], list):
                raw_list = payload["data"]
            else:
                raw_list = [payload]
        elif isinstance(payload, list):
            raw_list = payload
        else:
            return {
                "success": False,
                "error_message": "Format payload JSON tidak valid (harus berupa Object atau Array)."
            }

        if not raw_list:
            return {
                "success": False,
                "error_message": "Payload JSON kosong atau array 'data' tidak memuat baris data."
            }

        df = pd.DataFrame(raw_list)

        # 2. Pemeriksaan Identitas Dasar
        id_col = None
        for col in ["id", "respondent_id", "ID"]:
            if col in df.columns:
                id_col = col
                break

        name_col = None
        for col in ["name", "nama", "nama_siswa", "Name"]:
            if col in df.columns:
                name_col = col
                break

        post_date_col = None
        for col in ["post_date", "date", "created_at", "timestamp"]:
            if col in df.columns:
                post_date_col = col
                break

        identity_missing = []
        if not id_col:
            identity_missing.append("id / respondent_id")
        if not name_col:
            identity_missing.append("name / nama_siswa")
        if not post_date_col:
            identity_missing.append("post_date")

        # 3. Pemeriksaan Syarat Visualisasi 1: Grafik Tingkat Stres (kalkulasi & kategori)
        kalkulasi_col = None
        for col in ["kalkulasi", "kalkuasi", "score", "skor", "stress_score"]:
            if col in df.columns:
                kalkulasi_col = col
                break

        kategori_col = None
        for col in ["kategori", "category", "stress_level", "level"]:
            if col in df.columns:
                kategori_col = col
                break

        chart_missing_params = []
        if identity_missing:
            chart_missing_params.extend(identity_missing)
        if not kalkulasi_col:
            chart_missing_params.append("kalkulasi")
        if not kategori_col:
            chart_missing_params.append("kategori")

        can_render_chart = (len(chart_missing_params) == 0)

        # 4. Pemeriksaan Syarat Visualisasi 2: Word Cloud Komparatif (essay_1 ... essay_N)
        essay_cols = [c for c in df.columns if re.search(r"essay|esai|komentar|ulasan", c, re.IGNORECASE) and df[c].dtype == "object"]
        
        wordcloud_missing_params = []
        if identity_missing:
            wordcloud_missing_params.extend(identity_missing)
        if not essay_cols:
            wordcloud_missing_params.append("essay_1 ... essay_N")

        can_render_wordcloud = (len(wordcloud_missing_params) == 0)

        # 5. Transformasi Data
        processed_records = []
        for idx, row in df.iterrows():
            rec = {}
            rec["id"] = str(row[id_col]) if id_col and pd.notna(row[id_col]) else f"ID-{idx+1}"
            rec["name"] = str(row[name_col]) if name_col and pd.notna(row[name_col]) else f"Responden {idx+1}"
            rec["post_date"] = str(row[post_date_col]) if post_date_col and pd.notna(row[post_date_col]) else "-"

            # Parameter Kalkulasi & Kategori
            if can_render_chart:
                try:
                    val_kalkulasi = float(row[kalkulasi_col])
                except (ValueError, TypeError):
                    val_kalkulasi = 3.0
                rec["kalkulasi"] = round(val_kalkulasi, 2)
                rec["rounded_scale"] = int(max(1, min(5, round(val_kalkulasi))))
                rec["kategori"] = self.normalize_kategori(row[kategori_col])
            else:
                rec["kalkulasi"] = None
                rec["rounded_scale"] = None
                rec["kategori"] = "Belum Diketahui"

            # Parameter Teks Esai
            if can_render_wordcloud:
                text_parts = [str(row[ec]) for ec in essay_cols if pd.notna(row[ec]) and str(row[ec]).strip()]
                combined_essay = " ".join(text_parts)
                tokens = self.preprocessor.tokenize(combined_essay)
                ngrams = self.preprocessor.extract_ngrams(tokens, mode=ngram_mode)
                
                rec["essay_text"] = combined_essay
                rec["tokens"] = tokens
                rec["ngrams"] = ngrams
            else:
                rec["essay_text"] = ""
                rec["tokens"] = []
                rec["ngrams"] = []

            processed_records.append(rec)

        processed_df = pd.DataFrame(processed_records)

        # 6. Frekuensi Kata untuk Word Cloud (jika essay valid)
        frequencies = {"Semua": {}, "Tinggi": {}, "Sedang": {}, "Rendah": {}}
        if can_render_wordcloud:
            frequencies["Semua"] = self.wc_generator.compute_frequencies(processed_df["ngrams"].tolist())
            if can_render_chart:
                high_df = processed_df[processed_df["kategori"] == "Tinggi"]
                frequencies["Tinggi"] = self.wc_generator.compute_frequencies(high_df["ngrams"].tolist())

                med_df = processed_df[processed_df["kategori"] == "Sedang"]
                frequencies["Sedang"] = self.wc_generator.compute_frequencies(med_df["ngrams"].tolist())

                low_df = processed_df[processed_df["kategori"] == "Rendah"]
                frequencies["Rendah"] = self.wc_generator.compute_frequencies(low_df["ngrams"].tolist())

        # 7. Summary Hasil
        summary = {
            "total_records": len(processed_df),
            "can_render_chart": can_render_chart,
            "chart_missing_params": chart_missing_params,
            "can_render_wordcloud": can_render_wordcloud,
            "wordcloud_missing_params": wordcloud_missing_params,
            "essay_columns_found": essay_cols,
            "stress_counts": processed_df["kategori"].value_counts().to_dict() if can_render_chart else {},
            "average_score": round(float(processed_df["kalkulasi"].dropna().mean()), 2) if can_render_chart and not processed_df["kalkulasi"].dropna().empty else None
        }

        return {
            "success": True,
            "summary": summary,
            "processed_df": processed_df,
            "frequencies": frequencies
        }
