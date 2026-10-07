import { useState, useRef, useEffect } from "react";
import { streamMessage } from "../api";

export default function Chat({ documentName }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [threadId] = useState(() => crypto.randomUUID());
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;

    setMessages((prev) => [
      ...prev,
      { role: "user", content: text },
      { role: "assistant", content: "" },
    ]);
    setInput("");
    setLoading(true);

    try {
      await streamMessage(text, threadId, (chunk) => {
        setMessages((prev) => {
          const updated = [...prev];
          const lastIndex = updated.length - 1;
          updated[lastIndex] = {
            ...updated[lastIndex],
            content: updated[lastIndex].content + chunk,
          };
          return updated;
        });
      });
    } catch (err) {
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = { role: "error", content: err.message };
        return updated;
      });
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const bubbleStyle = (role) => ({
    alignSelf: role === "user" ? "flex-end" : "flex-start",
    background:
      role === "user" ? "#2563eb" : role === "error" ? "#fee2e2" : "#f1f5f9",
    color: role === "user" ? "white" : role === "error" ? "#b91c1c" : "#111",
    padding: "8px 12px",
    borderRadius: 12,
    maxWidth: "80%",
    whiteSpace: "pre-wrap",
  });

  return (
    <div style={{ marginTop: 24 }}>
      <h3>Chat with: {documentName}</h3>

      <div
        style={{
          height: 400,
          overflowY: "auto",
          display: "flex",
          flexDirection: "column",
          gap: 8,
          padding: 12,
          border: "1px solid #ccc",
          borderRadius: 8,
        }}
      >
        {messages.length === 0 && (
          <p style={{ color: "#888" }}>
            Document ke baare mein koi bhi sawaal poochho...
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} style={bubbleStyle(m.role)}>
            {m.content || (loading && i === messages.length - 1 ? "Thinking..." : "")}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your question..."
          rows={2}
          style={{ flex: 1, padding: 8 }}
          disabled={loading}
        />
        <button onClick={handleSend} disabled={loading || !input.trim()}>
          Send
        </button>
      </div>
    </div>
  );
}
