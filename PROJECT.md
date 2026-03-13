# CodeWhisper — Project Document

> **This is the single source of truth for the entire project.** Every phase spec references this document. Cursor should read this file before starting any phase to understand the full product, architecture, and conventions.

---

## What Is CodeWhisper

CodeWhisper is a real-time AI companion that watches your IDE screen and explains what AI-generated code is doing — through voice — so you can vibe code without losing understanding.

**Tagline:** "Vibe code without losing the mental model."

**One-liner:** A browser-based AI that sees your IDE via screen share, explains code through voice in real-time, and lets you interrupt anytime to ask questions.

---

## The Problem We Solve

Vibe coding (using AI tools like Cursor, Copilot, Claude Code to generate code from natural language prompts) has exploded. Developers accept AI-generated code without understanding what it does or why. The data:

- "Vibe coding" was Collins Dictionary Word of the Year 2025.
- 25% of YC Winter 2025 startups had 95% AI-generated codebases.
- 45% of developers say debugging AI-generated code takes longer than expected (Stack Overflow 2025).
- AI co-authored code has 1.7x more major issues and 2.74x more security vulnerabilities (CodeRabbit 2025).
- Experienced devs are 19% SLOWER with AI tools while believing they are 24% faster (METR 2025).
- Real startups have shut down because founders could not understand or debug their AI-generated code.

**The gap:** Every AI coding tool helps you WRITE code faster. Nobody helps you UNDERSTAND the code that was written for you. CodeWhisper fills this gap.

---

## How It Works (User Perspective)

1. User opens CodeWhisper in a browser tab (separate from their IDE).
2. Clicks "Start Session."
3. Browser asks for screen share permission — user picks their IDE window (VS Code, Cursor, terminal, anything).
4. Browser asks for microphone permission.
5. CodeWhisper starts watching the screen and talking — explaining what the code on screen does, what patterns are used, what the logic flow is.
6. User continues coding normally in their IDE. CodeWhisper does NOT touch the IDE. It just watches.
7. When AI-generated code appears (from Cursor, Copilot, etc.), CodeWhisper explains it.
8. User can interrupt anytime by speaking: "Wait, what does that function do?" — CodeWhisper stops, answers, then resumes.
9. User can switch Flow Modes with voice: "go quiet" / "walk me through this" / "just watch for now."
10. When done, user says "let's wrap up" or clicks End Session. CodeWhisper delivers a session summary.

**Key principle:** CodeWhisper is tool-agnostic. It works with Cursor, VS Code, Claude Code, Windsurf, Replit, Bolt.new, or anything visible on screen. No plugins. No integrations. Just screen share.

---

## Target Hackathon

**Gemini Live Agent Challenge** (Devpost)

- Track: Live Agents
- Deadline: March 16, 2026 @ 5:00 PM PDT
- Prizes: $80,000 total. Grand Prize $25,000. Best Live Agent $10,000.
- Mandatory tech: Gemini Live API or ADK. Google GenAI SDK. At least one Google Cloud service. Hosted on Google Cloud.
- Submission: Public GitHub repo, text description, architecture diagram, demo video under 4 minutes, GCP deployment proof.
- Bonus points: Blog post with #GeminiLiveAgentChallenge (+0.6 pts), automated cloud deployment in repo (+0.2 pts), GDG membership (+bonus).

---

## Architecture Overview

The system has three layers connected by WebSockets:

**Layer 1: Browser (React frontend)**

The browser handles all user-facing interaction. It captures the user's IDE screen using the getDisplayMedia() browser API at approximately 1 frame per second. Each frame is resized to 768x768 pixels and encoded as a base64 JPEG. It simultaneously captures microphone audio using getUserMedia() as 16-bit PCM at 16kHz mono. Both the screen frames and audio are sent to the backend through a single WebSocket connection. The browser also receives audio responses from the backend through the same WebSocket and plays them through the speakers using the Web Audio API at 24kHz. The UI shows session controls (start, stop), the current Flow Mode, the Learning Pulse indicator, and the Session Summary when a session ends.

**Layer 2: Backend (FastAPI + Python)**

