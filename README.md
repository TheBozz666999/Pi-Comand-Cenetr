# Pi 5 Command Center

A cyber-styled, live terminal performance dashboard for Raspberry Pi OS Lite. It runs in an SSH session using `tmux`, with the monitor in the upper pane and an interactive shell in the lower pane.

## Features

- Per-core CPU utilization with short history sparklines
- CPU temperature and frequency
- Raspberry Pi throttling flags via `vcgencmd` when available
- RAM, swap, root filesystem usage, and free disk space
- System load average and uptime
- Network upload/download rates and cumulative traffic
- Top processes by sampled CPU usage and resident memory
- One-second refresh interval
- Interactive shell remains available in the lower tmux pane

## Requirements

- Raspberry Pi OS Lite (64-bit recommended)
- Python 3
- `tmux`
- Python packages `psutil` and `rich`

## Install

Clone the repository on your Raspberry Pi:

```bash
git clone https://github.com/YOUR_GITHUB_USERNAME/pi5-command-center.git
cd pi5-command-center
```

Install dependencies:

```bash
chmod +x scripts/install.sh scripts/start-pi5cc
./scripts/install.sh
```

## Run

```bash
./scripts/start-pi5cc
```

The top pane displays the dashboard. Use the lower pane as a normal shell to run other commands while monitoring continues.

## tmux controls

| Action | Shortcut / command |
|---|---|
| Detach and leave it running | `Ctrl+B`, then `D` |
| Reattach | `tmux attach -t pi5cc` |
| Switch panes | `Ctrl+B`, then an arrow key |
| Enter scroll mode | `Ctrl+B`, then `[`; press `q` to exit |
| Stop the session | `tmux kill-session -t pi5cc` |

Mouse support is enabled for pane selection and resizing in compatible terminal clients.

## Notes and limitations

- `vcgencmd` is used for Raspberry Pi temperature and throttling telemetry when installed and accessible. Temperature falls back to the Linux thermal-zone interface.
- Some Raspberry Pi OS images may not expose every telemetry field; unavailable values are shown as `N/A` or `vcgencmd unavailable`.
- Process CPU percentages are sampled and can initially appear as zero.
- The dashboard currently monitors the root filesystem (`/`) for disk capacity. It does not yet report NVMe read/write throughput.
- This project is a lightweight terminal monitor, not a replacement for a full diagnostic or alerting system.

## Contributing

Issues and pull requests are welcome. Please include your Raspberry Pi model, OS release, and the full error output when reporting a problem.

## License

MIT. See [LICENSE](LICENSE).
