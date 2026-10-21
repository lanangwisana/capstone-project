from typing import Dict, List, Optional, Tuple, Any
from collections import Counter
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import pandas as pd
import io
import base64
from PIL import Image

class WordCloudGenerator:
    """
    Generator Word Cloud khusus Technostress dengan dukungan ekstraksi frasa (Bigram),
    resolusi tinggi, palet modern, dan ekspor instan.
    """

    def __init__(self, width: int = 1000, height: int = 550, background_color: str = "white"):
        self.width = width
        self.height = height
        self.background_color = background_color

        # Palet warna modern & profesional
        self.colormap_config = {
            "Tinggi": "Reds",          # Gradasi merah koral hingga marun
            "Rendah": "YlGn",          # Gradasi hijau zamrud segar
            "Sedang": "Blues",         # Gradasi biru sejuk
            "Semua": "plasma"          # Multi-warna harmonis
        }

    def compute_frequencies(self, ngram_tokens_list: List[List[str]]) -> Dict[str, int]:
        """Menghitung frekuensi kemunculan kata / frasa n-gram."""
        flattened = [token for sublist in ngram_tokens_list for token in sublist if token]
        return dict(Counter(flattened))

    def generate_wordcloud_object(
        self,
        frequencies: Dict[str, int],
        category: str = "Semua",
        max_words: int = 75,
        bg_color: Optional[str] = None
    ) -> Optional[WordCloud]:
        """Menghasilkan object WordCloud murni dengan konfigurasi tajam & anti-alias."""
        if not frequencies:
            return None

        colormap = self.colormap_config.get(category, "coolwarm")
        effective_bg = bg_color if bg_color else self.background_color

        wc = WordCloud(
            width=self.width,
            height=self.height,
            background_color=effective_bg,
            colormap=colormap,
            max_words=max_words,
            collocations=False,
            prefer_horizontal=0.85,
            scale=2,  # Skala x2 untuk resolusi super tajam (HD)
            min_font_size=12,
            max_font_size=110,
            random_state=42
        ).generate_from_frequencies(frequencies)
        return wc

    def generate_wordcloud_image(
        self,
        frequencies: Dict[str, int],
        category: str = "Semua",
        max_words: int = 75,
        bg_color: Optional[str] = None
    ) -> Optional[Image.Image]:
        """
        Menghasilkan objek PIL Image langsung (tanpa bingkai matplotlib),
        sangat tajam dan estetis saat dirender di antarmuka web.
        """
        wc = self.generate_wordcloud_object(frequencies, category, max_words, bg_color)
        if wc is None:
            return None
        return wc.to_image()

    def generate_wordcloud_bytes(
        self,
        frequencies: Dict[str, int],
        category: str = "Semua",
        max_words: int = 75,
        bg_color: Optional[str] = None
    ) -> Optional[bytes]:
        """Menghasilkan byte PNG untuk tombol download file gambar."""
        img = self.generate_wordcloud_image(frequencies, category, max_words, bg_color)
        if img is None:
            return None
        buf = io.BytesIO()
        img.save(buf, format="PNG", quality=95)
        return buf.getvalue()

    def generate_comparative_images(
        self,
        high_stress_freq: Dict[str, int],
        low_stress_freq: Dict[str, int],
        max_words: int = 60,
        bg_color: Optional[str] = None
    ) -> Tuple[Optional[Image.Image], Optional[Image.Image]]:
        """Menghasilkan gambar PIL untuk perbandingan komparatif Stres Tinggi vs Rendah."""
        img_high = self.generate_wordcloud_image(high_stress_freq, category="Tinggi", max_words=max_words, bg_color=bg_color)
        img_low = self.generate_wordcloud_image(low_stress_freq, category="Rendah", max_words=max_words, bg_color=bg_color)
        return img_high, img_low

    def get_top_ngrams_df(self, frequencies: Dict[str, int], top_n: int = 15) -> pd.DataFrame:
        """Menghasilkan DataFrame top n frasa/kata untuk tabel analisis detail."""
        sorted_items = sorted(frequencies.items(), key=lambda x: x[1], reverse=True)[:top_n]
        df = pd.DataFrame(sorted_items, columns=["Frasa", "Frekuensi"])
        return df
