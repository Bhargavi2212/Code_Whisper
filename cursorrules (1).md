# CodeWhisper — Cursor Rules

> **Read PROJECT.md first.** Before starting any task, read PROJECT.md in the project root to understand the full product. Before starting a specific phase, read the corresponding docs/PHASE_X_SPEC.md file.

---

## Project Identity

- Project: CodeWhisper
- Purpose: Real-time AI companion that watches IDE screens and explains AI-generated code through voice.
- Stack: React + Tailwind (frontend), Python + FastAPI (backend), Gemini Live API (AI), Docker + Google Cloud Run (infra).
- OS: Windows (development machine)
- Package Manager: npm (frontend), pip (backend)

---

## Golden Rules

1. **Read the spec before coding.** Every phase has a spec in docs/PHASE_X_SPEC.md. Read it fully before writing any code. Do not invent features not in the spec.
2. **Do not add features.** Only build what the current phase spec asks for. No "nice to have" additions. No future-proofing beyond what the spec states. If something is not in the phase spec, do not build it.
3. **Do not delete or modify code from previous phases** unless the current phase spec explicitly says to. Previous phases are done and working.
4. **Ask before assuming.** If the spec is ambiguous, ask. Do not guess. Do not make assumptions about how the Gemini Live API works — refer to the SDK docs.
5. **Test as you go.** After implementing each piece, verify it works before moving to the next. Do not build the entire phase and test at the end.
6. **Keep it simple.** This is a hackathon. Ship fast, ship working. No premature abstractions, no over-engineering, no unnecessary layers.

---

## Code Style — Python (Backend)

### General
- Python 3.12+ features are allowed.
- Use type hints on all function signatures. Include return types.
- Use f-strings for string formatting. Never use .format() or % formatting.
- Use pathlib for file paths when needed.
- Prefer async/await over threads. The entire backend is async.
- Do not use global mutable state. Pass dependencies explicitly.

### Naming
- Files: snake_case.py (e.g., gemini_session.py, audio_handler.py).
- Functions: snake_case (e.g., start_session, handle_audio_chunk).
- Classes: PascalCase (e.g., GeminiSession, SessionManager).
- Constants: UPPER_SNAKE_CASE (e.g., SEND_SAMPLE_RATE, MAX_FRAME_SIZE).
- Private methods: prefix with underscore (e.g., _validate_audio_format).

### Imports
- Group imports in this order: stdlib, third-party, local. One blank line between groups.
- Use absolute imports, not relative.
- Do not use wildcard imports (from x import *).

### FastAPI Conventions
- Use async def for all endpoint handlers and WebSocket handlers.
- Use Pydantic models for any structured data (request/response bodies, config).
- Use dependency injection for shared resources (config, session manager).
- WebSocket endpoint path: /ws/session
- Health check endpoint path: /health
- All endpoints go in main.py. Do not create a separate router file — the app is small enough.

### Error Handling
- Use try/except around all external calls (Gemini API, WebSocket operations).
- Log errors with the logging module. Do not use print().
- On WebSocket errors, send an error message to the client before closing.
- Never let an exception crash the server. Always catch and handle.

### Logging
- Use Python's logging module. Configure in main.py.
- Log level: INFO for normal operations, DEBUG for detailed tracing, ERROR for failures.
- Format: timestamp - module - level - message.
- Log every session start, session end, Gemini connection open/close, and errors.

### Dependencies
- Pin all dependency versions in requirements.txt (e.g., fastapi==0.109.0, not fastapi>=0.109).
- Only add dependencies that are explicitly needed. Do not add utility libraries for things Python stdlib can do.
- Required dependencies for the project: fastapi, uvicorn, python-dotenv, google-genai, websockets, Pillow (for image processing if needed).

---

## Code Style — JavaScript/React (Frontend)

### General
- Use functional components only. No class components.
- Use React hooks for all state and side effects.
- Use ES6+ syntax: arrow functions, destructuring, template literals, optional chaining.
- Use const by default. Use let only when reassignment is needed. Never use var.
- All files use .jsx extension for React components, .js for utilities and hooks.

### Naming
- Component files: PascalCase.jsx (e.g., SessionControls.jsx, FlowModeIndicator.jsx).
- Hook files: camelCase.js starting with "use" (e.g., useWebSocket.js, useScreenCapture.js).
- Utility files: camelCase.js (e.g., audioUtils.js, frameUtils.js).
- Components: PascalCase (e.g., SessionControls, StatusBar).
- Hooks: camelCase starting with "use" (e.g., useWebSocket, useScreenCapture).
- Functions/variables: camelCase (e.g., startSession, isConnected).
- Constants: UPPER_SNAKE_CASE (e.g., FRAME_RATE, WS_URL).
- CSS classes: Use Tailwind utilities. No custom CSS class names unless absolutely necessary.

### Component Structure
- One component per file.
- Default export for every component.
- Props destructured in the function signature.
- Hooks at the top of the component, before any logic.
- Return JSX at the bottom.
- Keep components under 150 lines. Extract sub-components if larger.

### Hooks Structure
- Custom hooks go in src/hooks/.
- Each hook manages one concern (WebSocket, screen capture, audio input, audio output, session state).
- Hooks return objects with clear property names: { isActive, start, stop, data }.
- Use useRef for mutable values that should not trigger re-renders (WebSocket instances, audio contexts, media streams).
- Use useCallback for functions passed to child components.
- Use useEffect for setup/teardown (connecting, disconnecting, starting/stopping media).
- Always include cleanup functions in useEffect.

