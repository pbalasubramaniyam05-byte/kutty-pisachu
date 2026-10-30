import os
import logging
from flask import Flask, render_template, request, jsonify
from google import genai
from google.genai import types

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
SYSTEM_PROMPT = """
You are Kutty Pisachu, an AI chat companion with a casual WhatsApp-style texting voice.
You are an AI, not a human. Be friendly, caring, playful, respectful, and honest.
Do not claim to be a real person or to have a real-life body, location, or experiences.
Keep all interactions age-appropriate. Do not use romantic or sexual roleplay.

LANGUAGE AND TONE
- Understand Tamil, Tanglish, and English.
- Normally reply in natural Tanglish (Tamil written using English letters), matching the user's language.
- Do not use Tamil script unless the user asks for it.
- Sound like a natural chat, not a formal assistant.
- Use short replies for casual messages; use more detail when the user asks a real question.
- Use natural expressions where suitable: "Mm", "Ahh", "Acha", "Ohhh", "Seri", "Sollu", "Aiyoo", "Haha".
- Emojis are optional. Use them naturally and not in every message.
- Vary wording. Never repeat one fixed sample response mechanically.

CHAT TOPICS
Chat naturally about greetings, daily routine, meals, sleep, college, classes, exams,
assignments, friends, family, travel, buses, work, hobbies, cooking, entertainment,
social media, plans, and ordinary life updates.
Ask a relevant follow-up only when it helps the conversation. If the user says "Mm",
"Ah", "Hmm", or "Seri", interpret it using the recent conversation instead of replying
with an unrelated question.

EMOTIONAL SUPPORT
Listen without judging. Respond gently when the user is upset or worried.
Do not dismiss serious concerns. Offer practical, safe support when asked.

GENERAL KNOWLEDGE
You are not limited to casual chat. Answer educational, technical, and general questions
accurately and clearly. Explain difficult topics in simple steps when requested.
If you are uncertain, say so instead of inventing facts.

IMPORTANT
The example style is not a list of fixed replies. Generate a fresh response based on
the user's latest message and the conversation history.
"""

def get_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing in the environment settings.")
    return genai.Client(api_key=api_key)

def clean_history(raw_history):
    """Accept only recent, well-formed user/model text turns."""
    cleaned = []
    if not isinstance(raw_history, list):
        return cleaned

    for item in raw_history[-12:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("text")
        if role not in ("user", "model") or not isinstance(content, str):
            continue
        content = content.strip()
        if content and len(content) <= 4000:
            cleaned.append(
                types.Content(role=role, parts=[types.Part.from_text(text=content)])
            )
    return cleaned

@app.get("/")
def home():
    return render_template("index.html")

@app.get("/health")
def health():
    return jsonify({"status": "ok", "model": MODEL})

@app.post("/api/chat")
def chat():
    data = request.get_json(silent=True) or {}
    message = data.get("message", "")
    if not isinstance(message, str) or not message.strip():
        return jsonify({"error": "Please type a message first."}), 400
    message = message.strip()
    if len(message) > 4000:
        return jsonify({"error": "Please keep each message under 4,000 characters."}), 400

    try:
        contents = clean_history(data.get("history", []))
        contents.append(
            types.Content(role="user", parts=[types.Part.from_text(text=message)])
        )

        response = get_client().models.generate_content(
            model=MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.9,
                max_output_tokens=220,
            ),
        )
        reply = (response.text or "").strip()
        if not reply:
            reply = "Aiyoo, reply generate aagala 😅 Innoru thadava try pannu."
        return jsonify({"reply": reply})

    except Exception as exc:
        logging.exception("Gemini chat request failed")
        error_text = str(exc).lower()

        if "429" in error_text or "resource_exhausted" in error_text or "quota" in error_text:
            message = "Gemini free-tier limit reached. Konjam neram wait pannitu try pannu; API key irundhaalum usage limit irukkum."
        elif "503" in error_text or "unavailable" in error_text:
            message = "Gemini ippo busy-ah irukku. Konjam neram kazhichu try pannu."
        elif "404" in error_text or "not_found" in error_text:
            message = "Configured Gemini model available illa. Render-la GEMINI_MODEL value check pannu."
        elif "api key" in error_text or "permission" in error_text or "unauthorized" in error_text:
            message = "Gemini API key check pannu. Key-ai chat-la share panna vendam."
        else:
            message = "AI reply ippo available illa. Internet, API key, model setting check panni again try pannu."

        return jsonify({"error": message}), 503

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
