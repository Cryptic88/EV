# E.V. — Personal Voice AI Assistant

Windows voice assistant with local speech and a choice of Groq or Ollama.

Microphone → E.V. wake phrase → Silero VAD → faster-whisper → LLM/tools → streamed sentences → Kokoro → speakers.

The defaults target a CPU with 16 GB RAM: Whisper `small.en` with INT8, Silero ONNX, and Kokoro ONNX `af_bella`. Groq remains the default brain. Speech stays local after model downloads; Groq receives transcribed text and tool results. Edge cloud speech is optional and never used as an automatic fallback unless you enable it. Web tools still need internet even with Ollama.

## Install on Windows

Use **Python 3.12, 64-bit**. Kokoro's supported Python range excludes 3.14. Keep the existing `.venv` if you want to retain the old environment.

If this upgrade already created `.runtime` and `.venv-local`, free at least 2 GB and run `.\setup-local.ps1` to finish installing, download models, and run both checks. Otherwise, install Python 3.12 and follow these steps:

```powershell
py -3.12 -m venv .venv-local
.\.venv-local\Scripts\python.exe -m pip install -r requirements.txt
.\.venv-local\Scripts\python.exe setup_models.py
```

If Python was installed into this project's `.runtime` folder with uv, use its `python.exe` to create the environment instead. Model setup downloads quantized Kokoro (about 88 MB), its voices, Silero, Whisper and the existing Vosk wake model. Downloads need internet and disk space; model files and environments are ignored by Git. Setup can be rerun after an interrupted download. Whisper/Vosk use their library caches.

Keep your existing `.env`. Add settings from `.env.example` as needed; do not overwrite a real Groq key with the empty example. Environment variables take priority over `.env`.

```powershell
.\start-ev.ps1
# Or:
.\.venv-local\Scripts\python.exe main.py
```

Until the new environment and models are ready, `.\start-ev.ps1 -Legacy` runs the existing Python environment with Edge speech, energy-based silence detection, Vosk, and `base.en` Whisper. The launcher restores the previous environment settings when E.V. exits. Keep at least 2 GB free for dependency installation and model downloads.

Say **“E.V.”**, pause briefly, then your command. After each reply, E.V. listens for another request for eight seconds without requiring its name again. If no speech starts, it returns to wake-word mode. The microphone stays closed while replies play, with a brief 0.2-second pause before reopening. The tray menu opens the UI at http://127.0.0.1:5000 and can stop E.V. The listener allows five seconds to start the initial command and ends after 0.8 seconds without speech. Each command gets up to 15 seconds from speech onset, independent of time spent waiting. Voice confirmations use the same VAD. Barge-in is not implemented.

Replies are generated as a token stream, prepared on a bounded synthesis worker, and played in order on a separate bounded playback worker. This lets the next sentence synthesize during current playback; gaps can still occur if CPU synthesis is slower than the audio. Tool arguments are assembled before execution. Both audio stages finish before tools request microphone confirmation. Responses favor conversational wording and contractions without repetitive acknowledgements. Windows application, browser, volume, and search tools remain available.

To compare the installed American Bella and British Emma voices, run `.\.venv-local\Scripts\python.exe audition_voices.py`. Matching WAV samples are saved in `artifacts/voices/`. Bella is active by default. To choose Emma, set `KOKORO_VOICE=bf_emma` and `KOKORO_LANGUAGE=en-gb` in `.env`, then restart E.V.

## Application shortcuts

E.V. has 34 configured app shortcuts based on this laptop's installed Start-menu entries. Voice aliases and Windows launch targets are in `config/app_shortcuts.json`.

| Group | Applications |
| --- | --- |
| IDEs and development | Visual Studio Code, Visual Studio, Android Studio, Arduino IDE, Postman, Docker Desktop, GitHub Desktop, Terminal |
| Databases | SQL Server Management Studio, MySQL Workbench, pgAdmin |
| Messaging and meetings | WhatsApp, Outlook, Outlook (classic), Microsoft Teams, Discord, Zoom |
| Office | Word, Excel, PowerPoint, OneNote |
| Browsers and media | Chrome, Edge, Firefox, Spotify, CapCut |
| Utilities | Notepad, Calculator, Paint, File Explorer, Task Manager, Snipping Tool, 7-Zip, WinRAR |

Examples: “Open VS Code”, “Open WhatsApp”, “Open Outlook”, “Open classic Outlook”, “Open Android Studio”, “Open Postman”, or “Close Visual Studio”. Closing an app still requires spoken confirmation. Known app aliases map to exact executable names, so closing VS Code targets `Code.exe`, while Visual Studio targets `devenv.exe`. Outlook selects the new app; classic Outlook is separate. Opening these apps launches them; it does not read or send their messages or edit their contents.

