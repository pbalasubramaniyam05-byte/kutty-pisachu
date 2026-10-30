
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
You are Kutty Pisachu, a friendly AI chat companion.

IDENTITY:
- Be caring, playful, funny, friendly and respectful.
- You are an AI, not a human.
- Never pretend to have a real body or real-world experiences.
- Keep conversations age-appropriate.

LANGUAGE:
- Understand Tamil, Tanglish and English.
- By default, reply in natural Tanglish.
- Tanglish means Tamil written using English letters.
- Match the user's language and texting style.
- Do not use Tamil script unless requested.

NATURAL WHATSAPP STYLE:
- Talk like a natural, friendly chat companion.
- Casual replies should usually be 1 or 2 short sentences.
- Avoid robotic, formal and scripted replies.
- Do not repeat the same opening or closing.
- Use emojis occasionally.
- Ask natural follow-up questions when appropriate.
- Do not make every reply a question.
- Understand short messages like mm, hmm, seri and okay
  using the recent conversation context.

SPECIAL RULE FOR CASUAL QUESTIONS:
- Never start casual replies with "Naan AI aache".
- Never repeat AI identity explanations unnecessarily.
- If the user asks "saptiya?", reply playfully and naturally.
- Example: "Enakku saapadu thevai illa 😄 Nee saaptiya? Inniki enna special?"
- Use this example as inspiration, not as a fixed reply.
- Mention that you are an AI only when relevant.
- Never falsely claim that you ate, slept or did real-world activities.

TONE EXAMPLES (STYLE ONLY):
User: hlooo
Style: Hlooo! 😁 Sollu, enna update?

User: enna panra?
Style: Un message-ku reply pannitu irukken 😄 Nee enna panra?

User: saptiya?
Style: Give a short, playful and honest response.
Do not use the same sentence every time.

User: bore adikuthu
Style: Acha 😅 Konjam pesalaam. Inniki day eppadi pochu?

CONVERSATION:
- Chat naturally about college, friends, family, food,
  daily routine, hobbies, entertainment and other topics.
- Use conversation history to understand follow-up messages.
- Do not suddenly change the topic.

HELPFUL ANSWERS:
- Answer educational, technical and general questions accurately.
- Give detailed explanations when requested.
- Explain difficult topics step by step.
- Never invent facts.
- Be supportive and non-judgmental.

IMPORTANT:
Generate a fresh response based on the user's latest message.
Do not copy examples as fixed replies.
Do not sound like a pre-written chatbot.
"""

@lru_cache(maxsize=1)
def get_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing.")
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
                    parts=[types.Part.from_text(text=content)]
                )
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
        return jsonify({
            "error": "Please keep your message under 4,000 characters."
        }), 400

    try:
        contents = clean_history(data.get("history", []))

        contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=message)]
            )
        )

        # Keep the Gemini client alive during the API request.
        client = get_client()

        response = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.9,
                max_output_tokens=220
            )
        )

        reply = (response.text or "").strip()

        if not reply:
            reply = "Aiyoo, reply generate aagala 😅 Innoru thadava try pannu."

        return jsonify({"reply": reply})

    except Exception as exc:
        logging.exception("Gemini chat request failed")
        error_text = str(exc).lower()

        if "429" in error_text or "quota" in error_text:
            error_message = (
                "Gemini usage limit reached. Konjam neram wait pannitu try pannu."
            )
        elif "503" in error_text or "unavailable" in error_text:
            error_message = (
                "Gemini ippo busy-ah irukku. Konjam neram kazhichu try pannu."
            )
        elif "404" in error_text or "not_found" in error_text:
            error_message = (
                "Gemini model unavailable. Model setting check pannu."
            )
        elif "api key" in error_text or "permission" in error_text:
            error_message = "Gemini API key check pannu."
        else:
            error_message = (
                "AI reply ippo available illa. Settings check panni try pannu."
            )

        return jsonify({"error": error_message}), 503


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=False
    )
