
import os
import logging
from functools import lru_cache

from flask import Flask, render_template, request, jsonify
from google import genai
from google.genai import types

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

SYSTEM_PROMPT = """
You are Kutty Pisachu, an AI chat companion with a casual
WhatsApp-style texting voice.

You are an AI, not a human. Be friendly, caring, playful,
respectful, and honest.

Do not claim to be a real person or have a real-life body,
location, or experiences. Keep all interactions age-appropriate.
Do not use romantic or sexual roleplay.

LANGUAGE AND TONE:
- Understand Tamil, Tanglish, and English.
- Normally reply in natural Tanglish (Tamil using English letters).
- Do not use Tamil script unless the user asks.
- Sound like a natural chat, not a formal assistant.
- Keep casual replies short.
- Give detailed answers when users ask questions.
- Vary your replies. Do not repeat fixed responses.

CHAT TOPICS:
Chat naturally about daily routine, meals, college, classes,
exams, assignments, friends, family, travel, hobbies,
cooking, entertainment, social media, and ordinary life.

EMOTIONAL SUPPORT:
Listen without judging. Respond gently when the user is upset.
Offer practical, safe support when asked.

GENERAL KNOWLEDGE:
Answer educational, technical, and general questions accurately.
Explain difficult topics in simple steps when requested.
If uncertain, say so instead of inventing facts.

IMPORTANT:
Generate a fresh response based on the user's latest message
and conversation history.
"""

# Reuse one Gemini client instead of creating a temporary client
@lru_cache(maxsize=1)
def get_client():
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing in environment settings."
        )

    return genai.Client(api_key=api_key)


def clean_history(raw_history):
    cleaned = []

    if not isinstance(raw_history, list):
        return cleaned

    for item in raw_history[-12:]:
        if not isinstance(item, dict):
            continue

        role = item.get("role")
        content = item.get("text")

        if role not in ("user", "model"):
            continue

        if not isinstance(content, str):
            continue

        content = content.strip()

        if content and len(content) <= 4000:
            cleaned.append(
                types.Content(
                    role=role,
                    parts=[
                        types.Part.from_text(text=content)
                    ],
                )
            )

    return cleaned


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "model": MODEL
    })


@app.post("/api/chat")
def chat():
    data = request.get_json(silent=True) or {}

    message = data.get("message", "")

    if not isinstance(message, str) or not message.strip():
        return jsonify({
            "error": "Please type a message first."
        }), 400

    message = message.strip()

    if len(message) > 4000:
        return jsonify({
            "error": "Please keep each message under 4,000 characters."
        }), 400

    try:
        contents = clean_history(data.get("history", []))

        contents.append(
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=message)
                ],
            )
        )

        # Important: keep the client in a variable during the request
        client = get_client()

        response = client.models.generate_content(
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
            reply = (
                "Aiyoo, reply generate aagala 😅 "
                "Innoru thadava try pannu."
            )

        return jsonify({"reply": reply})

    except Exception as exc:
        logging.exception("Gemini chat request failed")

        error_text = str(exc).lower()

        if (
            "429" in error_text
            or "resource_exhausted" in error_text
            or "quota" in error_text
        ):
            error_message = (
                "Gemini usage limit reached. "
                "Konjam neram wait pannitu try pannu."
            )

        elif "503" in error_text or "unavailable" in error_text:
            error_message = (
                "Gemini ippo busy-ah irukku. "
                "Konjam neram kazhichu try pannu."
            )

        elif "404" in error_text or "not_found" in error_text:
            error_message = (
                "Gemini model unavailable. "
                "Render-la GEMINI_MODEL setting check pannu."
            )

        elif (
            "api key" in error_text
            or "permission" in error_text
            or "unauthorized" in error_text
        ):
            error_message = (
                "Gemini API key check pannu. "
                "Key-ai chat-la share panna vendam."
            )

        else:
            error_message = (
                "AI reply ippo available illa. "
                "Internet, API key, model setting check pannu."
            )

        return jsonify({"error": error_message}), 503


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=False,
    )
