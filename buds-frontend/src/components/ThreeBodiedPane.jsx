import { useState } from "react";
import ChatbotPane from "./ChatbotPane";
import PDFFilereader from "./PDFFileReader";
import UploadSidebar from "./UploadSidebar";

// This is the main dashboard layout.
// It owns the selected file so all three panels can respond to it.
export default function ThreeBodiedPane() {
    // activeDoc keeps track of the file the user clicked in the sidebar.
    // null means no file is selected yet.
    const [activeDoc, setActiveDoc] = useState(null);

    // Called by UploadSidebar when the user chooses a document.
    // It updates the shared state in the parent and re-renders the app.
    const handleSelectDoc = (file) => {
        setActiveDoc(file);
    };

    return (
        <div className="w-full flex-1 min-h-0 pb-6 flex gap-8 flex-row" id="panels container">
            {/* Left panel: upload files and select an active document */}
            <div className="flex-1 h-full min-h-0">
                <UploadSidebar activeDoc={activeDoc} onSelectDoc={handleSelectDoc} />
            </div>

            {/* Middle panel: preview the selected PDF */}
            <div className="flex-2 h-full min-h-0">
                <PDFFilereader activeDoc={activeDoc} />
            </div>

            {/* Right panel: ask questions based on the chosen document */}
            <div className="flex-1 h-full min-h-0">
                <ChatbotPane activeDoc={activeDoc} />
            </div>
        </div>
    );
}