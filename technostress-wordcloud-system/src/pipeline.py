import re
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
from .nlp_preprocessor import NLPPreprocessor
from .stress_classifier import HybridStressClassifier
from .wordcloud_generator import WordCloudGenerator

class TechnostressPipeline:
    """
    Pipeline terpadu untuk analisis Technostress:
    Menerima input CSV / JSON, melakukan klasifikasi Hybrid (Likert vs NLP Fallback),
    preprocessing teks, tagging dimensi, dan penghitungan n-gram.
    """

    def __init__(self, additional_stopwords: Optional[set] = None):
        self.preprocessor = NLPPreprocessor(additional_stopwords=additional_stopwords)
        self.classifier = HybridStressClassifier()
        self.wc_generator = WordCloudGenerator()

    def find_text_column(self, df: pd.DataFrame) -> Optional[str]:
        """Mendeteksi kolom esai/teks dari kandidat nama kolom yang umum."""
        # Abaikan kolom ID atau metadata
        ignore_pattern = re.compile(r"(_id$|^id$|uuid|code|no$|nomor|index|timestamp|date|time)", re.IGNORECASE)
        pattern = re.compile(r"(essay|esai|komentar|comment|ulasan|review|keluhan|feedback|teks|text|jawaban|opini|cerita)", re.IGNORECASE)
        
        candidate_cols = [c for c in df.columns if not ignore_pattern.search(c)]
        
        # Cari yang match nama kandidat
        for col in candidate_cols:
            if pattern.search(col):
                return col
        
        # Jika tidak ditemukan nama yang cocok, cari kolom object/string dengan rata-rata panjang terpanjang
        text_cols = [c for c in candidate_cols if df[c].dtype == "object"]
        if text_cols:
            best_col = max(text_cols, key=lambda c: df[c].dropna().astype(str).map(len).mean() if len(df[c].dropna()) > 0 else 0)
            return best_col
        return None

    def process_dataframe(
        self,
        df: pd.DataFrame,
        text_col: Optional[str] = None,
        ngram_mode: str = "both"
    ) -> Dict[str, Any]:
        """
        Memproses DataFrame lengkap (baik dari CSV maupun list JSON).
        """
        if df.empty:
            return {"error": "DataFrame kosong"}

        # 1. Identifikasi Kolom
        if not text_col or text_col not in df.columns:
            text_col = self.find_text_column(df)
            
        if not text_col:
            return {"error": "Tidak dapat menemukan kolom teks / esai dalam data"}

        likert_cols = self.classifier.detect_likert_columns(df)
        active_mode = "LIKERT" if len(likert_cols) > 0 else "NLP_INFERRED"

        # 2. Proses Klasifikasi & Preprocessing Tiap Baris
        results = []
        for _, row in df.iterrows():
            # Klasifikasi Stres (Hybrid)
            res = self.classifier.process_row(row, likert_cols, text_col)
            
            # Preprocessing Teks NLP
            text_val = res["text"]
            tokens = self.preprocessor.tokenize(text_val)
            ngrams = self.preprocessor.extract_ngrams(tokens, mode=ngram_mode)
            dimensions = self.preprocessor.tag_dimensions(text_val)
            
            res["tokens"] = tokens
            res["ngrams"] = ngrams
            res["dimensions"] = dimensions
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
            "text_column_used": text_col,
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
            # Jika ada key 'likert_scores' bersarang, lakukan flatten
            if "likert_scores" in payload and isinstance(payload["likert_scores"], dict):
                flat_item = {k: v for k, v in payload.items() if k != "likert_scores"}
                for lk, lv in payload["likert_scores"].items():
                    flat_item[f"likert_{lk}"] = lv
                df = pd.DataFrame([flat_item])
            else:
                df = pd.DataFrame([payload])
        elif isinstance(payload, list):
            flattened_list = []
            for item in payload:
                if isinstance(item, dict) and "likert_scores" in item and isinstance(item["likert_scores"], dict):
                    flat_item = {k: v for k, v in item.items() if k != "likert_scores"}
                    for lk, lv in item["likert_scores"].items():
                        flat_item[f"likert_{lk}"] = lv
                    flattened_list.append(flat_item)
                else:
                    flattened_list.append(item)
            df = pd.DataFrame(flattened_list)
        else:
            return {"error": "Format JSON tidak valid (harus Object atau Array)"}

        return self.process_dataframe(df, ngram_mode=ngram_mode)
