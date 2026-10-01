# UploadSidebar.jsx

This file is the left sidebar for the app. Its job is to let the user:

- upload a PDF file
- see already uploaded PDFs
- click one to select it as the active document

It is a React component, which means it is a reusable UI block.

## File purpose

This component is responsible for the document library panel. It is the part of the app where the user manages the source documents used for the app's question-answer system.

In plain English:

- the user picks a PDF
- the app uploads it to the backend
- the backend processes it
- the file appears in the list
- the user can click it to select it

---

## Component signature

```jsx
export default function UploadSidebar({ activeDoc, onSelectDoc }) {
```

This means the component receives props from its parent.

- `activeDoc`: the currently selected document name
- `onSelectDoc`: a function passed from the parent so this child can tell the parent which file was clicked

This is how React passes data from parent to child and from child back to parent.

---

## State variables

```jsx
const [files, setFiles] = useState([])
const [isLoading, setIsLoading] = useState(true)
const [isUploading, setIsUploading] = useState(false)
const fileInputRef = useRef(null)
```

### `files`
Stores the list of uploaded file names returned by the backend.

Example:

```jsx
["Atomic Habits.pdf", "Notes.pdf"]
```

### `isLoading`
Tells the UI whether the file list is still being fetched.

### `isUploading`
Tells the UI whether the upload request is still in progress.

### `fileInputRef`
This is a reference to the hidden file input element. It lets us open the file picker programmatically without showing the raw input.

---

## On mount: load existing files

```jsx
useEffect(() => {
    fetchFiles()
}, [])
```

This runs once when the component is first rendered.

Its purpose is to fetch the uploaded document names from the backend.

---

## fetchFiles()

```jsx
const fetchFiles = async () => {
    try {
        setIsLoading(true)
        const res = await fetch("http://localhost:8000/list_files")
        const data = await res.json()
        setFiles(data.files || [])
    } catch (err) {
        console.error("Failed to fetch files from backend:", err)
    } finally {
        setIsLoading(false)
    }
}
```

### What it does

- calls the backend endpoint `GET /list_files`
- gets a JSON object like `{ files: [...] }`
- stores the result in React state
- stops the loading state when done

### Why this matters

The UI needs to know which files already exist before it can show them in the sidebar.

---

## handleFileChange()

```jsx
const handleFileChange = async (e) => {
    const selectedFile = e.target.files?.[0]
    if (!selectedFile) return

    try {
        setIsUploading(true)

        const formData = new FormData()
        formData.append("file", selectedFile)

        const res = await fetch("http://localhost:8000/upload", {
            method: "POST",
            body: formData,
        })

        if (res.ok) {
            await fetchFiles()
        } else {
            alert("Failed to upload file")
        }
    } catch (err) {
        console.error("Upload error:", err)
    } finally {
        setIsUploading(false)
        e.target.value = ""
    }
}
```

### Step by step

1. `e.target.files?.[0]` gets the file the user selected
2. if no file was picked, the function exits
3. a `FormData` object is created
4. the file is added under the key `file`
5. a POST request is sent to `http://localhost:8000/upload`
6. if upload succeeds, the sidebar refreshes the file list
7. the input is cleared so the same file can be selected again later

### Why `FormData`?

Because the backend expects a file upload in a form-style request, not raw JSON.

---

## Hidden file input pattern

```jsx
<input
    type="file"
    accept=".pdf"
    ref={fileInputRef}
    onChange={handleFileChange}
    className="hidden"
/>
```

This hidden input is the actual file picker.

The button uses:

```jsx
onClick={() => fileInputRef.current?.click()}
```

This means: when the user clicks the visible upload button, trigger the real hidden input behind it.

This is a nice UI pattern because the file input is hidden but still works normally.

---

## The upload button

```jsx
<Button
    variant="default"
    onClick={() => fileInputRef.current?.click()}
    disabled={isUploading}
>
    <Plus className="h-4 w-4 text-white"/>
    <h2>{isUploading ? "Uploading..." : "Upload PDF files"}</h2>
</Button>
```

This is the visible button users click to choose a PDF.

- if uploading, the button becomes disabled
- otherwise, it says `Upload PDF files`

---

## Rendering the file list

```jsx
{isLoading ? (
    <p>Loading files...</p>
) : files.length === 0 ? (
    <p>No documents found.</p>
) : (
    <ul>
        {files.map((file, idx) => {
            const isSelected = activeDoc === file

            return (
                <li
                    key={idx}
                    onClick={() => onSelectDoc && onSelectDoc(file)}
                    className={...}
                >
                    <FileText />
                    <span>{file}</span>
                </li>
            )
        })}
    </ul>
)}
```

### What this means

- if files are still loading, show `Loading files...`
- if no files exist, show `No documents found.`
- otherwise map through the list and render each file as a clickable item

### Selection logic

```jsx
const isSelected = activeDoc === file
```

This compares the current selected PDF with this list item.

If they match, the item is highlighted.

### Click behavior

```jsx
onClick={() => onSelectDoc && onSelectDoc(file)}
```

When a file is clicked, it tells the parent component which file was selected.

This is how the selected document is shared across the app.

---

## Big picture

This component is the document manager of the app.

It is the bridge between:

- the user
- the browser file picker
- the backend upload API
- the rest of the app that needs the selected document

It does not do the heavy AI logic itself. It just handles file selection and communication with the backend and parent component.

---

## Beginner summary

If you had to explain this file in one sentence:

> UploadSidebar is the panel that lets the user upload PDF files, view their uploaded documents, and select one to become the active document for the rest of the app.
