"use client";

import { useState } from "react";

export default function Home() {
  const [messages, setMessages] = useState<any[]>([]);
  const [input, setInput] = useState("");

  async function send() {
    const userMsg = { role: "user", content: input };
    setMessages(prev => [...prev, userMsg]);

    const res = await fetch("https://chatbot-jo3e.onrender.com", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt: input,
        messages
      })
    });

    const reader = res.body!.getReader();
    let text = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      text += new TextDecoder().decode(value);
      setMessages(prev => [
        ...prev.slice(0, -1),
        { role: "assistant", content: text }
      ]);
    }

    setInput("");
  }

  return (
    <main style={{ maxWidth: 800, margin: "auto", padding: 24 }}>
      {messages.map((m, i) => (
        <div key={i} style={{ marginBottom: 12 }}>
          <b>{m.role === "user" ? "You" : "Assistant"}:</b>
          <div>{m.content}</div>
        </div>
      ))}

      <input
        value={input}
        onChange={e => setInput(e.target.value)}
        onKeyDown={e => e.key === "Enter" && send()}
        placeholder="Ask anything..."
        style={{ width: "100%", padding: 12 }}
      />
    </main>
  );
}
