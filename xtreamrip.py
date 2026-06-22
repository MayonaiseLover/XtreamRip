#!/usr/bin/env python3
"""
XtreamRip — Terminal client for Xtream Codes IPTV
https://github.com/MayonaiseLover/XtreamRip
"""

__version__ = "3.0.0"
__author__  = "Mazen Haitham"

import argparse, json, re, shutil, subprocess, sys, tempfile, threading, time, zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import questionary, requests
from questionary import Style as QStyle
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.rule import Rule
from rich.table import Table

CONFIG_DIR   = Path.home() / ".config" / "xtreamrip"
CREDS_FILE   = CONFIG_DIR / "creds.json"
CONFIG_FILE  = CONFIG_DIR / "config.json"
HISTORY_FILE = CONFIG_DIR / "history.json"

DEFAULT_CFG = {
    "crf": 20, "workers": 2, "download_dir": "",
    "skip_existing": True, "notify": True, "use_arabic_fix": False,
}

ARABIC_FIX_ENABLED = False
console = Console()

STYLE = QStyle([
    ("qmark","fg:ansicyan bold"),("question","bold"),("answer","fg:ansigreen bold"),
    ("pointer","fg:ansicyan bold"),("highlighted","fg:ansicyan"),("selected","fg:ansigreen"),
    ("separator","fg:ansiblack"),("instruction","fg:ansiblack"),
])

BANNER = """\
[bold cyan]
 ██╗  ██╗████████╗██████╗ ███████╗ █████╗ ███╗   ███╗██████╗ ██╗██████╗
 ╚██╗██╔╝╚══██╔══╝██╔══██╗██╔════╝██╔══██╗████╗ ████║██╔══██╗██║██╔══██╗
  ╚███╔╝    ██║   ██████╔╝█████╗  ███████║██╔████╔██║██████╔╝██║██████╔╝
  ██╔██╗    ██║   ██╔══██╗██╔══╝  ██╔══██║██║╚██╔╝██║██╔══██╗██║██╔═══╝
 ██╔╝ ██╗   ██║   ██║  ██║███████╗██║  ██║██║ ╚═╝ ██║██║  ██║██║██║
 ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝╚═╝╚═╝
[/bold cyan][dim]                    v{version}  ·  stream. encode. save.[/dim]
""".format(version=__version__)

CHECKBOX_HINT = "[dim]  SPACE = toggle   ENTER with nothing selected = grab ALL[/dim]"

# ─── Arabic fix ───────────────────────────────────────────────────────────────

def fix_arabic(text: str) -> str:
    if not text or not ARABIC_FIX_ENABLED:
        return text
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except ImportError:
        return text

# ─── Quality tiers ────────────────────────────────────────────────────────────

QUALITY_TIERS = [
    {"key":"copy",   "label":"🚀  Fast copy       no encoding, original size",      "est":"~1–2 GB/ep  (instant, zero CPU)", "crf":None,"scale":None,"hw_br":None},
    {"key":"source", "label":"📺  Source quality  H.265, original resolution",       "est":"~700 MB–1.2 GB/ep",              "crf":20,  "scale":None,         "hw_br":"3000k"},
    {"key":"1080p",  "label":"🔥  1080p HD        H.265",                           "est":"~450–800 MB/ep",                 "crf":20,  "scale":"scale=-2:1080","hw_br":"2500k"},
    {"key":"720p",   "label":"✅  720p            best size / quality balance",      "est":"~200–400 MB/ep",                 "crf":20,  "scale":"scale=-2:720", "hw_br":"1500k"},
    {"key":"480p",   "label":"💾  480p            smaller, still great on a phone", "est":"~100–200 MB/ep",                 "crf":22,  "scale":"scale=-2:480", "hw_br":"800k"},
    {"key":"360p",   "label":"📱  360p            compact, sharing friendly",        "est":"~50–100 MB/ep",                  "crf":26,  "scale":"scale=-2:360", "hw_br":"400k"},
]

