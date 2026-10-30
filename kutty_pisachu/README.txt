# Kutty Pisachu – Updated Chat-Only Build

## Files
- `app.py` – Flask + Gemini backend, conversation history, WhatsApp-style system prompt
- `templates/index.html` – English UI
- `static/script.js` – chat frontend and in-page conversation history
- `static/style.css` – responsive purple chat design
- `requirements.txt` – Python dependencies

## Run on Windows
1. Open Command Prompt in the project folder.
2. Activate your existing virtual environment if you use one.
3. Install dependencies:
   `pip install -r requirements.txt`
4. Set your Gemini key for this terminal session:
   `set GEMINI_API_KEY=YOUR_GEMINI_API_KEY`
5. If needed, set the model enabled for your Gemini API key:
   `set GEMINI_MODEL=gemini-3.6-flash`
6. Run:
   `python app.py`
7. Open `http://127.0.0.1:5000`

Do not paste your API key into source code or send it in chat.

## Render
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`
- Environment variables:
  - `GEMINI_API_KEY` = your Gemini API key
  - `GEMINI_MODEL` = a model name available to your API key (the default in app.py is `gemini-3.6-flash`)

## Notes
- Conversation history is kept in the browser tab while it remains open. Clear Chat resets it.
- The browser sends up to the last 12 messages as context.
- Gemini free-tier quotas and model availability still apply. An API key does not mean unlimited requests.
- This build is chat-only; it does not include photo upload or camera analysis.