The backend is a Python FastAPI server with a single WebSocket endpoint at /ws/session. When a browser connects, the backend opens a corresponding Gemini Live API session using the google-genai SDK's client.aio.live.connect() method. The backend acts as a proxy: it receives screen frames and audio from the browser WebSocket and forwards them to the Gemini WebSocket. It receives audio responses from Gemini and relays them back to the browser WebSocket. The backend also manages the session lifecycle (starting, stopping, error recovery) and holds the system prompt configuration that defines CodeWhisper's personality and behavior. The backend does NOT process audio or images itself — it just routes data between the browser and Gemini.

**Layer 3: Gemini Live API (Google)**

The Gemini Live API is Google's real-time bidirectional streaming API. We use the model gemini-2.5-flash-native-audio-preview-12-2025 which supports native audio input/output and vision input simultaneously over a persistent WebSocket connection. Gemini receives the screen frames (sees the IDE), receives the mic audio (hears the user), and generates audio responses (speaks explanations). Gemini handles Voice Activity Detection (VAD) natively — it detects when the user starts speaking and automatically interrupts its own output. Gemini also maintains session memory within the WebSocket connection, so it remembers everything it has seen and heard during the session. The system prompt (sent at connection time) defines CodeWhisper's personality, Flow Modes, Danger Zone behavior, and all other intelligent behavior.

**Deployment:**

For local development, Docker Compose runs the backend and frontend as two containers. For production/hackathon submission, a single Docker container on Google Cloud Run serves both the FastAPI backend and the React frontend (static files served by FastAPI). The only required environment variable is GEMINI_API_KEY.

---

## Tech Stack

**Frontend:**
- React 18+ — UI framework.
- Tailwind CSS 3+ — styling.
- Vite 5+ — build tool and dev server.
- getDisplayMedia() — browser-native screen capture API.
- getUserMedia() — browser-native microphone capture API.
- Web Audio API / AudioWorklet — low-latency PCM audio playback.
- WebSocket (browser native) — bidirectional communication with backend.

**Backend:**
- Python 3.12+ — language. Gemini SDK is Python-first.
- FastAPI 0.100+ — async web framework with native WebSocket support.
- asyncio — Python's async runtime. Required for Gemini Live API's async interface.
- google-genai (latest) — official Google SDK for Gemini Live API. Provides client.aio.live.connect() for bidirectional streaming.
- uvicorn — ASGI server to run FastAPI.
- python-dotenv — load environment variables from .env file.

**AI:**
- Gemini Live API — Google's real-time bidirectional audio + vision streaming API.
- Model: gemini-2.5-flash-native-audio-preview-12-2025 — native audio model with vision support, bidirectional streaming, VAD, interruption handling, affective dialog.

**Infrastructure:**
- Docker + Docker Compose — containerized local development, one-command startup.
- Google Cloud Run — serverless container hosting for production. Required by hackathon.
- Cloud Build / cloudbuild.yaml (optional) — automated deployment for bonus points.

---

## Project Structure

