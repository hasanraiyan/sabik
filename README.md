# Sabik - Terminal AI Assistant 🧠💻

**Speed. Control. Focus.**  
Sabik is your personal CLI assistant built for fast, privacy-respecting, AI-powered productivity.

---

## ✨ What is Sabik?

Sabik is a terminal-first AI agent that helps you automate information tasks, generate content (text, images), analyze data, and interact with your filesystem—all with natural language in your terminal.

---

## 🚀 Features

- **Natural language command processing** using OpenAI LLMs (calls OpenAI-compatible APIs).
- **Tool-calling support**: The agent can automatically use:
  - Text-to-image generation (`generate_ai_image`)
  - Image content analysis (`analyze_image_content`)
  - Audio file transcription (`transcribe_audio_file`)
  - Text-to-speech audio generation (`generate_speech_audio`)
  - Simple web search (`simple_web_search`)
  - Calculator (`calculator`)
- **Rich CLI interface:** Fast, keyboard-driven, with minimal distractions.

---

## ⚙️ Installation & Setup

1. **Clone the repository:**

   ```bash
   git clone <your-sabik-repo-url>
   cd sabik
   ```

2. **Set up environment variables:**  
   Create a `.env` file (see `.env.example` for required variables):

   ```
   OPENAI_BASE_URL_TEXT=...
   OPENAI_IMAGE_BASE_URL_TEXT=...
   OPENAI_API_KEY=sk-...
   OUTPUT_DIR=./outputs
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   # (If requirements.txt is missing, install: openai, requests, rich)
   ```

4. **Run the assistant:**

   ```bash
   python main.py
   ```

---

## 📝 How to Use

Once started, Sabik runs in your terminal and awaits your input.  
**Just type your request**, for example:

- `Generate an image of a futuristic city at sunset.`
- `What is depicted in the image located at ./cat.jpg?`
- `Transcribe the audio content from meeting.wav.`
- `Can you say "Hello, world!" using the echo voice?`
- `What is the result of (350 / 7) * 3 + 15?`
- `Fetch the main content from https://example.com.`

**To exit:**  
Type `quit` or `exit`.

---

## 🔐 Configuration

Environment variables (see `.env.example`):

| Variable                  | Purpose                                    |
|---------------------------|--------------------------------------------|
| OPENAI_BASE_URL_TEXT      | Text endpoints for OpenAI-compatible API   |
| OPENAI_IMAGE_BASE_URL_TEXT| Image generation API endpoint              |
| OPENAI_API_KEY            | Your OpenAI (or compatible) API key        |
| OUTPUT_DIR                | Directory to store outputs                 |

---

## 🏗️ Project Structure

```
sabik/
├── main.py                 # CLI entry point
├── sabik_agent/            # Core logic (agent, tools, config, interface)
├── .env.example            # Example environment config
```

---

## 📦 Requirements

- Python 3.8+
- Packages: openai, requests, rich

---

## 👤 Author

**Raiyan Hasan**  
MIT Muzaffarpur | [PYQDeck](https://pyqdeck.vercel.app)

---

## 📜 License

MIT License

---

> Think faster. Build faster. Live cleaner.  
> **Sabik** — terminal automation, reimagined.
