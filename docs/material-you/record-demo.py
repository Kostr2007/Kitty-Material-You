"""Record the actual built fork, with no synthetic terminal rendering.
Run under Xvfb after building result-demo; requires ffmpeg and openbox.
The --scene mode runs inside Kitty and only writes terminal escape sequences.
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/material-you"

def scene():
    def write(s):
        sys.stdout.write(s)
        sys.stdout.flush()
    write("\033[2J\033[H\033[?25l")
    lines = [
        "",
        "  KITTY  /  MATERIAL YOU",
        "  Spring motion. Rounded shapes. Living color.",
        "",
        "  REAL TERMINAL  •  native rendering",
        "",
        "  Palette",
        "",
        "  Cursor trail  /  m3-expressive-fast",
        "",
        "",
        "",
        "",
        "  Dark → Light → Dark  /  OKLab color transition",
        "",
        "  github.com/Kostr2007/Kitty-Material-You",
    ]
    write("\r\n".join(lines))
    write("\033[8;4H")
    for i in range(8):
        write(f"\033[48;5;{i + 8}m    \033[0m ")
    write("\033[?25h")
    while True:
        for row, col in [(11, 5), (11, 45), (13, 45), (13, 5), (11, 25), (13, 60)]:
            write(f"\033[{row};{col}H")
            time.sleep(0.55)

def main():
    kitty = ROOT / "result-demo/bin/kitty"
    if not kitty.exists():
        raise SystemExit("Build first: nix build .#kitty-material-you-no-tests --out-link result-demo")
    with tempfile.TemporaryDirectory(prefix="kitty-demo-") as folder:
        tmp = Path(folder)
        socket = tmp / "control"
        config = tmp / "kitty.conf"
        config.write_text(
            f"include {ROOT}/extras/material-you.conf\n"
            f"include {ROOT}/extras/themes/material-you-dark.conf\n"
            "font_family DejaVu Sans Mono\nfont_size 17\n"
            "window_padding_width 24\n"
            "confirm_os_window_close 0\nallow_remote_control socket-only\n"
            "linux_display_server x11\n"
        )
        session = tmp / "session"
        command = f"{sys.executable} {Path(__file__).resolve()} --scene"
        session.write_text(
            f"new_tab Material You\nlaunch {command}\n"
            f"new_tab Palette\nlaunch {command}\n"
            "focus_tab 1\n"
        )
        wm = subprocess.Popen(["openbox"], stdout=subprocess.DEVNULL)
        terminal = None
        recorder = None
        try:
            time.sleep(1)
            terminal_env = os.environ.copy()
            terminal_env["LIBGL_DRIVERS_PATH"] = str(ROOT / "result-mesa/lib/dri")
            terminal_env["LD_LIBRARY_PATH"] = f"{ROOT}/result-gl/lib:{ROOT}/result-mesa/lib"
            terminal_env["__GLX_VENDOR_LIBRARY_NAME"] = "mesa"
            terminal = subprocess.Popen([
                str(kitty), "--config", str(config), "--session", str(session),
                "--listen-on", f"unix:{socket}", "--start-as", "fullscreen",
            ], env=terminal_env)
            deadline = time.monotonic() + 30
            while not socket.exists():
                if terminal.poll() is not None:
                    raise RuntimeError("Kitty exited before remote control became available")
                if time.monotonic() > deadline:
                    raise TimeoutError("Kitty remote control was not ready")
                time.sleep(0.2)
            time.sleep(2)
            recorder = subprocess.Popen([
                "ffmpeg", "-y", "-loglevel", "warning",
                "-f", "x11grab", "-video_size", "1000x620", "-framerate", "30",
                "-draw_mouse", "0", "-i", os.environ["DISPLAY"],
                "-t", "15", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-crf", "18", str(OUT / "demo.mp4"),
            ])
            for theme in ["light", "dark"]:
                time.sleep(5)
                subprocess.run([
                    str(kitty), "@", "--to", f"unix:{socket}",
                    "set-colors", "--all",
                    str(ROOT / f"extras/themes/material-you-{theme}.conf"),
                ], check=True)
            if recorder.wait(timeout=30) != 0:
                raise RuntimeError("Screen recording failed")
            subprocess.run([
                "ffmpeg", "-y", "-loglevel", "warning", "-i", str(OUT / "demo.mp4"),
                "-filter_complex",
                "fps=20,scale=900:-1:flags=lanczos,split[a][b];"
                "[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=sierra2_4a",
                "-loop", "0", str(OUT / "demo.gif"),
            ], check=True)
        finally:
            for process in [recorder, terminal, wm]:
                if process is not None and process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()

if __name__ == "__main__":
    if "--scene" in sys.argv:
        scene()
    else:
        main()
