# Dispatch: Milestone 3 Explorer 3 — UI State Machine, Dark Styling & Interaction UX

## Objectives
Investigate UI state management, dark mode QSS styling, and UX controls:
1. Application State Machine:
   - States: `UNAUTHENTICATED`, `AUTHENTICATING`, `AUTHENTICATED_IDLE`, `LIVE_STREAMING`, `ONDEMAND_CAPTURING`, `ERROR`.
   - Enabled/disabled states for buttons and inputs across each state (e.g. disable mode toggle during active live streaming; enable mic mute at all times when authenticated).
   - Microphone mute toggle: Icon, color, and text changes (Muted vs Unmuted), immediate synchronization with `AudioPipeline.set_muted(bool)`.
   - On-demand query flow: Input text query field, "Capture & Send" action, loading indicator, and rendering model response text into the transcript.
2. Styling & Visual Polish:
   - Modern dark theme QSS (`gemini_desktop_screenshare/ui/styles.py`): Google Material-inspired dark palette (#202124 background, #303134 surface cards, #1a73e8 primary blue, #34a853 green success badge, #ea4335 red warning/mute badge, #5f6368 borders).
   - High DPI scaling: `QApplication.setHighDpiScaleFactorRoundingPolicy` and Qt DPI attributes.
3. Verification and Headless / Automated Testing Strategy for PyQt6:
   - How can Workers and Reviewers programmatically verify the UI components, hotkey manager, and state transitions without requiring manual human clicks or GUI displays (e.g. `pytest-qt` or `QTest`, creating widgets offscreen or in headless mode `QT_QPA_PLATFORM=offscreen`).

## Inputs
- `c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\ORIGINAL_REQUEST.md`
- `c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\PROJECT.md`
- `c:\Users\Arman\Documents\antigravity\quirky-turing\gemini_desktop_screenshare\`

## Output
Write report to: `c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\explorer_m3_3\handoff.md`


## 2026-11-08T14:31:55Z
You are teamwork_explorer (UI State Machine & Dark Styling Explorer).
Working directory: c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\explorer_m3_3\

Read your dispatch instructions and requirements:
1. c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\ORIGINAL_REQUEST.md (MANDATORY: read first)
2. c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\PROJECT.md
3. c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\explorer_m3_3\DISPATCH.md
4. Existing engine modules in c:\Users\Arman\Documents\antigravity\quirky-turing\gemini_desktop_screenshare\

Investigate and produce an actionable architectural plan for:
- Application UI State Machine:
  - Transition flow across UNAUTHENTICATED, AUTHENTICATING, SIGNED_IN_IDLE, LIVE_STREAMING, ONDEMAND_CAPTURING, ERROR.
  - Button enable/disable matrix for each state.
  - Visual controls for mic mute/unmute (icon, badge, text, color).
  - Transcript view design (auto-scroll, formatting user turns vs model turns).
  - On-demand capture prompt input dialog / dock.
- Dark theme QSS styling:
  - Google Material dark palette (#202124 background, #303134 card surfaces, #1a73e8 primary blue accent, #34a853 connected badge, #ea4335 error/mute badge, #bdc1c6 text).
  - Modern card layouts, rounded corners, clean flat buttons.
- Headless & programmatic verification strategy:
  - Designing UI components so they can be thoroughly tested in headless/CI environments (e.g. via pytest-qt or QTest with QT_QPA_PLATFORM=offscreen).
- Recommend concrete class design and interface signatures for gemini_desktop_screenshare/ui/styles.py and UI widgets.

Write your findings and recommendations to:
c:\Users\Arman\Documents\antigravity\quirky-turing\.agents\teamwork\explorer_m3_3\handoff.md
Update progress.md with your liveness heartbeat. Send a message when finished.
