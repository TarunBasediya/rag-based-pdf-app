import { useState } from "react";
import { uploadPdf } from "../api";

export default function UploadPdf({ onUploaded }) {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | uploading | success | error
  const [message, setMessage] = useState("");

  const handleUpload = async () => {
    if (!file) return;
    setStatus("uploading");
    setMessage("");

    try {
      const data = await uploadPdf(file);
      setStatus("success");
      setMessage(`${data.message} (${data.chunks_created} chunks created)`);
      onUploaded(file.name);
    } catch (err) {
      setStatus("error");
      setMessage(err.message);
    }
  };

  return (
    <div style={{ padding: 16, border: "1px solid #ccc", borderRadius: 8 }}>
      <h3>Upload your PDF</h3>
      <input
        type="file"
        accept="application/pdf"
        onChange={(e) => setFile(e.target.files[0])}
        disabled={status === "uploading"}
      />
      <button
        onClick={handleUpload}
        disabled={!file || status === "uploading"}
        style={{ marginLeft: 8 }}
      >
        {status === "uploading" ? "Processing..." : "Upload"}
      </button>

      {status === "uploading" && (
        <p>PDF ko chunk aur embed kiya ja raha hai, thoda time lagega...</p>
      )}
      {status === "success" && <p style={{ color: "green" }}>{message}</p>}
      {status === "error" && <p style={{ color: "red" }}>{message}</p>}
    </div>
  );
}
