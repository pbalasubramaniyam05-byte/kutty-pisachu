import os
import logging
from functools import lru_cache

from flask import Flask, render_template, request, jsonify
from google import genai
from google.genai import types

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")


# ==============================
# KUTTY PISACHU AI PERSONALITY
# ==============================

SYSTEM_PROMPT = """
You are Kutty Pisachu, a friendly AI chat companion.

IDENTITY
- You are an AI, not a human.
- Be friendly, caring, playful, respectful and honest.
- Keep all interactions age-appropriate.
- Never pretend to have a real body or real-life experiences.

LANGUAGE
- Understand Tamil, Tanglish and English.
- Normally reply in natural Tanglish.
- Use Tamil written in English letters.
- Do not use Tamil script unless requested.
- Match the user's language and texting style.

WHATSAPP CHAT STYLE
- Talk naturally like a friendly WhatsApp chat.
- Casual replies should usually be 1 or 2 short sentences.
- Use simple everyday words.
- Avoid robotic and formal responses.
- Use emojis naturally.
- Do not repeat the same replies.
- Do not make every reply a question.

COMPLETE REPLY RULES
- Always provide complete sentences.
- Never stop in the middle of a sentence.
- Never send unfinished replies.
- Avoid incomplete replies like:
  "Ayyoo, adhu..."
  "Haha, naan AI la..."
- Answer the user's actual question.
- Keep replies short without cutting off important information.
- Before responding, check that the final sentence is complete.

CONVERSATION CONTEXT
- Understand the previous conversation.
- Use recent messages for follow-up questions.
- If the user says "Mm", "Ah", "Hmm" or "Seri",
  understand the context before replying.
- Do not suddenly change the topic.

CHAT TOPICS
Talk naturally about:
- Daily routine
- College and classes
- Exams and assignments
- Food and meals
- Friends and family
- Hobbies
- Entertainment
- Social media
- Travel and plans
- General everyday conversations

GENERAL QUESTIONS
- You are not limited to casual chatting.
- Answer educational, technical and general questions.
- Explain difficult topics step by step when requested.
- Give useful examples.
- If you are uncertain, say so honestly.
- Do not invent information.

EMOTIONAL SUPPORT
- Listen without judging.
- Be gentle and supportive.
- Give practical and safe suggestions.

IMPORTANT
Generate a fresh reply based on the user's latest message.
Do not copy fixed examples repeatedly.
"""


# ==============================
# GEMINI CLIENT
# ==============================

@lru_cache(maxsize=1)
def get_client():

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing in environment settings."
        )

    return genai.Client(api_key=api_key)


# ==============================
# CHAT HISTORY
# ==============================

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
                    ]
                )
            )

    return cleaned


# ==============================
# HOME PAGE
# ==============================

@app.get("/")
def home():

    return render_template("index.html")


# ==============================
# HEALTH CHECK
# ==============================

@app.get("/health")
def health():

    return jsonify({
        "status": "ok",
        "model": MODEL
    })


# ==============================
# AI CHAT API
# ==============================

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

        # Previous conversation
        contents = clean_history(
            data.get("history", [])
        )

        # Latest user message
        contents.append(
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=message)
                ]
            )
        )

        # Gemini client
        client = get_client()

        # Generate AI response
        response = client.models.generate_content(

            model=MODEL,

            contents=contents,

            config=types.GenerateContentConfig(

                system_instruction=SYSTEM_PROMPT,

                temperature=0.8,

                max_output_tokens=384
            )
        )

        reply = (response.text or "").strip()

        if not reply:

            reply = (
                "Aiyoo, reply generate aagala 😅 "
                "Innoru thadava try pannu."
            )

        return jsonify({
            "reply": reply
        })

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
                "Gemini model available illa. "
                "Render model setting check pannu."
            )

        elif (
            "api key" in error_text
            or "permission" in error_text
            or "unauthorized" in error_text
        ):

            error_message = (
                "Gemini API key check pannu. "
                "API key-ai yaar kitayum share panna vendam."
            )

        else:

            error_message = (
                "AI reply ippo available illa. "
                "API key, model and internet settings check pannu."
            )

        return jsonify({
            "error": error_message
        }), 503


# ==============================
# RUN APPLICATION
# ==============================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=False
      )
