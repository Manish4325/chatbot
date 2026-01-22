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

    const userMessage: Message = {
      role: "user",
      content: input,
    };

    // 1️⃣ Add user message immediately
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      // 2️⃣ Call backend
      const res = await fetch(
        "https://chatbot-jo3e.onrender.com/chat",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ message: userMessage.content }),
        }
      );

      if (!res.ok) {
        throw new Error("Backend error");
      }

      // 3️⃣ Parse JSON response
      const data = await res.json();

      const assistantMessage: Message = {
        role: "assistant",
        content: data.response,
      };

      // 4️⃣ Add assistant message
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "❌ Error contacting server.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main style={{ maxWidth: 800, margin: "40px auto", padding: 20 }}>
      {messages.map((msg, i) => (
        <div key={i} style={{ marginBottom: 12 }}>
          <b>{msg.role === "user" ? "You" : "Assistant"}:</b>
          <div>{msg.content}</div>
        </div>
      ))}

      {loading && <div><i>Assistant is typing...</i></div>}

      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && sendMessage()}
        placeholder="Ask anything..."
        style={{
          width: "100%",
          padding: 12,
          marginTop: 20,
          border: "2px solid black",
        }}
      />
    </main>
  );
}
