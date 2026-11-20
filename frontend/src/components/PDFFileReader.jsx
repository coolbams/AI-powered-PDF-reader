import { useEffect, useMemo, useRef, useState } from "react"
import { ToggleGroup, ToggleGroupItem } from "./ui/toggle-group"
import { FileText, Form, ChevronLeft, ChevronRight, ZoomIn, ZoomOut, ArrowDownUp, ArrowLeftRight } from "lucide-react"
import { Button } from "@base-ui/react/button"
import { Document, Page, pdfjs } from "react-pdf"
import { marked } from "marked"
import { API_BASE_URL } from "../config"
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
    const [scrollMode, setScrollMode] = useState("vertical")
    const [numPages, setNumPages] = useState(0)
    const [pageNumber, setPageNumber] = useState(1)
    const [pageWidth, setPageWidth] = useState(0)
    const [scale, setScale] = useState(1.0)
    const [loadError, setLoadError] = useState("")
    const [markdownPages, setMarkdownPages] = useState([])
    const [markdownLoading, setMarkdownLoading] = useState(false)
    const viewerRef = useRef(null)
    const isProgrammaticScroll = useRef(false)
    const programmaticTimeoutRef = useRef(null)

    const scrollToPage = (pageNum) => {
        isProgrammaticScroll.current = true
        if (programmaticTimeoutRef.current) {
            clearTimeout(programmaticTimeoutRef.current)
        }
        programmaticTimeoutRef.current = setTimeout(() => {
            isProgrammaticScroll.current = false
        }, 700)

        setPageNumber(pageNum)

        if (scrollMode === "vertical") {
            const id = viewMode === "pdf" ? `pdf-page-${pageNum}` : `md-page-${pageNum}`
            const el = document.getElementById(id)
            if (el) {
                el.scrollIntoView({ behavior: "smooth", block: "start" })
            }
        }
    }

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
                scrollToPage(pageNum)
            }
        }
    }, [targetPage, numPages])

    // Fetch markdown extract when markdown view is active
    useEffect(() => {
        if (viewMode === "markdown" && activeDoc) {
            let ignore = false
            setMarkdownLoading(true)
            fetch(`${API_BASE_URL}/markdown/${encodeURIComponent(activeDoc)}`)
                .then((res) => {
                    if (!res.ok) throw new Error("Markdown not found")
                    return res.json()
                })
                .then((data) => {
                    if (!ignore) {
                        const pages = data.pages || []
                        setMarkdownPages(pages)
                        if (pages.length > 0) {
                            setNumPages((prev) => (prev > 0 ? prev : pages.length))
                        }
                    }
                })
                .catch(() => {
                    if (!ignore) setMarkdownPages([])
                })
                .finally(() => {
                    if (!ignore) setMarkdownLoading(false)
                })
            return () => {
                ignore = true
            }
        }
    }, [viewMode, activeDoc])

    // Auto-scroll on viewMode or scrollMode toggle if in vertical mode
    useEffect(() => {
        if (scrollMode === "vertical") {
            const timer = setTimeout(() => {
                const id = viewMode === "pdf" ? `pdf-page-${pageNumber}` : `md-page-${pageNumber}`
                const el = document.getElementById(id)
                if (el) {
                    el.scrollIntoView({ behavior: "smooth", block: "start" })
                }
            }, 100)
            return () => clearTimeout(timer)
        }
    }, [viewMode, scrollMode])

    // Real-time Scroll-Spy: detect which page is in view and update pageNumber
    useEffect(() => {
        if (scrollMode !== "vertical") return

        const container = viewerRef.current
        if (!container) return

        const observer = new IntersectionObserver(
            (entries) => {
                if (isProgrammaticScroll.current) return

                const visible = entries.filter((e) => e.isIntersecting)
                if (visible.length === 0) return

                const containerTop = container.getBoundingClientRect().top
                visible.sort((a, b) => {
                    const topA = Math.abs(a.boundingClientRect.top - containerTop)
                    const topB = Math.abs(b.boundingClientRect.top - containerTop)
                    return topA - topB
                })

                const pageAttr = visible[0].target.getAttribute("data-page-num")
                if (pageAttr) {
                    const parsed = parseInt(pageAttr, 10)
                    if (parsed && parsed !== pageNumber) {
                        setPageNumber(parsed)
                    }
                }
            },
            {
                root: container,
                threshold: [0, 0.2, 0.5, 0.8],
                rootMargin: "-10% 0px -40% 0px",
            }
        )

        const selector = viewMode === "pdf" ? "[data-pdf-page]" : "[data-md-page]"
        const elements = container.querySelectorAll(selector)
        elements.forEach((el) => observer.observe(el))

        return () => observer.disconnect()
    }, [scrollMode, viewMode, numPages, markdownPages, scale, pageNumber])

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
                prevPage()
            } else if (e.key === "ArrowRight") {
                nextPage()
            }
        }
        window.addEventListener("keydown", handleKeyDown)
        return () => window.removeEventListener("keydown", handleKeyDown)
    }, [numPages, pageNumber, markdownPages])

    const fileUrl = activeDoc ? `${API_BASE_URL}/files/${encodeURIComponent(activeDoc)}` : null

    const prevPage = () => {
        const target = Math.max(1, pageNumber - 1)
        scrollToPage(target)
    }

    const nextPage = () => {
        const max = numPages || (markdownPages.length > 0 ? markdownPages.length : pageNumber + 1)
        const target = Math.min(max, pageNumber + 1)
        scrollToPage(target)
    }

    const zoomIn = () => setScale((s) => Math.min(2.0, +(s + 0.15).toFixed(2)))
    const zoomOut = () => setScale((s) => Math.max(0.6, +(s - 0.15).toFixed(2)))

    return (
        <div className="flex flex-col w-full h-full rounded-2xl bg-[#1F1F1F] overflow-hidden min-h-0" id="PDFFileReader Container">

            {/* Unified Top Control Sub-Bar */}
            <div className="w-full h-11 px-4 border-b border-zinc-800/80 bg-[#161616] flex items-center justify-between text-xs text-gray-300 select-none shrink-0" id="Sub-Bar">
                {/* Left: Page Navigation */}
                <div className="flex items-center gap-1.5 min-w-[170px]">
                    {activeDoc && (
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

                {/* Center: Zoom Controls & Scroll Mode */}
                <div className="flex items-center gap-3">
                    {activeDoc && viewMode === "pdf" && (
                        <div className="flex items-center gap-1.5">
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
                        </div>
                    )}

                    {activeDoc && (
                        <ToggleGroup
                            value={[scrollMode]}
                            onValueChange={(val) => {
                                const selected = Array.isArray(val) ? val[val.length - 1] : val
                                if (selected) {
                                    setScrollMode(selected)
                                    if (selected === "vertical") {
                                        setTimeout(() => scrollToPage(pageNumber), 50)
                                    }
                                }
                            }}
                            variant="default"
                        >
                            <ToggleGroupItem
                                value="vertical"
                                aria-label="Vertical continuous scroll"
                                title="Vertical continuous scroll"
                                className="text-white data-pressed:bg-[#484848] data-[state=on]:bg-[#484848] aria-pressed:bg-[#484848] hover:bg-[#282828] hover:text-white transition-colors rounded-lg px-2.5 py-1 text-xs"
                            >
                                <ArrowDownUp className="h-3.5 w-3.5 mr-1" />
                                Vertical
                            </ToggleGroupItem>
                            <ToggleGroupItem
                                value="horizontal"
                                aria-label="Horizontal single page"
                                title="Horizontal single page"
                                className="text-white data-pressed:bg-[#484848] data-[state=on]:bg-[#484848] aria-pressed:bg-[#484848] hover:bg-[#282828] hover:text-white transition-colors rounded-lg px-2.5 py-1 text-xs"
                            >
                                <ArrowLeftRight className="h-3.5 w-3.5 mr-1" />
                                Horizontal
                            </ToggleGroupItem>
                        </ToggleGroup>
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
                        onLoadSuccess={({ numPages: loadedPages }) => {
                            setNumPages(loadedPages)
                            setLoadError("")
                        }}
                        onLoadError={(error) => setLoadError(error.message)}
                        loading={<p className="text-sm text-gray-400 my-8">Loading PDF...</p>}
                        error={<p className="text-sm text-red-400 my-8">{loadError || "Could not load this PDF."}</p>}
                        className="flex flex-col items-center w-full"
                    >
                        {scrollMode === "vertical" ? (
                            Array.from(new Array(numPages || 1), (_, index) => {
                                const pageNum = index + 1
                                return (
                                    <div
                                        key={`pdf_page_${pageNum}`}
                                        id={`pdf-page-${pageNum}`}
                                        data-pdf-page="true"
                                        data-page-num={pageNum}
                                        className="mb-4 flex flex-col items-center"
                                    >
                                        {pageWidth > 0 && (
                                            <Page
                                                pageNumber={pageNum}
                                                width={Math.floor(pageWidth * scale)}
                                                className="max-w-full shadow-2xl rounded-sm overflow-hidden"
                                            />
                                        )}
                                    </div>
                                )
                            })
                        ) : (
                            <div
                                key={`pdf_page_${pageNumber}`}
                                id={`pdf-page-${pageNumber}`}
                                data-pdf-page="true"
                                data-page-num={pageNumber}
                                className="flex flex-col items-center"
                            >
                                {pageWidth > 0 && (
                                    <Page
                                        pageNumber={pageNumber}
                                        width={Math.floor(pageWidth * scale)}
                                        className="max-w-full shadow-2xl rounded-sm overflow-hidden"
                                    />
                                )}
                            </div>
                        )}
                    </Document>
                ) : (
                    // Formatted Markdown Document
                    <div className="w-full h-full overflow-y-auto p-6 flex flex-col items-center">
                        {markdownLoading ? (
                            <p className="text-sm text-gray-400 my-8">Loading markdown preview...</p>
                        ) : markdownPages.length === 0 ? (
                            <div className="text-gray-400 text-sm my-8">No markdown extract found for this document.</div>
                        ) : scrollMode === "vertical" ? (
                            <div className="w-full max-w-4xl flex flex-col gap-6 pb-12">
                                {markdownPages.map((page) => (
                                    <section
                                        key={page.page_number}
                                        id={`md-page-${page.page_number}`}
                                        data-md-page="true"
                                        data-page-num={page.page_number}
                                        className="p-8 bg-[#181818] rounded-2xl border border-zinc-800 shadow-xl"
                                    >
                                        <div className="border-b border-zinc-800/80 pb-2 mb-4 select-none">
                                            <span className="text-xs font-mono text-zinc-500 tracking-wider">
                                                PAGE {page.page_number}
                                            </span>
                                        </div>
                                        <div
                                            className="markdown-body"
                                            dangerouslySetInnerHTML={{ __html: marked.parse(page.text || "") }}
                                        />
                                    </section>
                                ))}
                            </div>
                        ) : (
                            <div className="w-full max-w-4xl flex flex-col gap-6">
                                {(() => {
                                    const curPage = markdownPages.find((p) => p.page_number === pageNumber) || markdownPages[0]
                                    if (!curPage) return null
                                    return (
                                        <section
                                            key={curPage.page_number}
                                            id={`md-page-${curPage.page_number}`}
                                            data-md-page="true"
                                            data-page-num={curPage.page_number}
                                            className="p-8 bg-[#181818] rounded-2xl border border-zinc-800 shadow-xl"
                                        >
                                            <div className="border-b border-zinc-800/80 pb-2 mb-4 select-none">
                                                <span className="text-xs font-mono text-zinc-500 tracking-wider">
                                                    PAGE {curPage.page_number}
                                                </span>
                                            </div>
                                            <div
                                                className="markdown-body"
                                                dangerouslySetInnerHTML={{ __html: marked.parse(curPage.text || "") }}
                                            />
                                        </section>
                                    )
                                })()}
                            </div>
                        )}
                    </div>
                )}
            </div>

        </div>
    )
}