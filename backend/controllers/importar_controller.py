from config.db import fetch_one, fetch_all, execute_query
from utils.fecha import obtener_fecha_hora_cdmx_completa
from utils.excel_utils import convertir_hora_excel
import logging
from datetime import datetime, time

logger = logging.getLogger(__name__)


# --------------------------
# Estudiantes
# --------------------------
async def insertar_estudiantes(estudiantes):
    """
    Inserta estudiantes en la base de datos
    """
    estudiantes_insertados = 0
    estudiantes_actualizados = 0
    errores = []
    
    for i, est in enumerate(estudiantes):
        try:
            matricula = str(est.get("matricula", "")).strip()
            nombre = str(est.get("nombre", "")).strip()
            apellido = str(est.get("apellido", "")).strip()
            grupo = str(est.get("grupo", "")).strip()
            email = est.get("email")
            no_lista = est.get("no_lista")

            # Limpiar email si existe
            if email:
                email = str(email).strip()
                if email == '':
                    email = None

            # Validar datos obligatorios
            if not matricula or not nombre or not apellido or not grupo:
                logger.warning(f"Fila {i+1}: Datos incompletos, se omite - matricula: {matricula}, nombre: {nombre}, apellido: {apellido}, grupo: {grupo}")
                errores.append(f"Fila {i+1}: Datos incompletos - matricula: {matricula}")
                continue

            # Obtener id_grupo
            grupo_res = await fetch_one("SELECT id_grupo FROM grupo WHERE nombre = %s", [grupo])
            if not grupo_res:
                logger.warning(f"Fila {i+1}: Grupo no encontrado: {grupo}, se omite estudiante {matricula}")
                errores.append(f"Grupo no encontrado: {grupo} para estudiante {matricula}")
                continue
            id_grupo = grupo_res["id_grupo"]

            # Convertir no_lista a entero - OBLIGATORIO
            numero_lista = None
            if no_lista is not None:
                try:
                    numero_lista = int(no_lista)
                except (ValueError, TypeError):
                    logger.warning(f"Fila {i+1}: Número de lista inválido para {matricula}: {no_lista}")
                    errores.append(f"Número de lista inválido para {matricula}: {no_lista}")
                    continue
            
            # Si no_lista es None, asignar un valor por defecto o saltarse
            if numero_lista is None:
                # Opción 1: Asignar un número automático basado en el orden
                numero_lista = i + 1
                logger.info(f"Asignando número de lista automático {numero_lista} para {matricula}")
                
                # Opción 2: O puedes saltarte este estudiante si no_lista es obligatorio
                # logger.warning(f"Fila {i+1}: Número de lista requerido para {matricula}")
                # errores.append(f"Número de lista requerido para estudiante {matricula}")
                # continue

            # Verificar si el estudiante ya existe
            estudiante_existente = await fetch_one(
                "SELECT matricula FROM estudiante WHERE matricula = %s", 
                [matricula]
            )

            try:
                if estudiante_existente:
                    # Actualizar estudiante existente
                    await execute_query(
                        """
                        UPDATE estudiante 
                        SET nombre = %s, apellido = %s, correo = %s, id_grupo = %s, no_lista = %s
                        WHERE matricula = %s
                        """,
                        [nombre, apellido, email, id_grupo, numero_lista, matricula]
                    )
                    estudiantes_actualizados += 1
                    logger.info(f"Estudiante actualizado: {matricula} - {nombre} {apellido}")
                else:
                    # Insertar nuevo estudiante
                    await execute_query(
                        """
                        INSERT INTO estudiante 
                        (matricula, nombre, apellido, correo, id_grupo, no_lista, estado_actual)
                        VALUES (%s, %s, %s, %s, %s, %s, 'activo')
                        """,
                        [matricula, nombre, apellido, email, id_grupo, numero_lista]
                    )
                    estudiantes_insertados += 1
                    logger.info(f"Estudiante insertado: {matricula} - {nombre} {apellido}")
                    
            except Exception as e:
                error_msg = f"Error procesando estudiante {matricula}: {str(e)}"
                logger.error(error_msg)
                errores.append(error_msg)

        except Exception as e:
            error_msg = f"Error en fila {i+1}: {str(e)}"
            logger.error(error_msg)
            errores.append(error_msg)

    # Log del resumen
    logger.info(f"Proceso completado: {estudiantes_insertados} estudiantes insertados, {estudiantes_actualizados} actualizados")
    if errores:
        logger.warning(f"Se encontraron {len(errores)} errores durante el proceso")
        for error in errores[:5]:  # Mostrar solo los primeros 5 errores
            logger.warning(f"  - {error}")

    return {
        "estudiantes_insertados": estudiantes_insertados,
        "estudiantes_actualizados": estudiantes_actualizados,
        "errores": errores
    }



