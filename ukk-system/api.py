from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from analyzer import (
    baca_tabel,
    bersihkan_dan_kategorikan,
    data_contoh,
    hitung_analitik_json,
    proses_otomatis,
)

app = FastAPI(
    title="UKK Competency Analytics API",
    description="Backend API untuk pemetaan hasil Ujian Kompetensi Keahlian (UKK) SMK: ringkasan tren, rubrik kategori, distribusi nilai, dan analisis paket soal.",
    version="1.0.0",
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
    data: List[Dict[str, Any]] = Field(..., description="Array objek data siswa (memuat kolom nilai/rentang, tahun/tanggal, opsional nama & paket)")
    tahun_manual: Optional[int] = Field(default=None, ge=1990, le=2100, description="Tahun fallback jika tidak ada kolom tahun di payload")
    tahun_filter: Optional[List[int]] = Field(default=None, description="Opsional daftar tahun yang ingin difilter")
    source_name: str = Field(default="json_payload", description="Label sumber data")


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "ukk-analytics-api"}


@app.get("/api/sample")
def get_sample_analysis():
    df_sample = bersihkan_dan_kategorikan(data_contoh())
    return {
        "success": True,
        "source": "sample",
        **hitung_analitik_json(df_sample),
    }


@app.post("/api/analyze")
def analyze_json(req: AnalyzeRequest):
    if not req.data:
        raise HTTPException(status_code=400, detail="Payload 'data' tidak boleh kosong.")

    raw = pd.DataFrame(req.data)
    raw.columns = [str(c).strip() for c in raw.columns]
    processed = proses_otomatis(raw, filename=req.source_name, tahun_manual=req.tahun_manual)
    clean_df = bersihkan_dan_kategorikan(processed, tahun_filter=req.tahun_filter)

    if clean_df.empty:
        raise HTTPException(
            status_code=400,
            detail="Tidak ada nilai valid (0-100) dengan tahun yang valid dari data yang dikirim.",
        )

    return {
        "success": True,
        "source": req.source_name,
        **hitung_analitik_json(clean_df),
    }


@app.post("/api/analyze/upload")
async def analyze_upload(
    files: List[UploadFile] = File(...),
    header_row: int = Form(-1),
    tahun_manual: Optional[int] = Form(None),
    tahun_filter: Optional[str] = Form(None),
):
    if not files:
        raise HTTPException(status_code=400, detail="Minimal satu file CSV atau Excel harus diunggah.")

    frames = []
    for f in files:
        filename = f.filename or "uploaded_file.csv"
        if not filename.lower().endswith((".csv", ".xlsx", ".xls")):
            raise HTTPException(status_code=400, detail=f"Format file tidak didukung: {filename}. Gunakan CSV atau Excel.")

        content = await f.read()
        try:
            raw = baca_tabel(content, filename=filename, header_row=header_row)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Gagal membaca file '{filename}': {exc}") from exc

        frames.append(proses_otomatis(raw, filename=filename, tahun_manual=tahun_manual))

    combined = pd.concat(frames, ignore_index=True)

    parsed_filter: Optional[List[int]] = None
    if tahun_filter:
        try:
            parsed_filter = [int(t.strip()) for t in tahun_filter.split(",") if t.strip()]
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Format 'tahun_filter' harus angka dipisah koma, mis. '2022,2024'.") from exc

    clean_df = bersihkan_dan_kategorikan(combined, tahun_filter=parsed_filter)
    if clean_df.empty:
        raise HTTPException(
            status_code=400,
            detail="Tidak ada nilai valid (0-100) atau tahun valid yang ditemukan pada file yang diunggah.",
        )

    return {
        "success": True,
        "files_processed": [f.filename for f in files],
        **hitung_analitik_json(clean_df),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api:app", host="0.0.0.0", port=8001, reload=True)
