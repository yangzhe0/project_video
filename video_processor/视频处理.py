import tkinter as tk
from tkinter import messagebox, filedialog
import ttkbootstrap as ttk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
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
    SERIES_FOLDER_SUFFIX = "系列"

    def __init__(self, root):
        self.root = root
        self.root.title("Video Processor")
        self.root.geometry("620x920")
        self.root.minsize(680, 620)
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.drive_root = os.path.dirname(self.base_dir)
        self.root_config_path = os.path.join(self.drive_root, "配置.json")
        self.report_dir = os.path.join(self.drive_root, "reports")
        self.config_path = os.path.join(self.base_dir, "settings.json")
        self.snapshot_store_path = os.path.join(self.base_dir, "snapshots.json")
        
        self.config = {
            "paths": {
                "input_dir": "../library",
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
        for key in ("input_dir", "thumbnail_dir"):
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
        self.config["paths"]["thumbnail_dir"] = self.resolve_root_path(library_dir)
        self.report_dir = self.resolve_root_path(root_config.get("报告", "./reports"))

    def setup_styles(self):
        # ttkbootstrap 负责全局主题和控件样式。
        self.colors = {"bg": "#f6f7fb", "panel": "#ffffff", "text": "#1f2937", "muted": "#667085"}

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
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        shell = ttk.Frame(self.root, padding=18)
        shell.grid(row=0, column=0, sticky=NSEW)
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(3, weight=1)

        header = ttk.Frame(shell)
        header.grid(row=0, column=0, sticky=EW, pady=(0, 16))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="视频处理工作台", font=("Microsoft YaHei UI", 22, "bold"), bootstyle="primary").grid(row=0, column=0, sticky=W)
        ttk.Label(header, text="缩略图 · 快照 · 归档", font=("Microsoft YaHei UI", 10), bootstyle="secondary").grid(row=1, column=0, sticky=W, pady=(3, 0))
        self.status_label = ttk.Label(header, text="就绪", bootstyle="success", padding=(10, 4))
        self.status_label.grid(row=0, column=1, rowspan=2, sticky=E)

        self.create_path_section(shell, 1)
        self.create_tools_section(shell, 2)

        log_card = ttk.LabelFrame(shell, text="运行日志", padding=10, bootstyle="secondary")
        log_card.grid(row=3, column=0, sticky=NSEW, pady=(0, 8))
        log_card.columnconfigure(0, weight=1); log_card.rowconfigure(1, weight=1)
        self.progress = ttk.Progressbar(log_card, mode='indeterminate', bootstyle="info-striped")
        self.progress.grid(row=0, column=0, sticky=EW, pady=(0, 8))
        self.log_text = tk.Text(log_card, height=14, bg="#172033", fg="#e6edf7", insertbackground="#ffffff", relief="flat", bd=0, padx=10, pady=8, font=("Consolas", 10))
        scrollbar = ttk.Scrollbar(log_card, orient="vertical", command=self.log_text.yview, bootstyle="round")
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.grid(row=1, column=0, sticky=NSEW); scrollbar.grid(row=1, column=1, sticky=NS)
        ttk.Label(shell, text="提示：处理前请确认输入目录；勾选“覆盖”后会替换已存在结果。", bootstyle="secondary").grid(row=4, column=0, sticky=W)

    def create_path_section(self, parent, row):
        card = ttk.LabelFrame(parent, text=" 目录设置 ", padding=14, bootstyle="primary")
        card.grid(row=row, column=0, sticky=EW, pady=(0, 12))
        card.columnconfigure(1, weight=1)
        ttk.Label(card, text="输入目录", bootstyle="secondary").grid(row=0, column=0, padx=(0, 10), pady=6, sticky=W)
        self.input_path_var = tk.StringVar(value=self.config['paths']['input_dir'])
        ttk.Entry(card, textvariable=self.input_path_var).grid(row=0, column=1, padx=6, pady=6, sticky=EW)
        ttk.Button(card, text="浏览", command=self.browse_input_path, bootstyle="outline-secondary").grid(row=0, column=2, padx=(6, 0), pady=6)
        ttk.Label(card, text="缩略图目录", bootstyle="secondary").grid(row=1, column=0, padx=(0, 10), pady=6, sticky=W)
        self.thumbnail_path_var = tk.StringVar(value=self.config['paths']['thumbnail_dir'])
        ttk.Entry(card, textvariable=self.thumbnail_path_var).grid(row=1, column=1, padx=6, pady=6, sticky=EW)
        ttk.Button(card, text="浏览", command=self.browse_thumbnail_path, bootstyle="outline-secondary").grid(row=1, column=2, padx=(6, 0), pady=6)
        ttk.Button(card, text="保存路径设置", command=self.save_paths, bootstyle="primary").grid(row=2, column=1, padx=6, pady=(10, 0), sticky=W)

    def create_tools_section(self, parent, row):
        card = ttk.LabelFrame(parent, text=" 处理工具 ", padding=14, bootstyle="primary")
        card.grid(row=row, column=0, sticky=EW, pady=(0, 12))
        card.columnconfigure(1, weight=1); card.columnconfigure(4, weight=1)
        thumb = ttk.Frame(card)
        thumb.grid(row=0, column=0, columnspan=3, sticky=EW, padx=(0, 14))
        ttk.Label(thumb, text="缩略图", font=("Microsoft YaHei UI", 11, "bold"), bootstyle="primary").grid(row=0, column=0, sticky=W)
        ttk.Label(thumb, text="输出 960×540", bootstyle="secondary").grid(row=1, column=0, sticky=W, pady=(3, 0))
        self.show_info_header_var = tk.BooleanVar(value=self.config['thumbnail'].get('show_info_header', True))
        ttk.Checkbutton(thumb, text="显示信息栏", variable=self.show_info_header_var, bootstyle="round-toggle").grid(row=2, column=0, sticky=W, pady=(10, 0))
        ttk.Button(thumb, text="生成缩略图", command=self.start_generate_thumbnails, bootstyle="success").grid(row=0, column=1, rowspan=3, padx=(28, 0), sticky=E)
        ttk.Separator(card, orient=VERTICAL).grid(row=0, column=3, rowspan=2, sticky=NS, padx=12)
        settings = ttk.Frame(card)
        settings.grid(row=0, column=4, columnspan=2, sticky=EW)
        ttk.Label(settings, text="运行设置", font=("Microsoft YaHei UI", 11, "bold"), bootstyle="primary").grid(row=0, column=0, columnspan=2, sticky=W)
        ttk.Label(settings, text="线程数", bootstyle="secondary").grid(row=1, column=0, sticky=W, pady=(10, 0))
        self.thread_count_var = tk.StringVar(value=str(self.config['processing']['max_workers']))
        ttk.Entry(settings, textvariable=self.thread_count_var, width=7).grid(row=1, column=1, sticky=W, padx=(10, 0), pady=(10, 0))
        self.overwrite_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(settings, text="覆盖已存在文件", variable=self.overwrite_var, bootstyle="round-toggle").grid(row=2, column=0, columnspan=2, sticky=W, pady=(10, 0))
        actions = ttk.Frame(card)
        actions.grid(row=1, column=0, columnspan=6, sticky=EW, pady=(16, 0))
        ttk.Button(actions, text="生成快照清单", command=self.start_snapshot_check, bootstyle="info-outline").pack(side=LEFT)
        ttk.Button(actions, text="归档", command=self.start_organize_by_tag, bootstyle="secondary-outline").pack(side=LEFT, padx=(10, 0))

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
        self.config['paths']['thumbnail_dir'] = self.thumbnail_path_var.get()
        self.save_config()
        messagebox.showinfo("成功", "路径设置已保存")

    def ensure_snapshot_runtime_dirs(self):
        os.makedirs(self.report_dir, exist_ok=True)

    def normalize_snapshot_root(self, directory):
        return os.path.normcase(os.path.abspath(os.path.normpath(directory)))

    def get_series_roots(self, directory):
        """返回所选目录自身或其第一层中以“系列”结尾的文件夹。"""
        directory = os.path.abspath(os.path.normpath(directory))
        if not os.path.isdir(directory):
            return []

        if os.path.basename(directory).endswith(self.SERIES_FOLDER_SUFFIX):
            return [directory]

        try:
            roots = [
                entry.path
                for entry in os.scandir(directory)
                if entry.is_dir() and entry.name.endswith(self.SERIES_FOLDER_SUFFIX)
            ]
        except OSError:
            return []
        return sorted(roots, key=lambda path: path.casefold())

    def scan_directory_snapshot(self, directory):
        snapshot = {}
        for series_root in self.get_series_roots(directory):
            for root, _, files in os.walk(series_root):
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
        snapshot_key = f"{self.normalize_snapshot_root(directory)}::series-folders"
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
        for series_root in self.get_series_roots(directory):
            for root, _, files in os.walk(series_root):
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

        for series_root in self.get_series_roots(input_dir):
            series_name = os.path.basename(series_root)
            tag_directories.setdefault(series_name, []).append(series_root)
            for root, dirs, _ in os.walk(series_root):
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
    

def main():
    root = tb.Window(themename="flatly")
    app = VideoProcessor(root)
    root.mainloop()

if __name__ == "__main__":
    main()

