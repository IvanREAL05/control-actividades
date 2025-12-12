from config.db import fetch_one, fetch_all, execute_query
from utils.fecha import obtener_fecha_hora_cdmx_completa
from utils.excel_utils import convertir_hora_excel
import logging
from datetime import datetime, time
from bcrypt import hashpw, gensalt

logger = logging.getLogger(__name__)


# --------------------------
# Estudiantes
# --------------------------
async def insertar_estudiantes(estudiantes):
    """
    Inserta estudiantes en la base de datos
    Columnas requeridas: matricula, nombre, apellido, grupo, email, no_lista
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
                logger.warning(f"Fila {i+1}: Datos incompletos - matricula: {matricula}")
                errores.append(f"Fila {i+1}: Datos incompletos - matricula: {matricula}")
                continue

            # Obtener id_grupo
            grupo_res = await fetch_one("SELECT id_grupo FROM grupo WHERE nombre = %s", [grupo])
            if not grupo_res:
                logger.warning(f"Fila {i+1}: Grupo no encontrado: {grupo}")
                errores.append(f"Fila {i+1}: Grupo '{grupo}' no encontrado. Importe grupos primero.")
                continue
            id_grupo = grupo_res["id_grupo"]

            # Convertir no_lista a entero
            numero_lista = None
            if no_lista is not None:
                try:
                    numero_lista = int(no_lista)
                except (ValueError, TypeError):
                    logger.warning(f"Fila {i+1}: Número de lista inválido: {no_lista}")
                    errores.append(f"Fila {i+1}: Número de lista debe ser un número entero")
                    continue
            
            # Asignar número automático si no existe
            if numero_lista is None:
                numero_lista = i + 1
                logger.info(f"Asignando número de lista automático {numero_lista} para {matricula}")

            # Verificar si el estudiante ya existe
            estudiante_existente = await fetch_one(
                "SELECT id_estudiante FROM estudiante WHERE matricula = %s", 
                [matricula]
            )

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
                logger.info(f"✅ Estudiante actualizado: {matricula} - {nombre} {apellido}")
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
                logger.info(f"✅ Estudiante insertado: {matricula} - {nombre} {apellido}")

        except Exception as e:
            error_msg = f"Error en fila {i+1}: {str(e)}"
            logger.error(error_msg)
            errores.append(error_msg)

    # Log del resumen
    logger.info(f"📊 Resumen Estudiantes: {estudiantes_insertados} insertados, {estudiantes_actualizados} actualizados")
    if errores:
        logger.warning(f"⚠️ {len(errores)} errores encontrados")

    return {
        "estudiantes_insertados": estudiantes_insertados,
        "estudiantes_actualizados": estudiantes_actualizados,
        "errores": errores
    }


# --------------------------
# Profesores (con creación de usuario)
# --------------------------
async def insertar_profesores(profesores):
    """
    Inserta profesores y crea sus usuarios en la base de datos
    Columnas requeridas: nombre, correo, usuario_login, contrasena
    """
    profesores_insertados = 0
    profesores_actualizados = 0
    errores = []
    
    for i, prof in enumerate(profesores):
        try:
            nombre = str(prof.get("nombre", "")).strip()
            correo = str(prof.get("correo", "")).strip()
            usuario_login = str(prof.get("usuario_login", "")).strip()
            contrasena = str(prof.get("contrasena", "")).strip()
            
            # Validar datos obligatorios
            if not all([nombre, correo, usuario_login, contrasena]):
                logger.warning(f"Fila {i+1}: Datos incompletos")
                errores.append(f"Fila {i+1}: Faltan datos obligatorios (nombre, correo, usuario_login o contrasena)")
                continue
            
            # Verificar si el usuario ya existe por correo o usuario_login
            usuario_existente = await fetch_one(
                "SELECT id_usuario FROM usuario WHERE correo = %s OR usuario_login = %s", 
                [correo, usuario_login]
            )
            
            if usuario_existente:
                id_usuario = usuario_existente["id_usuario"]
                
                # Verificar si el profesor ya existe
                prof_existente = await fetch_one(
                    "SELECT id_profesor FROM profesor WHERE id_usuario = %s", 
                    [id_usuario]
                )
                
                if prof_existente:
                    # Actualizar nombre del profesor
                    await execute_query(
                        "UPDATE profesor SET nombre = %s WHERE id_usuario = %s",
                        [nombre, id_usuario]
                    )
                    profesores_actualizados += 1
                    logger.info(f"✅ Profesor actualizado: {nombre}")
                else:
                    # Crear profesor con usuario existente
                    await execute_query(
                        "INSERT INTO profesor (nombre, id_usuario) VALUES (%s, %s)",
                        [nombre, id_usuario]
                    )
                    profesores_insertados += 1
                    logger.info(f"✅ Profesor insertado con usuario existente: {nombre}")
            else:
                # Hashear la contraseña
                try:
                    contrasena_hash = hashpw(contrasena.encode('utf-8'), gensalt()).decode('utf-8')
                except Exception as e:
                    logger.error(f"Error hasheando contraseña en fila {i+1}: {e}")
                    # Si falla el hasheo, usar la contraseña tal cual (NO RECOMENDADO EN PRODUCCIÓN)
                    contrasena_hash = contrasena
                
                # Crear nuevo usuario
                id_usuario = await execute_query(
                    """
                    INSERT INTO usuario (nombre_completo, correo, usuario_login, contrasena, rol)
                    VALUES (%s, %s, %s, %s, 'docente')
                    """,
                    [nombre, correo, usuario_login, contrasena_hash]
                )
                
                # Crear profesor con el nuevo usuario
                await execute_query(
                    "INSERT INTO profesor (nombre, id_usuario) VALUES (%s, %s)",
                    [nombre, id_usuario]
                )
                profesores_insertados += 1
                logger.info(f"✅ Profesor y usuario creados: {nombre} (usuario: {usuario_login})")
                
        except Exception as e:
            error_msg = f"Error en fila {i+1}: {str(e)}"
            logger.error(error_msg)
            errores.append(error_msg)
    
    logger.info(f"📊 Resumen Profesores: {profesores_insertados} insertados, {profesores_actualizados} actualizados")
    if errores:
        logger.warning(f"⚠️ {len(errores)} errores encontrados")
    
    return {
        "profesores_insertados": profesores_insertados,
        "profesores_actualizados": profesores_actualizados,
        "errores": errores
    }


# --------------------------
# Grupos
# --------------------------
async def insertar_grupos(grupos):
    """
    Inserta grupos en la base de datos
    Columnas requeridas: nombre, turno, nivel
    """
    grupos_insertados = 0
    grupos_actualizados = 0
    errores = []
    
    for i, grupo in enumerate(grupos):
        try:
            nombre = str(grupo.get("nombre", "")).strip()
            turno = str(grupo.get("turno", "")).strip().lower()
            nivel = grupo.get("nivel")
            
            # Validar datos obligatorios
            if not nombre or not turno:
                logger.warning(f"Fila {i+1}: Datos incompletos")
                errores.append(f"Fila {i+1}: Faltan datos obligatorios (nombre o turno)")
                continue
            
            # Validar turno
            if turno not in ['matutino', 'vespertino']:
                logger.warning(f"Fila {i+1}: Turno inválido '{turno}'")
                errores.append(f"Fila {i+1}: Turno debe ser 'matutino' o 'vespertino' (minúsculas)")
                continue
            
            # Convertir nivel a string si existe
            if nivel is not None:
                nivel = str(nivel).strip()
            
            # Verificar si ya existe
            grupo_existente = await fetch_one(
                "SELECT id_grupo FROM grupo WHERE nombre = %s", 
                [nombre]
            )
            
            if grupo_existente:
                # Actualizar
                await execute_query(
                    """
                    UPDATE grupo 
                    SET turno = %s, nivel = %s
                    WHERE nombre = %s
                    """,
                    [turno, nivel, nombre]
                )
                grupos_actualizados += 1
                logger.info(f"✅ Grupo actualizado: {nombre} ({turno}, nivel {nivel})")
            else:
                # Insertar
                await execute_query(
                    """
                    INSERT INTO grupo (nombre, turno, nivel)
                    VALUES (%s, %s, %s)
                    """,
                    [nombre, turno, nivel]
                )
                grupos_insertados += 1
                logger.info(f"✅ Grupo insertado: {nombre} ({turno}, nivel {nivel})")
                
        except Exception as e:
            error_msg = f"Error en fila {i+1}: {str(e)}"
            logger.error(error_msg)
            errores.append(error_msg)
    
    logger.info(f"📊 Resumen Grupos: {grupos_insertados} insertados, {grupos_actualizados} actualizados")
    if errores:
        logger.warning(f"⚠️ {len(errores)} errores encontrados")
    
    return {
        "grupos_insertados": grupos_insertados,
        "grupos_actualizados": grupos_actualizados,
        "errores": errores
    }


# --------------------------
# Materias
# --------------------------
async def insertar_materias(materias):
    """
    Inserta materias en la base de datos
    Columnas requeridas: nombre, clave, descripcion, num_curso
    """
    materias_insertadas = 0
    materias_actualizadas = 0
    errores = []
    
    for i, mat in enumerate(materias):
        try:
            nombre = str(mat.get("nombre", "")).strip()
            clave = mat.get("clave")
            descripcion = mat.get("descripcion")
            num_curso = mat.get("num_curso")
            
            # Validar nombre obligatorio
            if not nombre:
                logger.warning(f"Fila {i+1}: Nombre de materia vacío")
                errores.append(f"Fila {i+1}: El nombre de la materia es obligatorio")
                continue
            
            # Procesar clave (generar si no existe)
            if not clave or str(clave).strip() == '':
                palabras = nombre.split()
                clave = ''.join([p[0] for p in palabras[:5]]).upper()[:10]
                logger.info(f"Clave generada automáticamente: {clave} para {nombre}")
            else:
                clave = str(clave).strip()[:10]
            
            # Procesar descripcion (opcional)
            if descripcion and str(descripcion).strip() != '':
                descripcion = str(descripcion).strip()
            else:
                descripcion = None
            
            # Procesar num_curso (opcional pero único)
            if num_curso and str(num_curso).strip() != '':
                num_curso = str(num_curso).strip()[:10]
            else:
                num_curso = None
            
            # Verificar si la materia ya existe por nombre
            materia_existente = await fetch_one(
                "SELECT id_materia FROM materia WHERE nombre = %s", 
                [nombre]
            )
            
            if materia_existente:
                # Actualizar materia existente
                await execute_query(
                    """
                    UPDATE materia 
                    SET clave = %s, descripcion = %s, num_curso = %s
                    WHERE nombre = %s
                    """,
                    [clave, descripcion, num_curso, nombre]
                )
                materias_actualizadas += 1
                logger.info(f"✅ Materia actualizada: {nombre} ({clave})")
            else:
                # Insertar nueva materia
                await execute_query(
                    """
                    INSERT INTO materia (nombre, clave, descripcion, num_curso)
                    VALUES (%s, %s, %s, %s)
                    """,
                    [nombre, clave, descripcion, num_curso]
                )
                materias_insertadas += 1
                logger.info(f"✅ Materia insertada: {nombre} ({clave})")
                
        except Exception as e:
            error_msg = f"Error en fila {i+1}: {str(e)}"
            logger.error(error_msg)
            errores.append(error_msg)
    
    logger.info(f"📊 Resumen Materias: {materias_insertadas} insertadas, {materias_actualizadas} actualizadas")
    if errores:
        logger.warning(f"⚠️ {len(errores)} errores encontrados")
    
    return {
        "materias_insertadas": materias_insertadas,
        "materias_actualizadas": materias_actualizadas,
        "errores": errores
    }


# --------------------------
# Clases (incluye horarios)
# --------------------------
async def insertar_clases(clases):
    """
    Inserta clases y sus horarios en la base de datos.
    Columnas requeridas: nombre_clase, materia, profesor, grupo, dia, hora_inicio, hora_fin, nrc
    """
    clases_map = {}
    clases_insertadas = 0
    horarios_insertados = 0
    errores = []

    for i, clase in enumerate(clases):
        try:
            # Extraer y limpiar datos
            nombre_clase = str(clase.get("nombre_clase", "")).strip()
            materia = str(clase.get("materia", "")).strip()
            profesor = str(clase.get("profesor", "")).strip()
            grupo = str(clase.get("grupo", "")).strip()
            dia = str(clase.get("dia", "")).strip()
            hora_inicio_raw = clase.get("hora_inicio")
            hora_fin_raw = clase.get("hora_fin")
            nrc = str(clase.get("nrc", "")).strip()

            # Validación de datos básicos
            if not all([nombre_clase, materia, profesor, grupo]):
                logger.warning(f"Fila {i+1}: Faltan datos básicos de la clase")
                errores.append(f"Fila {i+1}: Faltan datos básicos (nombre_clase, materia, profesor o grupo)")
                continue
                
            if not all([dia, hora_inicio_raw, hora_fin_raw, nrc]):
                logger.warning(f"Fila {i+1}: Faltan datos de horario")
                errores.append(f"Fila {i+1}: Faltan datos de horario (dia, hora_inicio, hora_fin o nrc)")
                continue

            # Convertir horas
            hora_inicio = convertir_hora_excel(hora_inicio_raw)
            hora_fin = convertir_hora_excel(hora_fin_raw)

            if not isinstance(hora_inicio, time) or not isinstance(hora_fin, time):
                logger.warning(f"Fila {i+1}: Formato de hora inválido")
                errores.append(f"Fila {i+1}: Formato de hora inválido (use formato HH:MM, ej: 07:20)")
                continue

            # Normalizar día (capitalizar primera letra)
            dia = dia.capitalize()
            dias_validos = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado']
            if dia not in dias_validos:
                logger.warning(f"Fila {i+1}: Día inválido '{dia}'")
                errores.append(f"Fila {i+1}: Día debe ser uno de: {', '.join(dias_validos)}")
                continue

            # Obtener IDs de las tablas relacionadas
            prof_res = await fetch_one("SELECT id_profesor FROM profesor WHERE nombre = %s", [profesor])
            if not prof_res:
                logger.warning(f"Fila {i+1}: Profesor no encontrado: '{profesor}'")
                errores.append(f"Fila {i+1}: Profesor '{profesor}' no encontrado. Importe profesores primero.")
                continue
            id_profesor = prof_res["id_profesor"]

            grupo_res = await fetch_one("SELECT id_grupo FROM grupo WHERE nombre = %s", [grupo])
            if not grupo_res:
                logger.warning(f"Fila {i+1}: Grupo no encontrado: '{grupo}'")
                errores.append(f"Fila {i+1}: Grupo '{grupo}' no encontrado. Importe grupos primero.")
                continue
            id_grupo = grupo_res["id_grupo"]

            materia_res = await fetch_one("SELECT id_materia FROM materia WHERE nombre = %s", [materia])
            if not materia_res:
                logger.warning(f"Fila {i+1}: Materia no encontrada: '{materia}'")
                errores.append(f"Fila {i+1}: Materia '{materia}' no encontrada. Importe materias primero.")
                continue
            id_materia = materia_res["id_materia"]

            # Crear clave única para evitar duplicados en el mismo archivo
            clave = f"{nrc}"
            id_clase = clases_map.get(clave)

            if not id_clase:
                # Verificar si existe en BD por NRC (que es único)
                clase_existente = await fetch_one(
                    "SELECT id_clase FROM clase WHERE nrc = %s",
                    [nrc]
                )
                
                if clase_existente:
                    id_clase = clase_existente["id_clase"]
                    logger.info(f"⚠️ Clase existente encontrada: {nombre_clase} (NRC: {nrc})")
                else:
                    # Insertar nueva clase
                    id_clase = await execute_query(
                        """
                        INSERT INTO clase (nombre_clase, id_profesor, id_materia, id_grupo, nrc, aula)
                        VALUES (%s, %s, %s, %s, %s, NULL)
                        """,
                        [nombre_clase, id_profesor, id_materia, id_grupo, nrc]
                    )
                    clases_insertadas += 1
                    logger.info(f"✅ Clase insertada: {nombre_clase} (NRC: {nrc}, ID: {id_clase})")
                        
                clases_map[clave] = id_clase

            # Verificar si el horario ya existe
            horario_existente = await fetch_one(
                """
                SELECT id_horario FROM horario_clase 
                WHERE id_clase=%s AND dia=%s AND hora_inicio=%s AND hora_fin=%s
                """,
                [id_clase, dia, hora_inicio, hora_fin]
            )
            
            if horario_existente:
                logger.info(f"⚠️ Horario ya existe: {nombre_clase} - {dia} {hora_inicio}-{hora_fin}")
                continue

            # Insertar horario
            await execute_query(
                """
                INSERT INTO horario_clase (id_clase, dia, hora_inicio, hora_fin)
                VALUES (%s, %s, %s, %s)
                """,
                [id_clase, dia, hora_inicio, hora_fin]
            )
            horarios_insertados += 1
            logger.info(f"✅ Horario insertado: {nombre_clase} - {dia} {hora_inicio}-{hora_fin}")

        except Exception as e:
            error_msg = f"Error en fila {i+1}: {str(e)}"
            logger.error(error_msg)
            errores.append(error_msg)

    logger.info(f"📊 Resumen Clases: {clases_insertadas} clases insertadas, {horarios_insertados} horarios insertados")
    if errores:
        logger.warning(f"⚠️ {len(errores)} errores encontrados")

    return {
        "clases_insertadas": clases_insertadas,
        "horarios_insertados": horarios_insertados,
        "errores": errores
    }



'''async def insertar_calificaciones(calificaciones_data):
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
    }'''

# --------------------------
# Calificaciones
# --------------------------
async def insertar_calificaciones(calificaciones_data):
    """
    Inserta o actualiza calificaciones de parciales desde Excel.
    Columnas requeridas: matricula, nrc
    Columnas opcionales: parcial_1, parcial_2, ordinario (al menos una debe estar presente)
    """
    calificaciones_insertadas = 0
    calificaciones_actualizadas = 0
    errores = []
    
    logger.info(f"📊 Iniciando procesamiento de {len(calificaciones_data)} filas de calificaciones")
    
    for i, registro in enumerate(calificaciones_data, start=1):
        try:
            # Extraer y limpiar datos
            matricula = str(registro.get("matricula", "")).strip()
            nrc = str(registro.get("nrc", "")).strip()
            
            # Validar datos obligatorios
            if not matricula or not nrc:
                logger.warning(f"Fila {i}: Datos obligatorios incompletos")
                errores.append(f"Fila {i}: Faltan matrícula o NRC")
                continue
            
            # Extraer calificaciones
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
                logger.warning(f"Fila {i}: No hay calificaciones para {matricula}")
                errores.append(f"Fila {i}: Sin calificaciones para {matricula}")
                continue
            
            # Buscar estudiante por matrícula
            estudiante = await fetch_one(
                "SELECT id_estudiante, id_grupo FROM estudiante WHERE matricula = %s",
                [matricula]
            )
            if not estudiante:
                logger.warning(f"Fila {i}: Estudiante no encontrado: {matricula}")
                errores.append(f"Fila {i}: Estudiante '{matricula}' no encontrado. Importe estudiantes primero.")
                continue
            
            id_estudiante = estudiante["id_estudiante"]
            id_grupo_estudiante = estudiante["id_grupo"]
            
            # Buscar clase por NRC
            clase = await fetch_one(
                "SELECT id_clase, id_grupo FROM clase WHERE nrc = %s",
                [nrc]
            )
            if not clase:
                logger.warning(f"Fila {i}: Clase no encontrada: NRC {nrc}")
                errores.append(f"Fila {i}: Clase con NRC '{nrc}' no encontrada. Importe clases primero.")
                continue
            
            id_clase = clase["id_clase"]
            id_grupo_clase = clase["id_grupo"]
            
            # Verificar que el estudiante pertenece al grupo de la clase
            if id_grupo_estudiante != id_grupo_clase:
                logger.warning(f"Fila {i}: Estudiante {matricula} no está en el grupo de NRC {nrc}")
                errores.append(f"Fila {i}: Estudiante {matricula} no pertenece al grupo correcto")
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
                        logger.info(f"✅ Actualizada {tipo_parcial} para {matricula}: {calificacion}")
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
                        logger.info(f"✅ Insertada {tipo_parcial} para {matricula}: {calificacion}")
                        
                except Exception as e:
                    error_msg = f"Error procesando {tipo_parcial}: {str(e)}"
                    logger.error(error_msg)
                    errores.append(f"Fila {i}: {error_msg}")
            
        except Exception as e:
            error_msg = f"Error en fila {i}: {str(e)}"
            logger.error(error_msg)
            errores.append(error_msg)
    
    logger.info(f"📊 Resumen Calificaciones: {calificaciones_insertadas} insertadas, {calificaciones_actualizadas} actualizadas")
    if errores:
        logger.warning(f"⚠️ {len(errores)} errores encontrados")
    
    return {
        "calificaciones_insertadas": calificaciones_insertadas,
        "calificaciones_actualizadas": calificaciones_actualizadas,
        "errores": errores
    }