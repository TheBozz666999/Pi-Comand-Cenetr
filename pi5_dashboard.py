#!/usr/bin/env python3
"""Pi 5 Command Center: live Rich dashboard for Raspberry Pi OS."""
from __future__ import annotations

import os
import socket
import subprocess
import time
from collections import deque
from datetime import timedelta

import psutil
from rich import box
from rich.align import Align
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()
HISTORY_LEN = 48
cpu_history = [
    deque([0.0] * HISTORY_LEN, maxlen=HISTORY_LEN)
    for _ in range(psutil.cpu_count(logical=True) or 4)
]
net_history = deque([0.0] * HISTORY_LEN, maxlen=HISTORY_LEN)
last_net = psutil.net_io_counters()
last_tick = time.monotonic()
boot_time = psutil.boot_time()


def read_text(path: str, default: str = "") -> str:
    try:
        with open(path, "r", encoding="utf-8") as file:
            return file.read().strip()
    except (OSError, ValueError):
        return default


def temperature() -> str:
    """Read Raspberry Pi temperature, with a Linux thermal-zone fallback."""
    try:
        result = subprocess.run(
            ["vcgencmd", "measure_temp"],
            capture_output=True,
            text=True,
            timeout=1,
            check=False,
        )
        if result.returncode == 0 and "=" in result.stdout:
            return result.stdout.strip().split("=", 1)[1].replace("'C", "°C")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    raw = read_text("/sys/class/thermal/thermal_zone0/temp")
    try:
        return f"{float(raw) / 1000:.1f}°C"
    except ValueError:
        return "N/A"


def cpu_frequency() -> str:
    freq = psutil.cpu_freq()
    if freq and freq.current:
        return f"{freq.current / 1000:.2f} GHz"

    raw = read_text("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq")
    try:
        return f"{int(raw) / 1_000_000:.2f} GHz"
    except ValueError:
        return "N/A"


def throttle_status() -> str:
    try:
        result = subprocess.run(
            ["vcgencmd", "get_throttled"],
            capture_output=True,
            text=True,
            timeout=1,
            check=False,
        )
        if result.returncode == 0:
            value = result.stdout.strip().split("=", 1)[-1]
            if value == "0x0":
                return f"[green]{value}[/green] (clear)"
            return f"[bold yellow]{value}[/bold yellow] (flags set)"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return "[dim]vcgencmd unavailable[/dim]"


def bar(percent: float, width: int = 18) -> str:
    percent = max(0.0, min(100.0, percent))
    filled = round(width * percent / 100)
    color = "green" if percent < 65 else "yellow" if percent < 85 else "red"
    return f"[{color}]{'█' * filled}[/][dim]{'░' * (width - filled)}[/] {percent:5.1f}%"


def sparkline(values: deque[float], maximum: float | None = None) -> str:
    chars = "▁▂▃▄▅▆▇█"
    if not values:
        return ""
    top = maximum if maximum is not None else max(max(values), 1.0)
    return "".join(chars[min(7, int((value / top) * 7))] for value in values)


