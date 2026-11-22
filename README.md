# Custom Shell with GUI

A command shell with a graphical interface, built in Python/Tkinter for the Operating Systems course (Jul 2025). It runs built-in commands itself and hands everything else to the operating system.

## Features
- **Built-in commands:** `cd`, `pwd`, `echo`, `mkdir`, `rmdir`, `clear`/`cls`, `color`, `help`, `exit`
- **External commands** executed with `subprocess`, with stdout/stderr streamed live in separate threads
- **Background processes** (`&`) with monitoring
- **Command history** navigation with the arrow keys
- **Themes:** dark and light, with configurable fonts
- Cross-platform: `main.py` (Windows/Linux) and `Ubuntu.py` (Linux-tuned)

## Run
```bash
python main.py      # or: python Ubuntu.py on Linux
```
No external dependencies (standard library only).

## Structure
| File | Role |
| --- | --- |
| `main.py` / `Ubuntu.py` | Shell logic: parsing, built-ins, process execution |
| `gui.py` | Tkinter interface |
| `config.py` | Fonts and color themes |
