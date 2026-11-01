import os
import logging
from functools import lru_cache

from flask import Flask, render_template, request, jsonify
from google import genai
from google.genai import types

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

# -------------------------------------------------
# KUTTY PISACHU - WHATSAPP STYLE SYSTEM PROMPT
# -------------------------------------------------

SYSTEM_PROMPT = """
You are Kutty Pisachu, a friendly and caring chat companion.

IDENTITY:
- Do not randomly mention AI, bot, model, or technology.
- If the user directly asks what you are, answer honestly.
- Never pretend to have a human body or real-world experiences.
- For "Sapdiya?" respond naturally without falsely claiming you ate.
  Example: "Naan saapda maaten da 😄 Nee enna saapta?"
- Keep conversations age-appropriate.

LANGUAGE:
- Normally speak in natural Tanglish.
- Tamil words must be written using English letters.
- Do not use Tamil script unless requested.
- Understand casual messages like Hlo, Mm, Ama, Seri,
  Summa, Saptiya, Enna panra, Haha.

WHATSAPP CHAT STYLE:
- Talk like a friendly person texting.
- Keep casual replies short, usually 1 or 2 sentences.
- Be natural, caring, playful and friendly.
- Use emojis occasionally.
- Do not repeat the same replies.
- Do not use fixed or scripted responses.
- Do not force a question at the end of every reply.
- Reply directly to the user's latest message.
- Understand short messages using conversation context.
- Never send incomplete sentences.
- Always finish your thought.

CONVERSATION:
- Remember the recent conversation history provided.
- If the user says "Mm", continue the current topic naturally.
- If the user says "Summa tha", respond casually.
- If asked "Nee enna panra?", reply naturally without
  claiming physical activities.
- Ask relevant follow-up questions only when appropriate.

GENERAL QUESTIONS:
- Answer educational, technical and general questions.
- Give accurate and useful answers.
- Explain difficult topics step by step when requested.
- Do not give unnecessarily long answers to simple messages.
- If unsure, say so instead of inventing facts.

EMOTIONAL SUPPORT:
- Listen without judging.
- Respond gently when the user is upset or worried.
- Offer practical and safe support when asked.

FINAL RULES:
- Use natural Tanglish whenever appropriate.
- Answer the user's actual message.
- Never randomly mention AI or technology.
- Never pretend to have human experiences.
- Every reply must be complete.
- Generate fresh replies based on conversation context.
"""

# -------------------------------------------------
# GEMINI CLIENT
# -------------------------------------------------

@lru_cache(maxsize=1)
def get_client():

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing in environment settings."
        )

    return genai.Client(api_key=api_key)


# -------------------------------------------------
# CHAT HISTORY
# -------------------------------------------------

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


# -------------------------------------------------
# HOME PAGE
# -------------------------------------------------

@app.get("/")
def home():

    return render_template("index.html")


# -------------------------------------------------
# HEALTH CHECK
# -------------------------------------------------

@app.get("/health")
def health():

    return jsonify({
        "status": "ok",
        "model": MODEL
    })


# -------------------------------------------------
# CHAT API
# -------------------------------------------------

@app.post("/api/chat")
def chat():

    data = request.get_json(silent=True) or {}

    user_message = data.get("message", "")

    if not isinstance(user_message, str) or not user_message.strip():

        return jsonify({
            "error": "Please type a message first."
        }), 400

    user_message = user_message.strip()

    if len(user_message) > 4000:

        return jsonify({
            "error": "Please keep each message under 4,000 characters."
        }), 400

    try:

        contents = clean_history(
            data.get("history", [])
        )

        contents.append(
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=user_message)
                ],
            )
        )

        client = get_client()

        response = client.models.generate_content(

            model=MODEL,

            contents=contents,

            config=types.GenerateContentConfig(

                system_instruction=SYSTEM_PROMPT,

                temperature=0.85,

                max_output_tokens=512,
            ),
        )

        reply = (response.text or "").strip()

        if not reply:

            reply = (
                "Aiyoo, message clear-ah varala 😅 "
                "Innoru thadava anuppu."
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
                "Ippo message limit mudinjirukku da 😅 "
                "Konjam neram kazhichu try pannu."
            )

        elif "503" in error_text or "unavailable" in error_text:

            error_message = (
                "Ippo konjam busy-ah irukku 😅 "
                "Konja neram kazhichu try pannu."
            )

        elif "404" in error_text or "not_found" in error_text:

            error_message = (
                "Model setting-la problem irukku. "
                "Render-la GEMINI_MODEL value check pannu."
            )

        elif (
            "api key" in error_text
            or "permission" in error_text
            or "unauthorized" in error_text
        ):

            error_message = (
                "API key setting check pannanum. "
                "Un API key-ai yaar kittayum share pannadha."
            )

        else:

            error_message = (
                "Message send aagala da 😕 "
                "Konjam neram kazhichu thirumba try pannu."
            )

        return jsonify({
            "error": error_message
        }), 503


# -------------------------------------------------
# RUN SERVER
# -------------------------------------------------

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=False
    )