def pick_quality(has_hw: bool, default_crf: int) -> tuple[list[str], str]:
    choices = [{"name": f"{t['label']}   [dim]({t['est']})[/]", "value": t} for t in QUALITY_TIERS]
    tier = questionary.select("Pick quality:", choices=choices, style=STYLE).ask()
    if not tier:
        sys.exit(0)

    if tier["key"] == "copy":
        return ["-c:v", "copy", "-c:a", "copy"], "copy (no encode)"

    # ── FIX: always copy audio — never re-encode it ──
    if has_hw:
        args  = ["-c:v", "hevc_mediacodec", "-b:v", tier["hw_br"], "-c:a", "copy"]
        label = f"hw:hevc_mediacodec @ {tier['hw_br']}"
    else:
        crf  = tier["crf"] or default_crf
        args = ["-c:v", "libx265", "-crf", str(crf), "-preset", "ultrafast",
                "-threads", "0", "-c:a", "copy"]
        label = f"sw:libx265 crf{crf}"

    if tier["scale"]:
        args += ["-vf", tier["scale"]]

    return args, f"{tier['key']} · {label}"

# ─── Encoder detection ────────────────────────────────────────────────────────

def has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None

def has_hw_encoder() -> bool:
    if not has_ffmpeg():
        return False
    out = subprocess.run(["ffmpeg","-hide_banner","-encoders"], capture_output=True, text=True).stdout
    return "hevc_mediacodec" in out

# ─── Config ───────────────────────────────────────────────────────────────────

def load_cfg() -> dict:
    if CONFIG_FILE.exists():
        try: return {**DEFAULT_CFG, **json.loads(CONFIG_FILE.read_text())}
        except: pass
    return DEFAULT_CFG.copy()

def save_cfg(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))

def settings_menu(cfg: dict) -> dict:
    console.print(Rule("[bold cyan]Settings[/]"))
    fields = {
        "crf":            ("H.265 CRF quality  (18 = best,  28 = smallest)", int),
        "workers":        ("Concurrent downloads  (1–5)", int),
        "download_dir":   ("Download folder  (blank = current directory)", str),
        "skip_existing":  ("Skip already-downloaded files?  (true/false)", lambda x: x.strip().lower()=="true"),
        "notify":         ("Termux notification when done?  (true/false)",  lambda x: x.strip().lower()=="true"),
        "use_arabic_fix": ("Arabic text fix (turn ON if letters look backwards)  (true/false)",
                           lambda x: x.strip().lower()=="true"),
    }
    for key,(label,cast) in fields.items():
        val = questionary.text(f"{label}:", default=str(cfg[key]), style=STYLE).ask()
        if val is not None:
            try: cfg[key] = cast(val)
            except: pass
    save_cfg(cfg)
    console.print("[green]✓ Settings saved.[/]\n")
    return cfg

# ─── Credentials ──────────────────────────────────────────────────────────────

def load_creds() -> dict | None:
    if CREDS_FILE.exists():
        try: return json.loads(CREDS_FILE.read_text())
        except: return None

def save_creds(server, username, password) -> dict:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    data = {"server": server.rstrip("/"), "username": username, "password": password}
    CREDS_FILE.write_text(json.dumps(data, indent=2))
    return data

def prompt_credentials(existing=None) -> dict:
    console.print(Panel("[bold cyan]⚙  Server Setup[/]", expand=False))
    server   = questionary.text("Server URL:", default=existing["server"] if existing else "", style=STYLE).ask()
    if not server: console.print("[dim]Cancelled.[/]"); sys.exit(0)
    username = questionary.text("Username:", default=existing["username"] if existing else "", style=STYLE).ask()
    password = questionary.password("Password:", style=STYLE).ask()
    creds = save_creds(server, username, password)
    console.print("[green]✓ Credentials saved.[/]\n")
    return creds

# ─── History ──────────────────────────────────────────────────────────────────

def load_history() -> dict:
    if HISTORY_FILE.exists():
        try: return json.loads(HISTORY_FILE.read_text())
        except: pass
    return {"series": {}, "movies": {}}