```
D:\LinkedIn\CodeWhisper\
|
|-- PROJECT.md                  # This file. Single source of truth.
|-- .cursorrules                # Coding rules Cursor must follow.
|-- .env.example                # Template for environment variables.
|-- .env                        # Local env vars (gitignored).
|-- .gitignore
|-- docker-compose.yml          # One-command local development setup.
|-- README.md                   # Public-facing GitHub docs for judges.
|
|-- docs/                       # Phase specs and project documentation.
|   |-- PHASE_1_SPEC.md         # Project Setup + Backend Foundation
|   |-- PHASE_2_SPEC.md         # Gemini Live API Integration
|   |-- PHASE_3_SPEC.md         # Frontend Foundation
|   |-- PHASE_4_SPEC.md         # End-to-End Integration
|   |-- PHASE_5_SPEC.md         # System Prompt + Brain
|   |-- PHASE_6_SPEC.md         # Session Summary + Learning Pulse
|   |-- PHASE_7_SPEC.md         # UI Polish + Branding
|   |-- PHASE_8_SPEC.md         # Deploy + Ship
|   |-- architecture.png        # Architecture diagram for Devpost.
|
|-- backend/
|   |-- Dockerfile              # Backend container definition.
|   |-- requirements.txt        # Python dependencies with versions.
|   |-- main.py                 # FastAPI app. Entry point. Defines the
|   |                           # WebSocket endpoint /ws/session and
|   |                           # health check endpoint /health. Serves
|   |                           # React static files in production.
|   |-- config.py               # All configuration. Reads .env vars.
|   |                           # Defines GEMINI_MODEL, sample rates,
|   |                           # frame rate, frame size, host, port.
|   |-- gemini_session.py       # Manages the Gemini Live API connection.
|   |                           # Opens session with client.aio.live.connect().
|   |                           # Sends audio + frames to Gemini.
|   |                           # Receives audio responses from Gemini.
|   |                           # Handles connection lifecycle and errors.
|   |-- session_manager.py      # Manages the full session lifecycle.
|   |                           # Coordinates between browser WebSocket
|   |                           # and Gemini session. Handles start, stop,
|   |                           # error recovery, and cleanup.
|   |-- audio_handler.py        # Audio format utilities. Validates PCM
|   |                           # format, handles buffering, manages
|   |                           # chunks for smooth streaming.
|   |-- frame_handler.py        # Screen frame utilities. Validates
|   |                           # base64 JPEG, handles frame throttling
|   |                           # (ensures ~1 FPS), resizes if needed.
|   |-- prompts/
|       |-- system_prompt.py    # The master system prompt. Defines
|                               # CodeWhisper's personality, narration
|                               # behavior, Flow Modes, Danger Zone
|                               # alerts, Adaptive Depth, and all
|                               # other intelligent behavior. This is
|                               # the brain of the product.
|
|-- frontend/
    |-- Dockerfile              # Frontend container definition.
    |-- package.json            # Node dependencies.
    |-- vite.config.js          # Vite configuration. Dev server proxy
    |                           # to backend for WebSocket during dev.
    |-- index.html              # HTML entry point.
    |-- tailwind.config.js      # Tailwind configuration.
    |-- postcss.config.js       # PostCSS config for Tailwind.
    |-- src/
        |-- main.jsx            # React entry point. Renders App.
        |-- App.jsx             # Main app component. Manages session
        |                       # state, renders all child components,
        |                       # coordinates hooks.
        |-- hooks/
        |   |-- useWebSocket.js     # Manages WebSocket connection to
        |   |                       # backend. Handles connect, disconnect,
        |   |                       # reconnect, send messages, receive
        |   |                       # messages. Exposes send() and
        |   |                       # onMessage callback.
        |   |-- useScreenCapture.js # Manages screen sharing. Calls
        |   |                       # getDisplayMedia(), captures frames
        |   |                       # at ~1 FPS using canvas, resizes to
        |   |                       # 768x768, converts to base64 JPEG,
        |   |                       # exposes start/stop and frame data.
        |   |-- useAudioInput.js    # Manages microphone. Calls
        |   |                       # getUserMedia(), captures PCM audio
        |   |                       # at 16kHz mono using AudioWorklet
        |   |                       # or ScriptProcessorNode, exposes
        |   |                       # start/stop and audio chunks.
        |   |-- useAudioOutput.js   # Manages speaker playback. Receives
        |   |                       # PCM audio chunks (24kHz mono),
        |   |                       # queues them, plays through Web
        |   |                       # Audio API with smooth buffering.
        |   |                       # Handles gaps and interruptions.
        |   |-- useSession.js       # High-level session orchestrator.
        |                           # Coordinates all other hooks.
        |                           # Manages session state (idle,
        |                           # connecting, active, ending, ended).
        |                           # Handles the start/stop flow.
        |-- components/
        |   |-- SessionControls.jsx # Start Session / End Session buttons.
        |   |                       # Disabled states based on session
        |   |                       # status. Shows "Connecting..." during
        |   |                       # setup.
        |   |-- FlowModeIndicator.jsx # Shows which Flow Mode is active
        |   |                         # (Sportscaster, Catch-Up, Review).
        |   |                         # Updates when mode switches via
        |   |                         # voice command.
        |   |-- StatusBar.jsx       # Shows connection status (connected,
        |   |                       # disconnected), session status (idle,
        |   |                       # active), and Gemini status (listening,
        |   |                       # speaking, processing).
        |   |-- LearningPulse.jsx   # Understanding score indicator.
        |   |                       # Progress ring or percentage that
        |   |                       # updates in real-time based on how
        |   |                       # much code was explained vs skipped.
        |   |-- SessionSummary.jsx  # End-of-session summary display.
        |   |                       # Shows text summary with sections:
        |   |                       # what was built, key concepts, danger
        |   |                       # zones, things to review. Download
        |   |                       # as markdown button.
        |   |-- Header.jsx         # App header. CodeWhisper logo/name,
        |                          # tagline, minimal branding.
        |-- utils/
        |   |-- audioUtils.js      # PCM encoding/decoding helpers.
        |   |                      # Float32 to Int16 conversion,
        |   |                      # sample rate validation, chunk
        |   |                      # size calculations.
        |   |-- frameUtils.js      # Frame capture helpers. Canvas
        |                          # resize logic, JPEG quality
        |                          # settings, base64 encoding,
        |                          # frame rate throttling.
        |-- styles/
            |-- globals.css        # Tailwind base/components/utilities
                                   # imports. Any custom global styles.
```

