from fastapi import APIRouter, UploadFile, File, HTTPException
from utils.excel_utils import leer_excel, convertir_hora_excel
from controllers import importar_controller as ctrl
from datetime import datetime, time
from pydantic import BaseModel
from typing import List, Optional
from config.db import fetch_one, fetch_all, execute_query
import logging

router = APIRouter()
logger = logging.getLogger("api_importar")

# ==================== MODELOS ====================
class EstudianteBase(BaseModel):
    matricula: str
    nombre: str
    apellido: str
    correo: Optional[str] = None
    id_grupo: int
    estado_actual: Optional[str] = "activo"
    no_lista: int

class EstudianteEditar(BaseModel):
    matricula: Optional[str] = None
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    correo: Optional[str] = None
    id_grupo: Optional[int] = None
    estado_actual: Optional[str] = None

class EstudianteResponse(BaseModel):
    id_estudiante: int
    matricula: str
    nombre: str
    apellido: str
    correo: Optional[str]
    estado_actual: str
    activo: int  
    id_grupo: int
    nombre_grupo: str
    no_lista: int


# ==================== ENDPOINT PRINCIPAL ====================
@router.post("/{tipo}/archivo")
async def importar_archivo(tipo: str, file: UploadFile = File(...)):
    """
    Endpoint para importar datos desde archivos Excel.
    
    Tipos soportados:
    - estudiantes: matricula, nombre, apellido, grupo, email, no_lista
    - profesores: nombre, correo, usuario_login, contrasena
    - grupos: nombre, turno, nivel
    - materias: nombre, clave, descripcion, num_curso
    - clases: nombre_clase, materia, profesor, grupo, dia, hora_inicio, hora_fin, nrc
    """
    try:
        # Validar tipo
        tipos_validos = ["estudiantes", "profesores", "grupos", "clases", "materias", "calificaciones"]
        if tipo not in tipos_validos:
            raise HTTPException(
                status_code=400, 
                detail=f"Tipo no válido. Tipos permitidos: {', '.join(tipos_validos)}"
            )

        # Validar extensión de archivo
        if not file.filename.endswith((".xlsx", ".xls")):
            raise HTTPException(
                status_code=400, 
                detail="El archivo debe ser formato Excel (.xlsx o .xls)"
            )

        # Leer contenido del archivo
        logger.info(f"📥 Procesando archivo: {file.filename} para tipo: {tipo}")
        contents = await file.read()
        await file.close()
        
        # Convertir Excel a datos
        datos = leer_excel(contents)

        if not datos or len(datos) == 0:
            raise HTTPException(
                status_code=400, 
                detail="El archivo está vacío o no contiene datos válidos"
            )

        logger.info(f"📊 {len(datos)} filas encontradas en el archivo")
        # ✅ VALIDACIÓN ESPECIAL PARA CALIFICACIONES
        if tipo == "calificaciones":
            columnas_requeridas = ["matricula", "nrc"]
            columnas_calificaciones = ["parcial_1", "parcial_2", "ordinario"]
            
            primera_fila = datos[0] if datos else {}
            columnas_presentes = list(primera_fila.keys())
            
            # Verificar columnas obligatorias
            faltantes = [col for col in columnas_requeridas if col not in columnas_presentes]
            if faltantes:
                raise HTTPException(
                    status_code=400,
                    detail=f"Faltan columnas obligatorias: {', '.join(faltantes)}"
                )
            
            # Verificar que al menos una columna de calificación esté presente
            tiene_calificaciones = any(col in columnas_presentes for col in columnas_calificaciones)
            if not tiene_calificaciones:
                raise HTTPException(
                    status_code=400,
                    detail=f"Debe incluir al menos una columna de calificaciones: {', '.join(columnas_calificaciones)}"
                )

        # Procesar según el tipo
        resultado = {}
        
        if tipo == "estudiantes":
            resultado = await ctrl.insertar_estudiantes(datos)
            
        elif tipo == "profesores":
            resultado = await ctrl.insertar_profesores(datos)
            
        elif tipo == "grupos":
            resultado = await ctrl.insertar_grupos(datos)
            
        elif tipo == "materias":
            resultado = await ctrl.insertar_materias(datos)
            
        elif tipo == "clases":
            resultado = await ctrl.insertar_clases(datos)
        
        elif tipo == "calificaciones":  
            resultado = await ctrl.insertar_calificaciones(datos)

        # Construir respuesta
        response = {
            "message": f"✅ {tipo.capitalize()} procesados correctamente",
            "tipo": tipo,
            "total_filas": len(datos),
            **resultado
        }

        # Log del resultado
        if tipo == "estudiantes":
            logger.info(
                f"✅ Estudiantes: {resultado.get('estudiantes_insertados', 0)} insertados, "
                f"{resultado.get('estudiantes_actualizados', 0)} actualizados"
            )
        elif tipo == "profesores":
            logger.info(
                f"✅ Profesores: {resultado.get('profesores_insertados', 0)} insertados, "
                f"{resultado.get('profesores_actualizados', 0)} actualizados"
            )
        elif tipo == "grupos":
            logger.info(
                f"✅ Grupos: {resultado.get('grupos_insertados', 0)} insertados, "
                f"{resultado.get('grupos_actualizados', 0)} actualizados"
            )
        elif tipo == "materias":
            logger.info(
                f"✅ Materias: {resultado.get('materias_insertadas', 0)} insertadas, "
                f"{resultado.get('materias_actualizadas', 0)} actualizadas"
            )
        elif tipo == "clases":
            logger.info(
                f"✅ Clases: {resultado.get('clases_insertadas', 0)} insertadas, "
                f"{resultado.get('horarios_insertados', 0)} horarios creados"
            )
        elif tipo == "calificaciones":  # ✅ AGREGADO
            logger.info(
                f"✅ Calificaciones: {resultado.get('calificaciones_insertadas', 0)} insertadas, "
                f"{resultado.get('calificaciones_actualizadas', 0)} actualizadas"
            )

        # Si hay errores, incluirlos en la respuesta
        if resultado.get('errores') and len(resultado['errores']) > 0:
            response['total_errores'] = len(resultado['errores'])
            logger.warning(f"⚠️ Se encontraron {len(resultado['errores'])} errores")

        return response

    except HTTPException:
        raise
        
    except Exception as e:
        logger.error(f"❌ Error importando {tipo}: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error al procesar el archivo: {str(e)}"
        )