async def insertar_estudiante_nuevo(estudiante):
    matricula = estudiante.get("matricula", "").strip()
    nombre = estudiante.get("nombre", "").strip()
    apellido = estudiante.get("apellido", "").strip()
    grupo = estudiante.get("grupo", "").strip()
    email = estudiante.get("email", None)
    
    if not matricula or not nombre or not apellido or not grupo:
        raise ValueError("Datos incompletos")
    
    grupo_res = await fetch_one("SELECT id_grupo FROM grupo WHERE nombre = %s", [grupo])
    if not grupo_res:
        raise ValueError(f"Grupo no encontrado: {grupo}")
    id_grupo = grupo_res["id_grupo"]

    # Insertar o actualizar estudiante
    await execute_query(
        """
        INSERT INTO estudiante 
        (matricula, nombre, apellido, correo, id_grupo, estado_actual, foto)
        VALUES (%s, %s, %s, %s, %s, 'activo', NULL)
        ON DUPLICATE KEY UPDATE
            nombre = VALUES(nombre),
            apellido = VALUES(apellido),
            correo = VALUES(correo),
            id_grupo = VALUES(id_grupo)
        """,
        [matricula, nombre, apellido, email, id_grupo]
    )

    # Reordenar no_lista automáticamente
    await execute_query(
        """
        SET @num := 0;
        UPDATE estudiante
        SET no_lista = (@num := @num + 1)
        WHERE id_grupo = %s
        ORDER BY apellido ASC, nombre ASC;
        """,
        [id_grupo]
    )

# --------------------------
# Profesores
# --------------------------
async def insertar_profesores(profesores):
    for prof in profesores:
        nombre = prof.get("nombre")
        especialidad = prof.get("especialidad")
        try:
            await execute_query(
                """
                INSERT INTO profesor (nombre, especialidad, id_usuario)
                VALUES (%s, %s, 6)
                ON DUPLICATE KEY UPDATE
                    especialidad = VALUES(especialidad)
                """,
                [nombre, especialidad]
            )
        except Exception as e:
            logger.error(f"Error insertando profesor {nombre}: {e}")

# --------------------------
# Grupos
# --------------------------
async def insertar_grupos(grupos):
    for grupo in grupos:
        nombre = grupo.get("nombre")
        turno = grupo.get("turno")
        nivel = grupo.get("nivel")
        try:
            await execute_query(
                """
                INSERT INTO grupo (nombre, turno, nivel)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    turno = VALUES(turno),
                    nivel = VALUES(nivel)
                """,
                [nombre, turno, nivel]
            )
        except Exception as e:
            logger.error(f"Error insertando grupo {nombre}: {e}")