### State Management
- Use useState and useReducer. No external state management library (no Redux, Zustand, etc.).
- Lift state to the lowest common parent, not to the App root unless necessary.
- The session state machine (idle -> connecting -> active -> ending -> ended) lives in useSession.js.

### Styling
- Use Tailwind CSS utility classes exclusively.
- Do not write custom CSS unless Tailwind cannot achieve it.
- Do not use CSS-in-JS libraries (no styled-components, emotion, etc.).
- Use Tailwind's dark mode if desired, but light mode is default.
- Responsive: use Tailwind breakpoint prefixes (sm:, md:, lg:).
- Color palette: Use Tailwind's built-in colors. Define any brand colors in tailwind.config.js.

### Error Handling
- Wrap all async operations in try/catch.
- Display user-facing errors in the UI (e.g., "Could not connect to microphone").
- Log errors to console.error with context.
- Gracefully degrade: if screen share fails, show a message. If mic fails, show a message. Do not crash the app.

---

## WebSocket Protocol

All communication between the React frontend and the FastAPI backend goes through a single WebSocket connection at ws://localhost:8000/ws/session.

### Message Format

All messages are JSON with a "type" field:

```json
{
  "type": "message_type",
  "data": { ... }
}
```

### Client to Server Messages

```
{
  "type": "audio",
  "data": "<base64 encoded PCM audio chunk>"
}

{
  "type": "frame",
  "data": "<base64 encoded JPEG image>"
}

{
  "type": "control",
  "action": "start_session" | "end_session"
}
```

### Server to Client Messages

```
{
  "type": "audio",
  "data": "<base64 encoded PCM audio chunk from Gemini>"
}

{
  "type": "status",
  "status": "connected" | "gemini_connected" | "gemini_speaking" | "gemini_listening" | "session_ended" | "error"
}

{
  "type": "summary",
  "text": "<session summary text>"
}

{
  "type": "mode",
  "mode": "sportscaster" | "catchup" | "review"
}

{
  "type": "error",
  "message": "<error description>"
}
```

---

## File Organization Rules

- **Backend files go in /backend.** No exceptions.
- **Frontend files go in /frontend.** No exceptions.
- **No shared code between frontend and backend.** They are separate containers.
- **Config that both need (like WebSocket message types):** Define in both places. Duplication is fine for a hackathon — do not create a shared package.
- **Phase specs stay in /docs.** Do not modify them during implementation.
- **Environment variables go in .env.** Access them through config.py (backend) or vite.config.js / import.meta.env (frontend).

---

## Docker Rules

- Docker Compose is for local development. Two services: backend and frontend.
- The production Dockerfile (for Cloud Run) is a single multi-stage build that serves both.
- Do not use Docker volumes for code in production. Only in development for hot reload.
- Keep Docker images small. Use python:3.12-slim for backend, node:18-alpine for frontend build.
- Do not install dev dependencies in production images.

---

## Git Rules

- .env is in .gitignore. Never commit API keys.
- .env.example is committed. It has placeholder values.
- node_modules/ is in .gitignore.
- __pycache__/ is in .gitignore.
- .venv/ is in .gitignore.
- Do not commit large binary files.

---

## Gemini Live API Rules

- Use the google-genai SDK. Import as: from google import genai
- Create client: client = genai.Client(api_key=api_key)
- Open live session: async with client.aio.live.connect(model=model, config=config) as session
- The session object has: session.send() for sending data, session.receive() for receiving.
- Send audio as raw bytes with mime_type specified.
- Send images as base64 with mime_type "image/jpeg".
- The system prompt is passed in the config at connection time, not as a message.
- Do NOT invent API methods. If unsure how something works, check the google-genai documentation or ask.
- Handle connection drops gracefully. The WebSocket to Gemini can close unexpectedly.

---

## Testing Rules

- No formal test framework for the hackathon. Manual testing is fine.
- Each phase spec has acceptance criteria. Test against those.
- For the backend: use a WebSocket client (like websocat or a Python script) to test endpoints.
- For the frontend: test in Chrome. Screen share and mic require HTTPS or localhost.
- Test the full flow end-to-end after Phase 4. Do not wait until Phase 8.

---

## Performance Rules

- Screen frames: 1 FPS maximum. Do not send more than 1 frame per second.
- Frame size: 768x768 JPEG. Quality: 0.7 (70%). This balances readability with bandwidth.
- Audio chunks: Send in reasonably sized chunks (4096 bytes or similar). Do not send byte-by-byte.
- WebSocket: Use binary frames for audio, text frames for JSON messages.
- Do not block the main thread in the frontend. Use Web Workers or AudioWorklet for audio processing if needed.
- The backend is async. Never use blocking calls (no time.sleep, no synchronous I/O).

---

## What Cursor Should Never Do

- Never add authentication or login.
- Never add a database.
- Never add session persistence or history.
- Never create an IDE plugin or extension.
- Never write code that modifies the user's source code.
- Never add multi-user or collaboration features.
- Never add features not specified in the current phase.
- Never use print() for logging in Python. Use the logging module.
- Never use var in JavaScript.
- Never use class components in React.
- Never install a state management library (Redux, Zustand, MobX, etc.).
- Never install a CSS-in-JS library.
- Never commit .env or API keys.