# ==================== ENDPOINTS ADICIONALES ====================

@router.get("/tipos")
async def obtener_tipos_disponibles():
    """
    Devuelve los tipos de importación disponibles y sus columnas requeridas
    """
    return {
        "tipos_disponibles": {
            "estudiantes": {
                "columnas": ["matricula", "nombre", "apellido", "grupo", "email", "no_lista"],
                "descripcion": "Importar estudiantes con información básica y asignación a grupo"
            },
            "profesores": {
                "columnas": ["nombre", "correo", "usuario_login", "contrasena"],
                "descripcion": "Importar profesores y crear sus usuarios de acceso"
            },
            "grupos": {
                "columnas": ["nombre", "turno", "nivel"],
                "descripcion": "Importar grupos con turno (matutino/vespertino) y nivel"
            },
            "materias": {
                "columnas": ["nombre", "clave", "descripcion", "num_curso"],
                "descripcion": "Importar materias con información completa"
            },
            "clases": {
                "columnas": ["nombre_clase", "materia", "profesor", "grupo", "dia", "hora_inicio", "hora_fin", "nrc"],
                "descripcion": "Importar clases y sus horarios (requiere que profesores, materias y grupos ya existan)"
            },
            "calificaciones": { 
                "columnas": ["matricula", "nrc", "parcial_1", "parcial_2", "ordinario"],
                "descripcion": "Importar calificaciones de parciales (al menos una calificación debe estar presente)"
            }
        },
        "orden_recomendado": [
            "1. Profesores",
            "2. Materias", 
            "3. Grupos",
            "4. Estudiantes",
            "5. Clases",
            "6. Calificaciones" 
        ]
    }


