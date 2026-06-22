import customtkinter as ctk
import threading
import time
import requests
import json
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import tkinter.messagebox as messagebox

CONFIG_DIR = Path.home() / ".config" / "xtreamrip"
CREDS_FILE = CONFIG_DIR / "creds.json"
HISTORY_FILE = CONFIG_DIR / "history.json"

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class DownloadManager:
    def __init__(self):
        self.queue = [] # list of dicts: {'url', 'dest', 'name', 'status', 'progress', 'size', 'task_id'}
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.active_tasks = {}
        self.history = self.load_history()
        self.lock = threading.Lock()

    def load_history(self):
        if HISTORY_FILE.exists():
            try: return json.loads(HISTORY_FILE.read_text())
            except: pass
        return {"series": {}, "movies": {}}

    def save_history(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        HISTORY_FILE.write_text(json.dumps(self.history, indent=2))

    def mark_downloaded(self, cat, key, path, mb):
        with self.lock:
            self.history.setdefault(cat, {})[key] = {
                "path": str(path), "size_mb": round(mb, 1),
            }
            self.save_history()

    def is_downloaded(self, cat, key):
        with self.lock:
            e = self.history.get(cat, {}).get(key)
            return bool(e and Path(e["path"]).exists())

    def add_to_queue(self, url, dest_path, name, category, hkey):
        task_id = str(time.time())
        item = {
            'url': url, 'dest': dest_path, 'name': name, 'status': 'Pending',
            'progress': 0, 'size': 0, 'task_id': task_id, 'category': category, 'hkey': hkey
        }
        self.queue.append(item)
        self.executor.submit(self.download_worker, item)
        return task_id

    def download_worker(self, item):
        item['status'] = 'Downloading'
        dest = Path(item['dest'])
        dest.parent.mkdir(parents=True, exist_ok=True)
        
        if self.is_downloaded(item['category'], item['hkey']):
            item['status'] = 'Done (Exists)'
            item['progress'] = 100
            return

        resume = dest.stat().st_size if dest.exists() else 0
        headers = {"Range": f"bytes={resume}-"} if resume else {}

        try:
            with requests.get(item['url'], stream=True, timeout=60, headers=headers) as r:
                if r.status_code == 416: # already downloaded
                    item['status'] = 'Done'
                    item['progress'] = 100
                    self.mark_downloaded(item['category'], item['hkey'], dest, dest.stat().st_size / 1_048_576)
                    return
                    
                r.raise_for_status()
                total = int(r.headers.get("content-length", 0)) + resume
                item['size'] = total
                
                with open(dest, "ab" if resume else "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 256):
                        f.write(chunk)
                        resume += len(chunk)
                        item['progress'] = int((resume / total) * 100) if total else 0
            
            item['status'] = 'Done'
            item['progress'] = 100
            self.mark_downloaded(item['category'], item['hkey'], dest, dest.stat().st_size / 1_048_576)
        except Exception as e:
            item['status'] = f'Error'
            print(e)


class XtreamRipApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("XtreamRip")
        self.geometry("1100x750")
        
        self.creds = self.load_creds()
        self.server = ""
        self.username = ""
        self.password = ""
        self.dl_manager = DownloadManager()
        
        self.show_login()

    def load_creds(self):
        if CREDS_FILE.exists():
            try: return json.loads(CREDS_FILE.read_text())
            except: pass
        return None

    def save_creds(self, server, username, password):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {"server": server.rstrip("/"), "username": username, "password": password}
        CREDS_FILE.write_text(json.dumps(data, indent=2))
        return data

    def api_call(self, action=None, **kwargs):
        params = {"username": self.username, "password": self.password}
        if action: params["action"] = action
        params.update(kwargs)
        r = requests.get(f"{self.server}/player_api.php", params=params, timeout=40)
        r.raise_for_status()
        return r.json()

    def show_login(self):
        for widget in self.winfo_children(): widget.destroy()

        frame = ctk.CTkFrame(self, width=400, height=400)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(frame, text="XtreamRip", font=ctk.CTkFont(size=28, weight="bold")).pack(pady=20)

        self.server_entry = ctk.CTkEntry(frame, placeholder_text="Server URL", width=300)
        self.server_entry.pack(pady=10)
        
        self.user_entry = ctk.CTkEntry(frame, placeholder_text="Username", width=300)
        self.user_entry.pack(pady=10)
        
        self.pass_entry = ctk.CTkEntry(frame, placeholder_text="Password", width=300, show="*")
        self.pass_entry.pack(pady=10)

        if self.creds:
            self.server_entry.insert(0, self.creds.get("server", ""))
            self.user_entry.insert(0, self.creds.get("username", ""))
            self.pass_entry.insert(0, self.creds.get("password", ""))

        ctk.CTkButton(frame, text="Login", command=self.do_login, width=300).pack(pady=20)
        self.status_label = ctk.CTkLabel(frame, text="", text_color="red")
        self.status_label.pack(pady=5)

    def do_login(self):
        self.server = self.server_entry.get()
        self.username = self.user_entry.get()
        self.password = self.pass_entry.get()
        self.status_label.configure(text="Connecting...", text_color="white")
        threading.Thread(target=self._test_conn, daemon=True).start()

    def _test_conn(self):
        try:
            data = self.api_call()
            if data.get("user_info", {}).get("auth", 0):
                self.save_creds(self.server, self.username, self.password)
                self.after(0, self.setup_main_layout)
            else:
                self.after(0, lambda: self.status_label.configure(text="Authentication Failed"))
        except Exception as e:
            self.after(0, lambda: self.status_label.configure(text=f"Error: {e}"))

    def setup_main_layout(self):
        for widget in self.winfo_children(): widget.destroy()
            
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        
        ctk.CTkLabel(self.sidebar, text="XtreamRip", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=20)
        
        ctk.CTkButton(self.sidebar, text="Series", command=self.show_series, fg_color="transparent", border_width=1).pack(pady=10, padx=20, fill="x")
        ctk.CTkButton(self.sidebar, text="Movies", command=self.show_movies, fg_color="transparent", border_width=1).pack(pady=10, padx=20, fill="x")
        ctk.CTkButton(self.sidebar, text="Downloads", command=self.show_downloads, fg_color="transparent", border_width=1).pack(pady=10, padx=20, fill="x")
        
        self.content_frame = ctk.CTkFrame(self)
        self.content_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        
        self.show_series()

    def show_series(self):
        for w in self.content_frame.winfo_children(): w.destroy()
        
        top_bar = ctk.CTkFrame(self.content_frame)
        top_bar.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(top_bar, text="Series Categories", font=ctk.CTkFont(size=18, weight="bold")).pack(side="left", padx=10)
        
        self.cat_var = ctk.StringVar(value="Select Category")
        self.cat_menu = ctk.CTkOptionMenu(top_bar, variable=self.cat_var, values=["Loading..."], command=self.on_series_cat_select)
        self.cat_menu.pack(side="left", padx=10)
        
        self.series_list_frame = ctk.CTkScrollableFrame(self.content_frame)
        self.series_list_frame.pack(fill="both", expand=True, padx=10, pady=10)

        threading.Thread(target=self._load_series_cats, daemon=True).start()

    def _load_series_cats(self):
        try:
            self.cats = self.api_call("get_series_categories")
            cat_names = [c["category_name"] for c in self.cats]
            self.after(0, lambda: self.cat_menu.configure(values=cat_names))
        except Exception as e:
            print("Error loading cats:", e)

    def on_series_cat_select(self, cat_name):
        cat_id = next((c["category_id"] for c in self.cats if c["category_name"] == cat_name), None)
        if cat_id:
            for w in self.series_list_frame.winfo_children(): w.destroy()
            ctk.CTkLabel(self.series_list_frame, text="Loading series...").pack(pady=20)
            threading.Thread(target=self._load_series_by_cat, args=(cat_id,), daemon=True).start()

    def _load_series_by_cat(self, cat_id):
        try:
            series = self.api_call("get_series", category_id=cat_id)
            self.after(0, lambda: self._render_series_list(series))
        except Exception as e:
            print(e)

    def _render_series_list(self, series):
        for w in self.series_list_frame.winfo_children(): w.destroy()
        
        for i, s in enumerate(series):
            btn = ctk.CTkButton(
                self.series_list_frame, text=f"{s.get('name')} (Rating: {s.get('rating', 'N/A')})", 
                anchor="w", fg_color="transparent", border_width=1,
                command=lambda sid=s.get("series_id"), name=s.get("name"): self.show_series_details(sid, name)
            )
            btn.pack(fill="x", pady=2, padx=5)

    def show_series_details(self, series_id, name):
        for w in self.content_frame.winfo_children(): w.destroy()
        
        ctk.CTkButton(self.content_frame, text="← Back", command=self.show_series, width=100).pack(anchor="w", padx=10, pady=10)
        ctk.CTkLabel(self.content_frame, text=name, font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w", padx=10)
        
        self.details_scroll = ctk.CTkScrollableFrame(self.content_frame)
        self.details_scroll.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(self.details_scroll, text="Loading episodes...").pack(pady=20)

        threading.Thread(target=self._load_series_info, args=(series_id, name), daemon=True).start()

    def _load_series_info(self, series_id, name):
        try:
            info = self.api_call("get_series_info", series_id=series_id)
            self.after(0, lambda: self._render_series_info(info, name))
        except Exception as e:
            print(e)

    def _render_series_info(self, info, name):
        for w in self.details_scroll.winfo_children(): w.destroy()
        
        meta = info.get("info", {})
        plot = meta.get("plot") or meta.get("description") or "No description."
        ctk.CTkLabel(self.details_scroll, text=plot, wraplength=700, justify="left").pack(anchor="w", pady=10, padx=10)

        eps_by_season = info.get("episodes", {})
        seasons = sorted(eps_by_season.keys(), key=lambda x: int(x) if x.isdigit() else 0)

        # Download All Button
        def download_all():
            for s in seasons:
                self.queue_season(name, s, eps_by_season[s])
            messagebox.showinfo("Success", "All seasons added to download queue!")

        ctk.CTkButton(self.details_scroll, text="📥 Download All Seasons", command=download_all, fg_color="green").pack(anchor="w", padx=10, pady=10)

        for season in seasons:
            eps = eps_by_season[season]
            sf = ctk.CTkFrame(self.details_scroll)
            sf.pack(fill="x", pady=5, padx=10)
            
            top = ctk.CTkFrame(sf, fg_color="transparent")
            top.pack(fill="x", pady=5, padx=5)
            
            ctk.CTkLabel(top, text=f"Season {season} ({len(eps)} eps)", font=ctk.CTkFont(weight="bold")).pack(side="left")
            ctk.CTkButton(top, text="📥 Download Season", width=120, command=lambda s=season, e=eps: self.queue_season(name, s, e)).pack(side="right")

            for ep in eps:
                ep_num = ep.get('episode_num', 0)
                ep_title = ep.get('title', f"Episode {ep_num}")
                epf = ctk.CTkFrame(sf, fg_color="transparent")
                epf.pack(fill="x", padx=10, pady=2)
                ctk.CTkLabel(epf, text=f"S{int(season):02d}E{int(ep_num):02d} - {ep_title}").pack(side="left")
                ctk.CTkButton(epf, text="Download", width=80, command=lambda e=ep, s=season: self.queue_ep(name, s, e)).pack(side="right")

    def queue_ep(self, series_name, season, ep):
        ext = ep.get("container_extension", "mp4")
        ep_num = int(ep.get("episode_num", 0))
        fname = f"{series_name} - S{int(season):02d}E{ep_num:02d}.{ext}"
        
        # Sanitize filename
        fname = "".join(c for c in fname if c.isalnum() or c in (' ', '.', '-', '_')).strip()
        
        dl_dir = Path.home() / "Downloads" / "XtreamRip" / series_name / f"Season {int(season):02d}"
        dest = dl_dir / fname
        
        hkey = f"{series_name} / {fname}"
        url = f"{self.server}/series/{self.username}/{self.password}/{ep['id']}.{ext}"
        
        self.dl_manager.add_to_queue(url, str(dest), fname, "series", hkey)

    def queue_season(self, series_name, season, eps):
        for ep in eps:
            self.queue_ep(series_name, season, ep)

    def show_movies(self):
        for w in self.content_frame.winfo_children(): w.destroy()
        
        top_bar = ctk.CTkFrame(self.content_frame)
        top_bar.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(top_bar, text="Movie Categories", font=ctk.CTkFont(size=18, weight="bold")).pack(side="left", padx=10)
        
        self.movie_cat_var = ctk.StringVar(value="Select Category")
        self.movie_cat_menu = ctk.CTkOptionMenu(top_bar, variable=self.movie_cat_var, values=["Loading..."], command=self.on_movie_cat_select)
        self.movie_cat_menu.pack(side="left", padx=10)
        
        self.movies_list_frame = ctk.CTkScrollableFrame(self.content_frame)
        self.movies_list_frame.pack(fill="both", expand=True, padx=10, pady=10)

        threading.Thread(target=self._load_movie_cats, daemon=True).start()

    def _load_movie_cats(self):
        try:
            self.movie_cats = self.api_call("get_vod_categories")
            cat_names = [c["category_name"] for c in self.movie_cats]
            self.after(0, lambda: self.movie_cat_menu.configure(values=cat_names))
        except Exception as e:
            print("Error loading movie cats:", e)

    def on_movie_cat_select(self, cat_name):
        cat_id = next((c["category_id"] for c in self.movie_cats if c["category_name"] == cat_name), None)
        if cat_id:
            for w in self.movies_list_frame.winfo_children(): w.destroy()
            ctk.CTkLabel(self.movies_list_frame, text="Loading movies...").pack(pady=20)
            threading.Thread(target=self._load_movies_by_cat, args=(cat_id,), daemon=True).start()

    def _load_movies_by_cat(self, cat_id):
        try:
            movies = self.api_call("get_vod_streams", category_id=cat_id)
            self.after(0, lambda: self._render_movies_list(movies))
        except Exception as e:
            print(e)

    def _render_movies_list(self, movies):
        for w in self.movies_list_frame.winfo_children(): w.destroy()
        
        for i, m in enumerate(movies):
            f = ctk.CTkFrame(self.movies_list_frame, fg_color="transparent")
            f.pack(fill="x", pady=2, padx=5)
            
            ctk.CTkLabel(f, text=f"{m.get('name')} ({m.get('year', 'N/A')}) - Rating: {m.get('rating', 'N/A')}").pack(side="left")
            ctk.CTkButton(f, text="Download", width=100, command=lambda mo=m: self.queue_movie(mo)).pack(side="right")

    def queue_movie(self, movie):
        sid = movie["stream_id"]
        ext = movie.get("container_extension", "mp4")
        name = movie.get("name", f"Movie_{sid}")
        fname = "".join(c for c in name if c.isalnum() or c in (' ', '.', '-', '_')).strip() + f".{ext}"
        
        dl_dir = Path.home() / "Downloads" / "XtreamRip" / "Movies"
        dest = dl_dir / fname
        
        url = f"{self.server}/movie/{self.username}/{self.password}/{sid}.{ext}"
        
        self.dl_manager.add_to_queue(url, str(dest), fname, "movies", name)
        messagebox.showinfo("Success", f"Added {name} to queue!")

    def show_downloads(self):
        for w in self.content_frame.winfo_children(): w.destroy()
        
        ctk.CTkLabel(self.content_frame, text="Downloads Manager", font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w", padx=10, pady=10)
        
        self.dl_scroll = ctk.CTkScrollableFrame(self.content_frame)
        self.dl_scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        self._update_downloads_ui()
        self.dl_updater = self.after(1000, self._poll_downloads)

    def _poll_downloads(self):
        if self.content_frame.winfo_children() and hasattr(self, 'dl_scroll') and self.dl_scroll.winfo_exists():
            self._update_downloads_ui()
            self.dl_updater = self.after(1000, self._poll_downloads)

    def _update_downloads_ui(self):
        for w in self.dl_scroll.winfo_children(): w.destroy()
        
        if not self.dl_manager.queue:
            ctk.CTkLabel(self.dl_scroll, text="No active downloads.").pack(pady=20)
            return

        for item in self.dl_manager.queue:
            f = ctk.CTkFrame(self.dl_scroll)
            f.pack(fill="x", pady=5, padx=5)
            
            top = ctk.CTkFrame(f, fg_color="transparent")
            top.pack(fill="x", padx=5, pady=2)
            ctk.CTkLabel(top, text=item['name'], font=ctk.CTkFont(weight="bold")).pack(side="left")
            ctk.CTkLabel(top, text=item['status']).pack(side="right")
            
            pb = ctk.CTkProgressBar(f)
            pb.pack(fill="x", padx=10, pady=5)
            pb.set(item['progress'] / 100)

if __name__ == "__main__":
    app = XtreamRipApp()
    app.mainloop()
