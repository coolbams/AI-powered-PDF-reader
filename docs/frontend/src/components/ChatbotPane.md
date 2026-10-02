# ChatbotPane.jsx

This component is the chat panel on the right side of the app. It lets the user ask questions about the PDF selected in the sidebar, sends those questions to the backend, and displays the answer with its sources.

## Where the selected document comes from

`ChatbotPane` receives `activeDoc` as a prop from `ThreeBodiedPane`:

```jsx
<ChatbotPane activeDoc={activeDoc} />
```

`activeDoc` is the filename stem of the selected PDF. The parent owns this value, so the chat panel does not create a second copy of it in local state.

## State variables

```jsx
const [messages, setMessages] = useState([])
const [draft, setDraft] = useState("")
const [isLoading, setIsLoading] = useState(false)
const [error, setError] = useState("")
```

- `messages` holds the visible conversation. Each message has a `role` (`user` or `assistant`) and `content`. Assistant messages can also contain `sources`.
- `draft` holds the text currently in the textarea.
- `isLoading` is true while a question is being answered.
- `error` holds a message to show if the request fails.

Two refs support behavior without being part of the displayed state:

- `requestControllerRef` stores an `AbortController`, which can cancel a request when the selected document changes.
- `messagesEndRef` points to the bottom of the conversation so the panel can scroll to the latest message.

## Changing documents

An effect watches `activeDoc`. When it changes, the component clears the current messages, draft, and error. Its cleanup function cancels any in-progress request for the previous document.

This keeps conversations separate: selecting another PDF starts a fresh chat instead of carrying the previous PDF's conversation along.

## Sending a question

The composer is a form. Submitting it calls `handleSubmit`:

1. Stop the browser's normal form submission.
2. Trim whitespace from the draft and stop if there is no selected document, no text, or a request is already in progress.
3. Copy earlier messages into `history`, keeping only each message's `role` and `content`. Source excerpts are display-only and are not sent as chat history.
4. Add the user's question to the visible conversation and show the loading state.
5. Send a JSON request to `POST http://localhost:8000/ask`.

The request body looks like this:

```json
{
  "query": "What is the main idea?",
  "doc_name": "Atomic Habits James Clear PDF",
  "history": [
    { "role": "user", "content": "Earlier question" },
    { "role": "assistant", "content": "Earlier answer" }
  ]
}
```

`doc_name` tells retrieval to search only the selected PDF. The frontend filename stem matches the name the backend stores when indexing a PDF.

## Displaying the response

The backend returns an answer in `results` and the page numbers used to answer it in `sources`:

```json
{
  "results": "The answer text...",
  "sources": [
    {
      "page": 12
    }
  ]
}
```

The component adds `results` as an assistant message and attaches `sources` to it. The answer preserves line breaks, and each source is displayed as a single `Page N` line.

## Loading and errors

While the backend is working, `isLoading` displays a `Thinking...` status and disables the composer to prevent another request from being sent at the same time.

If the request fails, the component removes that unanswered user message, restores the question to the textarea, and displays the error. This lets the user retry without retyping.

## Keyboard behavior

- Pressing Enter submits the question.
- Pressing Shift+Enter inserts a new line.
- Enter during input-method composition does not submit prematurely.
- Empty questions and submissions while loading are ignored.

## Overall flow

```text
User types a question
        |
        v
ChatbotPane sends query + selected document + prior chat history
        |
        v
FastAPI /ask retrieves matching PDF passages and generates an answer
        |
        v
ChatbotPane displays the answer and source excerpts
```
