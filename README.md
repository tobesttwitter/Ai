# GitHub Models Chat

A mobile-first, installable PWA that calls the GitHub Models OpenAI-compatible API directly from the browser. There is no server or build step.

## Files

- `index.html` — complete app UI, API client, local history/settings
- `manifest.json` — PWA metadata
- `sw.js` — minimal offline shell cache
- `icon-192.png`, `icon-512.png` — install icons

## GitHub Personal Access Token

1. Sign in to GitHub.
2. Open **Settings → Developer settings → Personal access tokens**.
3. Create a token appropriate for your account (fine-grained tokens are recommended where supported).
4. Grant the **Models / models:read** permission requested by GitHub Models.
5. Copy the token and paste it into the app's **Settings** panel.

The token is stored only in the browser's localStorage and is sent by the app only to `https://models.github.ai/inference/chat/completions`. Never commit a token to this repository.

> Browser storage is not a hardware security vault. Anyone with access to the same browser profile/device may potentially access localStorage. Revoke the token from GitHub if the device is lost or compromised.

## GitHub Pages

1. Push these files to the repository's **main** branch.
2. On GitHub, open **Settings → Pages**.
3. Under **Build and deployment**, choose **Deploy from a branch**.
4. Select **main** and the **/(root)** folder, then save.
5. Open the Pages URL shown by GitHub.

No Actions workflow or build command is required.

## Add to Home Screen

### Android

Open the GitHub Pages URL in Chrome, then use the browser menu and choose **Add to Home screen** or **Install app**. Confirm the prompt.

### iPhone / iPad

Open the GitHub Pages URL in Safari, tap **Share**, choose **Add to Home Screen**, then tap **Add**.

## Models included

- `openai/gpt-4o-mini`
- `openai/gpt-4o`
- `meta/Llama-4-Maverick-17B-128E-Instruct`
- `deepseek/DeepSeek-R1`

## Notes

Assistant messages are rendered with marked.js and code blocks are highlighted with highlight.js. Chat history, selected model, system prompt, and token are stored locally. Streaming uses the browser Fetch API and ReadableStream.
