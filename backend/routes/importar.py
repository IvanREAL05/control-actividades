from fastapi import APIRouter, UploadFile, File, HTTPException
from utils.excel_utils import leer_excel, convertir_hora_excel
from controllers import importar_controller as ctrl
from datetime import datetime, time

router = APIRouter()


@router.post("/{tipo}/archivo")
async def importar_archivo(tipo: str, file: UploadFile = File(...)):
    try:
        # ✅ Validar extensión de archivo antes de leer
        if not file.filename.endswith((".xlsx", ".xls")):
            raise HTTPException(status_code=400, detail="Archivo debe ser Excel")

        contents = await file.read()
        await file.close()
        datos = leer_excel(contents)

        if not datos:
            raise HTTPException(status_code=400, detail="Archivo vacío")

        if tipo == "estudiantes":
            await ctrl.insertar_estudiantes(datos)
        elif tipo == "profesores":
            await ctrl.insertar_profesores(datos)
        elif tipo == "grupos":
            await ctrl.insertar_grupos(datos)
        elif tipo == "clases":
            await ctrl.insertar_clases(datos)
        elif tipo == "materias":
            await ctrl.insertar_materias(datos)
        else:
            raise HTTPException(status_code=400, detail="Tipo no válido")

        return {"message": f"{tipo.capitalize()} importados correctamente."}
    except Exception as e:
        print(f"❌ Error importando {tipo}: {e}")
        raise HTTPException(status_code=500, detail=f"Error al importar {tipo}")