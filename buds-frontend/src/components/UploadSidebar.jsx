import { useEffect, useState, useRef } from "react"
import { PanelLeft, Plus, FileText } from "lucide-react"
import { Button } from "@base-ui/react/button"

// This component is the left sidebar for managing uploaded PDFs.
// It lets the user:
// 1. upload a PDF file
// 2. see all files already uploaded
// 3. click a file to select it as the active document

export default function UploadSidebar({ activeDoc, onSelectDoc }) {
    // files = list of uploaded document names from the backend
    const [files, setFiles] = useState([])

    // isLoading tells us if we are waiting for the files from the server
    const [isLoading, setIsLoading] = useState(true)

    // This is a reference to the hidden file input element.
    // We use it to trigger the browser file picker programmatically.
    const fileInputRef = useRef(null)

    // isUploading is true while the PDF is being sent to the backend.
    const [isUploading, setIsUploading] = useState(false)

    // Runs once when the component first appears on the screen.
    // It fetches the existing uploaded files from the backend.
    useEffect(() => {
        fetchFiles()
    }, [])

    // Calls the backend endpoint /list_files and stores the returned filenames.
    const fetchFiles = async () => {
        try {
            setIsLoading(true)
            const res = await fetch("http://localhost:8000/list_files")
            const data = await res.json()

            // The server returns { files: [...] }
            // If it returns nothing, we default to an empty array.
            setFiles(data.files || [])
        } catch (err) {
            console.error("Failed to fetch files from backend:", err)
        } finally {
            setIsLoading(false)
        }
    }

    // Runs when the user picks a PDF from their computer.
    // It sends the file to the backend using a POST request.
    const handleFileChange = async (e) => {
        const selectedFile = e.target.files?.[0]
        if (!selectedFile) return

        try {
            setIsUploading(true)

            // FormData is used because we are uploading a file.
            const formData = new FormData()
            formData.append("file", selectedFile)

            const res = await fetch("http://localhost:8000/upload", {
                method: "POST",
                body: formData,
            })

            if (res.ok) {
                // After a successful upload, refresh the list of files.
                await fetchFiles()
            } else {
                alert("Failed to upload file")
            }
        } catch (err) {
            console.error("Upload error:", err)
        } finally {
            setIsUploading(false)

            // Clear the input so the same file can be selected again later.
            e.target.value = ""
        }
    }

    return (
        <div className="flex flex-col w-full h-full rounded-2xl bg-[#1F1F1F]" id="Upload Sidebar Container">

            {/* Top row: section title + small left-panel button */}
            <div className="w-full h-15 px-5 flex items-center justify-between" id="Title">
                <h2 className="text-gray-200"> Sources </h2>
                <Button variant="default" className=" h-8 w-8 flex items-center bg-[#1F1F1F] justify-center rounded-2xl  hover:bg-[#484848] transition-colors" >
                    <PanelLeft className="h-4 w-4 text-amber-50"/>
                </Button>
            </div>

            {/* Upload button area */}
            <div className="w-full h-10 my-5 px-5 flex items-center justify-center" id="Upload Button">
                <Button
                    variant="default"
                    // When clicked, trigger the hidden file input.
                    onClick={() => fileInputRef.current?.click()}
                    disabled={isUploading}
                    className="flex gap-2 rounded-2xl justify-center bg-[#0E0E0E] w-full h-full items-center cursor-pointer hover:bg-[#151515] transition-colors">
                    <Plus className="h-4 w-4 text-white"/>
                    <h2 className="text-gray-200"> {isUploading ? "Uploading..." : "Upload PDF files"} </h2>
                </Button>

                {/* Hidden input that opens the file picker */}
                <input
                    type="file"
                    accept=".pdf"
                    ref={fileInputRef}
                    onChange={handleFileChange}
                    className="hidden"
                />
            </div>

            {/* File list section */}
            <div className="mt-7 px-5 flex-1 overflow-y-auto">
                <h2 className="text-gray-400 font-medium text-sm"> Files </h2>

                {isLoading ? (
                    // Loading state while fetchFiles is working.
                    <p className="text-xs text-gray-500 my-2">Loading files...</p>
                ) : files.length === 0 ? (
                    // If no files exist, show an empty state.
                    <p className="text-xs text-gray-500 my-2">No documents found.</p>
                ) : (
                    // Show a clickable list of uploaded files.
                    <ul className="my-2 px-0.5 max-w-full flex flex-col gap-1.5 cursor-pointer">
                        {files.map((file, idx) => {
                            const isSelected = activeDoc === file

                            return (
                                <li
                                    key={idx}
                                    // Clicking a file tells the parent component which document is active.
                                    onClick={() => onSelectDoc && onSelectDoc(file)}
                                    className={`text-[14px] truncate flex items-center gap-2 px-2 py-1.5 rounded-lg transition-colors ${
                                        isSelected
                                            ? "text-blue-400 bg-blue-950/40 font-medium"
                                            : "text-gray-300 hover:text-white hover:bg-[#2A2A2A]"
                                    }`}
                                    title={file}
                                >
                                    <FileText className="h-4 w-4 shrink-0 text-blue-400" />
                                    <span className="truncate">{file}</span>
                                </li>
                            )
                        })}
                    </ul>
                )}
            </div>

        </div>
    )
}