def save_history(h: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(h, indent=2))

def mark_downloaded(h, cat, key, path, mb):
    h.setdefault(cat, {})[key] = {"path": str(path), "size_mb": round(mb,1), "date": datetime.now().strftime("%Y-%m-%d %H:%M")}
    save_history(h)

def is_downloaded(h, cat, key):
    e = h.get(cat, {}).get(key)
    return bool(e and Path(e["path"]).exists())

def show_library(h: dict) -> None:
    console.print(Rule("[bold cyan]My Library[/]"))
    found = False
    for cat, label in [("series","Series"),("movies","Movies")]:
        items = h.get(cat, {})
        if not items: continue
        found = True
        t = Table("Name","Size","Downloaded", header_style="bold cyan", box=None)
        for k,v in sorted(items.items()):
            t.add_row(k, f"{v['size_mb']} MB", v["date"])
        console.print(Panel(t, title=f"[bold]{label}[/]", border_style="cyan"))
    if not found:
        console.print("[dim]  Nothing downloaded yet.[/]")
    console.print()

# ─── API ──────────────────────────────────────────────────────────────────────

def api_call(creds, action=None, **kwargs):
    params = {"username": creds["username"], "password": creds["password"]}
    if action: params["action"] = action
    params.update(kwargs)
    r = requests.get(f"{creds['server']}/player_api.php", params=params, timeout=40)
    r.raise_for_status()
    return r.json()

def test_connection(creds) -> tuple[bool, dict]:
    try:
        data = api_call(creds)
        return bool(data.get("user_info",{}).get("auth",0)), data
    except: return False, {}

def show_account(data: dict) -> None:
    ui, si = data.get("user_info",{}), data.get("server_info",{})
    exp_ts = ui.get("exp_date")
    if exp_ts and str(exp_ts).isdigit():
        exp_dt = datetime.fromtimestamp(int(exp_ts))
        days   = (exp_dt - datetime.now()).days
        c      = "green" if days>30 else "yellow" if days>7 else "red"
        exp_str = f"[{c}]{exp_dt.strftime('%Y-%m-%d')} ({days}d left)[/{c}]"
    else:
        exp_str = "[dim]unknown[/]"
    sc = "green" if ui.get("status")=="Active" else "red"
    t = Table(box=None, pad_edge=False, show_header=False)
    t.add_column("k", style="dim", width=16); t.add_column("v")
    t.add_row("Account",     f"[bold]{ui.get('username','—')}[/]")
    t.add_row("Status",      f"[{sc}]{ui.get('status','?')}[/{sc}]")
    t.add_row("Expires",     exp_str)
    t.add_row("Connections", f"{ui.get('active_cons','?')} / {ui.get('max_connections','?')} active")
    t.add_row("Server",      si.get("url","—"))
    console.print(Panel(t, title="[bold cyan]Account[/]", border_style="cyan", expand=False))
    console.print()

# ─── Helpers ──────────────────────────────────────────────────────────────────

def sanitize(name: str) -> str:
    name = re.sub(r'[\\/:*?"<>|]', "-", name)
    return re.sub(r'\s+', " ", name).strip()[:120]

def fuzzy_search(items, keyword, key="name"):
    kw = keyword.lower().strip()
    exact = [i for i in items if kw in i.get(key,"").lower()]
    if exact: return exact
    words = kw.split()
    return [i for i in items if all(w in i.get(key,"").lower() for w in words)]

def checkbox_or_all(question, choices, all_items):
    console.print(CHECKBOX_HINT)
    sel = questionary.checkbox(question, choices=choices, style=STYLE).ask()
    if sel is None: return []
    if not sel or "__all__" in sel:
        console.print("[dim]  → all selected[/]"); return all_items
    return sel

def get_download_dir(cfg) -> Path:
    d = cfg.get("download_dir","").strip()
    return Path(d).expanduser() if d else Path.cwd()

