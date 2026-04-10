# Cómo funciona Jarvis

Documentación técnica del script `bienvenido_jarvis.py`.

---

## Visión general

El script escucha el micrófono de forma continua en un hilo de audio dedicado. Cuando detecta dos aplausos dentro de una ventana de tiempo, dispara una secuencia de bienvenida: reproduce un mensaje de voz, abre YouTube y organiza dos apps en pantalla.

```
Micrófono
   │
   ▼
audio_callback()   ← hilo de sounddevice (tiempo real)
   │
   ├── mide RMS del bloque de audio
   ├── compara con THRESHOLD
   ├── registra timestamp del aplauso
   └── si count >= 2 → dispara secuencia_bienvenida() en nuevo hilo
                              │
                              ├── hablar()
                              ├── abrir_youtube()
                              └── abrir_apps_lado_a_lado()
```

---

## Pipeline de detección de audio

### 1. Captura de audio (`sounddevice.InputStream`)

- **Sample rate:** 44100 Hz (calidad CD)
- **Block size:** 2205 muestras = 50 ms por bloque
- El stream llama a `audio_callback()` cada 50 ms con el bloque de audio fresco

### 2. Cálculo de RMS

```python
rms = float(np.sqrt(np.mean(indata ** 2)))
```

El RMS (Root Mean Square) mide la energía sonora del bloque. Un aplauso genera un pico de energía muy por encima del ruido ambiente. El valor está normalizado en el rango `[0.0, 1.0]`.

### 3. Lógica de doble aplauso

```
rms > THRESHOLD
       │
       ├── ¿último aplauso fue hace menos de COOLDOWN? → ignorar (mismo aplauso)
       │
       └── registrar timestamp
               │
               └── limpiar aplausos fuera de DOUBLE_WINDOW
                       │
                       └── ¿count >= 2? → TRIGGER
```

| Constante       | Valor default | Efecto |
|----------------|--------------|--------|
| `THRESHOLD`    | `0.20`       | Sensibilidad: sube si hay falsos positivos, baja si no detecta |
| `COOLDOWN`     | `0.1 s`      | Evita que un solo aplauso cuente dos veces |
| `DOUBLE_WINDOW`| `2.0 s`      | Tiempo máximo entre el primer y segundo aplauso |

### 4. Concurrencia y thread safety

- `audio_callback` corre en el hilo de sounddevice (tiempo real, no bloquear)
- El estado compartido (`clap_times`, `triggered`) está protegido con `threading.Lock()`
- La secuencia de bienvenida corre en un hilo daemon separado para no bloquear la escucha
- `triggered = True` durante la secuencia evita re-disparos; se resetea a `False` después de 8 s en el hilo principal

---

## Secuencia de bienvenida

### `hablar(texto)`

1. Intenta `say -v Monica <texto>` (voz española de macOS, alta calidad, sin API key)
2. Si falla (Monica no disponible), usa `pyttsx3`:
   - Busca voces con `"es"` en el ID o `"spanish"` en el nombre
   - Fallback a voz por defecto si no encuentra español

### `abrir_youtube()`

Abre `YOUTUBE_URL` con `webbrowser.open()` (usa el navegador por defecto del sistema).

### `abrir_apps_lado_a_lado()`

1. Obtiene la resolución de pantalla via AppleScript + Finder
2. Abre la app Claude con `open -a Claude`
3. Busca el CLI de Cursor en paths conocidos y lo abre con `NEW_PROJECT`
4. Usa AppleScript para posicionar las ventanas:
   - Claude: mitad izquierda `(0, 0, mitad, alto)`
   - Cursor: mitad derecha `(mitad, 0, mitad, alto)`

---

## Flujo del hilo principal (`main`)

```
main()
  └── sd.InputStream (activo)
        └── loop: sleep 0.1s
              └── si triggered:
                    sleep 8s  ← espera que termine la secuencia
                    triggered = False
                    vuelve a escuchar
```

---

## Constantes de configuración

Todas están al inicio del archivo para facilitar ajuste sin tocar la lógica:

```python
SAMPLE_RATE    = 44100          # Hz de captura de audio
BLOCK_SIZE     = int(44100 * 0.05)  # muestras por bloque (50 ms)
THRESHOLD      = 0.20           # energía mínima para detectar aplauso
COOLDOWN       = 0.1            # segundos mínimos entre aplausos
DOUBLE_WINDOW  = 2.0            # ventana para contar 2 aplausos

YOUTUBE_URL    = "..."          # URL a abrir
MENSAJE        = "..."          # texto que dice la voz
NEW_PROJECT    = "..."          # carpeta que abre Cursor
```

---

## Dependencias

| Paquete       | Uso |
|--------------|-----|
| `sounddevice` | Captura de audio del micrófono |
| `numpy`       | Cálculo de RMS sobre el buffer |
| `pyttsx3`     | TTS fallback si `say` falla |
| `subprocess`  | `say`, `open`, `osascript`, `cursor` |
| `webbrowser`  | Abrir YouTube en el browser por defecto |
| `threading`   | Hilo para la secuencia + Lock para estado compartido |

---

## Limitaciones conocidas

- **macOS únicamente:** usa `say`, `open -a`, `osascript`, Finder
- **Apps hardcodeadas:** abre Claude y Cursor específicamente
- **Tiempo de reset hardcodeado:** 8 s fijos en `main()`, no espera al thread real
- **`COOLDOWN` corto:** 100 ms puede ser insuficiente para aplausos muy fuertes que generan eco
- **Sin config externa:** todo se configura editando el fuente directamente
