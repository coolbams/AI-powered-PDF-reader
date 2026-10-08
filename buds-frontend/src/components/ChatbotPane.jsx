import { useEffect, useRef, useState } from "react"
import { AlertCircle, Bot, Send, UserRound, FileText } from "lucide-react"
import { Button } from "./ui/button"
import { Textarea } from "./ui/textarea"

export default function ChatbotPane({ activeDoc, onJumpToPage }) {
    const [messages, setMessages] = useState([])
    const [draft, setDraft] = useState("")
    const [isLoading, setIsLoading] = useState(false)
    const [error, setError] = useState("")
    const requestControllerRef = useRef(null)
    const messagesEndRef = useRef(null)

    useEffect(() => {
        setMessages([])
        setDraft("")
        setError("")
        setIsLoading(false)

        return () => requestControllerRef.current?.abort()
    }, [activeDoc])

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
    }, [messages, isLoading])

    const handleSubmit = async (event) => {
        event.preventDefault()

        const query = draft.trim()
        if (!activeDoc || !query || isLoading) return

        const history = messages.map(({ role, content }) => ({ role, content }))
        const userMessage = {
            id: crypto.randomUUID(),
            role: "user",
            content: query,
        }
        const assistantMessageId = crypto.randomUUID()
        const assistantPlaceholder = {
            id: assistantMessageId,
            role: "assistant",
            content: "",
            sources: [],
        }

        const controller = new AbortController()
        requestControllerRef.current = controller

        // Add user query and placeholder assistant message immediately
        setMessages((currentMessages) => [...currentMessages, userMessage, assistantPlaceholder])
        setDraft("")
        setError("")
        setIsLoading(true)
        try {
            const response = await fetch("http://localhost:8000/ask/stream", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query, doc_name: activeDoc, history }),
                signal: controller.signal,
            })

            if (!response.ok) {
                throw new Error("Failed to connect to the streaming server.")
            }

            const reader = response.body.getReader()
            const decoder = new TextDecoder("utf-8")
            let buffer = ""

            while (true) {
                const { value, done } = await reader.read()
                if (done) break

                buffer += decoder.decode(value, { stream: true })
                const parts = buffer.split("\n\n")
                buffer = parts.pop()

                for (const part of parts) {
                    const trimmed = part.trim()
                    if (!trimmed.startsWith("data: ")) continue

                    try {
                        const eventData = JSON.parse(trimmed.slice(6))

                        if (eventData.type === "sources") {
                            setMessages((prev) =>
                                prev.map((msg) =>
                                    msg.id === assistantMessageId
                                        ? { ...msg, sources: eventData.sources || [] }
                                        : msg
                                )
                            )
                        } else if (eventData.type === "token") {
                            setMessages((prev) =>
                                prev.map((msg) =>
                                    msg.id === assistantMessageId
                                        ? { ...msg, content: msg.content + eventData.token }
                                        : msg
                                )
                            )
                        } else if (eventData.type === "error") {
                            throw new Error(eventData.detail || "Streaming error occurred.")
                        }
                    } catch (parseErr) {
                        if (parseErr.message && !parseErr.message.includes("JSON")) {
                            throw parseErr
                        }
                    }
                }
            }
        } catch (requestError) {
            if (controller.signal.aborted) return

            setMessages((currentMessages) =>
                currentMessages.filter((message) => message.id !== assistantMessageId)
            )
            setDraft(query)
            setError(requestError.message || "Something went wrong. Please try again.")
        } finally {
            if (requestControllerRef.current === controller) {
                requestControllerRef.current = null
                setIsLoading(false)
            }
        }
    } 

    const handleKeyDown = (event) => {
        if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
            event.preventDefault()
            event.currentTarget.form?.requestSubmit()
        }
    }

    return (
        <div className="flex h-full min-h-0 w-full flex-col overflow-hidden rounded-2xl bg-[#1F1F1F]" id="ChatBot Container">
            <div className="flex h-15 shrink-0 items-center justify-between border-b border-zinc-800 px-5">
                <h2 className="text-sm font-medium text-gray-200">Chat</h2>
                {activeDoc && (
                    <span className="max-w-[65%] truncate text-xs text-gray-500" title={activeDoc}>
                        {activeDoc}
                    </span>
                )}
            </div>

            <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-4 py-5">
                {!activeDoc ? (
                    <div className="m-auto max-w-56 text-center text-sm text-gray-500">
                        Select a document to start a conversation.
                    </div>
                ) : messages.length === 0 && !isLoading ? (
                    <div className="m-auto max-w-64 text-center text-sm text-gray-500">
                        Ask a question about {activeDoc}.
                    </div>
                ) : (
                    <div className="flex flex-col gap-5">
                        {messages.map((message) => (
                            <article key={message.id} className="flex items-start gap-2.5">
                                <span className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full bg-[#2A2A2A] text-gray-300">
                                    {message.role === "assistant" ? (
                                        <Bot className="size-4" aria-hidden="true" />
                                    ) : (
                                        <UserRound className="size-4" aria-hidden="true" />
                                    )}
                                </span>
                                <div className="min-w-0 flex-1">
                                    {message.content ? (
                                        <p className="whitespace-pre-wrap break-words text-sm leading-6 text-gray-200">
                                            {message.content}
                                            {isLoading && message.id === messages[messages.length - 1]?.id && (
                                                <span className="inline-block w-1.5 h-4 ml-1 bg-amber-400 animate-pulse align-middle" />
                                            )}
                                        </p>
                                    ) : (
                                        <div className="flex items-center gap-2 text-xs text-gray-400 py-1" role="status">
                                            <span className="inline-block size-2 rounded-full bg-amber-400 animate-ping" />
                                            Thinking...
                                        </div>
                                    )}

                                    {message.sources?.length > 0 && (
                                        <div className="mt-3 flex flex-wrap gap-1.5">
                                            {message.sources.map((source, index) => (
                                                <button
                                                    key={`${source.page}-${index}`}
                                                    type="button"
                                                    onClick={() => onJumpToPage?.(source.page)}
                                                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-[11px] font-medium bg-zinc-800 hover:bg-zinc-700 text-amber-300 hover:text-amber-200 border border-zinc-700/60 transition-colors cursor-pointer group"
                                                    title={`Jump to Page ${source.page}`}
                                                >
                                                    <FileText className="size-3 text-amber-400/70 group-hover:text-amber-300" />
                                                    Page {source.page}
                                                </button>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </article>
                        ))}
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {error && (
                <div className="mx-4 mb-3 flex items-start gap-2 rounded-md border border-red-900/70 bg-red-950/30 px-3 py-2 text-xs text-red-300" role="alert">
                    <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
                    <span>{error}</span>
                </div>
            )}

            <form onSubmit={handleSubmit} className="shrink-0 border-t border-zinc-800 p-3">
                <div className="flex items-end gap-2 rounded-xl border border-zinc-700 bg-[#171717] p-2 focus-within:border-zinc-500">
                    <Textarea
                        value={draft}
                        onChange={(event) => setDraft(event.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder={activeDoc ? "Ask about this document..." : "Select a document first"}
                        aria-label="Ask a question about the selected document"
                        disabled={!activeDoc || isLoading}
                        rows={1}
                        className="max-h-32 min-h-10 flex-1 border-0 bg-transparent px-2 py-2 text-sm text-white shadow-none focus-visible:ring-0 md:text-sm"
                    />
                    <Button
                        type="submit"
                        size="icon"
                        aria-label="Send message"
                        title="Send message"
                        disabled={!activeDoc || !draft.trim() || isLoading}
                        className="size-9 rounded-lg bg-amber-500 text-black hover:bg-amber-400"
                    >
                        <Send className="size-4" aria-hidden="true" />
                    </Button>
                </div>
                <p className="mt-2 px-1 text-[11px] text-gray-500">
                    Enter to send · Shift+Enter for a new line
                </p>
            </form>
        </div>
    )
}