---

## Features — Complete List

### Core Features

These are the features without which the product does not function. They form the base that all other features build on.

**C1. Screen Watching**

What it does: Captures the user's IDE screen and sends visual frames to Gemini so it can "see" what the developer is looking at.

How it works: The browser calls getDisplayMedia() which shows the user a picker to select which window or screen to share. Once selected, a canvas element captures one frame per second from the video stream. Each frame is resized to 768x768 pixels (Gemini's optimal input resolution for video frames) and converted to a base64-encoded JPEG. The frame is sent to the backend through the WebSocket, which forwards it to the Gemini Live API as an image input.

Why 1 FPS: Gemini Live API supports video input at 1 FPS. Code does not change faster than once per second in most cases. This keeps bandwidth low (each frame is roughly 50-100KB as JPEG) and avoids flooding the connection.

Why 768x768: This is Gemini's recommended resolution for video frame inputs. It provides enough detail to read code on screen while keeping the data size manageable.

Tool-agnostic: Because we capture the screen (not the IDE internals), CodeWhisper works with any tool visible on screen. Cursor, VS Code, a terminal running Claude Code, a browser tab with Replit — anything.

**C2. Bidirectional Voice**

What it does: Enables real-time two-way voice communication between the user and Gemini.

How it works (user to Gemini): The browser captures microphone audio using getUserMedia() as 16-bit PCM at 16kHz mono. The raw PCM data is chunked and sent to the backend via WebSocket, which forwards it to the Gemini Live API.

How it works (Gemini to user): Gemini generates audio responses as 16-bit PCM at 24kHz mono. The audio bytes are sent from Gemini to the backend via WebSocket, then relayed to the browser. The browser plays the audio through the speakers using the Web Audio API.

Why PCM and not MP3/WAV: The Gemini Live API works with raw PCM audio natively. No encoding/decoding overhead means lower latency. The browser's Web Audio API can play raw PCM directly.

Full-duplex: Both directions operate simultaneously. The user can speak while Gemini is still talking (this triggers the interruption mechanism described in C3).

**C3. Interrupt & Ask**

What it does: Allows the user to speak up at any time — even while Gemini is mid-sentence — to ask a question or make a comment. Gemini stops talking, listens, responds, then resumes.

How it works: Gemini Live API has built-in Voice Activity Detection (VAD). When it detects that the user has started speaking, it automatically interrupts its own audio output. The user's speech is processed in the context of the full session (everything Gemini has seen and heard so far). After Gemini responds to the user's question, it can resume narration naturally.

Why this matters: This is what makes CodeWhisper feel like a real conversation, not a chatbot. No "push to talk" button. No waiting for Gemini to finish. Just speak naturally, like talking to a person.

What we build: Nothing — this is entirely handled by Gemini's VAD. Our job is to make sure the WebSocket pipeline is low-latency enough that interruptions feel responsive (target: under 500ms from user speech to Gemini stopping).

**C4. Session Memory**

What it does: Within a single coding session, Gemini remembers everything it has seen and heard. It does not repeat itself, can reference earlier explanations, and builds a progressively richer understanding of the codebase.

How it works: The Gemini Live API maintains session state automatically within a WebSocket connection. Every frame sent, every audio exchange, every explanation given — all stay in Gemini's context window for the duration of the session. When the user asks "how does this connect to what we saw earlier?", Gemini can reference previous explanations.

Limitations: Session memory is limited by Gemini's context window. For typical sessions (30-60 minutes), this should be sufficient. For the hackathon demo (3-4 minutes), this is a non-issue. We do not need to build any custom memory management — Gemini handles it natively.

### Headline Feature

**H1. Flow Modes**

What it does: Gives users three distinct modes of interaction, switchable at any time by voice command. This solves the critical UX problem of fast code generation — when Cursor or Claude Code generates hundreds of lines in seconds, CodeWhisper needs different behaviors depending on what the user wants.

**Sportscaster Mode** (default)

Trigger: This is the default mode when a session starts. User can also switch to it by saying "walk me through this" or "start explaining."

Behavior: Continuous running commentary as code appears on screen. When code is being generated rapidly (fast scrolling, many lines appearing), CodeWhisper gives high-level play-by-play: "OK Cursor is building out the full authentication layer — I see JWT setup, bcrypt hashing, middleware..." When code generation slows or pauses, CodeWhisper goes deeper: "Alright, let me break down what just happened. The main file is auth.js which creates two endpoints..." When nothing is changing on screen, CodeWhisper stays quiet. It does not narrate static screens.

Best for: Learning sessions, exploring new frameworks, wanting full understanding of everything being generated.

**Catch-Up Mode**

Trigger: User says "go quiet" or "stay quiet for a bit" or "I'll ask when I'm ready."

Behavior: Completely silent during active code generation. CodeWhisper continues watching the screen and tracking what happens but does not speak. When there is a natural pause (code generation stops, user stops typing), CodeWhisper may offer a brief summary: "Just so you know, Cursor created 3 new files in that batch..." The user can also explicitly trigger a catch-up by saying "OK what just happened?" or "catch me up" — CodeWhisper then gives a comprehensive summary of everything that changed since it went quiet.

Best for: Experienced developers who want to stay in flow state without constant narration, but want the option to get caught up when they choose.

**Review Mode**

Trigger: User says "just watch for now" or "review mode" or "save it for the end."

Behavior: Completely silent for the entire session. No narration, no summaries, no interruptions (except Danger Zone alerts, which always come through in all modes). CodeWhisper watches and observes everything. When the user says "review time" or "give me the review" or ends the session, CodeWhisper delivers a comprehensive spoken review covering: everything that was built, architecture decisions it observed, code quality observations, security concerns, patterns used, and things the user should understand better.

Best for: Developers who want to vibe code freely without any interruption, then get a full debrief at the end.

**Switching between modes:** Entirely voice-controlled. The user speaks naturally and Gemini understands the intent. No buttons are needed (though the UI shows which mode is currently active). The user can switch as many times as they want during a session. Gemini's system prompt defines how to interpret mode-switching phrases.

### Differentiator Features

**D1. Danger Zone Alerts** (Priority: #1 — must have)

What it does: When CodeWhisper spots security vulnerabilities, bad practices, or risky patterns in the code visible on screen, it proactively warns the user with a distinct verbal cue.

What it watches for:
- Hardcoded API keys, secrets, tokens, or passwords in source code.
- SQL queries built with string concatenation (SQL injection risk).
- Authentication or authorization logic implemented on the client side.
- Missing input validation on user-facing endpoints.
- Sensitive data (emails, passwords, credit cards) exposed in frontend code.
- Missing error handling on network requests or database operations.
- Use of eval(), innerHTML, or other dangerous functions.
- Insecure dependencies or deprecated packages visible in imports.

How it works: The system prompt instructs Gemini to continuously monitor the code visible on screen for these patterns. When detected, Gemini uses a distinct verbal cue to differentiate alerts from normal narration. The cue sounds like: "Quick flag —" or "Heads up —" followed by a brief, specific explanation of the risk and what to do about it. For example: "Heads up — I see an API key hardcoded on line 12. You will want to move that to an environment variable before committing."

Tone: Like a colleague giving a friendly heads-up, not a linter throwing errors. Never alarming, never condescending.

Always active: Danger Zone alerts fire in ALL Flow Modes, including Catch-Up and Review. Even when CodeWhisper is otherwise silent, it will break silence for security issues. This is explicitly defined in the system prompt.

Implementation: Entirely system prompt engineering. No separate code or scanning logic needed.

**D2. Session Summary** (Priority: #2 — must have)

What it does: When a session ends, CodeWhisper generates a comprehensive summary of everything that happened during the coding session.

Trigger: User clicks "End Session" button OR says "let's wrap up" or "end session" or "that's it for today."

What the summary contains:
- What was built: A high-level description of the code/features created during the session.
- Key concepts: Programming patterns, libraries, and architectural decisions that were used.
- Danger zones: Any security or quality issues that were flagged during the session.
- Things to review: Specific areas the user should study or understand better.
- Recommended next steps: What to do next based on the session's context.

Delivery: The summary is delivered in two ways simultaneously. First, Gemini speaks the summary aloud (audio). Second, the summary text is displayed in the frontend UI in a dedicated SessionSummary component. The text version can optionally be downloaded as a markdown file.

Implementation: When the session end is triggered, the backend sends a specific prompt to Gemini asking it to summarize the session. The response is both played as audio and captured as text for display. The frontend SessionSummary component renders the text with proper formatting.

**D3. Adaptive Depth / "Explain Like I'm..."** (Priority: #3 — should have)

What it does: The user can control how deep or shallow CodeWhisper's explanations go, using natural voice commands. This makes CodeWhisper useful for developers of ALL skill levels.

How it works: The system prompt defines a default explanation depth (mid-level developer — assumes some coding experience). The user can shift this up or down at any time during the session by speaking naturally:

- "Explain like I'm new to React" — CodeWhisper switches to beginner level. Explains what hooks are, what JSX is, walks through fundamentals step by step.
- "Keep it senior level" — CodeWhisper goes high-level. Focuses only on architecture decisions, performance implications, unusual patterns, and gotchas. Skips basics.
- "Go deeper on that" — CodeWhisper gives a detailed deep-dive on the last thing it explained.
- "Skip the basics" — CodeWhisper stops explaining fundamental concepts and focuses on what is novel or unusual.
- "Explain everything" — Returns to full beginner-friendly explanations.

Persistence: The depth setting persists for the rest of the session (or until changed again). If the user says "explain like I'm new to Python" at the start, all subsequent explanations will be at that level until they say otherwise.

Implementation: Entirely system prompt engineering. The prompt defines how to interpret depth-related phrases and how to adjust explanation style accordingly.

**D4. Learning Pulse** (Priority: #4 — cut if behind schedule)

What it does: A real-time visual indicator in the UI that shows how much of the session's code the user has engaged with and understood versus how much was just accepted blindly.

What it tracks:
- Code changes detected: How many times new or changed code appeared on screen.
- Explanations given: How many of those code changes CodeWhisper explained.
- Questions asked: How many times the user interrupted to ask a question.
- Danger zones flagged: How many security/quality issues were identified.

Display: A progress ring or percentage displayed in the UI that updates in real-time. For example: "Understanding: 78%." The score increases when CodeWhisper explains code and when the user asks questions. It decreases when code changes happen without explanation (e.g., in Catch-Up mode during fast generation).

Inclusion in summary: The final Learning Pulse score is included in the Session Summary.

Implementation: This is the most complex differentiator. It requires frontend state tracking (counting events), backend event signaling (marking when explanations happen), and a UI component (the progress ring). If the team is behind schedule, this feature is the first to be cut.

**D5. Spotlight / "Rewind & Explain"** (Priority: #5 — free, already built into core)

What it does: The user can point at anything currently visible on their screen and ask about it. CodeWhisper looks at the screen, identifies what the user is referring to, and gives a focused deep-dive explanation.

Examples:
- "What does that function at the top do?"
- "Explain that block of code in the middle."
- "What is that import for?"
- "Why is there a try-catch around that?"
- "What does line 15 do?"

How it works: This is not a separate feature requiring additional engineering. It is the natural combination of screen watching (C1) + interrupt and ask (C3) + session memory (C4). When the user asks about something on screen, Gemini can see the current screen frame, understand spatial references ("at the top," "in the middle," "line 15"), and provide a focused explanation.

Why it is a named feature: Even though it requires no additional code, it is a powerful capability that should be highlighted in the demo video and pitch. It demonstrates Gemini's vision understanding in a tangible, impressive way. During the demo, showing someone scroll through code and ask "what does that do?" with CodeWhisper answering correctly by looking at the screen is a strong visual moment.

Works in all modes: Spotlight questions are always available regardless of Flow Mode. Even in Review Mode (where CodeWhisper is otherwise silent), the user can ask about specific code and get an answer.

### Personality

CodeWhisper's personality is defined entirely in the system prompt and applies across all features and modes.

**Character: Friendly senior developer.**

Core traits:
- Casual but knowledgeable. Talks like a colleague who happens to be really good at their job, not like a professor giving a lecture. Uses natural conversational language.
- Encouraging. Focuses on what the code is doing and why, not what is wrong with it. Uses phrases like "nice, so what Cursor did here is..." instead of "this code has problems."
- Concise. Does not over-explain things the user likely already knows. Focuses on what is interesting, unusual, or important. If something is straightforward boilerplate, a brief mention is enough.
- Honest about risks. When flagging Danger Zone issues, speaks directly and clearly. Does not sugarcoat security problems. But frames them as things to fix, not failures.
- Adaptive. Adjusts to the user's apparent skill level and energy. If the user asks basic questions, CodeWhisper adjusts to explain more fundamentals. If the user asks advanced questions, CodeWhisper matches that level.
- Light humor allowed. Natural and occasional, never forced. "OK Cursor went full beast mode on that one, let me break it down." Not constant jokes, just personality.
- Never condescending. Phrases like "you probably know this but..." or "as you should know..." are explicitly banned in the system prompt. CodeWhisper assumes the user is capable and treats questions as genuinely interesting, not obvious.

---

## What We Are NOT Building

These are explicit scope cuts. If Cursor tries to add any of these, redirect it back to the spec.

- No user accounts or login. The app has no authentication. Anyone who opens it can use it.
- No database. There is no persistent storage of any kind. Sessions are ephemeral.
- No saved sessions or history. When a session ends, the data is gone. The only persistence is the optional markdown download of the session summary.
- No IDE plugin or extension. CodeWhisper is a standalone web app. It does not integrate with VS Code, Cursor, or any other IDE.
- No code editing. CodeWhisper never writes, modifies, or touches the user's code. It only observes and explains.
- No multi-user or collaboration features. One user per session.
- No mobile app. Browser only.
- No time-travel through past screen frames. CodeWhisper can only see the current screen. It cannot replay or revisit earlier frames.
- No code annotation overlay. CodeWhisper does not visually highlight code on the shared screen. (Stretch goal only.)
- No multi-language explanations. CodeWhisper speaks English only. (Stretch goal only.)

---

## Phase Breakdown

| Phase | Name | What It Delivers |
|-------|------|-----------------|
| 1 | Project Setup + Backend Foundation | Project structure, Docker Compose, FastAPI server with WebSocket endpoint, config module, health check endpoint. A running backend that accepts WebSocket connections and responds to health checks. |
| 2 | Gemini Live API Integration | Backend connects to Gemini Live API using google-genai SDK. Can open a session, send text and audio, receive audio responses. Session open/close lifecycle works. Audio format handling validated. |
| 3 | Frontend Foundation | React app built with Vite + Tailwind. Screen capture hook working independently. Mic capture hook working independently. Speaker playback hook working independently. WebSocket hook connecting to backend. Session controls UI rendered. All hooks tested in isolation. |
| 4 | End-to-End Integration | Frontend and backend fully wired. Screen frames flow from browser through backend to Gemini. Mic audio flows from browser through backend to Gemini. Gemini audio responses flow back through backend to browser speakers. User can share screen, speak, and hear Gemini respond about what it sees. The full loop works. |
| 5 | System Prompt + Brain | Master system prompt written and tested. Proactive narration working (Gemini explains code it sees without being asked). All three Flow Modes working and switchable by voice. Danger Zone alerts firing on security issues. Adaptive Depth responding to skill-level commands. Spotlight working (user asks about specific code on screen). Personality feeling right. |
| 6 | Session Summary + Learning Pulse | End-of-session summary delivered as spoken audio and displayed as text in the UI. Markdown download working. Learning Pulse tracking and UI component showing real-time understanding score. (Learning Pulse may be cut if behind schedule.) |
| 7 | UI Polish + Branding | Professional visual design applied. All status indicators working (connection, session, Gemini speaking/listening). Flow Mode indicator visible. Loading and error states handled. Responsive layout. CodeWhisper branding (name, tagline, logo/icon). The app looks demo-ready, not like a hackathon prototype. |
| 8 | Deploy + Ship | Dockerfile working. Deployed to Google Cloud Run. cloudbuild.yaml for automated deployment (bonus points). README.md with full setup instructions. Architecture diagram created. Demo video recorded (under 4 minutes). Blog post published. GDG profile created. Everything submitted to Devpost before deadline. |

---

## Environment Variables

The only required variable is GEMINI_API_KEY. All others have sensible defaults.

```
# .env.example

# Required — get your key at https://aistudio.google.com/apikey
GEMINI_API_KEY=your_gemini_api_key_here

# Optional (defaults shown)
GEMINI_MODEL=gemini-2.5-flash-native-audio-preview-12-2025
SEND_SAMPLE_RATE=16000
RECEIVE_SAMPLE_RATE=24000
FRAME_RATE=1
FRAME_SIZE=768
HOST=0.0.0.0
BACKEND_PORT=8000
FRONTEND_PORT=3000
```

---

## How Users Run CodeWhisper

### With Docker (recommended)

Prerequisites: Docker and Docker Compose installed. A Gemini API key.

Steps:
1. Clone the repository.
2. Copy .env.example to .env.
3. Add your GEMINI_API_KEY to the .env file.
4. Run: docker compose up
5. Open http://localhost:3000 in your browser.
6. Click "Start Session", select your IDE window to share, allow microphone access.
7. Start coding. CodeWhisper will begin explaining what it sees.

### Without Docker (development)

Prerequisites: Python 3.12+, Node.js 18+, a Gemini API key.

Steps:
1. Clone the repository.
2. Copy .env.example to .env and add your GEMINI_API_KEY.
3. Start the backend: cd backend, pip install -r requirements.txt, uvicorn main:app --host 0.0.0.0 --port 8000 --reload
4. Start the frontend: cd frontend, npm install, npm run dev
5. Open http://localhost:3000 in your browser.

---

## Hackathon Submission Checklist

- [ ] Public GitHub repo with full source code.
- [ ] README.md with spin-up instructions that judges can follow to reproduce.
- [ ] Text description (approximately 400 words) covering features, tech used, learnings.
- [ ] Architecture diagram showing browser to FastAPI to Gemini Live API to Google Cloud.
- [ ] Demo video under 4 minutes showing real vibe coding session with all features.
- [ ] GCP deployment proof: screen recording of Cloud Run console OR code file showing Google Cloud API usage.
- [ ] Bonus: Blog post on dev.to or Medium with #GeminiLiveAgentChallenge (+0.6 pts).
- [ ] Bonus: Automated deployment script (cloudbuild.yaml) included in repo (+0.2 pts).
- [ ] Bonus: GDG profile link provided (+bonus pts).

---

## Demo Video Script (under 4 minutes)

**0:00 to 0:30 — The Problem**
"Every day, millions of developers accept AI-generated code they don't understand. They ship faster, but learn nothing. When it breaks, they can't fix it." Show stats: 45% struggle debugging AI code, 1.7x more bugs, startups shutting down.

**0:30 to 1:00 — The Solution**
"CodeWhisper watches your screen and explains what's happening — through voice. No plugins, no integration. Just share your screen and start coding." Show the app opening, clicking Start Session, selecting the IDE window, allowing mic.

**1:00 to 2:00 — Sportscaster Mode**
Live demo: Open Cursor, prompt it to build something (e.g., "build a REST API for user auth"). Cursor generates code rapidly. CodeWhisper narrates: high-level during fast generation, deeper when it pauses. Show the natural flow.

**2:00 to 2:30 — Spotlight**
Scroll through the generated code. Point at a function: "What does this middleware do?" CodeWhisper looks at the screen and explains. Point at an import: "What's that library?" CodeWhisper answers.

**2:30 to 2:45 — Danger Zone**
Show code with a hardcoded API key. CodeWhisper catches it: "Quick flag — that API key is hardcoded on line 12. Move it to an environment variable."

**2:45 to 3:00 — Flow Mode Switch**
Say "go quiet for a bit." CodeWhisper goes to Catch-Up mode. Generate more code in silence. Say "OK what just happened?" CodeWhisper summarizes the new code.

**3:00 to 3:15 — Adaptive Depth**
Say "explain like I'm new to Express." CodeWhisper shifts to beginner level for the next explanation. Show the difference in depth.

**3:15 to 3:45 — Session Summary**
Say "let's wrap up." CodeWhisper delivers a spoken summary. The text summary appears in the UI. Show the key sections: what was built, concepts used, things to review.

**3:45 to 4:00 — Closing**
"CodeWhisper. Vibe code without losing the mental model." Flash the architecture diagram. Show the tech stack. Display the GitHub repo URL.
