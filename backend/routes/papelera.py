"""
Borrado lógico (soft delete) de grupos y estudiantes.

Módulo temporal mientras se construye el CRUD definitivo. Nada se borra
físicamente: se marca eliminado = 1 junto con la fecha y el usuario que
hizo la operación, de modo que todo se puede restaurar desde la papelera.

Al eliminar un grupo se aplica cascada lógica: alumnos, clases y horarios
del grupo se marcan con la MISMA fecha_eliminado. Esa fecha es la que
permite restaurar exactamente lo que se borró en esa operación, sin
resucitar alumnos que ya habían sido eliminados individualmente antes.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import aiomysql
import logging

from config.db import fetch_one, fetch_all, get_pool
from utils.fecha import obtener_fecha_hora_cdmx_completa

logger = logging.getLogger(__name__)

router = APIRouter()


# ===============================
# 📌 MODELOS DE REQUEST
# ===============================
class EliminarRequest(BaseModel):
    usuario: Optional[str] = None


class EliminarEstudianteRequest(BaseModel):
    usuario: Optional[str] = None
    # Renumera el no_lista de los alumnos que quedan en el grupo para que
    # el mapa de asientos no muestre huecos. Se puede desactivar si ya se
    # repartieron listas impresas con la numeración actual.
    reordenar: bool = True


class EliminarEstudiantesRequest(EliminarEstudianteRequest):
    ids: List[int]


class RestaurarEstudiantesRequest(BaseModel):
    ids: List[int]


# ===============================
# 📌 HELPERS
# ===============================
async def _reordenar_grupo(cur, id_grupo: int):
    """Renumera no_lista (1..N) entre los alumnos vivos de un grupo."""
    await cur.execute(
        """
        WITH ordenados AS (
            SELECT id_estudiante,
                   ROW_NUMBER() OVER (ORDER BY apellido ASC, nombre ASC) AS nuevo_numero
            FROM estudiante
            WHERE id_grupo = %s AND eliminado = 0
        )
        UPDATE estudiante e
        JOIN ordenados o ON e.id_estudiante = o.id_estudiante
        SET e.no_lista = o.nuevo_numero
        """,
        (id_grupo,),
    )


# ===============================
# 📌 IMPACTO (previsualización)
# ===============================
@router.get("/grupo/{id_grupo}/impacto")
async def impacto_eliminar_grupo(id_grupo: int):
    """Cuenta qué se va a marcar como eliminado antes de confirmar el borrado."""
    grupo = await fetch_one(
        "SELECT id_grupo, nombre, turno, nivel FROM grupo WHERE id_grupo = %s AND eliminado = 0",
        (id_grupo,),
    )
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")

    conteos = await fetch_one(
        """
        SELECT
            (SELECT COUNT(*) FROM estudiante WHERE id_grupo = %s AND eliminado = 0) AS alumnos,
            (SELECT COUNT(*) FROM clase      WHERE id_grupo = %s AND eliminado = 0) AS clases,
            (SELECT COUNT(*)
               FROM horario_clase h
               JOIN clase c ON h.id_clase = c.id_clase
              WHERE c.id_grupo = %s AND h.eliminado = 0) AS horarios
        """,
        (id_grupo, id_grupo, id_grupo),
    )

    return {"success": True, "data": {"grupo": grupo, **(conteos or {})}}


# ===============================
# 📌 ELIMINAR
# ===============================
@router.post("/grupo/{id_grupo}/eliminar")
async def eliminar_grupo(id_grupo: int, data: Optional[EliminarRequest] = None):
    """Marca como eliminado un grupo junto con sus alumnos, clases y horarios."""
    grupo = await fetch_one(
        "SELECT id_grupo, nombre FROM grupo WHERE id_grupo = %s AND eliminado = 0",
        (id_grupo,),
    )
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo no encontrado o ya eliminado")

    ahora = obtener_fecha_hora_cdmx_completa()
    usuario = ((data.usuario if data else None) or "sistema")[:100]

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            try:
                await conn.begin()

                await cur.execute(
                    """
                    UPDATE horario_clase h
                    JOIN clase c ON h.id_clase = c.id_clase
                    SET h.eliminado = 1, h.fecha_eliminado = %s, h.eliminado_por = %s
                    WHERE c.id_grupo = %s AND h.eliminado = 0
                    """,
                    (ahora, usuario, id_grupo),
                )
                horarios = cur.rowcount

                await cur.execute(
                    """
                    UPDATE clase
                    SET eliminado = 1, fecha_eliminado = %s, eliminado_por = %s
                    WHERE id_grupo = %s AND eliminado = 0
                    """,
                    (ahora, usuario, id_grupo),
                )
                clases = cur.rowcount

                await cur.execute(
                    """
                    UPDATE estudiante
                    SET eliminado = 1, fecha_eliminado = %s, eliminado_por = %s
                    WHERE id_grupo = %s AND eliminado = 0
                    """,
                    (ahora, usuario, id_grupo),
                )
                alumnos = cur.rowcount

                await cur.execute(
                    """
                    UPDATE grupo
                    SET eliminado = 1, fecha_eliminado = %s, eliminado_por = %s
                    WHERE id_grupo = %s AND eliminado = 0
                    """,
                    (ahora, usuario, id_grupo),
                )

                await conn.commit()
            except Exception as e:
                await conn.rollback()
                logger.error(f"❌ Error al eliminar grupo {id_grupo}: {e}")
                raise HTTPException(status_code=500, detail="Error al eliminar el grupo")

    logger.info(
        f"🗑️ Grupo '{grupo['nombre']}' eliminado por {usuario}: "
        f"{alumnos} alumnos, {clases} clases, {horarios} horarios"
    )

    return {
        "success": True,
        "message": f"Grupo '{grupo['nombre']}' enviado a la papelera",
        "data": {
            "grupo": grupo["nombre"],
            "alumnos": alumnos,
            "clases": clases,
            "horarios": horarios,
            "fecha_eliminado": ahora,
        },
    }


@router.post("/estudiante/{id_estudiante}/eliminar")
async def eliminar_estudiante(id_estudiante: int, data: Optional[EliminarEstudianteRequest] = None):
    """Marca como eliminado un solo estudiante."""
    reordenar = data.reordenar if data else True
    usuario = ((data.usuario if data else None) or "sistema")[:100]
    return await _eliminar_estudiantes([id_estudiante], usuario, reordenar)


@router.post("/estudiantes/eliminar")
async def eliminar_estudiantes(data: EliminarEstudiantesRequest):
    """Marca como eliminados varios estudiantes de una sola vez."""
    if not data.ids:
        raise HTTPException(status_code=400, detail="No se recibió ningún estudiante")
    return await _eliminar_estudiantes(data.ids, (data.usuario or "sistema")[:100], data.reordenar)


async def _eliminar_estudiantes(ids: List[int], usuario: str, reordenar: bool):
    placeholders = ", ".join(["%s"] * len(ids))

    encontrados = await fetch_all(
        f"""
        SELECT id_estudiante, id_grupo, matricula, nombre, apellido
        FROM estudiante
        WHERE id_estudiante IN ({placeholders}) AND eliminado = 0
        """,
        tuple(ids),
    )
    if not encontrados:
        raise HTTPException(status_code=404, detail="No se encontraron estudiantes activos con esos IDs")

    ahora = obtener_fecha_hora_cdmx_completa()
    ids_validos = [e["id_estudiante"] for e in encontrados]
    grupos_afectados = {e["id_grupo"] for e in encontrados}
    marcadores = ", ".join(["%s"] * len(ids_validos))

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            try:
                await conn.begin()

                await cur.execute(
                    f"""
                    UPDATE estudiante
                    SET eliminado = 1, fecha_eliminado = %s, eliminado_por = %s
                    WHERE id_estudiante IN ({marcadores})
                    """,
                    (ahora, usuario, *ids_validos),
                )
                eliminados = cur.rowcount

                if reordenar:
                    for id_grupo in grupos_afectados:
                        await _reordenar_grupo(cur, id_grupo)

                await conn.commit()
            except Exception as e:
                await conn.rollback()
                logger.error(f"❌ Error al eliminar estudiantes {ids_validos}: {e}")
                raise HTTPException(status_code=500, detail="Error al eliminar los estudiantes")

    logger.info(f"🗑️ {eliminados} estudiante(s) eliminados por {usuario}")

    return {
        "success": True,
        "message": f"{eliminados} alumno(s) enviados a la papelera",
        "data": {
            "eliminados": eliminados,
            "reordenados": reordenar,
            "estudiantes": [f"{e['nombre']} {e['apellido']}" for e in encontrados],
        },
    }


# ===============================
# 📌 RESTAURAR
# ===============================
@router.post("/grupo/{id_grupo}/restaurar")
async def restaurar_grupo(id_grupo: int):
    """
    Restaura un grupo y todo lo que se eliminó en la misma operación.

    Se usa fecha_eliminado del grupo como marca: solo vuelven los alumnos,
    clases y horarios que se borraron en ese mismo momento, no los que ya
    estaban eliminados de antes.
    """
    grupo = await fetch_one(
        "SELECT id_grupo, nombre, fecha_eliminado FROM grupo WHERE id_grupo = %s AND eliminado = 1",
        (id_grupo,),
    )
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo no encontrado en la papelera")

    marca = grupo["fecha_eliminado"]

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            try:
                await conn.begin()

                await cur.execute(
                    """
                    UPDATE grupo
                    SET eliminado = 0, fecha_eliminado = NULL, eliminado_por = NULL
                    WHERE id_grupo = %s
                    """,
                    (id_grupo,),
                )

                await cur.execute(
                    """
                    UPDATE estudiante
                    SET eliminado = 0, fecha_eliminado = NULL, eliminado_por = NULL
                    WHERE id_grupo = %s AND eliminado = 1 AND fecha_eliminado = %s
                    """,
                    (id_grupo, marca),
                )
                alumnos = cur.rowcount

                await cur.execute(
                    """
                    UPDATE horario_clase h
                    JOIN clase c ON h.id_clase = c.id_clase
                    SET h.eliminado = 0, h.fecha_eliminado = NULL, h.eliminado_por = NULL
                    WHERE c.id_grupo = %s AND h.eliminado = 1 AND h.fecha_eliminado = %s
                    """,
                    (id_grupo, marca),
                )
                horarios = cur.rowcount

                await cur.execute(
                    """
                    UPDATE clase
                    SET eliminado = 0, fecha_eliminado = NULL, eliminado_por = NULL
                    WHERE id_grupo = %s AND eliminado = 1 AND fecha_eliminado = %s
                    """,
                    (id_grupo, marca),
                )
                clases = cur.rowcount

                await conn.commit()
            except Exception as e:
                await conn.rollback()
                logger.error(f"❌ Error al restaurar grupo {id_grupo}: {e}")
                raise HTTPException(status_code=500, detail="Error al restaurar el grupo")

    logger.info(f"♻️ Grupo '{grupo['nombre']}' restaurado: {alumnos} alumnos, {clases} clases")

    return {
        "success": True,
        "message": f"Grupo '{grupo['nombre']}' restaurado",
        "data": {"grupo": grupo["nombre"], "alumnos": alumnos, "clases": clases, "horarios": horarios},
    }


@router.post("/estudiantes/restaurar")
async def restaurar_estudiantes(data: RestaurarEstudiantesRequest):
    """
    Restaura estudiantes eliminados.

    No se puede restaurar un alumno cuyo grupo sigue en la papelera:
    quedaría invisible en el sistema. En ese caso hay que restaurar
    primero el grupo.
    """
    if not data.ids:
        raise HTTPException(status_code=400, detail="No se recibió ningún estudiante")

    placeholders = ", ".join(["%s"] * len(data.ids))
    candidatos = await fetch_all(
        f"""
        SELECT e.id_estudiante, e.nombre, e.apellido, e.id_grupo, g.eliminado AS grupo_eliminado, g.nombre AS grupo
        FROM estudiante e
        LEFT JOIN grupo g ON e.id_grupo = g.id_grupo
        WHERE e.id_estudiante IN ({placeholders}) AND e.eliminado = 1
        """,
        tuple(data.ids),
    )
    if not candidatos:
        raise HTTPException(status_code=404, detail="No se encontraron estudiantes en la papelera con esos IDs")

    bloqueados = [c for c in candidatos if c["grupo_eliminado"] == 1]
    restaurables = [c for c in candidatos if c["grupo_eliminado"] != 1]

    if not restaurables:
        grupos = sorted({c["grupo"] for c in bloqueados})
        raise HTTPException(
            status_code=409,
            detail=f"Primero restaura el grupo: {', '.join(grupos)}",
        )

    ids_validos = [c["id_estudiante"] for c in restaurables]
    grupos_afectados = {c["id_grupo"] for c in restaurables}
    marcadores = ", ".join(["%s"] * len(ids_validos))

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            try:
                await conn.begin()

                await cur.execute(
                    f"""
                    UPDATE estudiante
                    SET eliminado = 0, fecha_eliminado = NULL, eliminado_por = NULL
                    WHERE id_estudiante IN ({marcadores})
                    """,
                    tuple(ids_validos),
                )
                restaurados = cur.rowcount

                # El alumno vuelve a la lista: renumeramos para que no choque
                # su no_lista viejo con el de otro alumno.
                for id_grupo in grupos_afectados:
                    await _reordenar_grupo(cur, id_grupo)

                await conn.commit()
            except Exception as e:
                await conn.rollback()
                logger.error(f"❌ Error al restaurar estudiantes {ids_validos}: {e}")
                raise HTTPException(status_code=500, detail="Error al restaurar los estudiantes")

    logger.info(f"♻️ {restaurados} estudiante(s) restaurados")

    return {
        "success": True,
        "message": f"{restaurados} alumno(s) restaurados",
        "data": {
            "restaurados": restaurados,
            "omitidos": [f"{b['nombre']} {b['apellido']} (grupo '{b['grupo']}' en papelera)" for b in bloqueados],
        },
    }


# ===============================
# 📌 CONSULTAR LA PAPELERA
# ===============================
@router.get("/grupos")
async def listar_grupos_eliminados():
    """Grupos que están en la papelera, con el conteo de lo que arrastraron."""
    query = """
        SELECT
            g.id_grupo,
            g.nombre,
            g.turno,
            g.nivel,
            g.fecha_eliminado,
            g.eliminado_por,
            (SELECT COUNT(*) FROM estudiante e
              WHERE e.id_grupo = g.id_grupo AND e.eliminado = 1
                AND e.fecha_eliminado = g.fecha_eliminado) AS alumnos,
            (SELECT COUNT(*) FROM clase c
              WHERE c.id_grupo = g.id_grupo AND c.eliminado = 1
                AND c.fecha_eliminado = g.fecha_eliminado) AS clases
        FROM grupo g
        WHERE g.eliminado = 1
        ORDER BY g.fecha_eliminado DESC, g.nombre
    """
    try:
        return {"success": True, "data": await fetch_all(query)}
    except Exception as e:
        logger.error(f"Error al listar grupos eliminados: {e}")
        raise HTTPException(status_code=500, detail="Error al consultar la papelera")


@router.get("/estudiantes")
async def listar_estudiantes_eliminados(id_grupo: Optional[int] = None):
    """
    Alumnos que están en la papelera.

    Por omisión solo se listan los alumnos borrados individualmente (los que
    siguen en un grupo activo); los que cayeron por cascada se ven y se
    restauran desde su grupo. Pasando id_grupo se listan los de ese grupo.
    """
    if id_grupo is not None:
        query = """
            SELECT e.id_estudiante, e.matricula, e.nombre, e.apellido, e.correo,
                   e.no_lista, e.fecha_eliminado, e.eliminado_por,
                   g.nombre AS grupo, g.eliminado AS grupo_eliminado
            FROM estudiante e
            LEFT JOIN grupo g ON e.id_grupo = g.id_grupo
            WHERE e.eliminado = 1 AND e.id_grupo = %s
            ORDER BY e.fecha_eliminado DESC, e.apellido, e.nombre
        """
        params = (id_grupo,)
    else:
        query = """
            SELECT e.id_estudiante, e.matricula, e.nombre, e.apellido, e.correo,
                   e.no_lista, e.fecha_eliminado, e.eliminado_por,
                   g.nombre AS grupo, g.eliminado AS grupo_eliminado
            FROM estudiante e
            LEFT JOIN grupo g ON e.id_grupo = g.id_grupo
            WHERE e.eliminado = 1 AND (g.eliminado = 0 OR g.id_grupo IS NULL)
            ORDER BY e.fecha_eliminado DESC, e.apellido, e.nombre
        """
        params = None

    try:
        return {"success": True, "data": await fetch_all(query, params)}
    except Exception as e:
        logger.error(f"Error al listar estudiantes eliminados: {e}")
        raise HTTPException(status_code=500, detail="Error al consultar la papelera")


@router.get("/resumen")
async def resumen_papelera():
    """Conteo rápido de lo que hay en la papelera."""
    query = """
        SELECT
            (SELECT COUNT(*) FROM grupo         WHERE eliminado = 1) AS grupos,
            (SELECT COUNT(*) FROM estudiante    WHERE eliminado = 1) AS estudiantes,
            (SELECT COUNT(*) FROM clase         WHERE eliminado = 1) AS clases,
            (SELECT COUNT(*) FROM horario_clase WHERE eliminado = 1) AS horarios
    """
    try:
        return {"success": True, "data": await fetch_one(query)}
    except Exception as e:
        logger.error(f"Error al obtener resumen de papelera: {e}")
        raise HTTPException(status_code=500, detail="Error al consultar la papelera")