def send_notification(title, body):
    try: subprocess.Popen(["termux-notification","--title",title,"--content",body], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError: pass

def show_series_panel(info: dict, name: str) -> None:
    meta  = info.get("info", {})
    plot  = fix_arabic((meta.get("plot") or meta.get("description") or "No description available.")[:240])
    parts = []
    rating = meta.get("rating") or meta.get("rating_5based")
    year   = meta.get("releaseDate") or meta.get("year")
    genre  = fix_arabic(meta.get("genre") or "")
    cast   = fix_arabic(meta.get("cast") or "")
    if rating or year or genre:
        parts.append("  ".join(filter(None,[
            f"⭐ {rating}" if rating else None,
            f"📅 {year}"   if year   else None,
            f"🎭 {genre}"  if genre  else None,
        ])))
    parts.append(f"\n[dim]{plot}[/]")
    if cast:
        parts.append(f"\n[dim]Cast: {', '.join(cast.split(',')[:4])}[/]")
    console.print(Panel("\n".join(parts), title=f"[bold cyan]{fix_arabic(name)}[/]", border_style="cyan", expand=False))
    console.print()

# ─── Download engine ──────────────────────────────────────────────────────────

def _transcode(url: str, dest: Path, enc_args: list[str],
               progress: Progress, task_id: int,
               has_hw: bool = False, crf: int = 20) -> float:
    """
    Stream URL → FFmpeg encode → dest.mp4
    Captures stderr to a temp file so errors are visible on failure.
    Falls back from hardware → software encoder automatically.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".partial.mp4")

    def run_cmd(args):
        cmd = ["ffmpeg", "-hide_banner", "-i", url,
               *args, "-progress", "pipe:1", "-nostats", "-y", str(tmp)]

        err_fd, err_path = tempfile.mkstemp(suffix=".ffmpeg.log")
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=err_fd,
                text=True,
                bufsize=1,
            )
            os.close(err_fd)

            size_mb = 0.0
            for line in proc.stdout:
                k, _, v = line.strip().partition("=")
                if k == "total_size" and v.lstrip("-").isdigit():
                    size_mb = max(0, int(v)) / 1_048_576
                    progress.update(task_id, size=f"{size_mb:.0f} MB")
                elif k == "speed":
                    progress.update(task_id, speed=v.strip())
            proc.wait()

            if proc.returncode != 0:
                err_text = Path(err_path).read_text(errors="replace")[-500:]
                raise RuntimeError(err_text)

            return size_mb
        finally:
            Path(err_path).unlink(missing_ok=True)

    # ── attempt 1: use provided args (hw encoder if available) ──
    try:
        size_mb = run_cmd(enc_args)
        tmp.rename(dest)
        return dest.stat().st_size / 1_048_576

    except RuntimeError as hw_err:
        # ── attempt 2: if hw failed, fall back to libx265 ──
        is_hw = any("mediacodec" in a for a in enc_args)
        if is_hw:
            console.print(f"\n  [yellow]⚠ Hardware encoder failed — retrying with software[/]")
            sw_args = []
            skip_next = False
            for i, a in enumerate(enc_args):
                if skip_next:
                    skip_next = False; continue
                if a == "-c:v":
                    sw_args += ["-c:v", "libx265", "-crf", str(crf), "-preset", "ultrafast"]
                    skip_next = True  # skip the hw encoder name
                elif a == "-b:v":
                    skip_next = True  # skip the bitrate value
                else:
                    sw_args.append(a)
            try:
                run_cmd(sw_args)
                tmp.rename(dest)
                return dest.stat().st_size / 1_048_576
            except RuntimeError as sw_err:
                tmp.unlink(missing_ok=True)
                raise RuntimeError(f"Both encoders failed.\nHW: {hw_err}\nSW: {sw_err}")
        else:
            tmp.unlink(missing_ok=True)
            raise RuntimeError(str(hw_err))


def _download_plain(url: str, dest: Path,
                    progress: Progress, task_id: int) -> float:
    """Plain HTTP download with resume support."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    resume  = dest.stat().st_size if dest.exists() else 0
    headers = {"Range": f"bytes={resume}-"} if resume else {}

    with requests.get(url, stream=True, timeout=60, headers=headers) as r:
        if r.status_code == 416:
            return dest.stat().st_size / 1_048_576
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0)) + resume
        progress.update(task_id, total=total or None, completed=resume)
        with open(dest, "ab" if resume else "wb") as f:
            for chunk in r.iter_content(65536):
                f.write(chunk)
                progress.advance(task_id, len(chunk))
                progress.update(task_id, size=f"{dest.stat().st_size / 1_048_576:.0f} MB")

    return dest.stat().st_size / 1_048_576