To add another shortcut, add a record with `name`, `aliases`, `target`, and `process_names`, then restart E.V. Store apps use `shell:AppsFolder\<AppID>`; use `Get-StartApps` to find installed app IDs. Executable paths also work. Some app IDs contain installation versions; update their records after an upgrade if launching stops working. The configured app names are included in E.V.'s prompt.

## Fully local brain (optional)

Install [Ollama](https://ollama.com), start its local server, then run:

```powershell
ollama pull qwen3:4b
```

In `.env`:

```dotenv
LLM_BACKEND=ollama
OLLAMA_MODEL=qwen3:4b
OLLAMA_BASE_URL=http://127.0.0.1:11434
```

Use a model that supports tool calling. No Groq key is needed in Ollama mode. Switching back uses `LLM_BACKEND=groq`; the app never silently sends an Ollama request to Groq. Small local models may follow tool instructions less reliably; confirmations before closing programs remain enabled.

## openWakeWord (optional)

The existing Vosk detector recognizes E.V. immediately. There is no bundled pretrained “Hey E.V.” openWakeWord model. Train or supply a compatible custom **ONNX** model using the [openWakeWord documentation](https://github.com/dscripka/openWakeWord), then:

```powershell
.\.venv-local\Scripts\python.exe -m pip install -r requirements-wake.txt
.\.venv-local\Scripts\python.exe setup_models.py --wake
```

```dotenv
WAKE_BACKEND=openwakeword
WAKE_MODEL_PATH=C:/path/to/hey_ev.onnx
WAKE_THRESHOLD=0.5
```

The ONNX backend is used on Windows; audio is buffered into 80 ms frames. Shared feature models must be cached before offline use. A missing custom model produces an explicit error instead of switching to an unrelated wake phrase. Training a custom voice or wake model is a separate task requiring suitable reference data. Chatterbox/RVC are not installed.

## Tuning and fallback

| Setting | Default | Purpose |
| --- | --- | --- |
| `TTS_BACKEND` | `kokoro` | Set `edge` to use the original online voice |
| `TTS_ALLOW_EDGE_FALLBACK` | `false` | Explicitly allow cloud speech if Kokoro fails |
| `KOKORO_VOICE` | `af_bella` | Voice in downloaded voice pack |
| `KOKORO_LANGUAGE` | `en-us` | Match the selected voice language |
| `KOKORO_SPEED` | `1.0` | Normal speech speed |
| `SENTENCE_PAUSE_SECONDS` | `0.35` | Added Kokoro silence after a sentence, including inside greetings; decimals and initials stay together |
| `WHISPER_MODEL_SIZE` | `small.en` | Use `base.en` for less CPU work |
| `MICROPHONE_DEVICE` | Windows default | Input index or name and audio driver, e.g. `Microphone Array AMD MME` |
| `WHISPER_DEVICE` | `cpu` | Use `cuda` only with NVIDIA CUDA/cuDNN installed |
| `WHISPER_COMPUTE_TYPE` | `int8` | CPU quantization; consider `float16` on CUDA |
| `VAD_BACKEND` | `silero` | Use `energy` for the original volume threshold |
| `VAD_THRESHOLD` | `0.5` | Increase to reject more noise |
| `COMMAND_START_TIMEOUT` | `5` | Seconds to begin speech after wake |
| `SILENCE_DURATION` | `0.8` | Pause in seconds that ends a spoken command |
| `FOLLOW_UP_SECONDS` | `8` | Seconds to start a follow-up; `0` requires the wake word each turn |
| `REPLY_TAIL_SECONDS` | `0.2` | Brief pause after playback before reopening the microphone |

`KOKORO_MODEL_PATH`, `KOKORO_VOICES_PATH`, and `SILERO_MODEL_PATH` can point to local assets. Rerun model setup when changing Whisper model. Restart E.V. after settings changes. If Kokoro is unavailable, run model setup and check that you launched the 3.12 environment. Model initialization and first speech can be slower than subsequent replies.

## Verification

```powershell
.\.venv-local\Scripts\python.exe -m unittest discover -s tests -v
.\.venv-local\Scripts\python.exe verify_local.py
```

Unit tests use fake audio/transports and execute no real Windows tools. `verify_local.py` loads the real speech models, synthesizes a WAV into `artifacts/`, and transcribes it without playing sound or opening a microphone. A real microphone check is still needed to tune wake reliability and room-noise handling.

Implementation references: [Kokoro ONNX](https://github.com/thewh1teagle/kokoro-onnx), [Silero VAD](https://github.com/snakers4/silero-vad), [faster-whisper](https://github.com/SYSTRAN/faster-whisper), [Ollama chat API](https://docs.ollama.com/api/chat).
