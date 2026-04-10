# CLAUDE.md — Jarvis Project

Contexto de desarrollo para Claude Code. Leer antes de modificar cualquier cosa.

---

## Qué es este proyecto

**Jarvis** es un sistema de automatización personal activado por sonido, pensado para correr en macOS. El script actual detecta dos aplausos por micrófono y ejecuta una secuencia de bienvenida (voz, música, apps).

El objetivo es ir agregando funcionalidades propias sobre esta base: nuevos disparadores de sonido, nuevas acciones, configuración externa, etc.

---

## Estado actual

### Archivo principal
- `bienvenido_jarvis.py` — script único, todo en un archivo

### Lo que hace hoy
1. Escucha el micrófono continuamente
2. Detecta 2 aplausos dentro de una ventana de 2 segundos
3. Dice "Bienvenido a casa, señor Tatay" con la voz del sistema
4. Abre YouTube con una URL fija
5. Abre Claude y Cursor en pantalla dividida (50/50)

### Documentación técnica
- `docs/how_it_works.md` — explicación detallada del pipeline de audio, threading y secuencia de bienvenida

---

## Arquitectura actual

```
bienvenido_jarvis.py
  ├── Configuración (constantes al inicio)
  ├── audio_callback()       ← hilo de sounddevice, no bloquear
  ├── secuencia_bienvenida() ← hilo daemon
  │     ├── hablar()
  │     ├── abrir_youtube()
  │     └── abrir_apps_lado_a_lado()
  └── main()                 ← loop principal
```

El estado de disparo es global (`triggered`, `clap_times`) protegido con `threading.Lock()`.

---

## Decisiones de diseño actuales

- **macOS only:** usa `say`, `open -a`, `osascript`. No hay soporte cross-platform todavía.
- **Script único:** toda la lógica en un archivo. Cuando agreguemos más funcionalidades, habrá que modularizar.
- **Configuración en el fuente:** las constantes están al inicio del archivo. El siguiente paso natural es moverlas a un archivo de config externo.
- **Sin API keys:** el TTS usa la voz del sistema (`say -v Monica`), sin dependencias de nube.

---

## Constantes clave que suelen ajustarse

```python
THRESHOLD      = 0.20    # subir si hay falsos positivos, bajar si no detecta
COOLDOWN       = 0.1     # segundos mínimos entre dos picos del mismo aplauso
DOUBLE_WINDOW  = 2.0     # ventana de tiempo para el segundo aplauso
MENSAJE        = "..."   # texto que dice la voz
YOUTUBE_URL    = "..."   # canción a abrir
NEW_PROJECT    = "..."   # carpeta que abre Cursor
```

---

## Próximas funcionalidades (backlog)

Estas son ideas a implementar — actualizar esta lista conforme avancemos:

- [ ] Archivo de configuración externo (`config.json` o `config.toml`) para no editar el fuente
- [ ] Múltiples patrones de sonido (1 aplauso, 3 aplausos, golpe en mesa) → acciones distintas
- [ ] Sistema de "acciones" configurable: qué apps abrir, qué URL, qué mensaje
- [ ] Modo debug que muestra el RMS en tiempo real para calibrar THRESHOLD
- [ ] CLI flags (`--threshold`, `--config`, `--dry-run`)
- [ ] Modularización: separar detección de audio, acciones y config en módulos distintos
- [ ] Logging a archivo en vez de solo prints

---

## Convenciones para seguir trabajando

- Mantener las constantes de configuración al inicio del archivo mientras sea un script único
- No introducir APIs de nube sin necesidad (preferir herramientas del sistema)
- Comentar en español (el proyecto está en español)
- Antes de agregar una funcionalidad nueva, actualizar este archivo con lo que se agregó
- Documentación técnica va en `docs/`

---

## Cómo correr el proyecto

```bash
# Instalar dependencias
pip install sounddevice numpy pyttsx3

# Correr
python bienvenido_jarvis.py
```

Requiere permiso de micrófono en macOS (Sistema → Privacidad → Micrófono → Terminal/iTerm).