def zip_season(files: list[Path], zip_dest: Path) -> float:
    zip_dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_dest, 'w', zipfile.ZIP_STORED) as zf:
        for f in files:
            zf.write(f, f.name)
            f.unlink()
    for f in files:
        try: f.parent.rmdir()
        except OSError: pass
    return zip_dest.stat().st_size / 1_048_576


def run_download_queue(
    queue:    list[tuple[str, Path, str]],
    enc_args: list[str] | None,
    enc_label: str,
    cfg:      dict,
    history:  dict,
    category: str,
    has_hw:   bool = False,
) -> tuple[int, float]:
    ffmpeg_ok = has_ffmpeg() and enc_args is not None
    workers   = max(1, min(cfg.get("workers", 2), len(queue)))
    lock      = threading.Lock()
    done      = 0
    total_mb  = 0.0
    crf       = cfg.get("crf", 20)

    with Progress(
        SpinnerColumn(),
        TextColumn("{task.description}", style="cyan"),
        BarColumn(bar_width=18),
        TextColumn("[bold]{task.fields[size]:>8}"),
        TextColumn("[dim]{task.fields[speed]:>9}[/]"),
        console=console,
        refresh_per_second=4,
    ) as prog:

        def process(item):
            nonlocal done, total_mb
            url, dest, hkey = item

            if cfg["skip_existing"] and is_downloaded(history, category, hkey):
                prog.add_task(f"[dim]─ {dest.name[:36]}[/]", total=1, completed=1, size="skipped", speed="")
                return

            label   = dest.name if len(dest.name) <= 40 else dest.name[:37] + "…"
            task_id = prog.add_task(label, total=None, size="—", speed="")

            try:
                if ffmpeg_ok:
                    mb = _transcode(url, dest, enc_args, prog, task_id, has_hw=has_hw, crf=crf)
                else:
                    mb = _download_plain(url, dest, prog, task_id)

                prog.update(task_id, description=f"[green]✓[/] {label}",
                            size=f"{mb:.0f} MB", speed="done", total=1, completed=1)
                with lock:
                    done     += 1
                    total_mb += mb
                    mark_downloaded(history, category, hkey, dest, mb)

            except KeyboardInterrupt:
                prog.update(task_id, description=f"[yellow]⏸[/] {label}", speed="paused"); raise
            except Exception as e:
                # Show the actual error so user knows what went wrong
                short_err = str(e)[:80].replace("\n", " ")
                prog.update(task_id, description=f"[red]✗[/] {label}",
                            size="—", speed="err")
                console.print(f"  [red]Error:[/] {short_err}")

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(process, item) for item in queue]
            try:
                for f in as_completed(futures): f.result()
            except KeyboardInterrupt:
                console.print("\n[yellow]  Stopped. Partial files kept.[/]")

    return done, total_mb

# ─── Series flow ──────────────────────────────────────────────────────────────

