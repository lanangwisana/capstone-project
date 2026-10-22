import re
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
import numpy as np

class HybridStressClassifier:
    """
    Classifier hybrid untuk mendeteksi tingkat Technostress:
    1. Mode Utama (Likert): Menggunakan rata-rata skor kuisioner Likert dinamis (1.00 - 5.00)
       dengan interpretasi berbasis pembulatan skala 1 sampai 5.
    2. Mode Fallback (NLP Inferred): Menggunakan analisis leksikon sentimen/stres pada teks esai.
    """

    def __init__(self):
        # Leksikon kata indikator stres tinggi (keluhan, frustrasi, beban, masalah teknis)
        self.high_stress_lexicon = {
            # Masalah teknis & kompleksitas
            "error": 2.0, "lambat": 1.5, "rusak": 2.0, "gangguan": 1.5, "gagal": 1.5,
            "bingung": 1.5, "sulit": 1.5, "susah": 1.5, "ribet": 1.5, "rumit": 1.5,
            # Emosi & beban mental
            "lelah": 2.0, "capek": 2.0, "pusing": 2.0, "stres": 2.5, "tertekan": 2.5,
            "frustrasi": 2.5, "cemas": 2.0, "takut": 1.5, "khawatir": 1.5, "muak": 2.5,
            "emosi": 2.0, "jengkel": 1.5, "panik": 2.0,
            # Invasi & Overload
            "lembur": 1.5, "malam": 1.0, "libur": 1.0, "numpuk": 1.5, "banjir": 1.0,
            "dikejar": 1.5, "deadline": 1.2, "terbebani": 2.0, "overload": 2.0
        }

        # Leksikon kata indikator stres rendah (kepuasan, kemudahan, kelancaran)
        self.low_stress_lexicon = {
            "lancar": 2.0, "mudah": 1.5, "terbantu": 2.0, "cepat": 1.5, "praktis": 1.5,
            "nyaman": 2.0, "suka": 1.5, "puas": 2.0, "senang": 1.5, "fleksibel": 1.5,
            "efektif": 1.5, "efisien": 1.5, "tenang": 2.0, "ringan": 1.5, "bagus": 1.2,
            "membantu": 1.5, "mantap": 1.5, "stabil": 1.5, "jelas": 1.2, "hebat": 1.5
        }

    def detect_likert_columns(self, df: pd.DataFrame) -> List[str]:
        """
        Mendeteksi secara otomatis apakah DataFrame memiliki kolom skala Likert atau rating.
        Pola: 'likert', 'q1', 'q2', 'skor', 'rating', 'bintang', 'star', 'pertanyaan_'.
        """
        likert_cols = []
        pattern = re.compile(r"(likert|soal_|pertanyaan_|skor_|score_|rating|star|bintang|^q\d+)", re.IGNORECASE)
        
        for col in df.columns:
            if pattern.search(col):
                if pd.api.types.is_numeric_dtype(df[col]):
                    likert_cols.append(col)
        return likert_cols

    def classify_by_likert(self, mean_score: float) -> Tuple[str, float, int]:
        """
        Mengelompokkan tingkat stres berdasarkan rata-rata skor Likert:
        - Perhitungan: Rata-rata desimal presisi (misal 4.30).
        - Skala Pembulatan Interpretasi:
          * Nilai >= 3.50 -> Dibulatkan ke Skala 4 atau 5 = "Tinggi"
          * Nilai 2.50 s/d < 3.50 -> Dibulatkan ke Skala 3 = "Sedang"
          * Nilai < 2.50 -> Dibulatkan ke Skala 1 atau 2 = "Rendah"
        """
        if pd.isna(mean_score):
            return "Sedang", 3.0, 3

        mean_val = float(mean_score)
        rounded_scale = int(max(1, min(5, round(mean_val))))

        if mean_val >= 3.50:
            return "Tinggi", mean_val, rounded_scale
        elif mean_val >= 2.50:
            return "Sedang", mean_val, 3
        else:
            return "Rendah", mean_val, rounded_scale

    def classify_by_text(self, text: str) -> Tuple[str, float, int, Dict[str, float]]:
        """
        Fallback: Mengelompokkan tingkat stres menggunakan leksikon NLP pada teks esai.
        Menghasilkan skor stress_index (1.00 s/d 5.00) agar setara skala Likert.
        """
        if not text or not isinstance(text, str):
            return "Sedang", 3.0, 3, {"high_stress_score": 0.0, "low_stress_score": 0.0}

        words = text.lower().split()
        high_score = 0.0
        low_score = 0.0

        for w in words:
            w_clean = re.sub(r"[^a-zA-Z]", "", w)
            if w_clean in self.high_stress_lexicon:
                high_score += self.high_stress_lexicon[w_clean]
            if w_clean in self.low_stress_lexicon:
                low_score += self.low_stress_lexicon[w_clean]

        net_stress = high_score - low_score
        
        if net_stress > 0:
            inferred_score = min(5.0, 3.0 + (net_stress * 0.5))
        elif net_stress < 0:
            inferred_score = max(1.0, 3.0 + (net_stress * 0.5))
        else:
            inferred_score = 3.0

        level, score, rounded_scale = self.classify_by_likert(inferred_score)
        return level, round(score, 2), rounded_scale, {"high_stress_score": high_score, "low_stress_score": low_score}

    def process_row(self, row: pd.Series, likert_cols: List[str], text_col: str) -> Dict[str, Any]:
        """
        Memproses satu baris data, memilih mode Likert jika ada, atau fallback ke NLP.
        Menyimpan stress_score (desimal asli) dan rounded_scale (angka bulat interpretasi 1-5).
        """
        text_val = str(row[text_col]) if text_col in row and pd.notna(row[text_col]) else ""
        
        if likert_cols:
            scores = [row[c] for c in likert_cols if pd.notna(row[c])]
            if scores:
                mean_likert = float(np.mean(scores))
                level, score, rounded_scale = self.classify_by_likert(mean_likert)
                return {
                    "stress_level": level,
                    "stress_score": round(score, 2),
                    "rounded_scale": rounded_scale,
                    "source_mode": "LIKERT",
                    "text": text_val
                }

        # Fallback ke NLP Mode
        level, score, rounded_scale, details = self.classify_by_text(text_val)
        return {
            "stress_level": level,
            "stress_score": score,
            "rounded_scale": rounded_scale,
            "source_mode": "NLP_INFERRED",
            "text": text_val
        }