# --------------------------
# Clases
# --------------------------
async def insertar_clases(clases):
    """
    Inserta clases y sus horarios en la base de datos.
    """
    clases_map = {}
    clases_insertadas = 0
    horarios_insertados = 0
    errores = []

    for i, clase in enumerate(clases):
        try:
            # Extraer y limpiar datos
            nombre_clase = clase.get("nombre_clase")
            materia = clase.get("materia") 
            profesor = clase.get("profesor")
            grupo = clase.get("grupo")
            dia = clase.get("dia")
            hora_inicio_raw = clase.get("hora_inicio")
            hora_fin_raw = clase.get("hora_fin")
            nrc = clase.get("nrc")

            # Limpiar espacios en blanco y caracteres especiales
            if dia:
                dia = dia.strip()
            if profesor:
                profesor = profesor.strip()
            if grupo:
                grupo = grupo.strip()
            if nombre_clase:
                nombre_clase = nombre_clase.strip()
            if materia:
                materia = materia.strip()

            # Convertir horas
            hora_inicio = None
            hora_fin = None
            
            if hora_inicio_raw:
                hora_inicio = convertir_hora_excel(hora_inicio_raw)
            if hora_fin_raw:
                hora_fin = convertir_hora_excel(hora_fin_raw)

            # Validación más específica
            if not nombre_clase or not materia or not profesor or not grupo:
                logger.warning(f"Fila {i+1}: Faltan datos básicos de la clase - {clase}")
                continue
                
            if not dia or not hora_inicio or not hora_fin or not nrc:
                logger.warning(f"Fila {i+1}: Faltan datos de horario - {clase}")
                continue

            # Validar que las horas sean válidas
            if not isinstance(hora_inicio, time) or not isinstance(hora_fin, time):
                logger.warning(f"Fila {i+1}: Horas inválidas - inicio: {hora_inicio} (tipo: {type(hora_inicio)}), fin: {hora_fin} (tipo: {type(hora_fin)})")
                continue

            # Obtener IDs con manejo de errores mejorado
            prof_res = await fetch_one("SELECT id_profesor FROM profesor WHERE nombre = %s", [profesor])
            if not prof_res:
                logger.warning(f"Fila {i+1}: Profesor no encontrado: {profesor}")
                errores.append(f"Profesor no encontrado: {profesor}")
                continue
            id_profesor = prof_res["id_profesor"]

            grupo_res = await fetch_one("SELECT id_grupo FROM grupo WHERE nombre = %s", [grupo])
            if not grupo_res:
                logger.warning(f"Fila {i+1}: Grupo no encontrado: {grupo}")
                errores.append(f"Grupo no encontrado: {grupo}")
                continue
            id_grupo = grupo_res["id_grupo"]

            materia_res = await fetch_one("SELECT id_materia FROM materia WHERE nombre = %s", [materia])
            if not materia_res:
                logger.warning(f"Fila {i+1}: Materia no encontrada: {materia}")
                errores.append(f"Materia no encontrada: {materia}")
                continue
            id_materia = materia_res["id_materia"]

            # Evitar duplicados en el mismo archivo
            clave = f"{nombre_clase}|{id_profesor}|{id_grupo}|{id_materia}|{nrc}"
            id_clase = clases_map.get(clave)

            if not id_clase:
                # Revisar si ya existe en DB
                clase_existente = await fetch_one(
                    """
                    SELECT id_clase FROM clase
                    WHERE nombre_clase=%s AND id_profesor=%s AND id_materia=%s AND id_grupo=%s AND nrc=%s
                    """,
                    [nombre_clase, id_profesor, id_materia, id_grupo, nrc]
                )
                
                if clase_existente:
                    id_clase = clase_existente["id_clase"]
                    logger.info(f"Clase existente encontrada: {nombre_clase} - ID: {id_clase}")
                else:
                    # Insertar nueva clase
                    try:
                        result = await execute_query(
                            """
                            INSERT INTO clase (nombre_clase, id_profesor, id_materia, id_grupo, nrc, aula)
                            VALUES (%s, %s, %s, %s, %s, NULL)
                            """,
                            [nombre_clase, id_profesor, id_materia, id_grupo, nrc]
                        )
                        id_clase = result  # Asumiendo que execute_query devuelve lastrowid
                        clases_insertadas += 1
                        logger.info(f"Nueva clase insertada: {nombre_clase} - ID: {id_clase}")
                    except Exception as e:
                        logger.error(f"Error insertando clase {nombre_clase}: {e}")
                        errores.append(f"Error insertando clase {nombre_clase}: {str(e)}")
                        continue
                        
                clases_map[clave] = id_clase

            # Verificar que tenemos un ID de clase válido
            if not id_clase:
                logger.error(f"Fila {i+1}: No se pudo obtener id_clase para {nombre_clase}")
                continue

            # Verificar si el horario ya existe para evitar duplicados
            horario_existente = await fetch_one(
                """
                SELECT id_horario FROM horario_clase 
                WHERE id_clase=%s AND dia=%s AND hora_inicio=%s AND hora_fin=%s
                """,
                [id_clase, dia, hora_inicio, hora_fin]
            )
            
            if horario_existente:
                logger.info(f"Horario ya existe para clase {nombre_clase} el {dia}")
                continue

            # Insertar horario_clase
            try:
                horario_result = await execute_query(
                    """
                    INSERT INTO horario_clase (id_clase, dia, hora_inicio, hora_fin)
                    VALUES (%s, %s, %s, %s)
                    """,
                    [id_clase, dia, hora_inicio, hora_fin]
                )
                horarios_insertados += 1
                logger.info(f"Horario insertado: Clase {nombre_clase}, {dia} {hora_inicio}-{hora_fin}")
                
            except Exception as e:
                logger.error(f"Error insertando horario para clase {nombre_clase} ({dia} {hora_inicio}-{hora_fin}): {e}")
                errores.append(f"Error insertando horario para {nombre_clase}: {str(e)}")

        except Exception as e:
            logger.error(f"Error procesando fila {i+1}: {e}")
            errores.append(f"Error en fila {i+1}: {str(e)}")

    # Log del resumen
    logger.info(f"Proceso completado: {clases_insertadas} clases insertadas, {horarios_insertados} horarios insertados")
    if errores:
        logger.warning(f"Se encontraron {len(errores)} errores durante el proceso")
        for error in errores[:5]:  # Mostrar solo los primeros 5 errores
            logger.warning(f"  - {error}")

    return {
        "clases_insertadas": clases_insertadas,
        "horarios_insertados": horarios_insertados,
        "errores": errores
    }
