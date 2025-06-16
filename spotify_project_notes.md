# Proyecto Spotify Automation – Resumen Técnico

**Autor:** Gonzalo  
**Inicio estimado:** 2025-05  
**Objetivo:** Crear una app para iPhone que permita generar atajos personalizados para reproducir canciones específicas de Spotify, integrables en automatizaciones como alarmas.

---

## 🔧 Estructura Técnica

- La app genera `.shortcut` personalizados que usan la acción **"Abrir URL"** con el esquema:

  ```
  spotify://track/{ID}
  ```

- El usuario ingresa un link de Spotify como:

  ```
  https://open.spotify.com/track/0Ca3ApUYoLm9w44wuSO6Ga?si=...
  ```

- Se extrae el **ID de la canción** y se reemplazan **16 bytes en la posición 5474** del archivo `.shortcut` para personalizarlo.

---

## 🛠️ Flujo Técnico del Proyecto

1. El usuario introduce un enlace de Spotify en la app o atajo.
2. Un script alojado en **PythonAnywhere** extrae el ID de canción desde el link.
3. Localmente, se modifica un archivo `.shortcut` reemplazando los bytes del ID.
4. El usuario recibe un nuevo atajo personalizado con nombre visible como:
   ```
   Reproducir [nombre de la canción]
   ```

---

## 📁 Detalles del Archivo `.shortcut`

- **Byte offset para el ID de Spotify**: `5474`
- **Longitud del ID**: 16 bytes
- **Codificación**: binaria

---

## 🔗 Integración con iOS

- Los atajos se integran al sistema mediante archivos `.shortcut` reutilizables.
- Se evita el uso de apps externas como Scriptable.
- El usuario final no necesita herramientas adicionales.

---

## 🌐 PythonAnywhere – API para extracción del ID

Script simple en Python que extrae el ID desde un link:

```python
import re

def extract_id(spotify_url):
    match = re.search(r"track/([a-zA-Z0-9]+)", spotify_url)
    return match.group(1) if match else None
```

Puede devolverse como texto plano al ser accedido por el atajo de iOS.

---

## 🔐 Protección de memoria externa

Se acordó usar una **URL protegida con token temporal** para permitir que GPT cargue todo el historial del proyecto en nuevos chats, mediante un servidor Flask básico.

Ejemplo de acceso:
```
https://gonzalo.pythonanywhere.com/spotify-notes?token=abc123
```

---

## 🧩 Elementos del diseño de la app

- Nombre tentativo: `Spotify Automation`
- Minimalista: solo se solicita el enlace de Spotify al usuario
- Internamente muestra el nombre de la canción y genera el atajo
- Soporte para automatizaciones como “Al despertar” en iOS 18

---

## 📌 Consideraciones Finales

- Todos los reemplazos de ID deben garantizar que el nuevo `.shortcut` sea funcional sin corromper otras secciones.
- Se está mapeando progresivamente el archivo `.shortcut` para identificar qué otras zonas podrían modificarse de forma segura.

---
