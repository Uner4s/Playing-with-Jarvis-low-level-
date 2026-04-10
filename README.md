# Jarvis - Automatización por Audio

Sistema de automatización personal activado por sonido, corriendo completamente local en macOS.

## Estado actual

El disparador funcional hoy es el **doble aplauso**: dos aplausos detectados por micrófono activan una secuencia de bienvenida — voz, música y apps.

Pero ese es solo el punto de partida.

## La meta real

El objetivo es construir un sistema de **reconocimiento de audio basado en matemáticas de señales**, sin depender de integraciones externas ni modelos de ML preentrenados. La idea es entender y controlar cada capa del pipeline:

```
Micrófono → señal de audio cruda
    → análisis matemático (RMS, FFT, MFCCs)
    → comparación de huellas sonoras
    → trigger específico por voz
    → acción
```

Que Jarvis entienda "hola Jarvis" o "hora de trabajar" no porque le dimos un modelo entrenado por otro, sino porque construimos nosotros la lógica que compara el sonido matemáticamente.

## Lo que hay hoy

| Archivo | Qué hace |
|---|---|
| `bienvenido_jarvis.py` | Script principal — doble aplauso → bienvenida + YouTube + Claude |
| `experiments/paso1_grabar_huella.py` | Graba una palabra y extrae su huella MFCC con numpy puro |
| `experiments/paso2_comparar.py` | Compara en tiempo real audio entrante contra el template guardado |
| `experiments/paso3_voz_trigger.py` | Trigger por frases usando Whisper como experimento de referencia |
| `docs/how_it_works.md` | Documentación técnica del pipeline de audio y threading |

## Lo que aprendimos experimentando

- El RMS solo detecta energía sonora — sirve para aplausos, no para palabras
- El promedio de MFCCs describe al hablante, no la palabra — no discrimina entre frases
- El recorte de silencio es crítico antes de comparar huellas
- Whisper funciona bien como referencia, pero la meta es no depender de él

## Instalación

```bash
pip3 install sounddevice numpy pyttsx3 scipy
```

## Uso

```bash
# Script principal (doble aplauso)
python3 bienvenido_jarvis.py

# Experimentos de audio
python3 experiments/paso1_grabar_huella.py
python3 experiments/paso2_comparar.py
python3 experiments/paso3_voz_trigger.py
```

## Requisitos

- macOS (usa `say` para TTS y `osascript` para apps)
- Python 3.9+
- Micrófono con permisos en Configuración → Privacidad → Micrófono
- iTerm2 o terminal con acceso al micrófono habilitado
