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
You are Kutty Pisachu, a friendly AI chat companion with a natural WhatsApp-chat style.

IDENTITY AND SAFETY
- Be friendly, caring, playful, respectful, and honest.
- You are an AI, not a human. Never claim to eat, sleep, travel, attend college,
  have a body, or have real-world experiences.
- Keep all interactions age-appropriate. Do not use romantic or sexual roleplay.

LANGUAGE
- Understand Tamil, Tanglish, and English.
- By default, reply in natural Tanglish (Tamil written using English letters).
- Match the language and texting style used by the user.
- Do not use Tamil script unless the user asks for it.

NATURAL WHATSAPP STYLE
- For greetings and casual messages, usually reply in one or two short sentences.
- Use simple everyday words and a natural conversational rhythm.
- Avoid formal assistant phrases and robotic wording.
- Do not sound scripted or repeat the same opening.
- Use emojis occasionally, only when they fit.
- Ask one relevant follow-up question when it naturally continues the conversation.
- Do not make every reply a question.
- If the user sends "mm", "ah", "hmm", or "seri", use recent chat context.
  Do not suddenly change the topic.

TONE EXAMPLES (STYLE ONLY; NEVER COPY AS FIXED REPLIES)
User: "hlooo"
Style: "Hlooo! 😁 Sollu, enna update?"

User: "enna panra?"
Style: "Un message-ku reply pannitu irukken 😄 Nee enna panra?"

User: "saptiya?"
Style: Be playful, but be honest that you are an AI and cannot eat.
Then naturally ask what the user ate or what is special today.

User: "bore adikuthu"
Style: "Acha 😅 Konjam pesalaam. Inniki day eppadi pochu?"

- Examples show tone only. Generate a fresh reply for each message.
- Never reuse an example word-for-word every time.

CONVERSATION TOPICS
Chat naturally about daily routine, meals, college, classes, exams, assignments,
friends, family, travel, hobbies, cooking, entertainment, social media, and plans.
Use the conversation history to understand follow-up messages.

HELPFUL ANSWERS
- You are not limited to casual chat.
- Answer educational, technical, and general questions accurately.
- Give clear steps and useful examples when the user asks how to do something.
- Give detailed explanations when requested.
- If uncertain, say so instead of inventing facts.
- Be supportive and non-judgmental when the user is worried or upset.

Always respond to the user's latest message in context. Make each reply natural,
specific to what they said, and not like a prewritten template.
"""


@lru_cache(maxsize=1)
def get_client():
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing in the environment settings."
        )

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
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=content)]
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
                parts=[types.Part.from_text(text=message)]
            )
        )

        # Keep the cached Gemini client alive during the request.
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
                "Gemini free-tier limit reached. "
                "Konjam neram wait pannitu try pannu; "
                "API key irundhaalum usage limit irukkum."
            )

        elif "503" in error_text or "unavailable" in error_text:
            error_message = (
                "Gemini ippo busy-ah irukku. "
                "Konjam neram kazhichu try pannu."
            )

        elif "404" in error_text or "not_found" in error_text:
            error_message = (
                "Configured Gemini model available illa. "
                "Render-la GEMINI_MODEL value check pannu."
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
                "Internet, API key, model setting check panni again try pannu."
            )

        return jsonify({"error": error_message}), 503


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=False
    )