def run_series(creds, has_hw, cfg, history) -> None:
    mode = questionary.select("Find by:", choices=[
        {"name":"🔍  Search by name","value":"search"},
        {"name":"📂  Browse by category","value":"category"},
    ], style=STYLE).ask()
    if not mode: return

    with console.status("[cyan]Loading series catalog…[/]"):
        try: all_series = api_call(creds, "get_series")
        except Exception as e: console.print(f"[red]API error:[/] {e}"); return

    if mode == "category":
        with console.status("[cyan]Loading categories…[/]"):
            cats = api_call(creds, "get_series_categories")
        cat_id = questionary.select("Pick a category:", choices=[
            {"name": fix_arabic(c["category_name"]), "value": c["category_id"]} for c in cats
        ], style=STYLE).ask()
        if not cat_id: return
        results = [s for s in all_series if str(s.get("category_id",""))==str(cat_id)]
        kw = questionary.text("Filter (optional):", style=STYLE).ask() or ""
        if kw: results = fuzzy_search(results, kw)
    else:
        kw = questionary.text("🔍  Search:", style=STYLE).ask()
        if not kw: return
        results = fuzzy_search(all_series, kw)

    if not results: console.print("[yellow]  No results found.[/]\n"); return

    t = Table(show_header=True, header_style="bold cyan", box=None, pad_edge=False)
    t.add_column("", style="dim", width=4); t.add_column("Name")
    t.add_column("⭐", width=5); t.add_column("Seasons", width=8)
    for i,s in enumerate(results[:60],1):
        t.add_row(str(i), fix_arabic(s.get("name","—")), str(s.get("rating","—")), str(s.get("num_seasons","?")))
    console.print(t)

    chosen = questionary.select("Pick a series:", choices=[
        {"name": fix_arabic(s["name"]), "value": s} for s in results[:60]
    ], style=STYLE).ask()
    if not chosen: return

    with console.status(f"[cyan]Loading {fix_arabic(chosen['name'])}…[/]"):
        try: info = api_call(creds, "get_series_info", series_id=chosen["series_id"])
        except Exception as e: console.print(f"[red]API error:[/] {e}"); return

    show_series_panel(info, chosen["name"])

    eps_by_season = info.get("episodes", {})
    if not eps_by_season: console.print("[red]  No episodes available yet.[/]\n"); return

    seasons   = sorted(eps_by_season.keys(), key=lambda x: int(x) if x.isdigit() else 0)
    total_eps = sum(len(eps_by_season[s]) for s in seasons)

    s_choices = [{"name": f"  Season {s:>2}   ({len(eps_by_season[s])} episodes)", "value": s} for s in seasons]
    s_choices.insert(0, {"name": f"📥  ALL seasons  ({total_eps} episodes total)", "value": "__all__"})
    chosen_seasons = checkbox_or_all("Which seasons?", s_choices, seasons)
    if not chosen_seasons: return

    dl_dir     = get_download_dir(cfg)
    series_dir = dl_dir / sanitize(chosen["name"])
    queue      = []

    for season in chosen_seasons:
        eps = eps_by_season[season]
        ep_choices = [{"name": f"  S{int(season):02d}E{int(e.get('episode_num',0)):02d}  {fix_arabic(e.get('title','Ep '+str(e.get('episode_num','?'))))}","value":e} for e in eps]
        ep_choices.insert(0, {"name": f"📥  ALL — Season {season}  ({len(eps)} episodes)", "value": "__all__"})
        chosen_eps = checkbox_or_all(f"Season {season} — pick episodes:", ep_choices, eps)
        for ep in chosen_eps:
            if not isinstance(ep, dict): continue
            ext    = ep.get("container_extension", "mp4")
            ep_num = int(ep.get("episode_num", 0))
            title  = sanitize(ep.get("title") or f"Episode {ep_num}")
            fname  = f"S{int(season):02d}E{ep_num:02d} - {title}.mp4"
            dest   = series_dir / f"Season {int(season):02d}" / fname
            hkey   = f"{chosen['name']} / {fname}"
            url    = f"{creds['server']}/series/{creds['username']}/{creds['password']}/{ep['id']}.{ext}"
            queue.append((url, dest, hkey))

    if not queue: console.print("[yellow]  Nothing queued.[/]\n"); return

    do_zip = questionary.confirm("📦  Package into a ZIP when done?", default=False, style=STYLE).ask()

    console.print(f"\n[bold]⬇  {len(queue)} episode(s)  →  {series_dir}[/]")
    enc_args, enc_label = pick_quality(has_hw, cfg["crf"])
    console.print(f"[dim]   encoder : {enc_label}   workers : {cfg.get('workers',2)}[/]\n")

    t0 = time.time()
    done, mb = run_download_queue(queue, enc_args, enc_label, cfg, history, "series", has_hw)

    if do_zip and done > 0:
        downloaded = [dest for _,dest,_ in queue if dest.exists()]
        if downloaded:
            season_groups: dict[Path, list[Path]] = {}
            for f in downloaded: season_groups.setdefault(f.parent, []).append(f)
            zip_mb = 0.0
            for sdir, files in season_groups.items():
                zip_name = f"{sanitize(chosen['name'])} {sdir.name}.zip"
                zip_dest = series_dir / zip_name
                console.print(f"[cyan]  📦 Zipping {len(files)} files → {zip_name}[/]")
                zip_mb += zip_season(files, zip_dest)
            mb = zip_mb

    _print_summary(done, len(queue), mb, int(time.time()-t0), series_dir)
    if cfg["notify"]: send_notification("XtreamRip", f"{chosen['name']} — {done} done ({mb:.0f} MB)")


