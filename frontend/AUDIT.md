# Frontend Codebase Audit

**What this repo does:**
This frontend is a React 19 single-page dashboard for an AI-powered PDF assistant. It displays a three-panel workspace where users can upload PDFs, read pages with zoom and citation jump links, and ask questions to receive streaming AI answers.
**Assumed load:** A single user running the interface locally in a modern desktop web browser connected to a local or remote backend.

---

### Must fix

1. **Arrow keys turn pages while user is typing in chat** ([PDFFileReader.jsx](file:///home/duke-cre/Programs/AI-powered-PDF-reader/frontend/src/components/PDFFileReader.jsx#L56-L66))
   - **What this is:** A global window keydown listener that turns PDF pages when pressing left or right arrow keys.
   - **Problem:** It listens on `window` without checking if the active element is an input or textarea. When a user presses ArrowLeft or ArrowRight to edit text in the chat input, the PDF turns pages in the background.
   - **Fix:** Ignore the event if the target is an editable element: `if (["INPUT", "TEXTAREA"].includes(e.target.tagName)) return;`.
   - **If we skip it:** Users cannot edit or navigate their typed questions without unintentionally flipping pages in the document viewer.

2. **Document switch leaves stale page count and error banners** ([PDFFileReader.jsx](file:///home/duke-cre/Programs/AI-powered-PDF-reader/frontend/src/components/PDFFileReader.jsx#L26-L29))
   - **What this is:** An effect hook that resets the PDF viewer state when the user selects a new document.
   - **Problem:** It resets `pageNumber` and `scale`, but does not reset `numPages` or `loadError`. When switching from a 50-page document to a 2-page document, the UI displays "Page 1 of 50" while loading and allows the user to navigate out of bounds.
   - **Fix:** Call `setNumPages(0)` and `setLoadError("")` inside the `activeDoc` reset effect.
   - **If we skip it:** The viewer displays phantom page counts and leftover error messages while loading subsequent files.

3. **Chat streaming error handler swallows backend errors containing "JSON"** ([ChatbotPane.jsx](file:///home/duke-cre/Programs/AI-powered-PDF-reader/frontend/src/components/ChatbotPane.jsx#L83-L109))
   - **What this is:** The Server-Sent Events (SSE) streaming loop that processes incoming tokens and error events from `/ask/stream`.
   - **Problem:** When the server emits an error event (`eventData.type === "error"`), it throws `new Error(eventData.detail)`. The catch block checks `!parseErr.message.includes("JSON")`, so any error mentioning JSON (e.g., "Failed to parse JSON schema") is swallowed and ignored.
   - **Fix:** Separate the `JSON.parse` call into its own `try/catch`, and handle `eventData.type === "error"` outside of it without string-matching error text.
   - **If we skip it:** Server errors mentioning JSON leave the user waiting indefinitely on a "Thinking..." pulse animation.

4. **Backend API endpoints are hardcoded to localhost:8000** ([UploadSidebar.jsx](file:///home/duke-cre/Programs/AI-powered-PDF-reader/frontend/src/components/UploadSidebar.jsx#L29), [UploadSidebar.jsx](file:///home/duke-cre/Programs/AI-powered-PDF-reader/frontend/src/components/UploadSidebar.jsx#L67), [PDFFileReader.jsx](file:///home/duke-cre/Programs/AI-powered-PDF-reader/frontend/src/components/PDFFileReader.jsx#L68), [ChatbotPane.jsx](file:///home/duke-cre/Programs/AI-powered-PDF-reader/frontend/src/components/ChatbotPane.jsx#L56))
   - **What this is:** Network calls for file listings, PDF uploads, document previews, and streaming query responses.
   - **Problem:** All four calls hardcode `http://localhost:8000`. Running the app in Docker, behind a reverse proxy, or accessing it across a local network causes every request to fail.
   - **Fix:** Store the base URL in a shared constant using `import.meta.env.VITE_API_BASE_URL || ""` or use relative paths routed through Vite's dev proxy.
   - **If we skip it:** The frontend cannot be tested across devices or deployed to staging and production environments.

---

### Should fix

5. **Silent upload failure on network or server errors** ([UploadSidebar.jsx](file:///home/duke-cre/Programs/AI-powered-PDF-reader/frontend/src/components/UploadSidebar.jsx#L78-L81))
   - **What this is:** The upload handler that submits a selected PDF file via `POST /upload`.
   - **Problem:** If the server is offline or drops the connection, `fetch` throws a network exception caught by `catch (err) { console.error(...) }`. The button resets to "Upload PDF files" with no feedback shown to the user.
   - **Fix:** Add an `alert("Upload failed. Could not connect to the server.")` or an inline error state banner inside the `catch` block.
   - **If we skip it:** Users assume their file uploaded successfully when the server never received it.

6. **Broken header logo image and hardcoded document title** ([Header.jsx](file:///home/duke-cre/Programs/AI-powered-PDF-reader/frontend/src/components/Header.jsx#L2-L12))
   - **What this is:** The top banner displaying the application logo and active title.
   - **Problem:** The `<img>` tag has an empty `src=""`, which produces a broken image icon in the browser, while the `logoImg` constant on line 2 is unused. The title is permanently hardcoded to `"Mastering Tmux: Setup, Configuration, and Workflow Optimization"`.
   - **Fix:** Set `<img src={logoImg} ...>` (or use an SVG icon) and pass `activeDoc` into `Header` as a prop so the title reflects the active document or app name.
   - **If we skip it:** The header always displays a broken image icon and an unrelated document name.

7. **Zero automated tests for streaming and viewer logic** ([package.json](file:///home/duke-cre/Programs/AI-powered-PDF-reader/frontend/package.json#L6-L11))
   - **What this is:** The npm build and verification scripts.
   - **Problem:** There are no tests, no test runner installed, and no `npm test` script. Edge cases in SSE token decoding and citation jumping have no automated checks.
   - **Fix:** Add Vitest and React Testing Library with unit tests covering SSE buffer splitting, error events, and citation jumps.
   - **If we skip it:** Regressions in streaming text decoding or citation navigation will only be discovered through manual testing in the browser.

8. **Inconsistent button imports and ignored variant props** ([UploadSidebar.jsx](file:///home/duke-cre/Programs/AI-powered-PDF-reader/frontend/src/components/UploadSidebar.jsx#L3), [PDFFileReader.jsx](file:///home/duke-cre/Programs/AI-powered-PDF-reader/frontend/src/components/PDFFileReader.jsx#L4))
   - **What this is:** Button elements used in the sidebar and the PDF control bar.
   - **Problem:** Both files import `@base-ui/react/button` directly rather than the custom wrapper in [button.jsx](file:///home/duke-cre/Programs/AI-powered-PDF-reader/frontend/src/components/ui/button.jsx), yet pass `variant="default"` which the raw primitive ignores.
   - **Fix:** Import `Button` from `./ui/button` consistently in both components.
   - **If we skip it:** Button behavior and styling remain inconsistent with the rest of the UI kit.

9. **Dead UI code, unreferenced template assets, and unused dependencies** ([toggle.jsx](file:///home/duke-cre/Programs/AI-powered-PDF-reader/frontend/src/components/ui/toggle.jsx#L27-L40), [package.json](file:///home/duke-cre/Programs/AI-powered-PDF-reader/frontend/package.json#L32), [package.json](file:///home/duke-cre/Programs/AI-powered-PDF-reader/frontend/package.json#L39))
   - **What this is:** The standalone `Toggle` component, unused starter assets (`src/assets/hero.png`, `react.svg`, `vite.svg`), and PostCSS/Autoprefixer packages.
   - **Problem:** `Toggle` is never imported (only `toggleVariants` is used), the assets are never referenced, and Tailwind v4 uses `@tailwindcss/vite` without PostCSS or Autoprefixer.
   - **Fix:** Delete the unused `Toggle` function, delete the dead files in `src/assets/`, and remove `autoprefixer` and `postcss` from `devDependencies`.
   - **If we skip it:** Unused code and packages increase build clutter and lockfile size.

---

### Nice to have

10. **Unbatched state re-renders on every streaming token** ([ChatbotPane.jsx](file:///home/duke-cre/Programs/AI-powered-PDF-reader/frontend/src/components/ChatbotPane.jsx#L94-L101))
    - **What this is:** Updating the React message state as each incoming token arrives from the server.
    - **Problem:** Calling `setMessages` on every single token maps the entire messages array and re-renders the component hundreds of times per second.
    - **Fix:** Accumulate incoming tokens in a local variable or string buffer, then flush updates using `requestAnimationFrame`.
    - **If we skip it:** Fast-streaming responses cause frame drops and UI stutter on lower-end devices.

11. **Inert sidebar toggle button and placeholder Markdown tab** ([UploadSidebar.jsx](file:///home/duke-cre/Programs/AI-powered-PDF-reader/frontend/src/components/UploadSidebar.jsx#L94-L96), [PDFFileReader.jsx](file:///home/duke-cre/Programs/AI-powered-PDF-reader/frontend/src/components/PDFFileReader.jsx#L157-L164))
    - **What this is:** The sidebar collapse button with `PanelLeft` icon and the "Markdown" view mode button.
    - **Problem:** The sidebar button has no `onClick` handler, and clicking the Markdown tab displays an empty placeholder box rather than rendered Markdown.
    - **Fix:** Connect the sidebar button to a collapse toggle state, and either implement markdown fetching/rendering or hide the toggle until ready.
    - **If we skip it:** Users encounter non-functional interactive elements in the main navigation.

12. **SSE trailing buffer discarded on stream close** ([ChatbotPane.jsx](file:///home/duke-cre/Programs/AI-powered-PDF-reader/frontend/src/components/ChatbotPane.jsx#L71-L77))
    - **What this is:** The stream chunk parsing loop for Server-Sent Events.
    - **Problem:** When `done` is true, the loop exits immediately. If the server does not append a trailing `\n\n` before closing the stream, whatever data remains in `buffer` is discarded.
    - **Fix:** Parse any leftover content remaining in `buffer` after exiting the `while` loop.
    - **If we skip it:** The final token or source list is dropped if the connection closes without trailing newlines.

---

**Verdict:** Fix the global arrow key capture (1) and hardcoded localhost URLs (4) first; the app runs, but input handling and deployment are broken.  
**Lean: -16 lines, -2 dependencies possible.**  
**Not checked:** Backend service endpoints and live PDF parsing server (audited frontend workspace only).
