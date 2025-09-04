from cryptography.fernet import Fernet
import os


# ⚠️ Sustituye esta clave por la que generaste para los QR

SECRET_KEY = os.getenv("FERNET_KEY").encode()
fernet = Fernet(SECRET_KEY)


def decrypt_qr(encrypted: str) -> str:
    try:
        return fernet.decrypt(encrypted.encode('utf-8')).decode('utf-8')
    except Exception as e:
        print(f"❌ Error desencriptando QR: {e}")
        raise ValueError("QR inválido o clave incorrecta")

def encrypt_qr(texto: str) -> str:
    """Encripta un texto con Fernet"""
    try:
        return fernet.encrypt(texto.encode('utf-8')).decode('utf-8')
    except Exception as e:
        print(f"❌ Error encriptando QR: {e}")
        raise ValueError("No se pudo encriptar el texto")
    
