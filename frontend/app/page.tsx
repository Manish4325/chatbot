"use client";

import { useState } from "react";

type Message = {
  role: "user" | "assistant";
  content: string;
};

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");

  async function sendMessage() {
    if (!input.trim()) return;

    const newMessages: Message[] = [
  ...messages,
  { role: "user", content: input },
];
    setMessages(newMessages);
    setInput("");

    const response = await fetch(
  "https://chatbot-jo3e.onrender.com/chat",
  {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ message: input })
  }
);
    const reader = response.body?.getReader();
    const decoder = new TextDecoder();
    let assistantText = "";

    if (!reader) return;

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      assistantText += decoder.decode(value);
      setMessages([
        ...newMessages,
        { role: "assistant", content: assistantText },
      ]);
    }
  }
 
  return (
    <main style={{ maxWidth: 800, margin: "40px auto", fontFamily: "Arial" }}>
      {messages.map((m, i) => (
        <div key={i} style={{ marginBottom: 16 }}>
          <strong>{m.role === "user" ? "You" : "Assistant"}:</strong>
          <div>{m.content}</div>
        </div>
      ))}

      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && sendMessage()}
        placeholder="Ask anything..."
        style={{
          width: "100%",
          padding: 12,
          fontSize: 16,
          marginTop: 20,
        }}
      />
    </main>
  );
}