@router.get("/validar/{tipo}")
async def validar_dependencias(tipo: str):
    """
    Valida si existen las dependencias necesarias antes de importar
    """
    try:
        resultado = {
            "tipo": tipo,
            "puede_importar": True,
            "advertencias": []
        }

        if tipo == "estudiantes":
            # Verificar que existan grupos
            grupos = await fetch_all("SELECT COUNT(*) as total FROM grupo")
            if grupos[0]['total'] == 0:
                resultado['puede_importar'] = False
                resultado['advertencias'].append("⚠️ No hay grupos registrados. Importe grupos primero.")

        elif tipo == "clases":
            # Verificar profesores
            profesores = await fetch_all("SELECT COUNT(*) as total FROM profesor")
            if profesores[0]['total'] == 0:
                resultado['advertencias'].append("⚠️ No hay profesores registrados.")
                resultado['puede_importar'] = False
            
            # Verificar materias
            materias = await fetch_all("SELECT COUNT(*) as total FROM materia")
            if materias[0]['total'] == 0:
                resultado['advertencias'].append("⚠️ No hay materias registradas.")
                resultado['puede_importar'] = False
            
            # Verificar grupos
            grupos = await fetch_all("SELECT COUNT(*) as total FROM grupo")
            if grupos[0]['total'] == 0:
                resultado['advertencias'].append("⚠️ No hay grupos registrados.")
                resultado['puede_importar'] = False

        elif tipo == "calificaciones":  # ✅ AGREGADO
            # Verificar estudiantes
            estudiantes = await fetch_all("SELECT COUNT(*) as total FROM estudiante")
            if estudiantes[0]['total'] == 0:
                resultado['advertencias'].append("⚠️ No hay estudiantes registrados.")
                resultado['puede_importar'] = False
            
            # Verificar clases
            clases = await fetch_all("SELECT COUNT(*) as total FROM clase")
            if clases[0]['total'] == 0:
                resultado['advertencias'].append("⚠️ No hay clases registradas.")
                resultado['puede_importar'] = False

        return resultado

    except Exception as e:
        logger.error(f"Error validando dependencias: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/estadisticas")
