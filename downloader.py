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
        self.root.geometry("520x320")
        self.root.resizable(False, False)

        # URL input
        ttk.Label(root, text="YouTube URL:").pack(anchor="w", padx=15, pady=(15, 0))
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
        self.folder_var = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Downloads"))
        ttk.Entry(folder_frame, textvariable=self.folder_var, width=45).pack(side="left", padx=(10, 5))
        ttk.Button(folder_frame, text="Browse", command=self.browse_folder).pack(side="left")

        # Download button
        self.download_btn = ttk.Button(root, text="Download", command=self.start_download)
        self.download_btn.pack(pady=15)

        # Progress bar
        self.progress = ttk.Progressbar(root, length=480, mode="determinate")
        self.progress.pack(padx=15)

        # Status label
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(root, textvariable=self.status_var).pack(pady=5)

    def browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.folder_var.get())
        if folder:
            self.folder_var.set(folder)

    def validate_url(self, url):
        pattern = r"(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[\w-]+"
        return bool(re.match(pattern, url.strip()))

    def progress_hook(self, d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            if total > 0:
                pct = downloaded / total * 100
                self.root.after(0, self._update_progress, pct, f"Downloading... {pct:.0f}%")
        elif d["status"] == "finished":
            self.root.after(0, self._update_progress, 100, "Processing...")

    def _update_progress(self, value, text):
        self.progress["value"] = value
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
        self.status_var.set("Starting...")
        threading.Thread(target=self.download, args=(url,), daemon=True).start()

    def download(self, url):
        fmt = self.format_var.get()
        folder = self.folder_var.get()

        opts = {
            "outtmpl": os.path.join(folder, "%(title)s.%(ext)s"),
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

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            self.root.after(0, self._done, True, "Download complete!")
        except Exception as e:
            self.root.after(0, self._done, False, str(e))

    def _done(self, success, msg):
        self.download_btn.config(state="normal")
        if success:
            self.progress["value"] = 100
            self.status_var.set(msg)
            messagebox.showinfo("Done", f"Saved to: {self.folder_var.get()}")
        else:
            self.progress["value"] = 0
            self.status_var.set("Error")
            messagebox.showerror("Error", msg)


if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubeDownloader(root)
    root.mainloop()
