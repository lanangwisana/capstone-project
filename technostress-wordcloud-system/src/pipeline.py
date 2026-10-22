import re
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np
from .nlp_preprocessor import NLPPreprocessor
from .stress_classifier import HybridStressClassifier
from .wordcloud_generator import WordCloudGenerator

class TechnostressPipeline:
    """
    Pipeline terpadu untuk analisis Technostress:
    Menerima input CSV / JSON, melakukan klasifikasi Hybrid (Likert Agnostik vs NLP Fallback),
    preprocessing teks (mendukung multi-kolom esai), tagging 5 Dimensi Technostress (Text-Driven),
    dan ekstraksi n-gram untuk visualisasi Word Cloud.
    """

    def __init__(self, additional_stopwords: Optional[set] = None):
        self.preprocessor = NLPPreprocessor(additional_stopwords=additional_stopwords)
        self.classifier = HybridStressClassifier()
        self.wc_generator = WordCloudGenerator()

    def find_essay_columns(self, df: pd.DataFrame) -> List[str]:
        """Mendeteksi semua kolom esai/teks dalam dataset secara dinamis."""
        ignore_pattern = re.compile(r"(_id$|^id$|nama|name|siswa|mahasiswa|uuid|code|no$|nomor|index|timestamp|date|time)", re.IGNORECASE)
        pattern = re.compile(r"(essay|esai|komentar|comment|ulasan|review|keluhan|feedback|teks|text|jawaban|opini|cerita)", re.IGNORECASE)
        
        essay_cols = []
        for col in df.columns:
            if not ignore_pattern.search(col):
                if pattern.search(col) and df[col].dtype == "object":
                    essay_cols.append(col)
        
        # Jika tidak ditemukan nama yang cocok, cari kolom string berkarakter panjang
        if not essay_cols:
            candidate_cols = [c for c in df.columns if not ignore_pattern.search(c) and df[c].dtype == "object"]
            if candidate_cols:
                best_col = max(candidate_cols, key=lambda c: df[c].dropna().astype(str).map(len).mean() if len(df[c].dropna()) > 0 else 0)
                essay_cols.append(best_col)

        return essay_cols

    def process_dataframe(
        self,
        df: pd.DataFrame,
        text_col: Optional[str] = None,
        ngram_mode: str = "both"
    ) -> Dict[str, Any]:
        """
        Memproses DataFrame lengkap (baik dari CSV maupun list JSON).
        Perhitungan Likert bersifat agnostik (fleksibel untuk berapa pun jumlah butir soal),
        dan pemetaan 5 Dimensi Technostress didasarkan pada narasi teks esai (Text-Driven NLP).
        """
        if df.empty:
            return {"error": "DataFrame kosong"}

        # 1. Identifikasi Kolom Esai & Likert
        detected_essay_cols = self.find_essay_columns(df)
        if not detected_essay_cols:
            return {"error": "Tidak dapat menemukan kolom teks / esai dalam data"}

        # Penentuan teks yang akan diproses
        active_essay_col = text_col
        if not active_essay_col or active_essay_col == "ALL_COMBINED":
            # Gabungkan seluruh kolom esai yang ada
            combined_series = df[detected_essay_cols].fillna('').astype(str).agg(' '.join, axis=1)
            working_df = df.copy()
            working_df["_processed_text_"] = combined_series
            text_target = "_processed_text_"
            text_column_label = f"Gabungan Esai ({', '.join(detected_essay_cols)})"
        else:
            if active_essay_col in df.columns:
                working_df = df.copy()
                working_df["_processed_text_"] = working_df[active_essay_col].fillna('').astype(str)
                text_target = "_processed_text_"
                text_column_label = active_essay_col
            else:
                return {"error": f"Kolom {active_essay_col} tidak ditemukan"}

        likert_cols = self.classifier.detect_likert_columns(df)
        active_mode = "LIKERT" if len(likert_cols) > 0 else "NLP_INFERRED"

        # 2. Proses Klasifikasi & Preprocessing Tiap Baris
        results = []
        for idx, row in working_df.iterrows():
            # Klasifikasi Stres (Hybrid: rata-rata dinamis dari seluruh kolom Likert yang ada)
            res = self.classifier.process_row(row, likert_cols, text_target)
            
            # Preprocessing Teks NLP & Deteksi Dimensi Technostress (Text-Driven)
            text_val = res["text"]
            tokens = self.preprocessor.tokenize(text_val)
            ngrams = self.preprocessor.extract_ngrams(tokens, mode=ngram_mode)
            dimensions = self.preprocessor.tag_dimensions(text_val)
            
            res["tokens"] = tokens
            res["ngrams"] = ngrams
            res["dimensions"] = dimensions
            
            # Pertahankan kolom metadata penting dari data asli
            for meta_col in ["respondent_id", "nama_siswa"] + detected_essay_cols:
                if meta_col in df.columns:
                    res[meta_col] = df.loc[idx, meta_col]

            results.append(res)

        processed_df = pd.DataFrame(results)

        # 3. Hitung Frekuensi N-gram per Kategori
        all_freq = self.wc_generator.compute_frequencies(processed_df["ngrams"].tolist())
        
        high_stress_df = processed_df[processed_df["stress_level"] == "Tinggi"]
        high_freq = self.wc_generator.compute_frequencies(high_stress_df["ngrams"].tolist())
        
        low_stress_df = processed_df[processed_df["stress_level"] == "Rendah"]
        low_freq = self.wc_generator.compute_frequencies(low_stress_df["ngrams"].tolist())
        
        medium_stress_df = processed_df[processed_df["stress_level"] == "Sedang"]
        medium_freq = self.wc_generator.compute_frequencies(medium_stress_df["ngrams"].tolist())

        # 4. Ringkasan Statistik
        summary = {
            "total_respondents": len(processed_df),
            "mode_used": active_mode,
            "likert_columns_detected": likert_cols,
            "likert_question_count": len(likert_cols),
            "essay_columns_detected": detected_essay_cols,
            "text_column_used": text_column_label,
            "stress_counts": processed_df["stress_level"].value_counts().to_dict(),
            "average_score": round(float(processed_df["stress_score"].mean()), 2)
        }

        return {
            "summary": summary,
            "processed_df": processed_df,
            "frequencies": {
                "Semua": all_freq,
                "Tinggi": high_freq,
                "Sedang": medium_freq,
                "Rendah": low_freq
            }
        }

    def process_json_payload(self, payload: Any, ngram_mode: str = "both") -> Dict[str, Any]:
        """
        Memproses payload JSON realtime (baik berupa dict tunggal maupun list of dicts).
        """
        if isinstance(payload, dict):
            if "likert_scores" in payload and isinstance(payload["likert_scores"], dict):
                flat_item = {k: v for k, v in payload.items() if k != "likert_scores"}
                for lk, lv in payload["likert_scores"].items():
                    flat_item[f"pertanyaan_{lk}" if not str(lk).startswith("pertanyaan_") else lk] = lv
                df = pd.DataFrame([flat_item])
            else:
                df = pd.DataFrame([payload])
        elif isinstance(payload, list):
            flattened_list = []
            for item in payload:
                if isinstance(item, dict) and "likert_scores" in item and isinstance(item["likert_scores"], dict):
                    flat_item = {k: v for k, v in item.items() if k != "likert_scores"}
                    for lk, lv in item["likert_scores"].items():
                        flat_item[f"pertanyaan_{lk}" if not str(lk).startswith("pertanyaan_") else lk] = lv
                    flattened_list.append(flat_item)
                else:
                    flattened_list.append(item)
            df = pd.DataFrame(flattened_list)
        else:
            return {"error": "Format JSON tidak valid (harus Object atau Array)"}

        return self.process_dataframe(df, ngram_mode=ngram_mode)
