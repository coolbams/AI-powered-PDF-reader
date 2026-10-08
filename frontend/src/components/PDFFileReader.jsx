import { useEffect, useRef, useState } from "react"
import { ToggleGroup, ToggleGroupItem } from "./ui/toggle-group"
import { FileText, Form, ChevronLeft, ChevronRight, ZoomIn, ZoomOut } from "lucide-react"
import { Button } from "@base-ui/react/button"
import { Document, Page, pdfjs } from "react-pdf"
import "react-pdf/dist/Page/AnnotationLayer.css"
import "react-pdf/dist/Page/TextLayer.css"

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
    "pdfjs-dist/build/pdf.worker.min.mjs",
    import.meta.url,
).toString()

// This component shows the selected document in the middle panel.
// It receives the active document name and targetPage as props from the parent.
export default function PDFFilereader({ activeDoc, targetPage }) {
    const [viewMode, setViewMode] = useState("pdf")
    const [numPages, setNumPages] = useState(0)
    const [pageNumber, setPageNumber] = useState(1)
    const [pageWidth, setPageWidth] = useState(0)
    const [scale, setScale] = useState(1.0)
    const [loadError, setLoadError] = useState("")
    const viewerRef = useRef(null)

    // Reset page and scale whenever a new document is selected
    useEffect(() => {
        setPageNumber(1)
        setScale(1.0)
    }, [activeDoc])

    // Jump to page when a citation badge is clicked in ChatbotPane
    useEffect(() => {
        if (targetPage) {
            const pageNum = typeof targetPage === "object" ? targetPage.page : targetPage
            if (pageNum && pageNum >= 1 && (numPages === 0 || pageNum <= numPages)) {
                setPageNumber(pageNum)
                setViewMode("pdf")
            }
        }
    }, [targetPage, numPages])

    // Measure the viewer so page fits available width
    useEffect(() => {
        const viewer = viewerRef.current
        if (!viewer) return

        const observer = new ResizeObserver(([entry]) => {
            setPageWidth(Math.max(0, Math.floor(entry.contentRect.width - 32)))
        })
        observer.observe(viewer)

        return () => observer.disconnect()
    }, [])

    // Keyboard arrow keys navigation
    useEffect(() => {
        const handleKeyDown = (e) => {
            if (e.key === "ArrowLeft") {
                setPageNumber((prev) => Math.max(1, prev - 1))
            } else if (e.key === "ArrowRight") {
                setPageNumber((prev) => (numPages ? Math.min(numPages, prev + 1) : prev + 1))
            }
        }
        window.addEventListener("keydown", handleKeyDown)
        return () => window.removeEventListener("keydown", handleKeyDown)
    }, [numPages])

    const fileUrl = activeDoc ? `http://localhost:8000/files/${encodeURIComponent(activeDoc)}` : null

    const prevPage = () => setPageNumber((p) => Math.max(1, p - 1))
    const nextPage = () => setPageNumber((p) => (numPages ? Math.min(numPages, p + 1) : p + 1))
    const zoomIn = () => setScale((s) => Math.min(2.0, +(s + 0.15).toFixed(2)))
    const zoomOut = () => setScale((s) => Math.max(0.6, +(s - 0.15).toFixed(2)))

    return (
        <div className="flex flex-col w-full h-full rounded-2xl bg-[#1F1F1F] overflow-hidden min-h-0" id="PDFFileReader Container">

            {/* Unified Top Control Sub-Bar */}
            <div className="w-full h-11 px-4 border-b border-zinc-800/80 bg-[#161616] flex items-center justify-between text-xs text-gray-300 select-none shrink-0" id="Sub-Bar">
                {/* Left: Page Navigation */}
                <div className="flex items-center gap-1.5 min-w-[170px]">
                    {activeDoc && viewMode === "pdf" && (
                        <>
                            <Button
                                onClick={prevPage}
                                disabled={pageNumber <= 1}
                                className="h-7 w-7 flex items-center justify-center rounded-lg bg-[#222222] hover:bg-[#333333] disabled:opacity-30 disabled:cursor-not-allowed transition-colors cursor-pointer"
                                title="Previous page (Left arrow)"
                            >
                                <ChevronLeft className="h-4 w-4" />
                            </Button>

                            <span className="px-2 font-mono text-gray-300">
                                Page <span className="text-white font-semibold">{pageNumber}</span> of{" "}
                                <span className="text-white font-semibold">{numPages || "..."}</span>
                            </span>

                            <Button
                                onClick={nextPage}
                                disabled={numPages > 0 && pageNumber >= numPages}
                                className="h-7 w-7 flex items-center justify-center rounded-lg bg-[#222222] hover:bg-[#333333] disabled:opacity-30 disabled:cursor-not-allowed transition-colors cursor-pointer"
                                title="Next page (Right arrow)"
                            >
                                <ChevronRight className="h-4 w-4" />
                            </Button>
                        </>
                    )}
                </div>

                {/* Center: Zoom Controls */}
                <div className="flex items-center gap-1.5">
                    {activeDoc && viewMode === "pdf" && (
                        <>
                            <Button
                                onClick={zoomOut}
                                disabled={scale <= 0.6}
                                className="h-7 w-7 flex items-center justify-center rounded-lg bg-[#222222] hover:bg-[#333333] disabled:opacity-30 disabled:cursor-not-allowed transition-colors cursor-pointer"
                                title="Zoom out"
                            >
                                <ZoomOut className="h-3.5 w-3.5" />
                            </Button>

                            <span className="w-12 text-center font-mono text-[11px] text-gray-400">
                                {Math.round(scale * 100)}%
                            </span>

                            <Button
                                onClick={zoomIn}
                                disabled={scale >= 2.0}
                                className="h-7 w-7 flex items-center justify-center rounded-lg bg-[#222222] hover:bg-[#333333] disabled:opacity-30 disabled:cursor-not-allowed transition-colors cursor-pointer"
                                title="Zoom in"
                            >
                                <ZoomIn className="h-3.5 w-3.5" />
                            </Button>
                        </>
                    )}
                </div>

                {/* Right: View Mode Toggle (PDF / Markdown) */}
                <div className="flex items-center">
                    <ToggleGroup
                        value={[viewMode]}
                        onValueChange={(val) => {
                            const selected = Array.isArray(val) ? val[val.length - 1] : val
                            if (selected) setViewMode(selected)
                        }}
                        variant="default"
                    >
                        <ToggleGroupItem 
                            value="pdf" 
                            aria-label="Toggle pdf" 
                            className="text-white data-pressed:bg-[#484848] data-[state=on]:bg-[#484848] aria-pressed:bg-[#484848] hover:bg-[#282828] hover:text-white transition-colors rounded-lg px-2.5 py-1 text-xs"
                        >
                            <FileText className="h-3.5 w-3.5 mr-1" />
                            PDF
                        </ToggleGroupItem>
                        <ToggleGroupItem 
                            value="markdown" 
                            aria-label="Toggle markdown" 
                            className="text-white data-pressed:bg-[#484848] data-[state=on]:bg-[#484848] aria-pressed:bg-[#484848] hover:bg-[#282828] hover:text-white transition-colors rounded-lg px-2.5 py-1 text-xs"
                        >
                            <Form className="h-3.5 w-3.5 mr-1" />
                            Markdown
                        </ToggleGroupItem>
                    </ToggleGroup>
                </div>
            </div>

            {/* Main Viewer Area (Full Container) */}
            <div ref={viewerRef} className="flex-1 w-full overflow-y-auto py-4 flex justify-center items-start min-h-0" id="pdf container / viewer">
                {!activeDoc ? (
                    // No document selected yet
                    <div className="flex flex-col items-center justify-center text-gray-500 gap-2 h-full my-auto">
                        <FileText className="h-10 w-10 text-gray-600 stroke-[1.5]" />
                        <p className="text-sm">Select a document from the sidebar to view it</p>
                    </div>
                ) : viewMode === "pdf" ? (
                    // Full-container PDF canvas view
                    <Document
                        key={activeDoc}
                        file={fileUrl}
                        onLoadSuccess={({ numPages }) => {
                            setNumPages(numPages)
                            setLoadError("")
                        }}
                        onLoadError={(error) => setLoadError(error.message)}
                        loading={<p className="text-sm text-gray-400 my-8">Loading PDF...</p>}
                        error={<p className="text-sm text-red-400 my-8">{loadError || "Could not load this PDF."}</p>}
                        className="flex flex-col items-center"
                    >
                        {pageWidth > 0 && (
                            <Page
                                key={`page_${pageNumber}`}
                                pageNumber={pageNumber}
                                width={Math.floor(pageWidth * scale)}
                                className="max-w-full shadow-2xl rounded-sm overflow-hidden"
                            />
                        )}
                    </Document>
                ) : (
                    // Markdown preview placeholder
                    <div className="flex flex-col items-center justify-center text-gray-400 p-6 text-center h-full my-auto">
                        <Form className="h-10 w-10 text-gray-500 mb-2 stroke-[1.5]" />
                        <p className="text-sm font-medium text-gray-300">Markdown View</p>
                        <p className="text-xs text-gray-500 mt-1">Preview for {activeDoc}</p>
                    </div>
                )}
            </div>

        </div>
    )
}