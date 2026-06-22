# XtreamRip

XtreamRip is a modern, cross-platform desktop application built with Tauri, React, and TypeScript. It allows you to browse and download content from Xtream Codes IPTV providers.

## Features

- **Direct Connection:** Connects directly to the IPTV server from your local machine, bypassing CORS restrictions without the need for complex serverless proxies.
- **Dynamic Login:** Securely log in using your provider's Server URL, your username, and password. Credentials are saved locally on your device.
- **Browse & Search:** Easily browse through series and movies, filter by genres, and search for specific titles.
- **Built-in Player:** Watch content directly within the app.
- **Direct Downloads:** Download movies, individual episodes, or entire seasons directly to your computer.
- **Sleek UI:** A modern, responsive, and hardware-accelerated user interface.

## Prerequisites

To build this project from source, you need to have the following installed:

- [Node.js](https://nodejs.org/) (v18 or later)
- [Rust](https://www.rust-lang.org/) (latest stable)
- [Tauri CLI prerequisites](https://tauri.app/v1/guides/getting-started/prerequisites) for your operating system.

## Getting Started

1. **Install dependencies:**

   ```bash
   npm install
   ```

2. **Run in development mode:**

   This will start the Vite development server and open the Tauri app window.

   ```bash
   npm run tauri dev
   ```

## Building for Production

To create a standalone executable for your operating system (e.g., an `.exe` installer for Windows):

```bash
npm run tauri build
```

The built installers and executables will be located in the `src-tauri/target/release/bundle/` directory.

## Technology Stack

- **Frontend:** React, TypeScript, Vite, Tailwind CSS, Lucide React
- **Backend/Desktop Integration:** Tauri (Rust)
