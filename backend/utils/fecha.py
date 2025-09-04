from datetime import datetime, timezone, timedelta
import pytz

# Zona horaria CDMX
CDMX = pytz.timezone("America/Mexico_City")

def obtener_fecha_hora_cdmx():
    """
    Retorna la fecha, hora y nombre del día en CDMX.
    """
    ahora = datetime.now(CDMX)
    fecha = ahora.date()
    hora = ahora.time().replace(microsecond=0)  # objeto time
    dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    dia_semana = dias[ahora.weekday()]  # 🔧 CORREGIDO: weekday() ya da 0=Lunes, 6=Domingo
    
    return {
        "fecha": fecha,
        "hora": hora, 
        "dia": dia_semana
    }

def convertir_fecha_a_cdmx(fecha_iso):
    """
    Convierte un string o datetime ISO a fecha CDMX (YYYY-MM-DD)
    """
    if not fecha_iso:
        return None
    if isinstance(fecha_iso, str):
        if len(fecha_iso) == 10:
            fecha = datetime.strptime(fecha_iso + " 12:00:00", "%Y-%m-%d %H:%M:%S")
        else:
            fecha = datetime.fromisoformat(fecha_iso)
    elif isinstance(fecha_iso, datetime):
        fecha = fecha_iso
    else:
        return None

    fecha_cdmx = fecha.astimezone(CDMX)
    return fecha_cdmx.strftime("%Y-%m-%d")

def obtener_fecha_hora_cdmx_completa():
    """
    Retorna fecha y hora completa en CDMX en formato YYYY-MM-DDTHH:MM:SS (compatible SQL)
    """
    ahora = datetime.now(CDMX)
    return ahora.strftime("%Y-%m-%dT%H:%M:%S")
