# Frontend UI Brief — mobile-first PWA rebuild

> UI/UX only. This does not cover API wiring — read `docs/api-contract.md` separately for that.

## The problem with the current build

The current app (`frontend/`) is rendering like a scaled-down desktop marketing page — wide canvas, content pinned to the left, a header nav bar spanning full width, huge empty margins. It is not mobile-first: it looks like a website that happens to work on a phone, not a phone-native PWA. The copy and basic idea (serif italic headline, orb button, hairline dark UI) are already close to right — the execution of layout, scale, and viewport is what's wrong.

**Fix the execution, don't start over on the concept.** Target viewport: 375–430px wide (actual phone), full-bleed, single column, everything stacked vertically, safe-area padding for notch/home-indicator on both ends. No fixed desktop-width containers anywhere. No header nav bar — this is not a website.

## The 5-screen flow — build exactly this, nothing more

Reference: the "01–05" phone-mockup strip already agreed on. Five screens, one linear flow, `useState` transitions per `AGENTS.md` (single route, no router-per-screen):

**01 · ARRIVE**
- Centered vertically in the top-third: "न्याय-दोस्त" wordmark + one-line tagline below it ("अपना कानूनी हक़, अपनी भाषा में सुनिए").
- Two stacked tap targets below, thumb-reachable in the lower half of the screen:
  - Primary: filled white pill, black text, mic icon + "बोलिए" label.
  - Secondary: outlined/ghost pill, white hairline border, camera icon + "फ़ोटो लें" with a smaller English sub-label ("Photograph the notice").
- Nothing else on screen. No form fields, no login, no onboarding carousel.

**02 · LISTEN (the home/recording screen)**
- Small-caps gray status label top-left: "CONNECTED".
- The orb, centered, large, glowing white circle on black — this is the whole visual center of the screen.
- Below the orb, a small status line: "सुन रहा हूँ…" (listening).
- Live transcript appears in a rounded bubble below that as speech is recognized, growing as more is said.
- Bottom bar: camera icon (small, secondary) + a red filled circular record/stop button (primary, larger). Thin horizontal scrub/progress hairline at the very bottom edge.

**03 · SHOW (document capture)**
- Small-caps gray label top-center: "DOCUMENT".
- One camera viewfinder frame filling most of the screen — corner brackets only (⌐ ⌐ / ⌐ ⌐ style), no grid overlay, no filter carousel, no crop step.
- Single shutter button below the frame (orb-style white circle), label "नोटिस की फोटो लें". One tap, one capture — no retake gallery/multi-shot picker.

**04 · THINK (processing)**
- The orb again, but visually tighter/smaller and pulsing faster than the listening state — this state must read as visually distinct from "listening," not the same animation.
- One status line below: "जाँच हो रही है…"
- **Exactly one** secondary status line below that, small-caps gray, stating what's actually being checked right now: e.g. "VERIFYING AGAINST RBI DIGITAL LENDING DIRECTIONS, 2025". Never a multi-step spinner list ("Uploading… Transcribing… Analyzing…") — one honest line that can update in place, not stack.

**05 · KNOW (the verdict)**
- Top: a small risk badge, left-aligned, colored (red/orange dot + text) — e.g. "● उच्च जोखिम · ILLEGAL THREAT".
- Immediately below: the plain-language verdict as a large headline — this is the first and biggest thing on screen, e.g. "यह धमकी गैर-कानूनी है। आपको तुरंत गिरफ़्तार नहीं किया जा सकता।"
- Below the headline, small and secondary (not competing with the headline): the citation, e.g. "RBI DLD 2025 · PARA 12" — proof it's grounded, not the lead item.
- Two stacked action buttons at the bottom: primary filled white pill "🔊 सुनें" (hear it spoken), secondary outlined pill "फिर पूछें" (ask again — returns to screen 02, keeping the same session/conversation).

## Design tokens — non-negotiable

- **Colors**: pure `#000000` background, pure `#FFFFFF` text/UI — no warm off-black, no off-white. A single accent (red/orange) only for risk badges and the record button, nothing else.
- **Strokes**: hairline (1px) borders only, never bold/thick borders, never drop shadows.
- **Typography**: serif italic display face for the big emotional/headline moments (screen 01's tagline energy, screen 05's verdict headline) — everything else (labels, status lines, buttons, meta) is a plain grotesk sans. Small-caps, letter-spaced, gray uppercase for every meta/status label ("CONNECTED", "DOCUMENT", "SPEAK NATURALLY").
- **The orb is the single visual centerpiece** — one Canvas-based element, not a static icon. It has exactly three states: idle glow, listening (breathes, reacts to transcript arriving), thinking (tighter, faster pulse, visually distinct from listening). It only exists full-screen during active voice/processing states — no persistent mini-orb badge elsewhere in the UI.
- **Buttons**: two types only. Primary = filled white pill, black text. Secondary = outlined pill, white hairline border, white text. No third button style.
- Everything full-bleed edge-to-edge at real phone width, safe-area-aware top and bottom, primary actions always reachable in the lower half of the screen for one-thumb use.

## What "done" looks like

Load the app on an actual phone (or a 390×844-ish viewport in dev tools) and each of the 5 screens should look exactly like its corresponding mockup — not a smaller version of a desktop layout, not approximately right. If a screen needs horizontal scrolling or content is cut off at real phone width, it's not done.
