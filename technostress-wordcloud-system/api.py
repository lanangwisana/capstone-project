import os
import json
import base64
from typing import Any, List, Optional, Dict
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.pipeline import TechnostressPipeline

app = FastAPI(
    title="Technostress Visual Analytics API",
    description="Backend API untuk memproses data survei Likert & Esai, klasifikasi tingkat stres, dan generasi Word Cloud HD.",
    version="1.0.0"
)

# Aktifkan CORS untuk Next.js (port 3000 dan lainnya)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeRequest(BaseModel):
    data: Any = Field(..., description="Array objek responden atau objek dengan key 'data'")
    ngram_mode: str = Field(default="both", description="'both' | 'bigram' | 'unigram'")
    cloud_theme: str = Field(default="white", description="'white' atau hex color")
    max_words: int = Field(default=60, ge=10, le=150)
    custom_stopwords: Optional[List[str]] = Field(default_factory=list)

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "technostress-analytics-api"}

@app.get("/api/sample")
def get_sample_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    sample_path = os.path.join(base_dir, "data", "sample_payload.json")
    if not os.path.exists(sample_path):
        raise HTTPException(status_code=404, detail="File sample_payload.json tidak ditemukan")
    with open(sample_path, "r", encoding="utf-8") as f:
        return json.load(f)

@app.post("/api/analyze")
def analyze_survey(req: AnalyzeRequest):
    stopwords_set = set(s.strip().lower() for s in (req.custom_stopwords or []) if s.strip())
    pipeline = TechnostressPipeline(additional_stopwords=stopwords_set)

    result = pipeline.process_json_payload(req.data, ngram_mode=req.ngram_mode)

    if not result.get("success", False):
        raise HTTPException(status_code=400, detail=result.get("error_message", "Gagal memproses data"))

    summary = result["summary"]
    processed_df = result["processed_df"]
    freqs = result["frequencies"]

    # Filter & format data siswa untuk chart
    display_cols = [c for c in ["id", "name", "post_date", "kalkulasi", "rounded_scale", "kategori", "essay_text"] if c in processed_df.columns]
    chart_df = processed_df[display_cols].copy()
    chart_records = chart_df.to_dict(orient="records")

    # Word clouds (Base64)
    wordcloud_images = {}
    if summary.get("can_render_wordcloud", False):
        for cat in ["Tinggi", "Rendah", "Sedang", "Semua"]:
            cat_freq = freqs.get(cat, {})
            if cat_freq:
                img_bytes = pipeline.wc_generator.generate_wordcloud_bytes(
                    frequencies=cat_freq,
                    category=cat,
                    max_words=req.max_words,
                    bg_color=req.cloud_theme
                )
                if img_bytes:
                    b64_str = base64.b64encode(img_bytes).decode("utf-8")
                    wordcloud_images[cat] = f"data:image/png;base64,{b64_str}"
                else:
                    wordcloud_images[cat] = None
            else:
                wordcloud_images[cat] = None

    # Top n-grams (Frasa)
    top_high = []
    top_low = []
    if freqs.get("Tinggi"):
        top_high = pipeline.wc_generator.get_top_ngrams_df(freqs["Tinggi"], top_n=10).to_dict(orient="records")
    if freqs.get("Rendah"):
        top_low = pipeline.wc_generator.get_top_ngrams_df(freqs["Rendah"], top_n=10).to_dict(orient="records")

    return {
        "success": True,
        "summary": summary,
        "students": chart_records,
        "top_ngrams": {
            "high": top_high,
            "low": top_low
        },
        "wordclouds": wordcloud_images
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
