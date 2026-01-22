"use client";

import { useState } from "react";

type Message = {
  role: "user" | "assistant";
  content: string;
};

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage: Message = { role: "user", content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    const response = await fetch(
  "https://chatbot-jo3e.onrender.com/chat",
  {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ message: userMessage.content }),
  }
);


    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    let assistantText = "";
    setMessages(prev => [...prev, { role: "assistant", content: "" }]);

    while (true) {
      const { value, done } = await reader!.read();
      if (done) break;

      assistantText += decoder.decode(value);
      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: "assistant",
          content: assistantText,
        };
        return updated;
      });
    }

    setLoading(false);
  };

  const toggleDark = () => {
    document.documentElement.classList.toggle("dark");
  };

  return (
    <main className="container">
      <header>
        <h1>Chatbot</h1>
        <button onClick={toggleDark}>🌙 Dark Mode</button>
      </header>

      <div className="chat">
        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.role}`}>
            {msg.content}
          </div>
        ))}
      </div>

      <div className="input-box">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Ask anything..."
          onKeyDown={e => e.key === "Enter" && sendMessage()}
        />
        <button onClick={sendMessage} disabled={loading}>
          Send
        </button>
      </div>
    </main>
  );
}
