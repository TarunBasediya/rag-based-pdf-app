const BASE_URL = "http://localhost:8000";

export async function uploadPdf(file) {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${BASE_URL}/upload-pdf`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Upload failed");
  }
  return res.json();
}

/**
 * Chat endpoint se NDJSON stream padhta hai.
 * Backend har line mein ek JSON event bhejta hai:
 *   {"type": "token", "content": "..."}
 *   {"type": "sources", "sources": [{"page": 1, "snippet": "..."}]}
 *   {"type": "error", "message": "..."}
 * onEvent har parsed event ke saath call hota hai.
 */
export async function streamMessage(message, threadId, onEvent) {
  const res = await fetch(`${BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, thread_id: threadId }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Something went wrong");
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  // Network chunk kisi JSON line ke beech mein toot sakta hai,
  // isliye adhuri line ko buffer mein rakhte hain
  let buffer = "";

  const handleLine = (line) => {
    if (!line.trim()) return;
    onEvent(JSON.parse(line));
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop(); // aakhri (shayad adhuri) line wapas buffer mein
    lines.forEach(handleLine);
  }

  // Decoder ke andar bacha hua koi byte flush karo, aur last line process karo
  buffer += decoder.decode();
  handleLine(buffer);
}
