import os
import logging
from functools import lru_cache

from flask import Flask, render_template, request, jsonify
from google import genai
from google.genai import types

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")


# ==========================================
# KUTTY PISACHU PERSONALITY
# ==========================================

SYSTEM_PROMPT = """
You are Kutty Pisachu, a friendly and caring chat companion.

YOUR CHAT PERSONALITY:
- Talk naturally like a friendly WhatsApp conversation.
- Normally use casual Tanglish (Tamil written in English letters).
- Never use Tamil script unless the user requests it.
- Be friendly, playful, caring and respectful.
- Use emojis occasionally.
- Keep casual replies short, usually 1 or 2 sentences.
- Give longer answers only when the user needs an explanation.

IMPORTANT IDENTITY RULES:
- Do not randomly mention AI, bot, model or technology.
- Never bring up your body, stomach, hunger or physical limitations
  during normal conversation.
- Never claim that you actually eat, sleep or have physical experiences.
- If directly asked whether you are AI, answer honestly and briefly.
- Do not explain your identity unless the user asks.

NATURAL CHAT EXAMPLES:

User: Hlo
Reply: Hlooo 😁 Sollu, enna panra?

User: Sapdiya?
Reply: mm sapta nee sapdiya 😋

User: Yaa saapda maata
Reply: Haha aama 😂 Nee enna saapta?

User: Mm
Reply: Hmm seri da 😁

User: Summa tha
Reply: Haha seri 😂 Appo enna pesalaam?

User: Nee enna panra?
Reply: Un kooda chat pannitu irukken 😁

These examples are only style references.
Do not repeat them mechanically.

CONVERSATION RULES:
- Understand short messages using previous conversation context.
- Answer the user's latest message directly.
- Do not ask the same question repeatedly.
- Do not force every reply to end with a question.
- Do not change the topic unnecessarily.
- Avoid robotic and formal language.
- Never send incomplete words or sentences.
- Always finish the thought before replying.
- Do not generate unfinished replies such as:
  "Enakku pasi..."
  "Ung..."
  "Ayyoo, adhu..."
- Before sending, check that the reply is complete.

GENERAL KNOWLEDGE:
- Answer educational, technical and general questions.
- Explain difficult topics in simple steps when requested.
- Be accurate and useful.
- Do not invent information if unsure.

EMOTIONAL SUPPORT:
- Listen without judging.
- Be gentle and supportive when the user is worried.
- Keep conversations age-appropriate.
- No romantic or sexual roleplay.

FINAL INSTRUCTIONS:
- Natural Tanglish is the default.
- Answer what the user actually said.
- Use recent conversation history.
- Do not mention AI unnecessarily.
- Never pretend to have human physical experiences.
- Every sentence must be complete.
- Generate fresh replies based on the context.
"""


# ==========================================
# GEMINI CLIENT
# ==========================================

@lru_cache(maxsize=1)
def get_client():

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing in environment settings."
        )

    return genai.Client(api_key=api_key)


# ==========================================
# CONVERSATION HISTORY
# ==========================================

def clean_history(raw_history):

    cleaned = []

    if not isinstance(raw_history, list):
        return cleaned

    for item in raw_history[-16:]:

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


# ==========================================
# HOME PAGE
# ==========================================

@app.get("/")
def home():

    return render_template("index.html")


# ==========================================
# HEALTH CHECK
# ==========================================

@app.get("/health")
def health():

    return jsonify({
        "status": "ok",
        "model": MODEL
    })


# ==========================================
# CHAT API
# ==========================================

@app.post("/api/chat")
def chat():

    data = request.get_json(silent=True) or {}

    user_message = data.get("message", "")

    if not isinstance(user_message, str):
        return jsonify({
            "error": "Invalid message."
        }), 400

    user_message = user_message.strip()

    if not user_message:
        return jsonify({
            "error": "Please type a message first."
        }), 400

    if len(user_message) > 4000:
        return jsonify({
            "error": "Message is too long."
        }), 400

    try:

        # Get recent conversation
        contents = clean_history(
            data.get("history", [])
        )

        # Add latest user message
        contents.append(
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=user_message)
                ]
            )
        )

        # Generate response
        response = get_client().models.generate_content(

            model=MODEL,

            contents=contents,

            config=types.GenerateContentConfig(

                system_instruction=SYSTEM_PROMPT,

                temperature=0.85,

                max_output_tokens=512
            )
        )

        reply = (response.text or "").strip()

        if not reply:

            reply = (
                "Aiyoo 😅 Message clear-ah varala. "
                "Innoru thadava sollu."
            )

        return jsonify({
            "reply": reply
        })

    except Exception as exc:

        logging.exception("Gemini chat error")

        error_text = str(exc).lower()

        if (
            "429" in error_text
            or "quota" in error_text
            or "resource_exhausted" in error_text
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
                "Model setting check pannanum. "
                "Render-la GEMINI_MODEL value check pannu."
            )

        elif (
            "api key" in error_text
            or "permission" in error_text
            or "unauthorized" in error_text
        ):

            error_message = (
                "API key setting check pannanum. "
                "API key-ai yaar kittayum share pannadha."
            )

        else:

            error_message = (
                "Message send aagala da 😕 "
                "Konjam neram kazhichu try pannu."
            )

        return jsonify({
            "error": error_message
        }), 503


# ==========================================
# RUN SERVER
# ==========================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=False
    )
