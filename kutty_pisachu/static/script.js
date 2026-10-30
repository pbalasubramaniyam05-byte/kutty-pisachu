const chat = document.getElementById("chat");
const form = document.getElementById("chatForm");
const input = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");
const clearBtn = document.getElementById("clearBtn");

// Previous successful turns are kept while this page remains open.
let conversationHistory = [];

function currentTime() {
  return new Intl.DateTimeFormat([], { hour: "numeric", minute: "2-digit" }).format(new Date());
}

function scrollToBottom() {
  chat.scrollTop = chat.scrollHeight;
}

function addMessage(text, who = "bot") {
  const row = document.createElement("div");
  row.className = `message-row ${who}`;

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;

  const time = document.createElement("div");
  time.className = "message-time";
  time.textContent = currentTime();

  row.appendChild(bubble);
  row.appendChild(time);
  chat.appendChild(row);
  scrollToBottom();
  return row;
}

function showTyping() {
  const row = document.createElement("div");
  row.className = "message-row bot";
  row.id = "typingIndicator";
  const bubble = document.createElement("div");
  bubble.className = "bubble typing";
  bubble.textContent = "Kutty Pisachu is typing...";
  row.appendChild(bubble);
  chat.appendChild(row);
  scrollToBottom();
}

function removeTyping() {
  document.getElementById("typingIndicator")?.remove();
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (!message) return;

  addMessage(message, "user");
  input.value = "";
  input.focus();
  sendBtn.disabled = true;
  showTyping();

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        history: conversationHistory.slice(-12)
      })
    });

    const data = await response.json();
    removeTyping();

    if (!response.ok) {
      addMessage(data.error || "AI reply available illa. Again try pannu 😅", "bot");
      return;
    }

    const reply = data.reply || data.response || "Hmm, reply varala 😅";
    addMessage(reply, "bot");

    // Save only successful exchanges for context in the next request.
    conversationHistory.push(
      { role: "user", text: message },
      { role: "model", text: reply }
    );
    conversationHistory = conversationHistory.slice(-12);
  } catch (error) {
    removeTyping();
    addMessage("Internet connection check panni again try pannu macha 😅", "bot");
  } finally {
    sendBtn.disabled = false;
    input.focus();
  }
});

clearBtn.addEventListener("click", () => {
  conversationHistory = [];
  chat.replaceChildren();
  addMessage("Hlooo 😁 Sollu, enna panra?", "bot");
  input.focus();
});

addMessage("Hlooo 😁 Sollu, enna panra?", "bot");
