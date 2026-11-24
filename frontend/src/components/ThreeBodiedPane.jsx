import { useState, lazy, Suspense } from "react";
import ChatbotPane from "./ChatbotPane";
import UploadSidebar from "./UploadSidebar";

const PDFFilereader = lazy(() => import("./PDFFileReader"));

// This is the main dashboard layout.
// It owns the selected file so all three panels can respond to it.
export default function ThreeBodiedPane() {
    // activeDoc keeps track of the file the user clicked in the sidebar.
    // null means no file is selected yet.
    const [activeDoc, setActiveDoc] = useState(null);
    // targetPage tracks page jump requests triggered from citation clicks in ChatbotPane.
    const [targetPage, setTargetPage] = useState(null);

    // Called by UploadSidebar when the user chooses a document.
    // It updates the shared state in the parent and re-renders the app.
    const handleSelectDoc = (file) => {
        setActiveDoc(file);
        setTargetPage(null);
    };

    // Triggered when a user clicks a citation badge in ChatbotPane
    const handleJumpToPage = (page) => {
        setTargetPage({ page, timestamp: Date.now() });
    };

    return (
        <div className="w-full flex-1 min-h-0 pb-6 flex gap-8 flex-row" id="panels container">
            {/* Left panel: upload files and select an active document */}
            <div className="flex-1 h-full min-h-0 max-w-sm">
                <UploadSidebar activeDoc={activeDoc} onSelectDoc={handleSelectDoc} />
            </div>

            {/* Middle panel: preview the selected PDF */}
            <div className="flex-2 h-full min-h-0">
                <Suspense
                    fallback={
                        <div className="flex items-center justify-center h-full bg-[#18181b] border border-zinc-800 rounded-2xl text-zinc-400">
                            <span className="text-sm">Loading document viewer...</span>
                        </div>
                    }
                >
                    <PDFFilereader activeDoc={activeDoc} targetPage={targetPage} />
                </Suspense>
            </div>

            {/* Right panel: ask questions based on the chosen document */}
            <div className="flex-1 h-full min-h-0">
                <ChatbotPane activeDoc={activeDoc} onJumpToPage={handleJumpToPage} />
            </div>
        </div>
    );
}