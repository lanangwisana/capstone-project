import re
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
import numpy as np

class HybridStressClassifier:
    """
    Classifier hybrid untuk mendeteksi tingkat Technostress:
    1. Mode Utama (Likert): Menggunakan rata-rata skor kuisioner Likert (1 - 5).
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
        Pola: 'likert', 'q1', 'q2', 'skor', 'rating', 'bintang', 'star'.
        """
        likert_cols = []
        pattern = re.compile(r"(likert|soal_|pertanyaan_|skor_|score_|rating|star|bintang|^q\d+)", re.IGNORECASE)
        
        for col in df.columns:
            if pattern.search(col):
                # Pastikan kolom bertipe numerik
                if pd.api.types.is_numeric_dtype(df[col]):
                    likert_cols.append(col)
        return likert_cols

    def classify_by_likert(self, mean_score: float) -> Tuple[str, float]:
        """
        Mengelompokkan tingkat stres berdasarkan rata-rata skor Likert (skala 1 - 5).
        - Rendah: < 2.5
        - Sedang: 2.5 s/d < 3.6
        - Tinggi: >= 3.6
        """
        if pd.isna(mean_score):
            return "Sedang", 3.0
            
        if mean_score >= 3.6:
            return "Tinggi", float(mean_score)
        elif mean_score >= 2.5:
            return "Sedang", float(mean_score)
        else:
            return "Rendah", float(mean_score)

    def classify_by_text(self, text: str) -> Tuple[str, float, Dict[str, float]]:
        """
        Fallback: Mengelompokkan tingkat stres menggunakan leksikon NLP pada teks esai.
        Menghasilkan skor stress_index (1.0 s/d 5.0) agar setara skala Likert.
        """
        if not text or not isinstance(text, str):
            return "Sedang", 3.0, {"high_stress_score": 0.0, "low_stress_score": 0.0}

        words = text.lower().split()
        high_score = 0.0
        low_score = 0.0

        for w in words:
            # Hilangkan tanda baca sederhana
            w_clean = re.sub(r"[^a-zA-Z]", "", w)
            if w_clean in self.high_stress_lexicon:
                high_score += self.high_stress_lexicon[w_clean]
            if w_clean in self.low_stress_lexicon:
                low_score += self.low_stress_lexicon[w_clean]

        # Kalkulasi index ekuivalen Likert (1 - 5)
        # Baseline = 3.0 (Netral)
        net_stress = high_score - low_score
        
        if net_stress > 0:
            # Cenderung stres tinggi (naik dari 3.0 menuju 5.0)
            inferred_score = min(5.0, 3.0 + (net_stress * 0.5))
        elif net_stress < 0:
            # Cenderung stres rendah (turun dari 3.0 menuju 1.0)
            inferred_score = max(1.0, 3.0 + (net_stress * 0.5))
        else:
            inferred_score = 3.0

        level, _ = self.classify_by_likert(inferred_score)
        return level, round(inferred_score, 2), {"high_stress_score": high_score, "low_stress_score": low_score}

    def process_row(self, row: pd.Series, likert_cols: List[str], text_col: str) -> Dict[str, Any]:
        """
        Memproses satu baris data, memilih mode Likert jika ada, atau fallback ke NLP.
        """
        text_val = str(row[text_col]) if text_col in row and pd.notna(row[text_col]) else ""
        
        if likert_cols:
            # Mode Likert
            scores = [row[c] for c in likert_cols if pd.notna(row[c])]
            if scores:
                mean_likert = float(np.mean(scores))
                level, score = self.classify_by_likert(mean_likert)
                return {
                    "stress_level": level,
                    "stress_score": round(score, 2),
                    "source_mode": "LIKERT",
                    "text": text_val
                }

        # Fallback ke NLP Mode
        level, score, details = self.classify_by_text(text_val)
        return {
            "stress_level": level,
            "stress_score": score,
            "source_mode": "NLP_INFERRED",
            "text": text_val
        }