def fmt_bytes(value: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"


def make_header() -> Panel:
    now = time.strftime("%a %d %b %Y  %H:%M:%S")
    title = Text(" PI 5 COMMAND CENTER ", style="bold bright_cyan")
    title.append("  //  ", style="dim")
    title.append(socket.gethostname(), style="bold white")
    title.append("  //  ", style="dim")
    title.append(now, style="bright_green")
    return Panel(Align.center(title), border_style="bright_cyan", box=box.DOUBLE)


def make_system_panel() -> Panel:
    vm = psutil.virtual_memory()
    swap = psutil.swap_memory()
    disk = psutil.disk_usage("/")
    load = os.getloadavg() if hasattr(os, "getloadavg") else (0, 0, 0)
    uptime = timedelta(seconds=int(time.time() - boot_time))

    table = Table.grid(expand=True, padding=(0, 1))
    table.add_column(ratio=1)
    table.add_column(ratio=1)
    table.add_row(
        f"[bold]CPU temp[/bold]  [bright_yellow]{temperature()}[/bright_yellow]",
        f"[bold]CPU clock[/bold]  [bright_cyan]{cpu_frequency()}[/bright_cyan]",
    )
    table.add_row(
        f"[bold]RAM[/bold]  {bar(vm.percent)}",
        f"[bold]Swap[/bold]  {bar(swap.percent)}",
    )
    table.add_row(
        f"[bold]Root SSD[/bold]  {bar(disk.percent)}",
        f"[bold]Uptime[/bold]  [white]{uptime}[/white]",
    )
    table.add_row(
        f"[bold]RAM used[/bold]  {fmt_bytes(vm.used)} / {fmt_bytes(vm.total)}",
        f"[bold]Disk free[/bold]  {fmt_bytes(disk.free)}",
    )
    table.add_row(
        f"[bold]Load avg[/bold]  [white]{load[0]:.2f}  {load[1]:.2f}  {load[2]:.2f}[/white]",
        f"[bold]Throttle[/bold]  {throttle_status()}",
    )
    return Panel(table, title="[bold bright_cyan]SYSTEM[/bold bright_cyan]", border_style="cyan")


def make_cpu_panel() -> Panel:
    values = psutil.cpu_percent(percpu=True)
    table = Table(box=box.SIMPLE, expand=True, show_header=True, header_style="bold bright_cyan")
    table.add_column("Core", style="white", width=7)
    table.add_column("Usage", ratio=2)
    table.add_column("Trend", ratio=1)
    for index, value in enumerate(values):
        if index < len(cpu_history):
            cpu_history[index].append(value)
            trend = f"[bright_cyan]{sparkline(cpu_history[index], 100)}[/]"
        else:
            trend = ""
        table.add_row(f"CPU {index}", bar(value, 16), trend)
    return Panel(table, title="[bold bright_cyan]PROCESSOR · PER CORE[/bold bright_cyan]", border_style="cyan")


def make_network_panel() -> Panel:
    global last_net, last_tick
    current = psutil.net_io_counters()
    now = time.monotonic()
    elapsed = max(now - last_tick, 0.001)
    download = (current.bytes_recv - last_net.bytes_recv) / elapsed
    upload = (current.bytes_sent - last_net.bytes_sent) / elapsed
    last_net, last_tick = current, now
    net_history.append(download + upload)

    table = Table.grid(expand=True)
    table.add_column(ratio=1)
    table.add_column(ratio=1)
    table.add_row(
        f"[bold green]↓ DOWNLOAD[/bold green]\n[bold white]{fmt_bytes(download)}/s[/]",
        f"[bold magenta]↑ UPLOAD[/bold magenta]\n[bold white]{fmt_bytes(upload)}/s[/]",
    )
    table.add_row(
        f"[dim]Total received: {fmt_bytes(current.bytes_recv)}[/]",
        f"[dim]Total sent: {fmt_bytes(current.bytes_sent)}[/]",
    )
    table.add_row(f"[bright_cyan]Traffic trend[/bright_cyan]  {sparkline(net_history)}", "")
    return Panel(table, title="[bold bright_cyan]NETWORK[/bold bright_cyan]", border_style="cyan")


def make_process_panel() -> Panel:
    processes = []
    for proc in psutil.process_iter(["pid", "name", "memory_info"]):
        try:
            info = proc.info
            cpu = proc.cpu_percent(interval=None)
            memory_info = info.get("memory_info")
            rss = memory_info.rss if memory_info else 0
            processes.append((cpu, rss, info["pid"], info.get("name") or "?"))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    processes.sort(reverse=True)
    table = Table(box=box.SIMPLE, expand=True, header_style="bold bright_cyan")
    table.add_column("PID", justify="right", width=7)
    table.add_column("Process", ratio=2, no_wrap=True)
    table.add_column("CPU", justify="right", width=7)
    table.add_column("RAM", justify="right", width=10)
    for cpu, rss, pid, name in processes[:6]:
        table.add_row(str(pid), name[:24], f"{cpu:.1f}%", fmt_bytes(rss))
    return Panel(table, title="[bold bright_cyan]TOP PROCESSES · LIVE[/bold bright_cyan]", border_style="cyan")


def render():
    from rich.layout import Layout

    layout = Layout()
    layout.split_column(
        Layout(make_header(), name="header", size=3),
        Layout(name="main", ratio=1),
        Layout(make_network_panel(), name="network", size=7),
    )
    layout["main"].split_row(Layout(name="left", ratio=1), Layout(name="right", ratio=1))
    layout["left"].split_column(
        Layout(make_system_panel(), name="system", ratio=1),
        Layout(make_cpu_panel(), name="cpu", ratio=1),
    )
    layout["right"].update(make_process_panel())
    return layout


def main() -> None:
    psutil.cpu_percent(interval=None)
    for proc in psutil.process_iter():
        try:
            proc.cpu_percent(interval=None)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    with Live(render(), console=console, screen=False, refresh_per_second=1) as live:
        while True:
            time.sleep(1)
            live.update(render(), refresh=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
