# Bud - Frontend

Interactive React 19 web application for the Bud RAG document assistant, built with Vite, Tailwind CSS v4, and `react-pdf`.

## Features

- **Three-Pane Dashboard**:
  - **Upload Sidebar**: Upload PDFs, view document library, select active document.
  - **PDF Viewer**: Document rendering with zoom, page navigation, and automatic citation jump.
  - **Chatbot Pane**: Ask questions, receive streaming SSE answers, and interact with clickable page citation badges.
- **Modern Styling**: Tailwind CSS v4, dark mode theme, Base UI, and Lucide icons.

## Requirements

- Node.js 18+
- npm (or pnpm / yarn)

## Setup & Installation

1. Install dependencies:
   ```bash
   npm install
   ```

2. Start the development server:
   ```bash
   npm run dev
   ```

The application will be accessible at `http://localhost:5173`. Make sure the Bud backend server is running at `http://localhost:8000`.

## Production Build

To build the static application bundle:

```bash
npm run build
```

To preview the production build locally:

```bash
npm run preview
```
