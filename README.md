# E.V. - Personal Voice AI Assistant

E.V. is a personal voice-controlled AI assistant for Windows.

## Architecture

E.V. uses:

- faster-whisper for local speech-to-text
- Groq for the AI/LLM
- Edge TTS for text-to-speech
- SoundDevice for microphone input
- Pycaw for Windows volume control
- psutil for process management

## Pipeline

Microphone
    ↓
Speech-to-Text
    ↓
Groq AI
    ↓
Tool Execution
    ↓
Response
    ↓
Text-to-Speech
    ↓
Speaker

## Installation

Install dependencies:

```bash
python -m pip install -r requirements.txt