let ticketName = null;
let locked = false;

window.onload = () => {
  const sendBtn = document.getElementById("sendButton");
  const messageInput = document.getElementById("message");
  const emailInput = document.getElementById("emailInput");

  if (sendBtn) {
    sendBtn.addEventListener("click", sendMessage);
  }

  if (messageInput) {
    messageInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
      }
    });
  }

  if (emailInput) {
    emailInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        submitEscalation();
      }
    });
  }
};

window.addEventListener("DOMContentLoaded", () => {
  if (localStorage.getItem("ticket_name")) {
    document.getElementById("emailPrompt").style.display = "none";
  }
});


async function sendMessage() {
  if (locked) return;

  const input = document.getElementById("message");
  const chatBox = document.getElementById("chat");
  const text = input.value.trim();
  input.value = "";

  if (!text) return;

  chatBox.innerHTML += `<div class="message user-message">${text}</div>`;

  locked = true;

  const payload = {
    question: text,
    ticket_name: ticketName
  };

  const res = await fetch("/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ticket_name: ticketName, question: text })
  });

  if (ticketName) {
    // const emailInput = document.getElementById("emailInput");
    const email = emailInput.value.trim();

    if (!email || !email.includes("@")) {
        chatBox.innerHTML += `<div class="info email-error"><b>Please enter a valid email address.</b></div>`;
        locked = false;
        return;
    };

    payload.email = email;
  };

  const data = await res.json();

  chatBox.innerHTML += `<div class="message bot-message"><b>Bot:</b> ${data.answer}</div>`;

  if (data.send) {
    document.getElementById("emailPrompt").style.display = "flex";
    document.getElementById("emailPrompt").scrollIntoView({ behavior: "smooth", block: "center" });
  }

  locked = false;
}


async function submitEscalation() {
  const email = document.getElementById("emailInput").value.trim();
  if (!email || !email.includes("@")) {
    alert("Please enter a valid email.");
    return;
  }

  document.getElementById("emailPrompt").style.display = "none";
  const chatBox = document.getElementById("chat");
  chatBox.innerHTML += `<div class="info email-sent"><b>You will receive an email soon regarding your question. Thank you</b></div>`;

  const res = await fetch("/escalate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: email })
  });

  const data = await res.json();
  ticketName = data.ticket_name;
  localStorage.setItem("ticket_name", ticketName);
  localStorage.setItem("user_email", email);
}
