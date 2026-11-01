const chat = document.getElementById("chat");
const form = document.getElementById("chatForm");
const input = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");
const clearBtn = document.getElementById("clearBtn");

// Store recent conversation for context
let conversationHistory = [];

const MAX_HISTORY = 16;

function currentTime() {
  return new Intl.DateTimeFormat([], {
    hour: "numeric",
    minute: "2-digit"
  }).format(new Date());
}

function scrollToBottom() {
  chat.scrollTop = chat.scrollHeight;
}

function addMessage(text, who = "bot") {
  const row = document.createElement("div");
  row.className = `message-row ${who}`;

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = String(text);

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
  bubble.textContent = "Typing...";

  row.appendChild(bubble);
  chat.appendChild(row);

  scrollToBottom();
}

function removeTyping() {
  document.getElementById("typingIndicator")?.remove();
}

function saveConversation(userMessage, botReply) {
  conversationHistory.push(
    { role: "user", text: userMessage },
    { role: "model", text: botReply }
  );

  conversationHistory =
    conversationHistory.slice(-MAX_HISTORY);
}

async function sendMessage(message) {
  const response = await fetch("/api/chat", {
    method: "POST",

    headers: {
      "Content-Type": "application/json"
    },

    body: JSON.stringify({
      message: message,
      history: conversationHistory.slice(-MAX_HISTORY)
    })
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data.error || "Message send aagala. Again try pannu 😅"
    );
  }

  const reply = data.reply || data.response;

  if (typeof reply !== "string" || !reply.trim()) {
    throw new Error("Reply varala da 😅 Innoru thadava try pannu.");
  }

  return reply.trim();
}

// Send message
form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const message = input.value.trim();

  if (!message || sendBtn.disabled) return;

  addMessage(message, "user");

  input.value = "";
  sendBtn.disabled = true;

  showTyping();

  try {
    const reply = await sendMessage(message);

    removeTyping();

    // Display the complete response received from backend
    addMessage(reply, "bot");

    // Save successful conversation for future context
    saveConversation(message, reply);

  } catch (error) {
    removeTyping();

    addMessage(
      error.message || "Internet connection check pannu 😅",
      "bot"
    );

  } finally {
    sendBtn.disabled = false;
    input.focus();
  }
});

// Clear conversation
clearBtn.addEventListener("click", () => {
  conversationHistory = [];

  chat.replaceChildren();

  addMessage(
    "Hlooo 😁 Sollu, enna panra?",
    "bot"
  );

  input.focus();
});

// Initial greeting
addMessage(
  "Hlooo 😁 Sollu, enna panra?",
  "bot"
);