def run_movies(creds, has_hw, cfg, history) -> None:
    mode = questionary.select("Find by:", choices=[
        {"name":"🔍  Search by name","value":"search"},
        {"name":"📂  Browse by category","value":"category"},
    ], style=STYLE).ask()
    if not mode: return

    with console.status("[cyan]Loading movie catalog…[/]"):
        try: all_movies = api_call(creds, "get_vod_streams")
        except Exception as e: console.print(f"[red]API error:[/] {e}"); return

    if mode == "category":
        with console.status("[cyan]Loading categories…[/]"):
            cats = api_call(creds, "get_vod_categories")
        cat_id = questionary.select("Pick a category:", choices=[
            {"name": fix_arabic(c["category_name"]), "value": c["category_id"]} for c in cats
        ], style=STYLE).ask()
        if not cat_id: return
        results = [m for m in all_movies if str(m.get("category_id",""))==str(cat_id)]
        kw = questionary.text("Filter (optional):", style=STYLE).ask() or ""
        if kw: results = fuzzy_search(results, kw)
    else:
        kw = questionary.text("🔍  Search:", style=STYLE).ask()
        if not kw: return
        results = fuzzy_search(all_movies, kw)

    if not results: console.print("[yellow]  No results found.[/]\n"); return

    t = Table(show_header=True, header_style="bold cyan", box=None, pad_edge=False)
    t.add_column("", style="dim", width=4); t.add_column("Name")
    t.add_column("Year", width=6); t.add_column("⭐", width=5)
    for i,m in enumerate(results[:60],1):
        t.add_row(str(i), fix_arabic(m.get("name","—")), str(m.get("year","—")), str(m.get("rating","—")))
    console.print(t)

    console.print(CHECKBOX_HINT)
    chosen = questionary.checkbox("Which movies?", choices=[
        {"name": f"{fix_arabic(m.get('name','—'))}  ({m.get('year','—')})", "value": m} for m in results[:60]
    ], style=STYLE).ask()
    if not chosen: console.print("[yellow]  Nothing selected.[/]\n"); return

    dl_dir = get_download_dir(cfg)
    queue  = []
    for movie in chosen:
        sid = movie["stream_id"]
        try:
            vi  = api_call(creds, "get_vod_info", vod_id=sid)
            ext = vi.get("movie_data",{}).get("container_extension") or movie.get("container_extension","mp4")
        except: ext = movie.get("container_extension","mp4")
        dest = dl_dir / (sanitize(movie["name"]) + ".mp4")
        url  = f"{creds['server']}/movie/{creds['username']}/{creds['password']}/{sid}.{ext}"
        queue.append((url, dest, movie["name"]))

    console.print(f"\n[bold]⬇  {len(queue)} movie(s)  →  {dl_dir}[/]")
    enc_args, enc_label = pick_quality(has_hw, cfg["crf"])
    console.print(f"[dim]   encoder : {enc_label}[/]\n")

    t0 = time.time()
    done, mb = run_download_queue(queue, enc_args, enc_label, cfg, history, "movies", has_hw)
    _print_summary(done, len(queue), mb, int(time.time()-t0), dl_dir)
    if cfg["notify"]: send_notification("XtreamRip", f"{done} movie(s) done ({mb:.0f} MB)")


