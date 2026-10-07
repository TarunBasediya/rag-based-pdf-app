import { useState } from "react";
import UploadPdf from "./components/UploadPdf";
import Chat from "./components/Chat";

export default function App() {
  const [uploadedFileName, setUploadedFileName] = useState(null);

  return (
    <div
      style={{ maxWidth: 700, margin: "40px auto", fontFamily: "sans-serif" }}
    >
      <h1>PDF Chat Assistant</h1>
      <UploadPdf onUploaded={setUploadedFileName} />

      {uploadedFileName && (
        <Chat key={uploadedFileName} documentName={uploadedFileName} />
      )}
    </div>
  );
}
