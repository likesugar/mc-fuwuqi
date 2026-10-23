#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MC开服 PC 版 — 一键下载核心/创建/配置/运行 Minecraft 服务器 (Windows)
数据目录: ~/MCFuwuqi/<服务器名>/
"""
import json, os, sys, threading, time, urllib.request, subprocess, shutil
import tkinter as tk
from tkinter import ttk, messagebox

HOME = os.path.join(os.path.expanduser("~"), "MCFuwuqi")
CFG = os.path.join(HOME, "servers.json")

CORES = {"Vanilla": "纯净官方核心",
         "Paper": "https://api.papermc.io/v2/projects/paper/versions/{v}/builds",
         "Purpur": "https://api.purpurmc.org/v2/purpur/{v}"}
MC_VERSIONS = ["1.21.4", "1.21.1", "1.20.6", "1.20.4", "1.20.2", "1.19.4", "1.18.2", "1.17.1", "1.16.5", "1.12.2", "1.8.8"]

DEFAULT_PROPS = """server-port=25565
motd=我的服务器
max-players=20
online-mode=false
enforce-secure-profile=false
difficulty=easy
gamemode=survival
pvp=true
white-list=false
view-distance=6
simulation-distance=4
network-compression-threshold=256
sync-chunk-writes=false
spawn-protection=0
max-tick-time=-1
"""


JRE_DIR = os.path.join(HOME, "jre")


def find_java():
    # 1) exe 旁边的 jre/（离线内置包）
    base = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
    for root, _, files in os.walk(os.path.join(base, "jre")):
        if "java.exe" in files:
            return os.path.join(root, "java.exe")
    # 2) ~/MCFuwuqi/jre（此前自动下载过）
    if os.path.isdir(JRE_DIR):
        for root, _, files in os.walk(JRE_DIR):
            if "java.exe" in files:
                return os.path.join(root, "java.exe")
    # 3) 系统 PATH
    return shutil.which("java")


def jre_url():
    u = "https://api.adoptium.net/v3/assets/latest/21/hotspot?os=windows&architecture=x64&image_type=jre"
    req = urllib.request.Request(u, headers={"User-Agent": "MC-Fuwuqi"})
    with urllib.request.urlopen(req, timeout=30) as r:
        assets = json.load(r)
    return assets[0]["binary"]["package"]["link"]


def download_jre(progress=lambda s: None):
    if os.path.isdir(JRE_DIR):
        j = find_java()
        if j: return j
    progress("下载内置 JRE（约 45MB，一次即可）…")
    zpath = os.path.join(HOME, "jre.zip")
    req = urllib.request.Request(jre_url(), headers={"User-Agent": "MC-Fuwuqi"})
    with urllib.request.urlopen(req, timeout=60) as r, open(zpath, "wb") as f:
        total = int(r.headers.get("Content-Length", 0)); done = 0
        while True:
            chunk = r.read(65536)
            if not chunk: break
            f.write(chunk); done += len(chunk)
            if total: progress(f"下载内置 JRE… {done*100//total}%")
    progress("解压 JRE…")
    import zipfile
    with zipfile.ZipFile(zpath) as z: z.extractall(HOME)
    os.remove(zpath)
    for d in os.listdir(HOME):
        src = os.path.join(HOME, d)
        if d.startswith("jdk-") and d.endswith("jre") and os.path.isdir(src):
            if not os.path.isdir(JRE_DIR): os.rename(src, JRE_DIR)
            else: shutil.rmtree(src, ignore_errors=True)
            break
    return find_java()


def http_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "MCFuwuqi/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def download(url, path, cb=None):
    req = urllib.request.Request(url, headers={"User-Agent": "MCFuwuqi/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r, open(path, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0); got = 0
        while True:
            b = r.read(65536)
            if not b: break
            f.write(b); got += len(b)
            if cb: cb(got, total)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MC开服")
        self.geometry("860x560")
        self.proc = None
        self.servers = self.load_servers()
        self.cur = None
        self._build()
        self.refresh_list()

    # ---------- 数据 ----------
    def load_servers(self):
        try:
            return json.load(open(CFG, encoding="utf-8"))
        except Exception:
            return []

    def save_servers(self):
        os.makedirs(HOME, exist_ok=True)
        json.dump(self.servers, open(CFG, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    def server_dir(self, name):
        return os.path.join(HOME, name)

    # ---------- UI ----------
    def _build(self):
        left = tk.Frame(self, width=220, bg="#1B1C1F")
        left.pack(side="left", fill="y")
        tk.Label(left, text="MC开服", fg="#4FC3F7", bg="#1B1C1F", font=("微软雅黑", 15, "bold"), pady=10).pack()
        self.listbox = tk.Listbox(left, bg="#121212", fg="#E8EAED", selectbackground="#2A4A5A",
                                  relief="flat", font=("微软雅黑", 11), width=22)
        self.listbox.pack(fill="both", expand=True, padx=8)
        self.listbox.bind("<<ListboxSelect>>", self.on_select)
        tk.Button(left, text="＋ 新建服务器", command=self.new_server_dlg, bg="#2D2F33", fg="#E8EAED",
                  relief="flat", pady=6, font=("微软雅黑", 10)).pack(fill="x", padx=8, pady=6)
        tk.Button(left, text="删除所选", command=self.del_server, bg="#2D2F33", fg="#FF6E6E",
                  relief="flat", pady=4).pack(fill="x", padx=8)

        right = tk.Frame(self, bg="#121212")
        right.pack(side="left", fill="both", expand=True)
        bar = tk.Frame(right, bg="#121212"); bar.pack(fill="x", pady=6, padx=10)
        self.btn_start = tk.Button(bar, text="▶ 启动", command=self.start_server, bg="#1B5E20", fg="white",
                                   relief="flat", padx=18, pady=6, font=("微软雅黑", 11, "bold"))
        self.btn_start.pack(side="left")
        self.btn_stop = tk.Button(bar, text="■ 停止", command=self.stop_server, bg="#5A1A1A", fg="white",
                                  relief="flat", padx=14, pady=6, state="disabled")
        self.btn_stop.pack(side="left", padx=8)
        tk.Button(bar, text="配置 server.properties", command=self.edit_props, bg="#2D2F33", fg="#E8EAED",
                  relief="flat", padx=10, pady=6).pack(side="left")
        tk.Button(bar, text="打开文件夹", command=self.open_dir, bg="#2D2F33", fg="#E8EAED",
                  relief="flat", padx=10, pady=6).pack(side="left")
        self.status = tk.Label(bar, text="", fg="#9AA0A6", bg="#121212", font=("微软雅黑", 10))
        self.status.pack(side="right")

        self.console = tk.Text(right, bg="#0D0E0F", fg="#C8E6C9", relief="flat",
                               font=("Consolas", 10), state="disabled")
        self.console.pack(fill="both", expand=True, padx=10, pady=(0, 4))
        cmdbar = tk.Frame(right, bg="#121212"); cmdbar.pack(fill="x", padx=10, pady=(0, 10))
        self.cmd = tk.Entry(cmdbar, bg="#1B1C1F", fg="#E8EAED", relief="flat", font=("Consolas", 11))
        self.cmd.pack(side="left", fill="x", expand=True, ipady=6)
        self.cmd.bind("<Return>", self.send_cmd)
        tk.Button(cmdbar, text="发送", command=self.send_cmd, bg="#2D2F33", fg="#E8EAED",
                  relief="flat", padx=14).pack(side="left", padx=(6, 0))

    def log(self, s):
        self.console.configure(state="normal")
        self.console.insert("end", s + "\n"); self.console.see("end")
        self.console.configure(state="disabled")

    def refresh_list(self):
        self.listbox.delete(0, "end")
        for s in self.servers: self.listbox.insert("end", s["name"])
        if self.servers and self.cur is None:
            self.listbox.selection_set(0); self.on_select()

    def sel_name(self):
        sel = self.listbox.curselection()
        return self.servers[sel[0]]["name"] if sel else None

    def on_select(self, *_):
        n = self.sel_name(); self.cur = n

    # ---------- 新建 ----------
    def new_server_dlg(self):
        win = tk.Toplevel(self); win.title("新建服务器"); win.configure(bg="#1B1C1F")
        win.geometry("340x300"); win.grab_set()
        def row(txt):
            tk.Label(win, text=txt, fg="#9AA0A6", bg="#1B1C1F", font=("微软雅黑", 10)).pack(anchor="w", padx=16, pady=(8, 0))
            e = tk.Entry(win, bg="#121212", fg="#E8EAED", relief="flat", font=("微软雅黑", 11))
            e.pack(fill="x", padx=16, ipady=5); return e
        e_name = row("服务器名")
        e_name.insert(0, "我的服务器")
        tk.Label(win, text="核心", fg="#9AA0A6", bg="#1B1C1F", font=("微软雅黑", 10)).pack(anchor="w", padx=16, pady=(8, 0))
        cb_core = ttk.Combobox(win, values=list(CORES), state="readonly", font=("微软雅黑", 11))
        cb_core.current(0); cb_core.pack(fill="x", padx=16)
        tk.Label(win, text="MC 版本", fg="#9AA0A6", bg="#1B1C1F", font=("微软雅黑", 10)).pack(anchor="w", padx=16, pady=(8, 0))
        cb_ver = ttk.Combobox(win, values=MC_VERSIONS, state="readonly", font=("微软雅黑", 11))
        cb_ver.current(0); cb_ver.pack(fill="x", padx=16)
        lbl_mem = tk.Label(win, text="内存 2048 MB", fg="#4FC3F7", bg="#1B1C1F", font=("微软雅黑", 10))
        lbl_mem.pack(anchor="w", padx=16, pady=(8, 0))
        mem = {"v": 2048}
        def memchange(ev):
            mem["v"] = 512 + ev.widget.get() * 256; lbl_mem.config(text=f"内存 {mem['v']} MB")
        sb = tk.Scale(win, from_=0, to=14, orient="horizontal", showvalue=False,
                      bg="#1B1C1F", highlightthickness=0, command=memchange); sb.set(6); sb.pack(fill="x", padx=16)

        def create():
            name = e_name.get().strip() or "我的服务器"
            if any(s["name"] == name for s in self.servers):
                messagebox.showwarning("提示", "同名服务器已存在"); return
            d = self.server_dir(name); os.makedirs(d, exist_ok=True)
            self.servers.append({"name": name, "core": cb_core.get(), "mc": cb_ver.get(), "mem": mem["v"]})
            self.save_servers(); self.refresh_list()
            open(os.path.join(d, "server.properties"), "w", encoding="utf-8").write(DEFAULT_PROPS)
            open(os.path.join(d, "eula.txt"), "w").write("#Auto\neula=true\n")
            win.destroy()
            threading.Thread(target=self.download_core, args=(name, cb_core.get(), cb_ver.get()), daemon=True).start()

        tk.Button(win, text="创 建", command=create, bg="#1B5E20", fg="white", relief="flat",
                  font=("微软雅黑", 12, "bold"), pady=6).pack(fill="x", padx=16, pady=14)

    def download_core(self, name, core, ver):
        d = self.server_dir(name)
        self.log(f"· 下载 {core} {ver} …")
        try:
            if core == "Vanilla":
                manifest = http_json("https://piston-meta.mojang.com/mc/game/version_manifest_v2.json")
                vurl = next(v["url"] for v in manifest["versions"] if v["id"] == ver)
                url = http_json(vurl)["downloads"]["server"]["url"]
            elif core == "Paper":
                builds = http_json(CORES["Paper"].format(v=ver))["builds"]
                b = builds[-1]["build"]
                jn = http_json(f"https://api.papermc.io/v2/projects/paper/versions/{ver}/builds/{b}")["downloads"]["application"]["name"]
                url = f"https://api.papermc.io/v2/projects/paper/versions/{ver}/builds/{b}/downloads/{jn}"
            else:  # Purpur
                data = http_json(CORES["Purpur"].format(v=ver))
                b = data["builds"]["latest"]
                url = f"https://api.purpurmc.org/v2/purpur/{ver}/{b}/download"
            jar = os.path.join(d, "server.jar")
            download(url, jar, lambda g, t: self.log(f"  {g//1024//1024}MB" + (f"/{t//1024//1024}MB" if t else "")))
            self.log("· 下载完成 ✓ 可以启动了")
            self.status.config(text=f"{name} 就绪")
        except Exception as e:
            self.log(f"· 下载失败: {e}")

    # ---------- 运行 ----------
    def start_server(self):
        if self.proc: messagebox.showinfo("提示", "已有服务器在运行"); return
        n = self.cur or self.sel_name()
        if not n: return
        cfg = next((s for s in self.servers if s["name"] == n), None)
        d = self.server_dir(n)
        jar = os.path.join(d, "server.jar")
        if not os.path.isfile(jar):
            messagebox.showwarning("提示", "server.jar 还没下载好"); return
        mem = cfg["mem"] if cfg else 2048
        java = find_java()
        if not java:
            self.log("· 首次运行：自动下载内置 JRE（约 45MB）…")
            def dl():
                try:
                    j = download_jre(progress=lambda s2: self.after(0, lambda: self.status.config(text=s2)))
                    self.after(0, lambda: self.start_server_with(n, j))
                except Exception as e:
                    self.after(0, lambda: self.log("JRE 下载失败: " + str(e)))
            threading.Thread(target=dl, daemon=True).start()
            return
        self.start_server_with(n, java)

    def start_server_with(self, n, java):
        cfg = next((s for s in self.servers if s["name"] == n), None)
        d = self.server_dir(n)
        mem = cfg["mem"] if cfg else 2048
        self.log(f"· 启动 {n}（{mem}MB）…")
        self.proc = subprocess.Popen([java, f"-Xms{mem}M", f"-Xmx{mem}M", "-Dfile.encoding=UTF-8",
                                      "-jar", "server.jar", "nogui"], cwd=d,
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE,
                                     text=True, encoding="utf-8", errors="replace")
        self.btn_start.config(state="disabled"); self.btn_stop.config(state="normal")
        self.status.config(text=f"{n} 运行中")
        threading.Thread(target=self._pump, daemon=True).start()

    def _pump(self):
        p = self.proc
        for line in p.stdout:
            self.log(line.rstrip())
        self.log("· 进程已退出")
        self.proc = None
        self.after(0, lambda: (self.btn_start.config(state="normal"), self.btn_stop.config(state="disabled"),
                               self.status.config(text="已停止")))

    def stop_server(self):
        if self.proc:
            try: self.proc.stdin.write("stop\n"); self.proc.stdin.flush()
            except Exception: pass

    def send_cmd(self, *_):
        c = self.cmd.get().strip(); self.cmd.delete(0, "end")
        if not self.proc: self.log("· 服务器未运行"); return
        try: self.proc.stdin.write(c + "\n"); self.proc.stdin.flush()
        except Exception as e: self.log(f"· 发送失败: {e}")

    # ---------- 其他 ----------
    def edit_props(self):
        n = self.cur or self.sel_name()
        if not n: return
        f = os.path.join(self.server_dir(n), "server.properties")
        win = tk.Toplevel(self); win.title(f"配置 — {n}"); win.geometry("620x520")
        t = tk.Text(win, bg="#121212", fg="#E8EAED", relief="flat", font=("Consolas", 10),
                    insertbackground="white")
        t.pack(fill="both", expand=True)
        try: t.insert("1.0", open(f, encoding="utf-8").read())
        except Exception: t.insert("1.0", DEFAULT_PROPS)
        def save():
            open(f, "w", encoding="utf-8").write(t.get("1.0", "end"))
            messagebox.showinfo("提示", "已保存，重启服务器后生效"); win.destroy()
        tk.Button(win, text="保存", command=save, bg="#1B5E20", fg="white", relief="flat",
                  font=("微软雅黑", 11, "bold"), pady=5).pack(fill="x", side="bottom")

    def open_dir(self):
        n = self.cur or self.sel_name()
        if n: os.startfile(self.server_dir(n))

    def del_server(self):
        n = self.sel_name()
        if not n: return
        if not messagebox.askyesno("删除", f"删除服务器「{n}」？（文件保留在磁盘）"): return
        self.servers = [s for s in self.servers if s["name"] != n]
        self.save_servers(); self.cur = None; self.refresh_list()


if __name__ == "__main__":
    os.makedirs(HOME, exist_ok=True)
    App().mainloop()
