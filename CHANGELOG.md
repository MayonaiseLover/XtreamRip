# Changelog

All notable changes to XtreamRip will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [3.0.0] — 2025-06-21

### ✨ Added

- **Quality picker** — choose from Fast Copy, Source, 1080p, 720p, 480p, 360p with estimated file sizes shown before download
- **Hardware H.265 encoding** — automatic `hevc_mediacodec` detection on Android for near-realtime encoding
- **Software H.265 fallback** — `libx265 ultrafast` when hardware encoding isn't available
- **Stream → encode → save pipeline** — FFmpeg encodes directly from stream URL, raw file never touches disk
- **Concurrent downloads** — multiple files at once, auto-capped to server's active connection limit
- **Resume support** — interrupted downloads pick up where they left off
- **Smart skip** — already-downloaded files are detected and skipped automatically
- **Download history** — local log of everything downloaded, with size and date
- **Fuzzy search** — finds results even with partial or slightly wrong spelling
- **Category browsing** — browse series and movies by genre
- **Series info panels** — shows plot, cast, ratings, and year
- **Season & episode picker** — multi-select with "grab all" shortcut
- **Account dashboard** — shows subscription expiry, active connections, and server info
- **Termux notifications** — push alert on Android when a batch finishes
- **Persistent settings** — CRF, workers, download folder saved across sessions

### 🏗️ Infrastructure

- Professional GitHub repository with issue templates, PR template, and contributing guide
- Security policy for responsible vulnerability disclosure
- MIT License

[3.0.0]: https://github.com/MayonaiseLover/XtreamRip/releases/tag/v3.0.0
