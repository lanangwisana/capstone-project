import re
from typing import List, Dict, Tuple, Set
from collections import Counter
from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory

class NLPPreprocessor:
    """
    Preprocessor teks khusus domain Technostress Bahasa Indonesia.
    Mendukung normalisasi slang, pembersihan teks, stopwords domain,
    serta ekstraksi unigram & bigram.
    """

    def __init__(self, additional_stopwords: Set[str] = None):
        # Inisialisasi stopwords dari Sastrawi
        factory = StopWordRemoverFactory()
        self.base_stopwords = set(factory.get_stop_words())

        # Stopwords khusus domain kuisioner / technostress (kata umum yang tidak memuat info keluhan)
        self.domain_stopwords = {
            "aplikasi", "sistem", "menggunakan", "pakai", "merasa", "saya", "kami",
            "kita", "mereka", "anda", "kamu", "dengan", "dan", "yang", "di", "ke",
            "dari", "untuk", "pada", "oleh", "ini", "itu", "ada", "adanya", "bisa",
            "sudah", "kalau", "karena", "jadi", "juga", "harus", "saat", "ketika",
            "dalam", "buat", "saja", "lagi", "mau", "akan", "tapi", "tetapi",
            "namun", "agak", "sangat", "banget", "terus", "selalu", "sering",
            "kadang", "terkadang", "seperti", "kayak", "gitu", "begini", "begitu",
            "hal", "halnya", "banyak", "kurang", "sedikit", "kali", "malah"
        }

        self.custom_stopwords = set(additional_stopwords) if additional_stopwords else set()
        self.all_stopwords = self.base_stopwords.union(self.domain_stopwords).union(self.custom_stopwords)

        # Kamus normalisasi singkatan / slang
        self.slang_dict = {
            "eror": "error",
            "erorr": "error",
            "lemot": "lambat",
            "lelet": "lambat",
            "lola": "lambat",
            "down": "gangguan",
            "crash": "rusak",
            "bug": "gangguan",
            "ga": "tidak",
            "gak": "tidak",
            "nggak": "tidak",
            "ngga": "tidak",
            "tdk": "tidak",
            "gabisa": "tidak bisa",
            "gakbisa": "tidak bisa",
            "bgt": "sangat",
            "bgtt": "sangat",
            "bngt": "sangat",
            "bener": "benar",
            "bgtu": "begitu",
            "udh": "sudah",
            "udah": "sudah",
            "sdh": "sudah",
            "blm": "belum",
            "blom": "belum",
            "dgn": "dengan",
            "utk": "untuk",
            "yg": "yang",
            "tp": "tapi",
            "klo": "kalau",
            "klu": "kalau",
            "krn": "karena",
            "bcs": "karena",
            "cape": "lelah",
            "capek": "lelah",
            "puyeng": "pusing",
            "mumet": "pusing",
            "notif": "notifikasi",
            "wa": "whatsapp",
            "zoom": "telekonferensi",
            "teams": "telekonferensi",
            "meet": "telekonferensi",
            "apk": "aplikasi",
            "apps": "aplikasi",
            "app": "aplikasi",
            "bikin": "membuat",
            "bbrp": "beberapa",
            "jg": "juga",
            "aja": "saja",
            "doang": "saja",
            "gimana": "bagaimana",
            "knp": "kenapa"
        }

        # Kamus Dimensi Technostress (Tarafdar et al., 2007)
        self.dimension_keywords = {
            "Techno-Overload": [
                "lembur", "tugas", "numpuk", "banjir", "beban", "banyak", "padat",
                "multitasking", "terus menerus", "waktu", "dikejar", "deadline", "kelelahan"
            ],
            "Techno-Invasion": [
                "malam", "libur", "istirahat", "keluarga", "pribadi", "dihubungi",
                "chat", "notifikasi", "kapan saja", "di luar jam", "gangguan waktu"
            ],
            "Techno-Complexity": [
                "rumit", "sulit", "bingung", "error", "lambat", "panduan", "training",
                "pelatihan", "pusing", "tidak paham", "susah", "ribet", "masalah teknis"
            ],
            "Techno-Insecurity": [
                "takut", "cemas", "ketinggalan", "tergantikan", "posisi", "gaptek",
                "kompetensi", "kalah saing", "khawatir", "tertekan"
            ],
            "Techno-Uncertainty": [
                "berubah", "ganti", "update", "pembaruan", "tidak pasti", "adaptasi",
                "baru lagi", "beralih", "aturan baru", "fitur baru"
            ]
        }

    def clean_text(self, text: str) -> str:
        """Membersihkan URL, karakter spesial, angka, dan spasi ganda."""
        if not text or not isinstance(text, str):
            return ""
        
        text = text.lower()
        # Hapus URL
        text = re.sub(r"http\S+|www\S+|https\S+", "", text, flags=re.MULTILINE)
        # Hapus mention & hashtag
        text = re.sub(r"@\w+|#\w+", "", text)
        # Hapus karakter non-alfabet (angka, tanda baca, simbol)
        text = re.sub(r"[^a-zA-Z\s]", " ", text)
        # Hapus spasi berlebih
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def normalize_slang(self, text: str) -> str:
        """Mengganti kata slang/singkatan dengan bentuk standarnya."""
        words = text.split()
        normalized_words = [self.slang_dict.get(w, w) for w in words]
        return " ".join(normalized_words)

    def remove_stopwords(self, words: List[str]) -> List[str]:
        """Menghapus stopwords umum dan domain."""
        return [w for w in words if w not in self.all_stopwords and len(w) > 2]

    def tokenize(self, text: str) -> List[str]:
        """Pipeline lengkap preprocessing menjadi list kata bersih."""
        cleaned = self.clean_text(text)
        normalized = self.normalize_slang(cleaned)
        words = normalized.split()
        filtered = self.remove_stopwords(words)
        return filtered

    def extract_bigrams(self, tokens: List[str]) -> List[str]:
        """Mengekstrak pasangan dua kata (Bigram) dari token."""
        if len(tokens) < 2:
            return []
        return [f"{tokens[i]} {tokens[i+1]}" for i in range(len(tokens) - 1)]

    def extract_ngrams(self, tokens: List[str], mode: str = "both") -> List[str]:
        """
        Mengekstrak n-gram berdasarkan mode:
        - 'unigram': kata tunggal saja
        - 'bigram': frasa 2 kata saja
        - 'both': gabungan unigram dan bigram
        """
        unigrams = tokens
        bigrams = self.extract_bigrams(tokens)
        
        if mode == "unigram":
            return unigrams
        elif mode == "bigram":
            return bigrams
        else: # both
            return unigrams + bigrams

    def tag_dimensions(self, text: str) -> List[str]:
        """Mendeteksi dimensi technostress yang muncul dalam teks."""
        cleaned = self.clean_text(text)
        detected = []
        for dim, keywords in self.dimension_keywords.items():
            for kw in keywords:
                if kw in cleaned:
                    detected.append(dim)
                    break
        return detected if detected else ["General/Unspecified"]

