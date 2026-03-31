import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import re
import yt_dlp
import os


class YouTubeDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Downloader")
        self.root.geometry("520x360")
        self.root.resizable(False, False)

        self._total = 0
        self._current = 0

        # URL input
        ttk.Label(root, text="YouTube URL (video, playlist, or album):").pack(anchor="w", padx=15, pady=(15, 0))
        self.url_var = tk.StringVar()
        ttk.Entry(root, textvariable=self.url_var, width=65).pack(padx=15, pady=5)

        # Format selection
        self.format_var = tk.StringVar(value="mp4")
        frame = ttk.Frame(root)
        frame.pack(anchor="w", padx=15, pady=5)
        ttk.Label(frame, text="Format:").pack(side="left")
        ttk.Radiobutton(frame, text="MP4 (Video)", variable=self.format_var, value="mp4").pack(side="left", padx=(10, 5))
        ttk.Radiobutton(frame, text="MP3 (Audio)", variable=self.format_var, value="mp3").pack(side="left", padx=5)

        # Output folder
        folder_frame = ttk.Frame(root)
        folder_frame.pack(fill="x", padx=15, pady=5)
        ttk.Label(folder_frame, text="Save to:").pack(side="left")
        default_folder = os.path.join(os.path.expanduser("~"), "Downloads", "YouTube Downloads")
        os.makedirs(default_folder, exist_ok=True)
        self.folder_var = tk.StringVar(value=default_folder)
        ttk.Entry(folder_frame, textvariable=self.folder_var, width=45).pack(side="left", padx=(10, 5))
        ttk.Button(folder_frame, text="Browse", command=self.browse_folder).pack(side="left")

        # Download button
        self.download_btn = ttk.Button(root, text="Download", command=self.start_download)
        self.download_btn.pack(pady=12)

        # Per-file progress bar
        ttk.Label(root, text="File progress:").pack(anchor="w", padx=15)
        self.progress = ttk.Progressbar(root, length=480, mode="determinate")
        self.progress.pack(padx=15, pady=(2, 6))

        # Overall playlist progress bar
        ttk.Label(root, text="Overall progress:").pack(anchor="w", padx=15)
        self.overall_progress = ttk.Progressbar(root, length=480, mode="determinate")
        self.overall_progress.pack(padx=15, pady=(2, 6))

        # Status label
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(root, textvariable=self.status_var).pack(pady=4)

    def browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.folder_var.get())
        if folder:
            self.folder_var.set(folder)

    def validate_url(self, url):
        pattern = r"https?://(www\.)?(youtube\.com|youtu\.be)/"
        return bool(re.match(pattern, url.strip()))

    def progress_hook(self, d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            if total > 0:
                pct = downloaded / total * 100
                overall_pct = ((self._current - 1 + pct / 100) / self._total * 100) if self._total > 0 else 0
                label = f"Downloading {self._current}/{self._total} — {pct:.0f}%" if self._total > 1 else f"Downloading... {pct:.0f}%"
                self.root.after(0, self._update_progress, pct, overall_pct, label)
        elif d["status"] == "finished":
            overall_pct = (self._current / self._total * 100) if self._total > 0 else 100
            self.root.after(0, self._update_progress, 100, overall_pct, "Processing...")

    def _update_progress(self, value, overall_value, text):
        self.progress["value"] = value
        self.overall_progress["value"] = overall_value
        self.status_var.set(text)

    def start_download(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Input needed", "Please paste a YouTube URL.")
            return
        if not self.validate_url(url):
            messagebox.showerror("Invalid URL", "That doesn't look like a valid YouTube URL.")
            return

        self.download_btn.config(state="disabled")
        self.progress["value"] = 0
        self.overall_progress["value"] = 0
        self.status_var.set("Fetching info...")
        threading.Thread(target=self.download, args=(url,), daemon=True).start()

    def download(self, url):
        fmt = self.format_var.get()
        folder = self.folder_var.get()

        # Get playlist info first so we know the total count
        try:
            with yt_dlp.YoutubeDL({"quiet": True, "extract_flat": True, "no_warnings": True}) as ydl:
                info = ydl.extract_info(url, download=False)
            entries = info.get("entries")
            self._total = len(entries) if entries else 1
            self._current = 0
        except Exception as e:
            self.root.after(0, self._done, False, str(e))
            return

        # Use playlist subfolder if it's a playlist/album
        if self._total > 1:
            playlist_name = info.get("title", "Playlist")
            safe_name = re.sub(r'[\\/*?:"<>|]', "", playlist_name)
            out_folder = os.path.join(folder, safe_name)
            os.makedirs(out_folder, exist_ok=True)
        else:
            out_folder = folder

        opts = {
            "outtmpl": os.path.join(out_folder, "%(title)s.%(ext)s"),
            "progress_hooks": [self.progress_hook],
            "quiet": True,
            "no_warnings": True,
        }

        if fmt == "mp3":
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]
        else:
            opts["format"] = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
            opts["merge_output_format"] = "mp4"

        def on_entry_start(d):
            if d.get("status") == "downloading" and d.get("downloaded_bytes", 0) < 50000:
                pass  # handled in progress_hook

        # Track when each new file starts
        original_hook = self.progress_hook

        def counting_hook(d):
            if d["status"] == "downloading":
                filename = d.get("filename", "")
                if not hasattr(self, "_last_file") or self._last_file != filename:
                    self._last_file = filename
                    self._current = min(self._current + 1, self._total)
            original_hook(d)

        opts["progress_hooks"] = [counting_hook]

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            self.root.after(0, self._done, True, f"Downloaded {self._total} file(s) to: {out_folder}")
        except Exception as e:
            self.root.after(0, self._done, False, str(e))

    def _done(self, success, msg):
        self.download_btn.config(state="normal")
        self._last_file = None
        if success:
            self.progress["value"] = 100
            self.overall_progress["value"] = 100
            self.status_var.set("Done!")
            messagebox.showinfo("Done", msg)
        else:
            self.progress["value"] = 0
            self.overall_progress["value"] = 0
            self.status_var.set("Error")
            messagebox.showerror("Error", msg)


if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubeDownloader(root)
    root.mainloop()
