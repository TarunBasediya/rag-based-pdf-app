import { useState, useRef, useEffect } from "react";
import { streamMessage } from "../api";

export default function Chat({ documentName }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [threadId] = useState(() => crypto.randomUUID());
  const bottomRef = useRef(null);

  useEffect(() => {
    // Streaming ke dauran instant scroll (smooth animations chunks par atak jaate hain)
    bottomRef.current?.scrollIntoView({
      behavior: loading ? "auto" : "smooth",
    });
  }, [messages, loading]);

  // Hamesha last message (current assistant bubble) ko update karta hai
  const updateLastMessage = (updater) => {
    setMessages((prev) => {
      const updated = [...prev];
      const lastIndex = updated.length - 1;
      updated[lastIndex] = updater(updated[lastIndex]);
      return updated;
    });
  };

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;

    setMessages((prev) => [
      ...prev,
      { role: "user", content: text },
      { role: "assistant", content: "", sources: [] },
    ]);
    setInput("");
    setLoading(true);

    try {
      await streamMessage(text, threadId, (event) => {
        if (event.type === "token") {
          updateLastMessage((m) => ({
            ...m,
            content: m.content + event.content,
          }));
        } else if (event.type === "sources") {
          updateLastMessage((m) => ({ ...m, sources: event.sources }));
        } else if (event.type === "error") {
          updateLastMessage((m) => ({
            ...m,
            content: m.content
              ? `${m.content}\n\n[Error: ${event.message}]`
              : `[Error: ${event.message}]`,
          }));
        }
      });
    } catch (err) {
      // Partial answer bacha ke rakho, error uske neeche jodo
      updateLastMessage((m) =>
        m.content
          ? {
              ...m,
              content: `${m.content}\n\n[Connection error: ${err.message}]`,
            }
          : { role: "error", content: err.message },
      );
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
            {m.content ||
              (loading && i === messages.length - 1 ? "Thinking..." : "")}

            {m.sources?.length > 0 && (
              <div
                style={{
                  marginTop: 8,
                  paddingTop: 8,
                  borderTop: "1px solid #cbd5e1",
                  fontSize: 13,
                  whiteSpace: "normal",
                }}
              >
                <strong>Sources</strong>
                {m.sources.map((s) => (
                  <details key={s.page} style={{ marginTop: 4 }}>
                    <summary style={{ cursor: "pointer" }}>
                      Page {s.page}
                    </summary>
                    <p style={{ margin: "4px 0 0 12px", color: "#475569" }}>
                      {s.snippet}...
                    </p>
                  </details>
                ))}
              </div>
            )}
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