def _print_summary(done, total, mb, secs, dest) -> None:
    skipped = total - done
    lines = [
        f"[green]✓  {done} / {total} completed[/]",
        f"   📦 {mb:.1f} MB on disk   ⏱ {secs//60}m {secs%60}s",
        f"   📁 {dest}",
    ]
    if skipped: lines.append(f"   [dim]⏭  {skipped} skipped (already on disk)[/]")
    console.print(Panel("\n".join(lines), title="[bold green]Done[/]", border_style="green", expand=False))
    console.print()


def main() -> None:
    import os  # needed inside _transcode too
    parser = argparse.ArgumentParser(prog="xtreamrip")
    parser.add_argument("--reset",   action="store_true")
    parser.add_argument("--version", action="version", version=f"XtreamRip {__version__}")
    args = parser.parse_args()

    console.print(BANNER)

    hw = has_hw_encoder()
    ff = has_ffmpeg()
    if hw:   console.print("[green]✓ Hardware encoder available[/]  [dim](hevc_mediacodec)[/]\n")
    elif ff: console.print("[cyan]✓ Software encoder ready[/]  [dim](libx265)[/]\n")
    else:    console.print("[yellow]⚠ ffmpeg not found.  pkg install ffmpeg[/]\n")

    cfg     = load_cfg()
    global ARABIC_FIX_ENABLED
    ARABIC_FIX_ENABLED = cfg.get("use_arabic_fix", False)
    history = load_history()
    creds   = None if args.reset else load_creds()
    if not creds: creds = prompt_credentials()

    with console.status("[cyan]Connecting…[/]"):
        ok, acct = test_connection(creds)

    if not ok:
        console.print(f"[red]⚠ Auth failed on {creds['server']}[/]")
        if questionary.confirm("Edit credentials?", style=STYLE).ask():
            creds = prompt_credentials(existing=creds)
        else: sys.exit(1)
    else:
        console.print(f"[green]✓  Connected →[/] [bold]{creds['server']}[/]\n")
        show_account(acct)

    MENU = [
        {"name":"📺  Series",            "value":"series"},
        {"name":"🎬  Movies",            "value":"movies"},
        {"name":"📚  My Library",        "value":"library"},
        {"name":"⚙   Settings",          "value":"settings"},
        {"name":"🔑  Change credentials","value":"creds"},
        {"name":"🚪  Exit",              "value":"exit"},
    ]

    while True:
        action = questionary.select("What do you want to do?", choices=MENU, style=STYLE).ask()
        if action in (None,"exit"): console.print("[cyan]Bye! 👋[/]"); break
        elif action == "series":  run_series(creds, hw, cfg, history)
        elif action == "movies":  run_movies(creds, hw, cfg, history)
        elif action == "library": show_library(history)
        elif action == "settings":
            cfg = settings_menu(cfg)
            hw  = has_hw_encoder()
            ARABIC_FIX_ENABLED = cfg.get("use_arabic_fix", False)
        elif action == "creds":
            creds = prompt_credentials(existing=creds)
            with console.status("[cyan]Re-testing…[/]"):
                ok, acct = test_connection(creds)
            if ok: show_account(acct)
            else: console.print("[red]  ✗ Auth failed.[/]\n")


if __name__ == "__main__":
    import os
    try: main()
    except KeyboardInterrupt: console.print("\n[dim]Bye.[/]")
