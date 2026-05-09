"""
DeepSeek API 余额查询桌宠
一个在桌面漂浮的宠物，可随时查询 DeepSeek API 余额
"""

import tkinter as tk
from tkinter import messagebox, simpledialog
from PIL import Image, ImageTk, ImageDraw
import requests
import json
import os
import sys
import threading
import time
import io
import re
import xml.etree.ElementTree as ET

# SVG 路径渲染 (纯 Python)
try:
    from svg.path import parse_path
except ImportError:
    parse_path = None

# ============ 配置 ============
CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "api_key": ""
}

# ============ 路径处理 ============
if getattr(sys, 'frozen', False):
    # PyInstaller 打包后的路径
    RESOURCE_DIR = sys._MEIPASS
    CONFIG_DIR = os.path.dirname(sys.executable)
else:
    RESOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
    CONFIG_DIR = RESOURCE_DIR

ICON_DIR = os.path.join(RESOURCE_DIR, "icon")
CONFIG_PATH = os.path.join(CONFIG_DIR, CONFIG_FILE)


# ============ 配置管理 ============
def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except Exception:
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()


def save_config(config):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"保存配置失败: {e}")


# ============ API 余额查询 ============
def check_balance(api_key):
    """查询 DeepSeek API 余额"""
    url = "https://api.deepseek.com/user/balance"
    payload = {}
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    try:
        resp = requests.request("GET", url, headers=headers, data=payload, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            # DeepSeek 实际返回格式:
            # { "is_available": true, "balance_infos": [{ "currency": "CNY",
            #   "total_balance": "110.00", "granted_balance": "10.00",
            #   "topped_up_balance": "100.00" }] }
            balance_infos = data.get("balance_infos", [])
            if balance_infos:
                info = balance_infos[0]
                total = info.get("total_balance", "N/A")
                return True, f"💰 ¥{total}"
            return False, "❌ 无法获取余额信息"
        elif resp.status_code == 401:
            return False, "❌ API Key 无效\n请检查后重试"
        elif resp.status_code == 429:
            return False, "⏳ 请求过于频繁\n请稍后再试"
        else:
            return False, f"❌ 错误: HTTP {resp.status_code}"
    except requests.exceptions.Timeout:
        return False, "⏰ 请求超时\n请检查网络连接"
    except requests.exceptions.ConnectionError:
        return False, "🌐 网络连接失败\n请检查网络"
    except requests.exceptions.RequestException as e:
        return False, f"🌐 网络错误:\n{str(e)[:30]}"


# ============ 对话框气泡 ============
class SpeechBubble(tk.Toplevel):
    """显示信息的对话气泡 - 半透明玻璃效果"""

    def __init__(self, parent, text, near_x, near_y, duration=4000):
        super().__init__(parent)
        self.overrideredirect(True)
        self.wm_attributes("-topmost", True)
        self.configure(bg="#1a1a1a")
        self.wm_attributes("-alpha", 0.88)

        # 尝试启用 Windows DWM 模糊效果
        self._enable_blur()

        # 气泡主体 (深色半透明玻璃)
        frame = tk.Frame(self, bg="#1a1a1a", padx=18, pady=12)
        frame.pack(fill="both", expand=True)

        self.label = tk.Label(frame, text=text, bg="#1a1a1a",
                              fg="#f0f0f0", font=("", 12),
                              justify="left")
        self.label.pack()

        # 计算尺寸并定位
        self.update_idletasks()
        w = self.winfo_reqwidth()
        h = self.winfo_reqheight()

        # 确保不超出屏幕
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()

        x = max(10, min(near_x - w // 2, screen_w - w - 10))
        y = near_y - h - 10

        # 如果气泡会超出顶部，显示在下方
        if y < 0:
            y = near_y + 60

        self.geometry(f"+{x}+{y}")

        # 自动关闭
        if duration > 0:
            self.after(duration, self.destroy)

        # 点击气泡关闭
        self.label.bind("<Button-1>", lambda e: self.destroy())
        frame.bind("<Button-1>", lambda e: self.destroy())

    def _enable_blur(self):
        """启用 Windows 窗口模糊效果 (DWM)"""
        try:
            import ctypes
            hwnd = self.winfo_id()
            # 扩展窗口框架以实现模糊
            margins = ctypes.c_int(-1)
            ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea(
                ctypes.c_int(hwnd), ctypes.byref(margins))
        except Exception:
            pass


# ============ 设置 API Key 对话框 ============
class SettingsDialog:
    def __init__(self, parent, current_key, on_save):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("设置 API Key")
        self.dialog.configure(bg="#f5f5f5")
        self.dialog.resizable(False, False)
        self.dialog.wm_attributes("-topmost", True)
        self.on_save = on_save

        # 居中显示
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        p_w = parent.winfo_width()
        p_h = parent.winfo_height()
        w, h = 420, 230
        x = parent_x + (p_w - w) // 2
        y = parent_y + (p_h - h) // 2
        self.dialog.geometry(f"{w}x{h}+{x}+{y}")

        # 标题
        tk.Label(self.dialog, text="DeepSeek API 配置",
                 font=("", 12, "bold"),
                 bg="#f5f5f5", fg="#333").pack(pady=(15, 5))

        tk.Label(self.dialog, text="请输入你的 DeepSeek API Key：",
                 font=("", 9),
                 bg="#f5f5f5", fg="#666").pack()

        # Key 输入框
        entry_frame = tk.Frame(self.dialog, bg="#f5f5f5")
        entry_frame.pack(pady=10)

        self.key_var = tk.StringVar(value=current_key)
        self.entry = tk.Entry(entry_frame, textvariable=self.key_var,
                              width=40, show="*",
                              font=("", 10),
                              bd=1, relief="solid")
        self.entry.pack(side="left", padx=(0, 5))
        self.entry.focus_set()

        # 显示/隐藏
        self.show_var = tk.BooleanVar(value=False)

        def toggle_show():
            self.entry.configure(show="" if self.show_var.get() else "*")

        tk.Checkbutton(entry_frame, text="显示", variable=self.show_var,
                       command=toggle_show,
                       bg="#f5f5f5", font=("", 9)).pack(side="left")

        # 提示文字
        tk.Label(self.dialog,
                 text="可在 platform.deepseek.com/api_keys 获取",
                 font=("", 8),
                 bg="#f5f5f5", fg="#999").pack()

        # 按钮
        btn_frame = tk.Frame(self.dialog, bg="#f5f5f5")
        btn_frame.pack(pady=(10, 15))

        tk.Button(btn_frame, text="保存", width=10,
                  font=("", 10),
                  bg="#4A90D9", fg="white", relief="flat",
                  activebackground="#357ABD",
                  command=self.save).pack(side="left", padx=5)

        tk.Button(btn_frame, text="取消", width=10,
                  font=("", 10),
                  bg="#e0e0e0", fg="#333", relief="flat",
                  command=self.dialog.destroy).pack(side="left", padx=5)

        self.dialog.protocol("WM_DELETE_WINDOW", self.dialog.destroy)
        self.dialog.bind("<Return>", lambda e: self.save())

    def save(self):
        key = self.key_var.get().strip()
        if key:
            self.on_save(key)
            self.dialog.destroy()
        else:
            messagebox.showwarning("提示", "请输入 API Key")

# ============ 主窗口 ============
class PetWindow:
    """桌面宠物主窗口"""

    def __init__(self, root):
        self.root = root
        self.config = load_config()
        self.balance_cache = ""
        self.last_check_time = 0

        # 窗口设置 - 先隐藏，防止窗口提前映射导致任务栏出现
        self.root.withdraw()
        self.root.overrideredirect(True)
        self.root.wm_attributes("-topmost", True)
        self.root.configure(bg="white")
        # 让白色背景透明
        try:
            self.root.wm_attributes("-transparentcolor", "white")
        except Exception:
            pass

        # 加载宠物图片 (SVG)
        self.pet_image_path = os.path.join(ICON_DIR, "API接入.svg")
        self.original_image = None
        self.pet_photo = None

        if os.path.exists(self.pet_image_path):
            try:
                self.original_image = self._load_svg(self.pet_image_path, 40)
            except Exception as e:
                print(f"加载 SVG 失败: {e}")
                self.original_image = None
        else:
            print(f"SVG 不存在: {self.pet_image_path}")
            self.original_image = None

        if self.original_image is None:
            self.create_placeholder()

        self.display_image = self.original_image.copy()
        self.update_pet_image()

        # 显示宠物 (可拖拽移动)
        self.drag_data = {"start_x": 0, "start_y": 0, "win_x": 0, "win_y": 0, "dragging": False}

        self.label = tk.Label(self.root, image=self.pet_photo,
                              bg="white", cursor="hand2")
        self.label.pack()

        # 鼠标事件: 点击不拖动→查余额, 拖动→移动位置
        self.label.bind("<ButtonPress-1>", self._drag_start)
        self.label.bind("<B1-Motion>", self._drag_move)
        self.label.bind("<ButtonRelease-1>", self._drag_end)

        # 右键菜单
        self.setup_context_menu()

        # 固定位置 - 屏幕右下角
        # 使用 update_idletasks 计算尺寸但不映射窗口
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w = self.root.winfo_reqwidth()
        h = self.root.winfo_reqheight()
        self.root.geometry(f"+{sw - w - 30}+{sh - h - 60}")

        # 设置 WS_EX_TOOLWINDOW 确保窗口不出现在任务栏
        self._hide_from_taskbar()

        # 设置任务栏图标
        ico_path = os.path.join(ICON_DIR, "app_icon.ico")
        if os.path.exists(ico_path):
            try:
                self.root.iconbitmap(ico_path)
            except Exception:
                pass

        # 显示窗口
        self.root.deiconify()

        # 如果有 API Key，启动后自动查询
        if self.config.get("api_key"):
            self.root.after(1500, self.check_balance_silent)

    def _hide_from_taskbar(self):
        """通过 WS_EX_TOOLWINDOW 使窗口不在任务栏显示（在窗口映射前调用）"""
        try:
            import ctypes
            hwnd = self.root.winfo_id()
            GWL_EXSTYLE = -20
            WS_EX_APPWINDOW = 0x00040000
            WS_EX_TOOLWINDOW = 0x00000080
            user32 = ctypes.windll.user32
            ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            # 移除 WS_EX_APPWINDOW，添加 WS_EX_TOOLWINDOW
            new_style = ex_style & ~WS_EX_APPWINDOW | WS_EX_TOOLWINDOW
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_style)
        except Exception:
            pass

    def create_placeholder(self):
        """创建占位图片"""
        img = Image.new("RGBA", (200, 200), (180, 200, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.ellipse([40, 30, 160, 150], fill=(255, 255, 200, 255))
        draw.ellipse([70, 60, 90, 85], fill=(0, 0, 0, 255))
        draw.ellipse([110, 60, 130, 85], fill=(0, 0, 0, 255))
        draw.arc([60, 90, 140, 130], 0, 180, fill=(200, 100, 100, 255), width=3)
        self.original_image = img.convert("RGB")

    def update_pet_image(self):
        """更新显示的宠物图片"""
        if self.display_image:
            self.pet_photo = ImageTk.PhotoImage(self.display_image)
            if hasattr(self, 'label'):
                self.label.configure(image=self.pet_photo)

    def _load_svg(self, path, size):
        """加载 SVG 并转换为 PIL Image (纯 Python，无需 cairo)"""
        tree = ET.parse(path)
        root = tree.getroot()

        # 获取 viewBox
        ns = "http://www.w3.org/2000/svg"
        vb = root.get("viewBox", "0 0 200 200")
        parts = [float(x) for x in vb.replace(",", " ").split()]
        vx, vy, vw, vh = parts

        # 计算缩放
        scale = min(size / max(vw, vh), 1.0) * 0.9
        iw = max(1, int(vw * scale))
        ih = max(1, int(vh * scale))

        img = Image.new("RGBA", (iw, ih), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # 遍历所有 path 元素
        for path_elem in root.iter(f"{{{ns}}}path"):
            d = path_elem.get("d", "")
            if not d:
                continue

            fill_color = self._parse_svg_color(path_elem.get("fill", "#333333"))

            if parse_path:
                try:
                    path_obj = parse_path(d)
                    # 对路径稠密采样绘制填充
                    samples = 40  # 每个 segment 采样点数
                    all_points = []
                    for seg in path_obj:
                        for i in range(samples + 1):
                            t = i / samples
                            pt = seg.point(t)
                            px = (pt.real - vx) * scale
                            py = (pt.imag - vy) * scale
                            all_points.append((px, py))
                    if len(all_points) > 2:
                        draw.polygon(all_points, fill=fill_color, outline=None)
                    continue
                except Exception:
                    pass

            # fallback: 简单路径字符串解析 (无 svg.path 时)
            self._draw_path_simple(draw, d, scale, -vx, -vy, fill_color)

        return img

    def _parse_svg_color(self, color_str):
        """解析 SVG 颜色值为 RGBA 元组"""
        color_str = color_str.strip()
        # 十六进制 #RRGGBB 或 #RGB
        m = re.match(r'^#([0-9a-fA-F]{2})([0-9a-fA-F]{2})([0-9a-fA-F]{2})$', color_str)
        if m:
            return tuple(int(x, 16) for x in m.groups()) + (255,)
        m = re.match(r'^#([0-9a-fA-F])([0-9a-fA-F])([0-9a-fA-F])$', color_str)
        if m:
            return tuple(int(x * 2, 16) for x in m.groups()) + (255,)
        # 命名颜色
        named = {"black": (51, 51, 51, 255), "white": (255, 255, 255, 255),
                 "none": (0, 0, 0, 0)}
        if color_str.lower() in named:
            return named[color_str.lower()]
        return (51, 51, 51, 255)  # 默认深灰

    def _draw_path_simple(self, draw, d, scale, dx, dy, fill_color):
        """简易 SVG path 解析器 (纯正则，处理 M/L/Z 命令)"""
        # 标准化：命令前加分隔符
        d_norm = re.sub(r'([MLZmlz])', r' \1 ', d)
        tokens = d_norm.split()
        i = 0
        current_pos = (0, 0)
        start_pos = (0, 0)
        polygon = []

        while i < len(tokens):
            t = tokens[i]
            if t.upper() == 'M':
                if polygon:
                    if len(polygon) > 2:
                        draw.polygon(polygon, fill=fill_color, outline=None)
                    polygon = []
                i += 1
                if i < len(tokens):
                    try:
                        x = float(tokens[i]) * scale + dx * scale
                        y = float(tokens[i + 1]) * scale + dy * scale
                        current_pos = (x, y)
                        start_pos = (x, y)
                        polygon.append((x, y))
                        i += 2
                    except (IndexError, ValueError):
                        break
            elif t.upper() == 'L':
                i += 1
                if i < len(tokens):
                    try:
                        x = float(tokens[i]) * scale + dx * scale
                        y = float(tokens[i + 1]) * scale + dy * scale
                        current_pos = (x, y)
                        polygon.append((x, y))
                        i += 2
                    except (IndexError, ValueError):
                        break
            elif t.upper() == 'Z':
                if len(polygon) > 2:
                    draw.polygon(polygon, fill=fill_color, outline=None)
                polygon = []
                current_pos = start_pos
                i += 1
            else:
                # 跳过无法解析的 token
                i += 1

        if len(polygon) > 2:
            draw.polygon(polygon, fill=fill_color, outline=None)

    def setup_context_menu(self):
        """设置右键菜单"""
        self.menu = tk.Menu(self.root, tearoff=0,
                            font=("", 10),
                            bg="#ffffff", fg="#333333",
                            activebackground="#4A90D9",
                            activeforeground="white")

        self.menu.add_command(label="🔍 查询余额",
                              command=self.on_check_balance)
        self.menu.add_command(label="⚙️ 设置 API Key",
                              command=self.on_set_api_key)
        self.menu.add_separator()
        self.menu.add_command(label="🚪 退出",
                              command=self.on_exit)

        self.root.bind("<Button-3>", self.show_context_menu)

    def show_context_menu(self, event):
        self.menu.post(event.x_root, event.y_root)

    # ========== 拖拽移动 ==========
    def _drag_start(self, event):
        self.drag_data["start_x"] = event.x_root
        self.drag_data["start_y"] = event.y_root
        self.drag_data["win_x"] = self.root.winfo_x()
        self.drag_data["win_y"] = self.root.winfo_y()
        self.drag_data["dragging"] = False

    def _drag_move(self, event):
        dx = event.x_root - self.drag_data["start_x"]
        dy = event.y_root - self.drag_data["start_y"]
        if abs(dx) > 3 or abs(dy) > 3:
            self.drag_data["dragging"] = True
        self.root.geometry(f"+{self.drag_data['win_x'] + dx}+{self.drag_data['win_y'] + dy}")

    def _drag_end(self, event):
        if not self.drag_data["dragging"]:
            self.on_check_balance()

    # ========== 余额查询 ==========
    def on_check_balance(self):
        """查询余额（显示加载气泡）"""
        api_key = self.config.get("api_key", "")
        if not api_key:
            self.on_set_api_key()
            return

        # 计算宠物中心位置
        pet_x = self.root.winfo_x() + self.root.winfo_width() // 2
        pet_y = self.root.winfo_y()

        # 显示加载中
        loading_bubble = SpeechBubble(
            self.root, "⏳ 查询中...",
            pet_x, pet_y, duration=0
        )

        def worker():
            success, msg = check_balance(api_key)
            if success:
                self.balance_cache = msg
                self.last_check_time = time.time()
                self.config["last_balance"] = msg
                save_config(self.config)

            self.root.after(0, lambda: self.show_balance(success, msg, loading_bubble))

        threading.Thread(target=worker, daemon=True).start()

    def check_balance_silent(self):
        """静默查询（不显示加载气泡）"""
        api_key = self.config.get("api_key", "")
        if not api_key:
            return

        def worker():
            success, msg = check_balance(api_key)
            if success:
                self.balance_cache = msg
                self.last_check_time = time.time()
                self.config["last_balance"] = msg
                save_config(self.config)
                # 显示结果
                pet_x = self.root.winfo_x() + self.root.winfo_width() // 2
                pet_y = self.root.winfo_y()
                self.root.after(0, lambda: SpeechBubble(
                    self.root, msg, pet_x, pet_y, duration=3000))

        threading.Thread(target=worker, daemon=True).start()

    def show_balance(self, success, msg, loading_bubble=None):
        """显示查询结果"""
        try:
            if loading_bubble:
                loading_bubble.destroy()
        except Exception:
            pass

        pet_x = self.root.winfo_x() + self.root.winfo_width() // 2
        pet_y = self.root.winfo_y()

        SpeechBubble(self.root, msg, pet_x, pet_y)

    # ========== 设置 ==========
    def on_set_api_key(self):
        """打开 API Key 设置"""
        current_key = self.config.get("api_key", "")

        def on_save(key):
            self.config["api_key"] = key
            save_config(self.config)
            # 保存后自动查询
            self.root.after(500, self.check_balance_silent)

        SettingsDialog(self.root, current_key, on_save)

    # ========== 退出 ==========
    def on_exit(self):
        try:
            self.root.quit()
            self.root.destroy()
        except Exception:
            pass
        os._exit(0)


# ============ 启动 ============
def main():
    root = tk.Tk()
    root.title("DeepSeek 余额桌宠")

    app = PetWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
