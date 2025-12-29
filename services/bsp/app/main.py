from fastapi import FastAPI, UploadFile, File, HTTPException
from app.bsp_service import process_record_files
import os

app = FastAPI(title="BSP Service")

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "bsp-service"}

@app.post("/analyze")
async def analyze_bsp_signals(
    header_file: UploadFile = File(...),
    dat_file: UploadFile = File(...),
):
    try:
        header_content = await header_file.read()
        dat_content = await dat_file.read()
        
        result = process_record_files(header_content, dat_content)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
