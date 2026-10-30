KUTTY PISACHU - FREE LOCAL OLLAMA VERSION
========================================

IMPORTANT
---------
This version uses Ollama running on the SAME computer as Flask. It does not
need an AI API key or API credits when used locally.

Putting this Flask app on Render does NOT put Ollama on Render automatically.
For online hosting, OLLAMA_URL must point to an Ollama server reachable from
Render. A home laptop's 127.0.0.1 is not reachable by Render, and the laptop
would need to stay on and securely expose a server. Do not expose Ollama to the
public internet without proper security. Free cloud AI services may have limits
and may require a free API key. This ZIP alone cannot guarantee free online AI.

LOCAL SETUP (Windows)
---------------------
1. Install Ollama: https://ollama.com/download/windows
2. Open Command Prompt and run:
       ollama pull gemma3:4b
3. Test the model:
       ollama run gemma3:4b
   Type a test message, then exit with Ctrl+C.
4. Open another Command Prompt in this folder and run:
       python -m pip install -r requirements.txt
       python app.py
5. Open http://127.0.0.1:5000 in the laptop browser.

For an 8 GB RAM PC, gemma3:4b may run slowly. If necessary, try a smaller
text-only model for chat, but image analysis needs a vision-capable model.

ONLINE HOSTING
--------------
The included Render configuration can host the Flask web layer, but the local
Ollama AI endpoint will not exist inside Render by default. Before deploying,
choose a remote inference host and configure OLLAMA_URL, or adapt the app to a
cloud AI provider. Never commit API keys or .env files to GitHub.