async def obtener_estadisticas():
    """
    Devuelve estadísticas de los datos importados
    """
    try:
        stats = {}
        
        # Estudiantes
        estudiantes = await fetch_all("SELECT COUNT(*) as total FROM estudiante")
        stats['estudiantes'] = estudiantes[0]['total']
        
        # Profesores
        profesores = await fetch_all("SELECT COUNT(*) as total FROM profesor")
        stats['profesores'] = profesores[0]['total']
        
        # Grupos
        grupos = await fetch_all("SELECT COUNT(*) as total FROM grupo")
        stats['grupos'] = grupos[0]['total']
        
        # Materias
        materias = await fetch_all("SELECT COUNT(*) as total FROM materia")
        stats['materias'] = materias[0]['total']
        
        # Clases
        clases = await fetch_all("SELECT COUNT(*) as total FROM clase")
        stats['clases'] = clases[0]['total']
        
        # Horarios
        horarios = await fetch_all("SELECT COUNT(*) as total FROM horario_clase")
        stats['horarios'] = horarios[0]['total']

        # Calificaciones - ✅ AGREGADO
        calificaciones = await fetch_all("SELECT COUNT(*) as total FROM calificacion_parcial")
        stats['calificaciones'] = calificaciones[0]['total']
        
        return {
            "estadisticas": stats,
            "ultima_actualizacion": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
# ==================== ENDPOINTS ====================

@router.get("/estudiante/buscar/matricula/{matricula}", response_model=EstudianteResponse)
async def buscar_por_matricula(matricula: str):
    """Busca estudiante por matrícula"""
    query = """
    SELECT e.*, g.nombre as nombre_grupo
    FROM estudiante e
    JOIN grupo g ON e.id_grupo = g.id_grupo
    WHERE e.matricula = %s
    """
    resultado = await fetch_one(query, (matricula,))
    if not resultado:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    
        # 🟢 Agregar campo 'activo' según el valor de 'estado_actual'
    resultado["activo"] = 1 if resultado["estado_actual"] == "activo" else 0
    return resultado


@router.get("/estudiante/buscar/nombre", response_model=List[EstudianteResponse])
async def buscar_por_nombre(nombre: str, apellido: Optional[str] = None):
    """Busca estudiantes por nombre y/o apellido"""
    if apellido:
        query = """
        SELECT e.*, g.nombre as nombre_grupo
        FROM estudiante e
        JOIN grupo g ON e.id_grupo = g.id_grupo
        WHERE e.nombre LIKE %s AND e.apellido LIKE %s
        """
        resultados = await fetch_all(query, (f"%{nombre}%", f"%{apellido}%"))
    else:
        query = """
        SELECT e.*, g.nombre as nombre_grupo
        FROM estudiante e
        JOIN grupo g ON e.id_grupo = g.id_grupo
        WHERE e.nombre LIKE %s OR e.apellido LIKE %s
        """
        resultados = await fetch_all(query, (f"%{nombre}%", f"%{nombre}%"))

    if not resultados:
        raise HTTPException(status_code=404, detail="No se encontraron estudiantes")
    return resultados


@router.get("/estudiante/buscar/grupo/{id_grupo}", response_model=List[EstudianteResponse])
async def buscar_por_grupo(id_grupo: int):
    """Lista todos los estudiantes de un grupo"""
    query = """
    SELECT e.*, g.nombre as nombre_grupo
    FROM estudiante e
    JOIN grupo g ON e.id_grupo = g.id_grupo
    WHERE e.id_grupo = %s
    ORDER BY e.no_lista
    """
    resultados = await fetch_all(query, (id_grupo,))
    if not resultados:
        raise HTTPException(status_code=404, detail="No hay estudiantes en este grupo")
    return resultados


@router.put("/estudiante/editar/{id_estudiante}")
async def editar_estudiante(id_estudiante: int, datos: EstudianteEditar):
    """Edita información de un estudiante"""
    # Verificar que existe
    estudiante = await fetch_one("SELECT id_estudiante FROM estudiante WHERE id_estudiante = %s", (id_estudiante,))
    if not estudiante:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")

    campos = []
    valores = []

    if datos.matricula:
        # Verificar duplicado
        existe = await fetch_one(
            "SELECT id_estudiante FROM estudiante WHERE matricula = %s AND id_estudiante != %s",
            (datos.matricula, id_estudiante)
        )
        if existe:
            raise HTTPException(status_code=400, detail="La matrícula ya existe")
        campos.append("matricula = %s")
        valores.append(datos.matricula)

    if datos.nombre:
        campos.append("nombre = %s")
        valores.append(datos.nombre)

    if datos.apellido:
        campos.append("apellido = %s")
        valores.append(datos.apellido)

    if datos.correo:
        campos.append("correo = %s")
        valores.append(datos.correo)

    if datos.id_grupo:
        grupo = await fetch_one("SELECT id_grupo FROM grupo WHERE id_grupo = %s", (datos.id_grupo,))
        if not grupo:
            raise HTTPException(status_code=400, detail="El grupo no existe")
        campos.append("id_grupo = %s")
        valores.append(datos.id_grupo)

    if datos.estado_actual:
        if datos.estado_actual not in ['activo', 'inactivo', 'egresado']:
            raise HTTPException(status_code=400, detail="Estado inválido")
        campos.append("estado_actual = %s")
        valores.append(datos.estado_actual)

    if not campos:
        raise HTTPException(status_code=400, detail="No se proporcionaron campos para actualizar")

    valores.append(id_estudiante)
    query = f"UPDATE estudiante SET {', '.join(campos)} WHERE id_estudiante = %s"
    await execute_query(query, valores)
    return {"message": "Estudiante actualizado correctamente", "id_estudiante": id_estudiante}


@router.delete("/estudiante/eliminar/{id_estudiante}")
async def eliminar_estudiante(id_estudiante: int):
    """Elimina un estudiante y sus registros relacionados"""
    estudiante = await fetch_one("SELECT matricula, nombre, apellido FROM estudiante WHERE id_estudiante = %s", (id_estudiante,))
    if not estudiante:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")

    # Eliminar asistencias primero
    await execute_query("DELETE FROM asistencia WHERE id_estudiante = %s", (id_estudiante,))

    # Eliminar estudiante
    await execute_query("DELETE FROM estudiante WHERE id_estudiante = %s", (id_estudiante,))
    
    return {
        "message": "Estudiante eliminado correctamente",
        "estudiante": estudiante
    }


@router.post("/calificaciones/archivo")
async def importar_calificaciones(file: UploadFile = File(...)):
    """
    Importa calificaciones de parciales desde un archivo Excel.
    
    Estructura esperada del Excel:
    | matricula | nrc | parcial_1 | parcial_2 | ordinario |
    |-----------|-----|-----------|-----------|-----------|
    | 2021001   | 123 | 8.5       | 9.0       |           |
    | 2021002   | 123 | 7.0       | 8.5       |           |
    
    - matricula: Matrícula del estudiante (obligatorio)
    - nrc: NRC de la clase (obligatorio)
    - parcial_1: Calificación del primer parcial (0-10, opcional)
    - parcial_2: Calificación del segundo parcial (0-10, opcional)
    - ordinario: Calificación del examen ordinario (0-10, opcional)
    
    Nota: Al menos una calificación debe estar presente.
    """
    try:
        # ✅ Validar extensión de archivo
        if not file.filename.endswith((".xlsx", ".xls")):
            raise HTTPException(
                status_code=400, 
                detail="El archivo debe ser formato Excel (.xlsx o .xls)"
            )

        # Leer archivo
        contents = await file.read()
        await file.close()
        datos = leer_excel(contents)

        if not datos:
            raise HTTPException(
                status_code=400, 
                detail="El archivo está vacío o no tiene datos válidos"
            )

        # Validar que tenga las columnas mínimas requeridas
        columnas_requeridas = ["matricula", "nrc"]
        columnas_calificaciones = ["parcial_1", "parcial_2", "ordinario"]
        
        primera_fila = datos[0] if datos else {}
        columnas_presentes = list(primera_fila.keys())
        
        # Verificar columnas obligatorias
        faltantes = [col for col in columnas_requeridas if col not in columnas_presentes]
        if faltantes:
            raise HTTPException(
                status_code=400,
                detail=f"Faltan columnas obligatorias en el Excel: {', '.join(faltantes)}"
            )
        
        # Verificar que al menos una columna de calificación esté presente
        tiene_calificaciones = any(col in columnas_presentes for col in columnas_calificaciones)
        if not tiene_calificaciones:
            raise HTTPException(
                status_code=400,
                detail=f"El Excel debe contener al menos una columna de calificaciones: {', '.join(columnas_calificaciones)}"
            )

        # Procesar calificaciones
        resultado = await ctrl.insertar_calificaciones(datos)
        
        return {
            "message": "Calificaciones procesadas correctamente",
            "calificaciones_insertadas": resultado["calificaciones_insertadas"],
            "calificaciones_actualizadas": resultado["calificaciones_actualizadas"],
            "total_procesadas": resultado["calificaciones_insertadas"] + resultado["calificaciones_actualizadas"],
            "errores": resultado["errores"],
            "total_errores": len(resultado["errores"])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error importando calificaciones: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error al importar calificaciones: {str(e)}"
        )
