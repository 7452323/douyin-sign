# douyin-sign / Paquete de firmas completo de Douyin

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## Español

### Descripción General

**douyin-sign** es una implementación pura en Python de la suite completa de algoritmos de firma de TikTok/Douyin. Encapsula todos los algoritmos de firma utilizados en la aplicación móvil de TikTok, ayudando a los desarrolladores a generar los encabezados de firma requeridos para las solicitudes de API en un solo lugar.

### Características

- ✅ **X-Gorgon** — Firma de solicitudes (variantes 0404/0405/0407, etc.)
- ✅ **X-Argus** — Firma de control de riesgos / huella digital del dispositivo
- ✅ **X-Ladon** — Firma adicional de control de riesgos
- ✅ **X-Khronos** — Firma de marca de tiempo de la solicitud
- ✅ **X-SS-STUB** — Firma de resumen MD5 del cuerpo de la solicitud
- ✅ **X-Bogus** — Firma web / ligera
- ✅ **TTEncrypt** — Algoritmo de cifrado personalizado de TikTok

### Instalación

```bash
pip install douyin-sign
```

### Inicio Rápido

```python
from sign import sign_all

headers = sign_all(
    method='POST',
    url='https://...',
    body=b'...',
    cookies='...',
)

# headers ahora contiene X-Gorgon, X-Khronos, X-SS-STUB, etc.
```

### Estructura del Directorio de Constantes

```
constants/
└── current/
    ├── sign_key.b64          # Clave de firma codificada en Base64 (44 bytes)
    ├── gorgon_table.hex      # Constante de tabla de búsqueda hexadecimal utilizada por el algoritmo Gorgon (20 bytes)
    └── protobuf_fields.json  # Tabla de mapeo de números de campo de Protobuf
```

Las constantes se actualizan junto con las versiones de la aplicación de TikTok. El directorio `current/` siempre apunta al conjunto de constantes verificadas más reciente. Las constantes históricas se guardan en directorios con número de versión (por ejemplo, `constants/v38.3.0/`).

### Política de Versiones

La versión de este paquete sigue los números de versión de la aplicación de TikTok (por ejemplo, `38.3.0`). La versión inicial es `1.0.0`. Cuando TikTok lanza una nueva versión de la aplicación, se puede utilizar el script `update.py` para extraer y actualizar las constantes automáticamente.

### Licencia

MIT
