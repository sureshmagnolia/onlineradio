# Broadcaster Studio Web App

You can absolutely have a Web App (PWA) that runs on your phone or PC! It allows you to skip third-party software (like BUTT) and bypass terminal scripts entirely. You will be able to just visit a hidden URL on your radio station (e.g., `https://onlineradio.onrender.com/studio`), log in, and hit a big "Go Live" button from your Android phone browser!

## User Review Required

> [!IMPORTANT]
> The Web App uses standard HTML5 Web Audio and a lightweight Javascript MP3 encoder. This requires microphone permissions to be granted in your browser (Chrome/Edge/Safari). Are you okay with accessing this via a hidden `/studio` URL on your existing server?

## Proposed Changes

We will build the Broadcaster Studio directly into your existing `server.py` so you don't need any extra servers.

### C:\Users\sures\onlineradio\server.py

#### [MODIFY] server.py
- Add a new route `/studio` that serves the new Broadcaster Web App HTML.
- Add a new secure endpoint `POST /api/stream` that accepts chunks of MP3 audio from the web app.
- Update the server logic to automatically switch to `LIVE` mode as soon as chunks arrive from the web app, and smoothly transition back to AutoDJ if the web app stops sending for 5 seconds.

### C:\Users\sures\onlineradio\studio.html (Internal to server.py)

#### [NEW] studio.html (String variable inside server.py)
- Build a beautiful, mobile-friendly interface with a big microphone button.
- Integrate `lame.min.js` (a pure Javascript MP3 encoder) to encode your microphone audio to 128kbps MP3 directly on your phone.
- Use the standard `fetch` API to continuously upload 2-second chunks of MP3 audio to the `POST /api/stream` endpoint.
- Include a visual volume meter so you can see your microphone levels while broadcasting.
- Add "Add to Home Screen" Web App capabilities (manifest) so it looks and feels like a native Android app!

## Verification Plan

### Manual Verification
1. I will deploy the updated server to GitHub and Render.
2. You will open `https://onlineradio.onrender.com/studio` on your Android phone or PC.
3. You will grant microphone permissions, enter your broadcast password, and tap "Go Live".
4. We will verify that the main website player seamlessly switches to your live voice and switches back when you stop!
