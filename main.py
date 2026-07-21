from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import io
import zipfile
import tempfile
from pathlib import Path
from nombraPv import renombrar_pdfs

app = FastAPI(title="Renombrador de PDFs")

# 🔥 Configuración CORS específica para tu frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://kanaybd.web.app"],
    allow_credentials=False,
    allow_methods=["POST", "OPTIONS"],  # Solo POST y OPTIONS
    allow_headers=["*"],
    expose_headers=["X-Renombrados", "X-Omitidos"],  # Para leer los headers personalizados
)

@app.post("/renombrar")
def renombrar_archivos(files: list[UploadFile] = File(...)):
    # Validar que sean PDFs
    for file in files:
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail=f"{file.filename} no es un PDF")

    # Crear carpeta temporal
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_dir = Path(tmpdir)
        # Guardar archivos subidos usando file.file.read() para modo síncrono
        for file in files:
            file_path = temp_dir / file.filename
            with open(file_path, "wb") as f:
                content = file.file.read()
                f.write(content)

        # Ejecutar renombrado
        resultado = renombrar_pdfs(str(temp_dir))
        
        # Preparar ZIP con los PDFs renombrados
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            for pdf in temp_dir.glob("*.pdf"):
                zip_file.write(pdf, pdf.name)
        
        zip_buffer.seek(0)
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": "attachment; filename=renombrados.zip",
                "X-Renombrados": str(resultado.get("renombrados", 0)),
                "X-Omitidos": str(resultado.get("omitidos", 0))
            }
        )