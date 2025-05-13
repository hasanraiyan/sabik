# Audio Auto-Play Feature

## Overview
This feature enables automatic playback of generated speech audio files immediately after they are created. The implementation supports multiple platforms (Windows, macOS, Linux) and includes fallback mechanisms to ensure compatibility across different environments.

## How It Works

1. When the speech generation tool creates an audio file, it can now automatically play it without requiring manual user action.
2. The system uses platform-specific methods to play audio:
   - **Windows**: Uses PowerShell's Media.SoundPlayer, with fallbacks to winsound and the default system player
   - **macOS**: Uses the `afplay` command
   - **Linux**: Tries multiple players (aplay, paplay, mpg123, mpg321)

## Configuration

Auto-play can be controlled in two ways:

1. **Environment Variable**: Set `TTS_AUTO_PLAY` to "true" or "false"
   ```python
   os.environ['TTS_AUTO_PLAY'] = 'true'  # Enable auto-play
   os.environ['TTS_AUTO_PLAY'] = 'false' # Disable auto-play
   ```

2. **Function Parameter**: Pass `auto_play=True` or `auto_play=False` directly to the function
   ```python
   generate_speech_audio(text, voice="alloy", auto_play=True)
   ```

## Default Behavior

By default, auto-play is enabled (set to `true`). If you want to disable it, you need to explicitly set it to `false`.

## Testing

A test script (`test_audio_play.py`) is included to verify the auto-play functionality:

```python
python test_audio_play.py
```

This will generate a test audio file and automatically play it.