# --------------------------
# Materias
# --------------------------
async def insertar_materias(materias):
    for mat in materias:
        nombre = mat.get("nombre")
        descripcion = mat.get("descripcion")
        clave = mat.get("clave")
        num_curso = mat.get("num_curso")
        try:
            await execute_query(
                """
                INSERT INTO materia (nombre, descripcion, clave, num_curso)
                VALUES (%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                    descripcion = VALUES(descripcion),
                    clave = VALUES(clave),
                    num_curso = VALUES(num_curso)
                """,
                [nombre, descripcion or None, clave or None, num_curso or None]
            )
        except Exception as e:
            logger.error(f"Error insertando materia {nombre}: {e}")


async def insertar_calificaciones(calificaciones_data):
    """
    Inserta o actualiza calificaciones de parciales desde Excel.
    
    Estructura esperada:
    - matricula: Matrícula del estudiante
    - nrc: NRC de la clase
    - parcial_1: Calificación del primer parcial (opcional)
    - parcial_2: Calificación del segundo parcial (opcional)
    - ordinario: Calificación del examen ordinario (opcional)
    """
    calificaciones_insertadas = 0
    calificaciones_actualizadas = 0
    errores = []
    
    logger.info(f"Iniciando procesamiento de {len(calificaciones_data)} filas de calificaciones")
    
    for i, registro in enumerate(calificaciones_data, start=1):
        try:
            # Extraer y limpiar datos
            matricula = str(registro.get("matricula", "")).strip()
            nrc = str(registro.get("nrc", "")).strip()
            
            # Validar datos obligatorios
            if not matricula or not nrc:
                logger.warning(f"Fila {i}: Datos obligatorios incompletos - matricula: '{matricula}', nrc: '{nrc}'")
                errores.append(f"Fila {i}: Faltan matrícula o NRC")
                continue
            
            # Extraer calificaciones (pueden ser None, vacías o números)
            parcial_1_raw = registro.get("parcial_1")
            parcial_2_raw = registro.get("parcial_2")
            ordinario_raw = registro.get("ordinario")
            
            # Función helper para validar y convertir calificaciones
            def validar_calificacion(valor, nombre_campo):
                """Valida que la calificación esté entre 0 y 10, o sea None/vacía"""
                if valor is None or valor == "" or str(valor).strip() == "":
                    return None
                
                try:
                    calif = float(valor)
                    if calif < 0 or calif > 10:
                        raise ValueError(f"{nombre_campo} debe estar entre 0 y 10")
                    # Convertir a entero si es un número entero
                    return int(calif) if calif == int(calif) else calif
                except (ValueError, TypeError):
                    raise ValueError(f"{nombre_campo} inválida: '{valor}'")
            
            # Validar y convertir calificaciones
            try:
                parcial_1 = validar_calificacion(parcial_1_raw, "parcial_1")
                parcial_2 = validar_calificacion(parcial_2_raw, "parcial_2")
                ordinario = validar_calificacion(ordinario_raw, "ordinario")
            except ValueError as ve:
                logger.warning(f"Fila {i}: {str(ve)}")
                errores.append(f"Fila {i}: {str(ve)}")
                continue
            
            # Verificar que al menos una calificación esté presente
            if parcial_1 is None and parcial_2 is None and ordinario is None:
                logger.warning(f"Fila {i}: No se proporcionó ninguna calificación para matricula {matricula}, nrc {nrc}")
                errores.append(f"Fila {i}: Sin calificaciones para {matricula}")
                continue
            
            # Buscar estudiante por matrícula
            estudiante = await fetch_one(
                "SELECT id_estudiante, id_grupo FROM estudiante WHERE matricula = %s",
                [matricula]
            )
            if not estudiante:
                logger.warning(f"Fila {i}: Estudiante no encontrado con matrícula: {matricula}")
                errores.append(f"Fila {i}: Estudiante no encontrado - {matricula}")
                continue
            
            id_estudiante = estudiante["id_estudiante"]
            id_grupo_estudiante = estudiante["id_grupo"]
            
            # Buscar clase por NRC
            clase = await fetch_one(
                "SELECT id_clase, id_grupo FROM clase WHERE nrc = %s",
                [nrc]
            )
            if not clase:
                logger.warning(f"Fila {i}: Clase no encontrada con NRC: {nrc}")
                errores.append(f"Fila {i}: Clase no encontrada - NRC {nrc}")
                continue
            
            id_clase = clase["id_clase"]
            id_grupo_clase = clase["id_grupo"]
            
            # Verificar que el estudiante pertenece al grupo de la clase
            if id_grupo_estudiante != id_grupo_clase:
                logger.warning(f"Fila {i}: Estudiante {matricula} no pertenece al grupo de la clase NRC {nrc}")
                errores.append(f"Fila {i}: Estudiante {matricula} no está en el grupo correcto")
                continue
            
            # Obtener fecha actual
            fecha_actual = obtener_fecha_hora_cdmx_completa()
            
            # Procesar cada tipo de calificación
            tipos_calificacion = [
                ("parcial_1", parcial_1),
                ("parcial_2", parcial_2),
                ("ordinario", ordinario)
            ]
            
            for tipo_parcial, calificacion in tipos_calificacion:
                if calificacion is None:
                    continue
                
                try:
                    # Verificar si ya existe la calificación
                    calif_existente = await fetch_one(
                        """
                        SELECT id_calificacion_parcial 
                        FROM calificacion_parcial
                        WHERE id_estudiante = %s AND id_clase = %s AND parcial = %s
                        """,
                        [id_estudiante, id_clase, tipo_parcial]
                    )
                    
                    if calif_existente:
                        # Actualizar calificación existente
                        await execute_query(
                            """
                            UPDATE calificacion_parcial
                            SET calificacion = %s, fuente = 'excel', fecha_registro = %s
                            WHERE id_calificacion_parcial = %s
                            """,
                            [calificacion, fecha_actual, calif_existente["id_calificacion_parcial"]]
                        )
                        calificaciones_actualizadas += 1
                        logger.info(f"Fila {i}: Actualizada {tipo_parcial} para {matricula} - Calificación: {calificacion}")
                    else:
                        # Insertar nueva calificación
                        await execute_query(
                            """
                            INSERT INTO calificacion_parcial 
                            (id_estudiante, id_clase, parcial, calificacion, fecha_registro, fuente)
                            VALUES (%s, %s, %s, %s, %s, 'excel')
                            """,
                            [id_estudiante, id_clase, tipo_parcial, calificacion, fecha_actual]
                        )
                        calificaciones_insertadas += 1
                        logger.info(f"Fila {i}: Insertada {tipo_parcial} para {matricula} - Calificación: {calificacion}")
                        
                except Exception as e:
                    error_msg = f"Error procesando {tipo_parcial} para {matricula}: {str(e)}"
                    logger.error(error_msg)
                    errores.append(f"Fila {i}: {error_msg}")
            
        except Exception as e:
            error_msg = f"Error en fila {i}: {str(e)}"
            logger.error(error_msg)
            errores.append(error_msg)
    
    # Log del resumen
    logger.info(f"Proceso completado: {calificaciones_insertadas} calificaciones insertadas, "
                f"{calificaciones_actualizadas} actualizadas")
    if errores:
        logger.warning(f"Se encontraron {len(errores)} errores durante el proceso")
        for error in errores[:10]:  # Mostrar solo los primeros 10 errores
            logger.warning(f"  - {error}")
    
    return {
        "calificaciones_insertadas": calificaciones_insertadas,
        "calificaciones_actualizadas": calificaciones_actualizadas,
        "errores": errores
    }