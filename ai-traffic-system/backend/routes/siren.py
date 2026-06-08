"""
/api/siren — siren sound detection endpoint
Accepts audio upload (WAV/MP3), returns classification result.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from services.siren_service import SirenDetectionService

router = APIRouter()
_siren_svc = SirenDetectionService()


@router.post("/siren/detect")
async def detect_siren(file: UploadFile = File(...)):
    """
    POST /api/siren/detect
    Upload an audio clip (WAV/MP3) to classify if it contains a siren.
    Returns: {"siren_detected": bool, "confidence": float}
    """
    allowed = {"audio/wav", "audio/wave", "audio/mpeg", "audio/mp3", "audio/x-wav"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported audio format: {file.content_type}")

    audio_bytes = await file.read()
    if len(audio_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty audio file")

    result = _siren_svc.predict(audio_bytes)
    return JSONResponse(content=result)


@router.get("/siren/status")
async def siren_status():
    """Check if siren detection model is loaded."""
    return {
        "model_loaded": _siren_svc.model_loaded,
        "threshold": 0.70,
        "description": "CNN trained on mel-spectrograms to classify ambulance siren audio",
    }
