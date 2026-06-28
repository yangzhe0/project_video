import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import subprocess
import os
import json
import shutil
import multiprocessing
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image, ImageDraw, ImageFont
import time
from datetime import datetime

class VideoProcessor:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Processor")
        self.root.geometry("432x620")
        self.root.minsize(420, 560)
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.drive_root = os.path.dirname(self.base_dir)
        self.root_config_path = os.path.join(self.drive_root, "配置.json")
        self.report_dir = os.path.join(self.drive_root, "reports")
        self.config_path = os.path.join(self.base_dir, "settings.json")
        self.snapshot_store_path = os.path.join(self.base_dir, "snapshots.json")
        
        self.config = {
            "paths": {
                "input_dir": "../library",
                "output_dir": "../library",
                "thumbnail_dir": "../library"
            },
            "ffmpeg": {
                "executable": "./FFmpeg/ffmpeg.exe",
                "probe_executable": "./FFmpeg/ffprobe.exe"
            },
            "thumbnail": {
                "canvas_width": 960,
                "canvas_height": 540,
                "landscape_frames": 4,
                "portrait_frames": 3,
                "font_size": 50,
                "text_color": [0, 0, 0],
                "background_color": [255, 255, 255],
                "show_info_header": True
            },
            "processing": {
                "max_workers": multiprocessing.cpu_count(),
                "show_progress": True
            }
        }
        
        self.load_config()
        self.apply_root_config()
        self.ensure_default_dirs()
        self.setup_styles()
        self.create_widgets()
        self.check_ffmpeg()
        self.is_processing = False

    def resolve_app_path(self, path):
        if os.path.isabs(path):
            return path
        return os.path.normpath(os.path.join(self.base_dir, path))

    def ensure_default_dirs(self):
        for key in ("input_dir", "output_dir", "thumbnail_dir"):
            os.makedirs(self.resolve_app_path(self.config["paths"][key]), exist_ok=True)
        os.makedirs(self.resolve_app_path(self.report_dir), exist_ok=True)

    def resolve_root_path(self, path):
        if os.path.isabs(path):
            return os.path.normpath(path)
        return os.path.normpath(os.path.join(self.drive_root, path))

    def load_root_config(self):
        if not os.path.exists(self.root_config_path):
            return {}
        try:
            with open(self.root_config_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            if not isinstance(payload, dict):
                return {}
            return {str(key): str(value) for key, value in payload.items() if isinstance(value, str)}
        except Exception:
            return {}

    def apply_root_config(self):
        root_config = self.load_root_config()
        library_dir = root_config.get("资源库", "./library")
        self.config["paths"]["input_dir"] = self.resolve_root_path(library_dir)
        self.config["paths"]["output_dir"] = self.resolve_root_path(library_dir)
        self.config["paths"]["thumbnail_dir"] = self.resolve_root_path(library_dir)
        self.report_dir = self.resolve_root_path(root_config.get("报告", "./reports"))

    def setup_styles(self):
        self.colors = {
            "bg": "#f6f7fb",
            "panel": "#ffffff",
            "panel_alt": "#f8fafd",
            "text": "#1f2937",
            "muted": "#667085",
            "line": "#d7deea",
            "accent": "#2563eb",
            "accent_hover": "#1d4ed8",
        }

        self.root.configure(bg=self.colors["bg"])
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        default_font = ("Microsoft YaHei UI", 9)
        section_font = ("Microsoft YaHei UI", 10, "bold")
        button_font = ("Microsoft YaHei UI", 9, "bold")

        style.configure(".", font=default_font)
        style.configure("App.TFrame", background=self.colors["bg"])
        style.configure("Panel.TFrame", background=self.colors["panel"])
        style.configure("Toolbar.TFrame", background=self.colors["panel_alt"])
        style.configure("ToolTitle.TLabel", background=self.colors["panel_alt"], foreground=self.colors["text"], font=("Microsoft YaHei UI", 10, "bold"))
        style.configure("Hint.TLabel", background=self.colors["panel_alt"], foreground=self.colors["muted"], font=("Microsoft YaHei UI", 9))
        style.configure(
            "Subtitle.TLabel",
            background=self.colors["bg"],
            foreground=self.colors["muted"],
            font=("Microsoft YaHei UI", 10),
        )
        style.configure(
            "Section.TLabelframe",
            background=self.colors["panel"],
            borderwidth=1,
            relief="solid",
        )
        style.configure(
            "Section.TLabelframe.Label",
            background=self.colors["panel"],
            foreground=self.colors["text"],
            font=section_font,
        )
        style.configure(
            "TLabel",
            background=self.colors["panel"],
            foreground=self.colors["text"],
        )
        style.configure(
            "Muted.TLabel",
            background=self.colors["panel"],
            foreground=self.colors["muted"],
        )
        style.configure(
            "TEntry",
            fieldbackground="#ffffff",
            bordercolor=self.colors["line"],
            lightcolor=self.colors["line"],
            darkcolor=self.colors["line"],
            padding=6,
        )
        style.configure(
            "TCheckbutton",
            background=self.colors["panel_alt"],
            foreground=self.colors["text"],
        )
        style.configure(
            "TProgressbar",
            troughcolor="#e5e7eb",
            background=self.colors["accent"],
            bordercolor="#e5e7eb",
            lightcolor=self.colors["accent"],
            darkcolor=self.colors["accent"],
            thickness=10,
        )
        style.configure(
            "Action.TButton",
            font=button_font,
            padding=(7, 5),
            background=self.colors["panel_alt"],
            foreground=self.colors["text"],
            bordercolor=self.colors["line"],
        )
        style.map(
            "Action.TButton",
            background=[("active", "#eef3ff")],
            bordercolor=[("active", "#bfd1ff")],
        )
        style.configure(
            "Primary.TButton",
            font=button_font,
            padding=(7, 5),
            background=self.colors["accent"],
            foreground="#ffffff",
            bordercolor=self.colors["accent"],
        )
        style.map(
            "Primary.TButton",
            background=[("active", self.colors["accent_hover"])],
            bordercolor=[("active", self.colors["accent_hover"])],
        )
        style.configure(
            "Danger.TButton",
            font=button_font,
            padding=(7, 5),
            background="#fff1f2",
            foreground="#b42318",
            bordercolor="#fecdd3",
        )
        style.map(
            "Danger.TButton",
            background=[("active", "#ffe4e6")],
            bordercolor=[("active", "#fda4af")],
        )

    def load_config(self):
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    saved_config = json.load(f)
                    self.config.update(saved_config)
            thumbnail_config = self.config.setdefault("thumbnail", {})
            thumbnail_config["canvas_width"] = int(thumbnail_config.get("canvas_width", 960) or 960)
            thumbnail_config["canvas_height"] = int(thumbnail_config.get("canvas_height", 540) or 540)
            thumbnail_config["landscape_frames"] = int(thumbnail_config.get("landscape_frames", 4) or 4)
            thumbnail_config["portrait_frames"] = int(thumbnail_config.get("portrait_frames", 3) or 3)
            thumbnail_config.setdefault("font_size", 50)
            thumbnail_config.setdefault("text_color", [0, 0, 0])
            thumbnail_config.setdefault("background_color", [255, 255, 255])
            thumbnail_config.setdefault("show_info_header", True)
        except Exception as e:
            self.log_message(f"加载配置失败: {e}")
    
    def save_config(self):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log_message(f"保存配置失败: {e}")
    
    def check_ffmpeg(self):
        try:
            result = subprocess.run([self.resolve_app_path(self.config['ffmpeg']['executable']), '-version'],
                                  capture_output=True, text=True, timeout=5, encoding='utf-8', errors='ignore')
            if result.returncode == 0:
                self.log_message("FFmpeg检查成功")
            else:
                self.log_message("FFmpeg检查失败")
        except Exception as e:
            self.log_message(f"FFmpeg检查失败: {e}")
            self.log_message("请确保已安装FFmpeg并添加到系统PATH环境变量中")
    
    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="8 8 8 8", style="App.TFrame")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.create_path_section(main_frame, 0)
        self.create_tools_section(main_frame, 1)
        
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(1, 4))
        
        self.status_label = ttk.Label(main_frame, text="就绪", style="Subtitle.TLabel")
        self.status_label.grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=(0, 3))
        
        log_frame = ttk.LabelFrame(main_frame, text="运行日志", padding="5", style="Section.TLabelframe")
        log_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(3, 0))
        
        self.log_text = tk.Text(
            log_frame,
            height=15,
            width=80,
            bg="#111827",
            fg="#e5eefc",
            insertbackground="#e5eefc",
            relief="flat",
            bd=0,
            padx=6,
            pady=6,
            font=("Consolas", 10),
        )
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
    
    def create_path_section(self, parent, row):
        frame = ttk.LabelFrame(parent, text="路径设置", padding="4", style="Section.TLabelframe")
        frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 4))
        
        ttk.Label(frame, text="输入目录:").grid(row=0, column=0, padx=5, sticky=tk.W)
        self.input_path_var = tk.StringVar(value=self.config['paths']['input_dir'])
        ttk.Entry(frame, textvariable=self.input_path_var, width=28).grid(row=0, column=1, padx=4, pady=0, sticky=(tk.W, tk.E))
        ttk.Button(frame, text="浏览", command=self.browse_input_path, style="Action.TButton").grid(row=0, column=2, padx=3, pady=1)
        
        ttk.Label(frame, text="输出目录:").grid(row=1, column=0, padx=5, sticky=tk.W)
        self.output_path_var = tk.StringVar(value=self.config['paths']['output_dir'])
        ttk.Entry(frame, textvariable=self.output_path_var, width=28).grid(row=1, column=1, padx=4, pady=0, sticky=(tk.W, tk.E))
        ttk.Button(frame, text="浏览", command=self.browse_output_path, style="Action.TButton").grid(row=1, column=2, padx=3, pady=1)
        
        ttk.Label(frame, text="缩略图目录:").grid(row=2, column=0, padx=5, sticky=tk.W)
        self.thumbnail_path_var = tk.StringVar(value=self.config['paths']['thumbnail_dir'])
        ttk.Entry(frame, textvariable=self.thumbnail_path_var, width=28).grid(row=2, column=1, padx=4, pady=0, sticky=(tk.W, tk.E))
        ttk.Button(frame, text="浏览", command=self.browse_thumbnail_path, style="Action.TButton").grid(row=2, column=2, padx=3, pady=1)
        
        action_frame = ttk.Frame(frame, style="Panel.TFrame")
        action_frame.grid(row=3, column=1, sticky=tk.W, padx=5, pady=(3, 0))
        ttk.Button(action_frame, text="保存路径设置", command=self.save_paths, style="Primary.TButton").grid(row=0, column=0, sticky=tk.W)
        ttk.Button(action_frame, text="生成快照清单", command=self.start_snapshot_check, style="Action.TButton").grid(row=0, column=1, sticky=tk.W, padx=(8, 0))
        frame.columnconfigure(1, weight=1)
    
    def create_tools_section(self, parent, row):
        frame = ttk.LabelFrame(parent, text="处理工具", padding="4", style="Section.TLabelframe")
        frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 4))

        PADX, PADY = 3, 2
        ENTRY_WIDTH = 4
        BUTTON_WIDTH = 7

        tools_grid = ttk.Frame(frame, style="Toolbar.TFrame", padding="6 4")
        tools_grid.grid(row=0, column=0, sticky=(tk.W, tk.E))

        def cell(parent_frame, row_index, column_index, sticky=tk.W):
            holder = ttk.Frame(parent_frame, style="Toolbar.TFrame")
            holder.grid(row=row_index, column=column_index, padx=PADX, pady=PADY, sticky=sticky)
            return holder

        ttk.Label(tools_grid, text="去广告", style="ToolTitle.TLabel").grid(row=0, column=0, padx=PADX, pady=PADY, sticky=tk.W)
        ad_params = cell(tools_grid, 0, 1)
        ttk.Label(ad_params, text="头").grid(row=0, column=0, padx=(0, 2), sticky=tk.W)
        self.head_time_var = tk.StringVar(value="0")
        ttk.Entry(ad_params, textvariable=self.head_time_var, width=ENTRY_WIDTH).grid(row=0, column=1, padx=(0, 6), sticky=tk.W)
        ttk.Label(ad_params, text="尾").grid(row=0, column=2, padx=(0, 2), sticky=tk.W)
        self.tail_time_var = tk.StringVar(value="0")
        ttk.Entry(ad_params, textvariable=self.tail_time_var, width=ENTRY_WIDTH).grid(row=0, column=3, sticky=tk.W)
        ttk.Button(tools_grid, text="去广告", width=BUTTON_WIDTH, command=self.start_remove_ads, style="Primary.TButton").grid(row=0, column=3, padx=PADX, pady=PADY, sticky=tk.E)

        ttk.Label(tools_grid, text="缩略图", style="ToolTitle.TLabel").grid(row=1, column=0, padx=PADX, pady=PADY, sticky=tk.W)
        ttk.Label(tools_grid, text="960x540", style="Hint.TLabel").grid(row=1, column=1, padx=PADX, pady=PADY, sticky=tk.W)
        self.show_info_header_var = tk.BooleanVar(value=self.config['thumbnail'].get('show_info_header', True))
        ttk.Checkbutton(tools_grid, text="信息栏", variable=self.show_info_header_var).grid(row=1, column=2, padx=PADX, pady=PADY, sticky=tk.W)
        ttk.Button(tools_grid, text="生成", width=BUTTON_WIDTH, command=self.start_generate_thumbnails, style="Primary.TButton").grid(row=1, column=3, padx=PADX, pady=PADY, sticky=tk.E)

        ttk.Label(tools_grid, text="视频裁剪", style="ToolTitle.TLabel").grid(row=2, column=0, padx=PADX, pady=PADY, sticky=tk.W)
        crop_params = cell(tools_grid, 2, 1)
        ttk.Label(crop_params, text="宽").grid(row=0, column=0, padx=(0, 2), sticky=tk.W)
        self.crop_width_var = tk.StringVar(value="268")
        ttk.Entry(crop_params, textvariable=self.crop_width_var, width=ENTRY_WIDTH).grid(row=0, column=1, padx=(0, 6), sticky=tk.W)
        ttk.Label(crop_params, text="高").grid(row=0, column=2, padx=(0, 2), sticky=tk.W)
        self.crop_height_var = tk.StringVar(value="480")
        ttk.Entry(crop_params, textvariable=self.crop_height_var, width=ENTRY_WIDTH).grid(row=0, column=3, sticky=tk.W)
        ttk.Button(tools_grid, text="裁剪", width=BUTTON_WIDTH, command=self.start_crop_videos, style="Primary.TButton").grid(row=2, column=3, padx=PADX, pady=PADY, sticky=tk.E)

        ttk.Label(tools_grid, text="设置", style="ToolTitle.TLabel").grid(row=3, column=0, padx=PADX, pady=PADY, sticky=tk.W)
        settings_params = cell(tools_grid, 3, 1)
        ttk.Label(settings_params, text="线程").grid(row=0, column=0, padx=(0, 2), sticky=tk.W)
        self.thread_count_var = tk.StringVar(value=str(self.config['processing']['max_workers']))
        ttk.Entry(settings_params, textvariable=self.thread_count_var, width=ENTRY_WIDTH).grid(row=0, column=1, padx=(0, 8), sticky=tk.W)
        
        self.overwrite_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(settings_params, text="覆盖", variable=self.overwrite_var).grid(row=0, column=2, sticky=tk.W)
        
        ttk.Button(tools_grid, text="停止", width=BUTTON_WIDTH, command=self.stop_processing, style="Danger.TButton").grid(row=3, column=2, padx=PADX, pady=PADY, sticky=tk.E)
        ttk.Button(tools_grid, text="归档", width=BUTTON_WIDTH, command=self.start_organize_by_tag, style="Action.TButton").grid(row=3, column=3, padx=PADX, pady=PADY, sticky=tk.E)

        frame.columnconfigure(0, weight=1)
        tools_grid.columnconfigure(0, minsize=66, weight=0)
        tools_grid.columnconfigure(1, minsize=126, weight=0)
        tools_grid.columnconfigure(2, minsize=72, weight=0)
        tools_grid.columnconfigure(3, weight=1)
    
    def browse_input_path(self):
        path = filedialog.askdirectory(title="选择输入目录")
        if path:
            self.input_path_var.set(path)
    
    def browse_output_path(self):
        path = filedialog.askdirectory(title="选择输出目录")
        if path:
            self.output_path_var.set(path)
    
    def browse_thumbnail_path(self):
        path = filedialog.askdirectory(title="选择缩略图目录")
        if path:
            self.thumbnail_path_var.set(path)
    
    def save_paths(self):
        self.config['paths']['input_dir'] = self.input_path_var.get()
        self.config['paths']['output_dir'] = self.output_path_var.get()
        self.config['paths']['thumbnail_dir'] = self.thumbnail_path_var.get()
        self.save_config()
        messagebox.showinfo("成功", "路径设置已保存")

    def ensure_snapshot_runtime_dirs(self):
        os.makedirs(self.report_dir, exist_ok=True)

    def normalize_snapshot_root(self, directory):
        return os.path.normcase(os.path.abspath(os.path.normpath(directory)))

    def scan_directory_snapshot(self, directory):
        snapshot = {}
        for root, _, files in os.walk(directory):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                try:
                    stat = os.stat(file_path)
                except OSError:
                    continue
                relative_path = os.path.relpath(file_path, directory).replace("\\", "/")
                snapshot[relative_path] = int(stat.st_size)
        return dict(sorted(snapshot.items(), key=lambda item: item[0].casefold()))

    def load_snapshot_store(self):
        self.ensure_snapshot_runtime_dirs()
        if not os.path.exists(self.snapshot_store_path):
            return {"snapshots": {}}
        try:
            with open(self.snapshot_store_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            if not isinstance(payload, dict):
                return {"snapshots": {}}
            snapshots = payload.get("snapshots", {})
            if not isinstance(snapshots, dict):
                snapshots = {}
            return {"snapshots": snapshots}
        except Exception as e:
            self.log_message(f"读取快照库失败，将重新初始化: {e}")
            return {"snapshots": {}}

    def save_snapshot_store(self, payload):
        self.ensure_snapshot_runtime_dirs()
        with open(self.snapshot_store_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def build_snapshot_diff(self, previous_files, current_files):
        upload_files = []
        deleted_files = []

        for relative_path, size in current_files.items():
            if relative_path not in previous_files or previous_files[relative_path] != size:
                upload_files.append(relative_path)

        for relative_path in previous_files:
            if relative_path not in current_files:
                deleted_files.append(relative_path)

        return upload_files, deleted_files

    def write_snapshot_report(self, directory, upload_files, deleted_files, is_initial_snapshot):
        self.ensure_snapshot_runtime_dirs()
        timestamp = datetime.now()
        report_name = f"upload_guide_{timestamp.strftime('%Y-%m-%d_%H-%M-%S')}.txt"
        report_path = os.path.join(self.report_dir, report_name)

        lines = [
            "扫描目录:",
            directory,
            "",
            "生成时间:",
            timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "",
            "模式:",
            "首次建快照（当前目录全部列为需上传文件）" if is_initial_snapshot else "增量比对",
            "",
            f"需上传文件: {len(upload_files)}",
        ]

        if upload_files:
            lines.extend(os.path.join(directory, relative_path.replace("/", os.sep)) for relative_path in upload_files)
        else:
            lines.append("无")

        lines.extend([
            "",
            f"已删除文件: {len(deleted_files)}",
        ])

        if deleted_files:
            lines.extend(os.path.join(directory, relative_path.replace("/", os.sep)) for relative_path in deleted_files)
        else:
            lines.append("无")

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        return report_path

    def run_snapshot_check(self):
        directory = self.input_path_var.get().strip()
        if not directory:
            self.root.after(0, lambda: messagebox.showerror("错误", "请输入或选择输入目录"))
            return

        directory = os.path.abspath(os.path.normpath(directory))
        if not os.path.isdir(directory):
            self.root.after(0, lambda: messagebox.showerror("错误", f"输入目录不存在: {directory}"))
            return

        self.config['paths']['input_dir'] = directory
        self.save_config()
        self.log_message(f"开始生成快照清单: {directory}")

        current_files = self.scan_directory_snapshot(directory)
        store = self.load_snapshot_store()
        snapshots = store.setdefault("snapshots", {})
        snapshot_key = self.normalize_snapshot_root(directory)
        previous_entry = snapshots.get(snapshot_key, {})
        previous_files = previous_entry.get("files", {}) if isinstance(previous_entry, dict) else {}
        if not isinstance(previous_files, dict):
            previous_files = {}

        is_initial_snapshot = len(previous_files) == 0
        upload_files, deleted_files = self.build_snapshot_diff(previous_files, current_files)

        snapshots[snapshot_key] = {
            "path": directory,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "files": current_files,
        }
        self.save_snapshot_store(store)

        report_path = self.write_snapshot_report(directory, upload_files, deleted_files, is_initial_snapshot)
        self.log_message(f"快照完成，需上传 {len(upload_files)} 个，已删除 {len(deleted_files)} 个")
        self.log_message(f"结果文件: {report_path}")
        self.root.after(0, lambda: messagebox.showinfo("完成", f"已生成快照清单:\n{report_path}"))

    def start_snapshot_check(self):
        if self.is_processing:
            messagebox.showwarning("警告", "正在处理中，请等待完成")
            return

        thread = threading.Thread(target=self.run_snapshot_check)
        thread.daemon = True
        thread.start()
    
    def log_message(self, message):
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def get_video_files(self, directory):
        video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm']
        video_files = []
        if os.path.exists(directory):
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in video_extensions):
                        video_files.append(os.path.join(root, file))
        return video_files

    def extract_tag_from_filename(self, file_path):
        base_name = os.path.splitext(os.path.basename(file_path))[0].strip()
        if not base_name:
            return ""

        parts = base_name.split(None, 1)
        if not parts:
            return ""

        return parts[0].replace("#", "").strip()

    def find_tag_directories(self, input_dir):
        tag_directories = {}
        report_dir_name = "_归档报告"

        for root, dirs, _ in os.walk(input_dir):
            dirs[:] = [directory for directory in dirs if directory != report_dir_name]
            for directory in dirs:
                tag_directories.setdefault(directory, []).append(os.path.join(root, directory))

        return tag_directories

    def is_in_tag_directory(self, file_path, tag, input_dir):
        relative_parent = os.path.relpath(os.path.dirname(file_path), input_dir)
        if relative_parent in (".", ""):
            return False
        return tag in relative_parent.split(os.sep)

    def build_organize_report_lines(self, input_dir, moved_records, missing_tags, ambiguous_tags):
        lines = [
            f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"输入目录: {os.path.abspath(input_dir)}",
            f"成功移动: {len(moved_records)}",
            f"缺失标签目录: {len(missing_tags)}",
            f"多目标标签: {len(ambiguous_tags)}",
            "",
        ]

        if missing_tags:
            lines.append("缺失标签目录:")
            for tag in sorted(missing_tags):
                lines.append(f"- {tag}")
            lines.append("")

        if ambiguous_tags:
            lines.append("存在多个候选目录的标签:")
            for tag, paths in sorted(ambiguous_tags.items()):
                lines.append(f"- {tag}")
                for path in sorted(paths):
                    lines.append(f"  {os.path.relpath(path, input_dir)}")
            lines.append("")

        if moved_records:
            lines.append("已移动文件:")
            for source_path, target_path in moved_records:
                lines.append(f"- {source_path} -> {target_path}")
            lines.append("")

        return lines

    def move_related_image_files(self, source_video_path, target_video_path, input_dir):
        moved_records = []
        source_stem, _ = os.path.splitext(source_video_path)
        target_stem, _ = os.path.splitext(target_video_path)
        image_extensions = [".jpg", ".jpeg", ".png", ".webp"]

        for extension in image_extensions:
            source_image = source_stem + extension
            if not os.path.exists(source_image):
                continue

            target_image = target_stem + extension
            if os.path.exists(target_image):
                continue

            try:
                shutil.move(source_image, target_image)
                moved_records.append(
                    (
                        os.path.relpath(source_image, input_dir),
                        os.path.relpath(target_image, input_dir),
                    )
                )
                self.log_message(
                    f"已移动关联图片: {os.path.relpath(source_image, input_dir)} -> {os.path.relpath(target_image, input_dir)}"
                )
            except Exception as e:
                self.log_message(f"移动关联图片失败: {os.path.relpath(source_image, input_dir)} - {e}")

        return moved_records

    def organize_videos_by_tag(self):
        input_dir = os.path.normpath(self.config['paths']['input_dir'])
        video_files = self.get_video_files(input_dir)
        if not video_files:
            self.root.after(0, lambda: messagebox.showerror("错误", f"在输入目录中未找到视频文件: {input_dir}"))
            return

        moved_records = []
        missing_tags = set()
        ambiguous_tags = {}
        tag_directories = self.find_tag_directories(input_dir)

        for file_path in video_files:
            if not self.is_processing:
                break

            normalized_path = os.path.normpath(file_path)
            relative_path = os.path.relpath(normalized_path, input_dir)

            tag = self.extract_tag_from_filename(normalized_path)
            if not tag:
                continue

            if self.is_in_tag_directory(normalized_path, tag, input_dir):
                continue

            candidates = tag_directories.get(tag, [])
            if not candidates:
                missing_tags.add(tag)
                continue

            if len(candidates) > 1:
                ambiguous_tags[tag] = candidates
                continue

            target_folder = candidates[0]
            target_path = os.path.join(target_folder, os.path.basename(normalized_path))
            if os.path.exists(target_path):
                continue

            try:
                shutil.move(normalized_path, target_path)
                moved_records.append((relative_path, os.path.relpath(target_path, input_dir)))
                self.log_message(f"已移动: {relative_path} -> {os.path.relpath(target_path, input_dir)}")
                moved_records.extend(self.move_related_image_files(normalized_path, target_path, input_dir))
            except Exception as e:
                self.log_message(f"移动失败: {relative_path} - {e}")

        report_lines = self.build_organize_report_lines(input_dir, moved_records, missing_tags, ambiguous_tags)
        self.log_message("按标签归档报告:")
        for line in report_lines:
            self.log_message(line if line else " ")

        summary_lines = [f"按标签归档完成，成功移动 {len(moved_records)} 个文件。"]
        if missing_tags:
            summary_lines.append(f"缺少目录: {'、'.join(sorted(missing_tags))}。请创建后重试。")
        if ambiguous_tags:
            summary_lines.append(f"存在多个同名标签目录: {'、'.join(sorted(ambiguous_tags))}。这些文件未移动，详情见报告。")
        summary_lines.append("详细结果已输出到运行日志。")
        summary_message = "\n".join(summary_lines)

        self.root.after(0, lambda: self.finish_organize_by_tag(summary_message))

    def finish_organize_by_tag(self, summary_message):
        self.is_processing = False
        self.progress.stop()
        self.status_label.config(text="就绪")
        messagebox.showinfo("按标签归档", summary_message)
    
    def get_video_info(self, file_path):
        try:
            file_path = os.path.normpath(file_path)
            if not os.path.exists(file_path):
                self.log_message(f"文件不存在: {os.path.basename(file_path)}")
                return None
            
            probe_exe = self.resolve_app_path(self.config['ffmpeg']['probe_executable'])
            if not probe_exe:
                self.log_message(f"ffprobe不可用，请确保已安装FFmpeg并添加到PATH")
                return None
            
            command = [
                probe_exe,
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                file_path
            ]
            
            result = subprocess.run(command, capture_output=True, text=True, timeout=30, encoding='utf-8', errors='ignore')
            if result.returncode == 0:
                duration_str = result.stdout.strip()
                if duration_str and duration_str != 'N/A':
                    try:
                        duration = float(duration_str)
                        if duration > 0:
                            return duration
                        else:
                            self.log_message(f"视频时长无效: {os.path.basename(file_path)} (时长: {duration})")
                            return None
                    except ValueError:
                        self.log_message(f"无法解析视频时长: {os.path.basename(file_path)} (输出: {duration_str})")
                        return None
                else:
                    self.log_message(f"无法获取视频时长: {os.path.basename(file_path)}")
                    return None
            else:
                self.log_message(f"ffprobe执行失败: {os.path.basename(file_path)} - {result.stderr}")
                return None
                
        except Exception as e:
            self.log_message(f"获取视频信息失败 {os.path.basename(file_path)}: {e}")
        return None
    
    def get_video_info_for_thumbnail(self, video_path):
        try:
            video_path = os.path.normpath(video_path)
            duration = self.get_video_info(video_path)
            duration_str = self.format_time(duration) if duration else "未知"
            
            size_str = "未知"
            if os.path.exists(video_path):
                try:
                    file_size = os.path.getsize(video_path)
                    if file_size < 1024:
                        size_str = f"{file_size} B"
                    elif file_size < 1024 * 1024:
                        size_str = f"{file_size / 1024:.1f} KB"
                    elif file_size < 1024 * 1024 * 1024:
                        size_str = f"{file_size / (1024 * 1024):.1f} MB"
                    else:
                        size_str = f"{file_size / (1024 * 1024 * 1024):.1f} GB"
                except:
                    pass
            
            return {'duration': duration_str, 'size': size_str}
            
        except Exception as e:
            self.log_message(f"获取缩略图信息失败: {e}")
            return {'duration': "未知", 'size': "未知"}

    def get_video_dimensions(self, video_path):
        try:
            probe_exe = self.resolve_app_path(self.config['ffmpeg']['probe_executable'])
            command = [
                probe_exe,
                '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=width,height',
                '-of', 'csv=s=x:p=0',
                video_path,
            ]
            result = subprocess.run(command, capture_output=True, text=True, timeout=15, encoding='utf-8', errors='ignore')
            if result.returncode != 0:
                return None
            width_text, height_text = result.stdout.strip().split('x')[:2]
            width = int(width_text)
            height = int(height_text)
            if width > 0 and height > 0:
                return width, height
        except Exception as e:
            self.log_message(f"获取视频尺寸失败: {os.path.basename(video_path)} - {e}")
        return None

    def get_thumbnail_layout(self, video_path):
        canvas_width = int(self.config['thumbnail'].get('canvas_width', 960) or 960)
        canvas_height = int(self.config['thumbnail'].get('canvas_height', 540) or 540)
        dimensions = self.get_video_dimensions(video_path)
        source_width, source_height = dimensions or (canvas_width, canvas_height)

        if source_height > source_width:
            cols = 3
            rows = 1
            num_frames = int(self.config['thumbnail'].get('portrait_frames', 3) or 3)
        else:
            cols = 2
            rows = 2
            num_frames = int(self.config['thumbnail'].get('landscape_frames', 4) or 4)

        num_frames = max(1, min(num_frames, cols * rows))
        cell_width = canvas_width // cols
        cell_height = canvas_height // rows
        return {
            'canvas_size': (canvas_width, canvas_height),
            'cell_size': (cell_width, cell_height),
            'cols': cols,
            'rows': rows,
            'num_frames': num_frames,
            'source_size': (source_width, source_height),
        }

    def resize_cover(self, image, target_size):
        target_width, target_height = target_size
        scale = max(target_width / image.width, target_height / image.height)
        resized_width = math.ceil(image.width * scale)
        resized_height = math.ceil(image.height * scale)
        resized = image.resize((resized_width, resized_height), Image.Resampling.LANCZOS)
        left = (resized_width - target_width) // 2
        top = (resized_height - target_height) // 2
        return resized.crop((left, top, left + target_width, top + target_height))
    
    def format_time(self, seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"
    
    def remove_ads_single(self, file_path, head_time, tail_time):
        try:
            file_path = os.path.normpath(file_path)
            
            duration = self.get_video_info(file_path)
            if not duration:
                return False, f"无法获取视频时长: {os.path.basename(file_path)}"
            
            input_dir = os.path.normpath(self.config['paths']['input_dir'])
            output_dir = os.path.normpath(self.config['paths']['output_dir'])
            relative_path = os.path.relpath(file_path, input_dir)
            output_path = os.path.normpath(os.path.join(output_dir, relative_path))
            
            # 检查是否覆盖
            if not self.overwrite_var.get() and os.path.exists(output_path):
                return True, f"跳过已存在文件: {os.path.basename(file_path)}"
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            end_duration = duration - head_time - tail_time
            if end_duration <= 0:
                return False, f"处理失败: {os.path.basename(file_path)} - 去除时长后剩余时长不大于 0"

            start_time = f"{head_time:.3f}"
            trim_duration = f"{end_duration:.3f}"
            temp_output_path = output_path
            replace_original = False

            if os.path.normcase(os.path.abspath(file_path)) == os.path.normcase(os.path.abspath(output_path)):
                temp_output_path = os.path.join(
                    os.path.dirname(output_path),
                    f"{os.path.splitext(os.path.basename(output_path))[0]}.__trim_tmp__{os.path.splitext(output_path)[1]}",
                )
                replace_original = True
                if os.path.exists(temp_output_path):
                    os.remove(temp_output_path)
            
            command = [
                self.resolve_app_path(self.config['ffmpeg']['executable']), '-y',
                '-fflags', '+genpts',
                '-ss', start_time,
                '-i', file_path,
                '-t', trim_duration,
                '-map', '0',
                '-c', 'copy',
                '-movflags', '+faststart',
                '-avoid_negative_ts', 'make_zero',
                temp_output_path,
            ]
            
            result = subprocess.call(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if result == 0:
                if replace_original:
                    os.replace(temp_output_path, output_path)
                return True, f"成功处理: {os.path.basename(file_path)}"
            else:
                if replace_original and os.path.exists(temp_output_path):
                    os.remove(temp_output_path)
                return False, f"处理失败: {os.path.basename(file_path)}"
                
        except Exception as e:
            return False, f"处理异常: {os.path.basename(file_path)} - {e}"
    
    def generate_thumbnail_single(self, file_path):
        import uuid
        import threading
        
        # 生成唯一的临时文件前缀，避免多线程冲突
        unique_id = str(uuid.uuid4())[:8]
        thread_id = threading.get_ident()
        temp_prefix = f"temp_{thread_id}_{unique_id}"
        
        frame_paths = []
        try:
            file_path = os.path.normpath(file_path)
            
            input_dir = os.path.normpath(self.config['paths']['input_dir'])
            thumbnail_dir = os.path.normpath(self.config['paths']['thumbnail_dir'])
            relative_path = os.path.relpath(file_path, input_dir)
            base_name = os.path.splitext(os.path.basename(relative_path))[0]
            
            # 保持目录结构：获取相对路径的目录部分
            relative_dir = os.path.dirname(relative_path)
            if relative_dir:
                output_dir = os.path.join(thumbnail_dir, relative_dir)
            else:
                output_dir = thumbnail_dir
            
            output_path = os.path.normpath(os.path.join(output_dir, f"{base_name}.jpg"))
            
            # 检查是否覆盖
            if not self.overwrite_var.get() and os.path.exists(output_path):
                return True, f"跳过已存在文件: {base_name}.jpg"
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            duration = self.get_video_info(file_path)
            if not duration:
                return False, f"无法获取视频时长: {os.path.basename(file_path)}"

            layout = self.get_thumbnail_layout(file_path)
            num_frames = layout['num_frames']
            
            frame_interval = duration / (num_frames + 1)
            
            # 提取帧
            for i in range(num_frames):
                timestamp = 0 if i == 0 else (i + 1) * frame_interval
                
                # 确保时间戳不超过视频长度
                if timestamp >= duration:
                    timestamp = duration - 1
                if timestamp < 0:
                    timestamp = 0
                
                frame_path = f"{temp_prefix}_frame_{i}.jpg"
                frame_paths.append(frame_path)
                
                # 重试机制
                success = False
                for retry in range(3):
                    try:
                        command = [
                            self.resolve_app_path(self.config['ffmpeg']['executable']), '-y',
                            '-ss', str(timestamp),
                            '-i', file_path,
                            '-vframes', '1',
                            '-q:v', '2',
                            frame_path
                        ]
                        
                        result = subprocess.run(command, capture_output=True, text=True, timeout=30, encoding='utf-8', errors='ignore')
                        if result.returncode == 0 and os.path.exists(frame_path) and os.path.getsize(frame_path) > 0:
                            success = True
                            break
                        else:
                            # 清理可能损坏的文件
                            if os.path.exists(frame_path):
                                try:
                                    os.remove(frame_path)
                                except:
                                    pass
                            # 等待后重试
                            time.sleep(0.5)
                            
                    except subprocess.TimeoutExpired:
                        # 超时处理
                        if os.path.exists(frame_path):
                            try:
                                os.remove(frame_path)
                            except:
                                pass
                        if retry < 2:  # 不是最后一次重试
                            time.sleep(1)
                        continue
                    except Exception as e:
                        # 其他异常
                        if os.path.exists(frame_path):
                            try:
                                os.remove(frame_path)
                            except:
                                pass
                        if retry < 2:
                            time.sleep(0.5)
                        continue
                
                if not success:
                    self.cleanup_temp_files(frame_paths)
                    return False, f"提取帧失败: {os.path.basename(file_path)}"
            
            # 合成缩略图
            success = self.compose_thumbnail(frame_paths, output_path, file_path, layout)
            
            # 清理临时文件
            self.cleanup_temp_files(frame_paths)
            
            if success:
                return True, f"成功缩略图: {base_name}.jpg"
            else:
                return False, f"合成缩略图失败: {os.path.basename(file_path)}"
            
        except Exception as e:
            self.cleanup_temp_files(frame_paths)
            return False, f"缩略图异常: {os.path.basename(file_path)} - {e}"
    
    def cleanup_temp_files(self, frame_paths):
        """安全清理临时文件"""
        for path in frame_paths:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass  # 忽略删除失败的错误
    
    def get_wrapped_text(self, text, font, max_width, draw):
        """将文本按最大宽度拆分为多行"""
        lines = []
        words = list(text) # 这里简单按字符拆分，适合中文
        if not words:
            return []
            
        current_line = []
        for word in words:
            test_line = "".join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append("".join(current_line))
                current_line = [word]
        if current_line:
            lines.append("".join(current_line))
        return lines

    def compose_thumbnail(self, frame_paths, output_path, video_path, layout):
        try:
            video_name = os.path.basename(video_path)
            images = []
            for path in frame_paths:
                if os.path.exists(path):
                    try:
                        if os.path.getsize(path) > 0:
                            img = Image.open(path)
                            img.verify()
                            img = Image.open(path)
                            images.append(img)
                    except Exception as e:
                        self.log_message(f"跳过损坏的帧文件: {path} - {e}")
                        continue
            
            if not images:
                return False
            
            grid_width, grid_height = layout['canvas_size']
            cell_width, cell_height = layout['cell_size']
            cols = layout['cols']
            
            # --- 字体加载函数 ---
            font_paths = [
                "C:/Windows/Fonts/simhei.ttf",
                "C:/Windows/Fonts/msyh.ttc",
                "C:/Windows/Fonts/simsun.ttc",
                "arial.ttf",
                "C:/Windows/Fonts/arial.ttf"
            ]
            def get_font(size):
                for fp in font_paths:
                    try: return ImageFont.truetype(fp, size)
                    except: continue
                return ImageFont.load_default()

            show_info_header = self.config['thumbnail'].get('show_info_header', True)
            bg_color = tuple(self.config['thumbnail'].get('background_color', [255, 255, 255]))
            text_color = tuple(self.config['thumbnail'].get('text_color', [0, 0, 0]))
            header_height = 0
            final_image = Image.new('RGB', (grid_width, grid_height), bg_color)
            draw = ImageDraw.Draw(final_image)

            if show_info_header:
                video_info = self.get_video_info_for_thumbnail(video_path)
                full_text = f"{video_name}  |  {video_info['duration']}  |  {video_info['size']}"
                padding_x = 10
                padding_y = 20
                content_width = grid_width - (padding_x * 2)
                target_size = self.config['thumbnail'].get('font_size', 50)
                best_font = get_font(target_size)
                temp_draw = ImageDraw.Draw(Image.new('RGB', (1, 1)))

                while target_size > 1:
                    bbox = temp_draw.textbbox((0, 0), full_text, font=best_font)
                    text_w = bbox[2] - bbox[0]
                    if text_w <= content_width:
                        break
                    target_size -= 1
                    best_font = get_font(target_size)

                bbox = temp_draw.textbbox((0, 0), full_text, font=best_font)
                text_h = bbox[3] - bbox[1]
                header_height = text_h + (padding_y * 2)
                final_image = Image.new('RGB', (grid_width, grid_height + header_height), bg_color)
                draw = ImageDraw.Draw(final_image)
                text_w = bbox[2] - bbox[0]
                x_pos = (grid_width - text_w) // 2
                y_pos = padding_y
                draw.text((x_pos, y_pos), full_text, fill=text_color, font=best_font)
            
            # --- 粘贴视频帧 ---
            for i, img in enumerate(images):
                col = i % cols
                row = i // cols
                x = col * cell_width
                y = row * cell_height + header_height
                final_image.paste(self.resize_cover(img.convert('RGB'), (cell_width, cell_height)), (x, y))
            
            final_image.save(output_path, quality=90)
            return True
            
        except Exception as e:
            self.log_message(f"重构缩略图失败: {e}")
            import traceback
            self.log_message(traceback.format_exc())
            return False
            
        except Exception as e:
            self.log_message(f"重构缩略图失败: {e}")
            import traceback
            self.log_message(traceback.format_exc())
            return False
    
    def crop_video_single(self, file_path, width, height):
        try:
            file_path = os.path.normpath(file_path)
            
            input_dir = os.path.normpath(self.config['paths']['input_dir'])
            output_dir = os.path.normpath(self.config['paths']['output_dir'])
            relative_path = os.path.relpath(file_path, input_dir)
            output_path = os.path.normpath(os.path.join(output_dir, relative_path))
            
            # 检查是否覆盖
            if not self.overwrite_var.get() and os.path.exists(output_path):
                return True, f"跳过已存在文件: {os.path.basename(file_path)}"
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            command = [
                self.resolve_app_path(self.config['ffmpeg']['executable']), '-y',
                '-i', file_path,
                '-vf', f'crop={width}:{height}',
                '-c:a', 'copy',
                output_path
            ]
            
            result = subprocess.call(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if result == 0:
                return True, f"成功裁剪: {os.path.basename(file_path)}"
            else:
                return False, f"裁剪失败: {os.path.basename(file_path)}"
                
        except Exception as e:
            return False, f"裁剪异常: {os.path.basename(file_path)} - {e}"
    
    def start_remove_ads(self):
        if self.is_processing:
            messagebox.showwarning("警告", "正在处理中，请等待完成")
            return
        
        try:
            head_time = float(self.head_time_var.get())
            tail_time = float(self.tail_time_var.get())
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")
            return
        
        self.config['paths']['input_dir'] = self.input_path_var.get()
        self.config['paths']['output_dir'] = self.output_path_var.get()
        
        video_files = self.get_video_files(self.config['paths']['input_dir'])
        if not video_files:
            messagebox.showerror("错误", f"在输入目录中未找到视频文件: {self.config['paths']['input_dir']}")
            return
        
        try:
            max_workers = int(self.thread_count_var.get())
            if max_workers <= 0:
                max_workers = 1
        except ValueError:
            max_workers = multiprocessing.cpu_count()
        
        self.is_processing = True
        self.progress.start()
        self.status_label.config(text="正在去广告...")
        self.log_message(f"开始去广告，共{len(video_files)}个文件，使用{max_workers}个线程")
        
        thread = threading.Thread(target=self.process_videos, 
                                args=(video_files, self.remove_ads_single, (head_time, tail_time), max_workers, "去广告"))
        thread.daemon = True
        thread.start()
    
    def start_generate_thumbnails(self):
        if self.is_processing:
            messagebox.showwarning("警告", "正在处理中，请等待完成")
            return
        
        self.config['paths']['input_dir'] = self.input_path_var.get()
        self.config['paths']['thumbnail_dir'] = self.thumbnail_path_var.get()
        self.config['thumbnail']['show_info_header'] = self.show_info_header_var.get()
        self.save_config()
        
        video_files = self.get_video_files(self.config['paths']['input_dir'])
        if not video_files:
            messagebox.showerror("错误", f"在输入目录中未找到视频文件: {self.config['paths']['input_dir']}")
            return
        
        try:
            max_workers = int(self.thread_count_var.get())
            if max_workers <= 0:
                max_workers = 1
        except ValueError:
            max_workers = multiprocessing.cpu_count()
        
        self.is_processing = True
        self.progress.start()
        self.status_label.config(text="正在生成缩略图...")
        self.log_message(f"开始缩略图，共{len(video_files)}个文件，使用{max_workers}个线程，输出统一 960x540")
        
        thread = threading.Thread(target=self.process_videos,
                                args=(video_files, self.generate_thumbnail_single, (), max_workers, "缩略图"))
        thread.daemon = True
        thread.start()
    
    def start_crop_videos(self):
        if self.is_processing:
            messagebox.showwarning("警告", "正在处理中，请等待完成")
            return
        
        try:
            width = int(self.crop_width_var.get())
            height = int(self.crop_height_var.get())
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")
            return
        
        self.config['paths']['input_dir'] = self.input_path_var.get()
        self.config['paths']['output_dir'] = self.output_path_var.get()
        
        video_files = self.get_video_files(self.config['paths']['input_dir'])
        if not video_files:
            messagebox.showerror("错误", f"在输入目录中未找到视频文件: {self.config['paths']['input_dir']}")
            return
        
        try:
            max_workers = int(self.thread_count_var.get())
            if max_workers <= 0:
                max_workers = 1
        except ValueError:
            max_workers = multiprocessing.cpu_count()
        
        self.is_processing = True
        self.progress.start()
        self.status_label.config(text="正在裁剪视频...")
        self.log_message(f"开始裁剪，共{len(video_files)}个文件，使用{max_workers}个线程")
        
        thread = threading.Thread(target=self.process_videos, 
                                args=(video_files, self.crop_video_single, (width, height), max_workers, "裁剪"))
        thread.daemon = True
        thread.start()

    def start_organize_by_tag(self):
        if self.is_processing:
            messagebox.showwarning("警告", "正在处理中，请等待完成")
            return

        self.config['paths']['input_dir'] = self.input_path_var.get()
        self.save_config()

        input_dir = os.path.normpath(self.config['paths']['input_dir'])
        if not os.path.exists(input_dir):
            messagebox.showerror("错误", f"输入目录不存在: {input_dir}")
            return

        self.is_processing = True
        self.progress.start()
        self.status_label.config(text="正在按标签归档...")
        self.log_message(f"开始按标签归档: {input_dir}")

        thread = threading.Thread(target=self.organize_videos_by_tag)
        thread.daemon = True
        thread.start()
    
    def start_processing(self, task_name, process_func, args):
        video_files = self.get_video_files(self.config['paths']['input_dir'])
        if not video_files:
            messagebox.showerror("错误", f"在输入目录中未找到视频文件: {self.config['paths']['input_dir']}")
            return
        
        try:
            max_workers = int(self.thread_count_var.get())
            if max_workers <= 0:
                max_workers = 1
        except ValueError:
            max_workers = multiprocessing.cpu_count()
        
        self.is_processing = True
        self.progress.start()
        self.status_label.config(text=f"正在{task_name}...")
        self.log_message(f"开始{task_name}，共{len(video_files)}个文件，使用{max_workers}个线程")
        
        thread = threading.Thread(target=self.process_videos, 
                                args=(video_files, process_func, args, max_workers, task_name))
        thread.daemon = True
        thread.start()
    
    def process_videos(self, video_files, process_func, args, max_workers, task_name):
        success_count = 0
        total_count = len(video_files)
        
        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = []
                for file_path in video_files:
                    future = executor.submit(process_func, file_path, *args)
                    futures.append(future)
                
                for future in as_completed(futures):
                    if not self.is_processing:
                        break
                    
                    try:
                        success, message = future.result(timeout=300)  # 5分钟超时
                        if success:
                            success_count += 1
                        is_thumbnail_skip = (
                            task_name == "缩略图"
                            and success
                            and message.startswith("跳过已存在文件:")
                        )
                        if not is_thumbnail_skip:
                            self.log_message(message)
                    except Exception as e:
                        self.log_message(f"处理异常: {e}")
                        # 继续处理其他文件，不中断整个流程
        
        except Exception as e:
            self.log_message(f"处理过程异常: {e}")
        
        finally:
            self.is_processing = False
            self.progress.stop()
            self.status_label.config(text="就绪")
            self.log_message(f"{task_name}完成，成功处理{success_count}/{total_count}个文件")
    
    def stop_processing(self):
        if self.is_processing:
            self.is_processing = False
            self.log_message("用户停止了处理")
        else:
            messagebox.showinfo("提示", "当前没有正在处理的任务")

def main():
    root = tk.Tk()
    app = VideoProcessor(root)
    root.mainloop()

if __name__ == "__main__":
    main()

