import tkinter as tk
import subprocess
import threading
import os
import sys
import shlex
import queue
from gui import ShellGUI

class ShellLogic:
    
    def __init__(self, gui_app):
        self.gui = gui_app
        self.background_processes = []
        self.command_history = []
        self.history_index = 0

    def start_command_execution(self, command_line):
        if command_line:
            if not self.command_history or self.command_history[-1] != command_line:
                self.command_history.append(command_line)
            self.history_index = len(self.command_history)
            
            thread = threading.Thread(target=self._execute_command_thread, args=(command_line,))
            thread.daemon = True
            thread.start()
        else:
            self.gui.re_enable_input()

    def get_history_entry(self, direction):
        if not self.command_history: return None
        
        if direction == "Up":
            if self.history_index > 0: self.history_index -= 1
        elif direction == "Down":
            if self.history_index < len(self.command_history): self.history_index += 1
        
        return self.command_history[self.history_index] if self.history_index < len(self.command_history) else ""

    def _pipe_reader_thread(self, pipe_fd, tag):
        try:
            with os.fdopen(pipe_fd, 'r', encoding='utf-8', errors='ignore') as pipe_file:
                for line in iter(pipe_file.readline, ''):
                    self.gui.write_to_output(line, tag)
        except Exception as e:
            self.gui.write_to_output(f"Pipe read error: {e}\n", 'error')
        finally:
            pass
    
    def _execute_command_thread(self, command_line):
        try:
            parts = shlex.split(command_line)
            command = parts[0].lower() if parts else ""

            
            if command == 'exit':
                self.gui.write_to_output("Exiting shell. Goodbye!\n")
                self.gui.root.after(500, self.gui.root.quit)
                return
            elif command == 'pwd':
                try:
                    current_dir = os.getcwd()
                    self.gui.write_to_output(f"\n{current_dir}\n")
                except Exception as e:
                    self.gui.write_to_output(f"pwd error: {e}\n", 'error')
                self.gui.gui_queue.put((self.gui.re_enable_input, [], {}))
                return
            elif command == 'echo':
                if '>' in parts:
                    redirect_index = parts.index('>')
                    output_content = ' '.join(parts[1:redirect_index])
                    if redirect_index + 1 < len(parts):
                        filename = parts[redirect_index + 1]
                        try:
                            with open(filename, 'w') as f:
                                f.write(output_content + '\n')
                            self.gui.write_to_output(f"Output redirected to {filename}\n", 'info')
                            self.gui.gui_queue.put((self.gui.refresh_all_gui_components, [], {})) 
                        except Exception as e:
                            self.gui.write_to_output(f"echo redirection error: {e}\n", 'error')
                    else:
                        self.gui.write_to_output("echo: missing filename for redirection\n", 'error')
                else:
                    output_string = ' '.join(parts[1:])
                    self.gui.write_to_output(f"\n{output_string}\n")
                self.gui.gui_queue.put((self.gui.re_enable_input, [], {}))
                return
            elif command == 'cd':
                target_dir = parts[1] if len(parts) > 1 else os.path.expanduser("~")
                try: 
                    os.chdir(target_dir)
                    self.gui.gui_queue.put((self.gui.refresh_all_gui_components, [], {}))
                except Exception as e: 
                    self.gui.write_to_output(f"cd: {e}\n", 'error')
                self.gui.gui_queue.put((self.gui.re_enable_input, [], {}))
                return
            elif command == 'mkdir':
                if len(parts) < 2:
                    self.gui.write_to_output("mkdir: missing operand\n", 'error')
                else:
                    dir_name = parts[1]
                    try:
                        os.mkdir(dir_name)
                        self.gui.gui_queue.put((self.gui.refresh_all_gui_components, [], {}))
                    except FileExistsError:
                        self.gui.write_to_output(f"mkdir: cannot create directory '{dir_name}': File exists\n", 'error')
                    except Exception as e:
                        self.gui.write_to_output(f"mkdir: {e}\n", 'error')
                self.gui.gui_queue.put((self.gui.re_enable_input, [], {}))
                return
            elif command == 'rmdir':
                if len(parts) < 2:
                    self.gui.write_to_output("rmdir: missing operand\n", 'error')
                else:
                    dir_name = parts[1]
                    try:
                        os.rmdir(dir_name)
                        self.gui.gui_queue.put((self.gui.refresh_all_gui_components, [], {}))
                    except FileNotFoundError:
                        self.gui.write_to_output(f"rmdir: failed to remove '{dir_name}': No such file or directory\n", 'error')
                    except OSError as e:
                        self.gui.write_to_output(f"rmdir: failed to remove '{dir_name}': {e.strerror}\n", 'error')
                    except Exception as e:
                        self.gui.write_to_output(f"rmdir: {e}\n", 'error')
                self.gui.gui_queue.put((self.gui.re_enable_input, [], {}))
                return
            elif command == 'color':
                color_map = {
                    '0': 'black', '1': 'blue', '2': 'green', '3': 'cyan',
                    '4': 'red', '5': 'purple', '6': 'yellow', '7': 'white',
                    '8': 'gray', '9': 'lightblue', 'a': 'lightgreen',
                    'b': 'lightcyan', 'c': 'lightcoral', 'd': 'violet',
                    'e': 'lightyellow', 'f': 'white'
                }
                if len(parts) < 2:
                    theme_fg = self.gui.themes[self.gui.current_theme]["output_fg"]
                    self.gui.gui_queue.put((self.gui.set_default_text_color, [theme_fg], {}))
                    self.gui.write_to_output("Color reset to default.\n", 'info')
                else:
                    color_code = parts[1].lower()
                    color_name = color_map.get(color_code)
                    if color_name:
                        self.gui.gui_queue.put((self.gui.set_default_text_color, [color_name], {}))
                    else:
                        self.gui.write_to_output(f"color: '{color_code}' is not a valid color code.\n", 'error')
                self.gui.gui_queue.put((self.gui.re_enable_input, [], {}))
                return
            elif command == 'clear' or (command == 'cls' and sys.platform == "win32"):
                self.gui.gui_queue.put((lambda: (
                    self.gui.terminal_output.config(state=tk.NORMAL),
                    self.gui.terminal_output.delete('1.0', tk.END),
                    self.gui.terminal_output.config(state=tk.DISABLED)
                ), [], {}))
                self.gui.gui_queue.put((self.gui.re_enable_input, [], {}))
                return
            elif command == 'help':
                builtins = {
                    "help": "Shows this list of built-in commands.",
                    "cd <dir>": "Changes the current directory. 'cd' alone goes home.",
                    "pwd": "Prints the current working directory.",
                    "echo [text]": "Displays text.",
                    "mkdir <dir>": "Creates a new directory.",
                    "rmdir <dir>": "Removes an empty directory.",
                    "color <id>": "Changes the prompt and text color (e.g., 'color 1').",
                    "clear / cls": "Clears the terminal screen.",
                    "exit": "Exits the shell."
                }
                help_text = "\n--- Python Shell Help ---\n\n"
                help_text += "Built-in Commands:\n"
                for cmd, desc in builtins.items():
                    help_text += f"  {cmd:<15} {desc}\n"
                
                help_text += "\nFeatures:\n"
                help_text += "  - Piping:           command1 | command2\n"
                help_text += "  - I/O Redirection:  command > file.txt or command < file.txt\n"
                help_text += "  - Backgrounding:    command &\n"
                
               
                self.gui.write_to_output(help_text)
                self.gui.gui_queue.put((self.gui.re_enable_input, [], {}))
                return
            
            if sys.platform == 'win32':
                self.gui.write_to_output("This shell version uses fork/exec and is designed for Unix-like systems (e.g., Ubuntu).\n", 'error')
                self.gui.write_to_output("Please use the Windows-compatible version for full functionality on Windows.\n", 'error')
                self.gui.gui_queue.put((self.gui.re_enable_input, [], {}))
                return

            is_background = command_line.strip().endswith('&')
            if is_background:
                command_line = command_line.strip()[:-1].strip()
                parts = shlex.split(command_line)
                command = parts[0]

            redirect_stdout_file = None
            if '>' in parts:
                redirect_index = parts.index('>')
                if redirect_index + 1 < len(parts):
                    redirect_stdout_file = parts[redirect_index + 1]
                    parts = parts[:redirect_index]
                    command = parts[0]
                else:
                    self.gui.write_to_output("Syntax error: missing filename for output redirection.\n", 'error')
                    self.gui.gui_queue.put((self.gui.re_enable_input, [], {}))
                    return
            
            stdout_read_fd, stdout_write_fd = os.pipe()
            stderr_read_fd, stderr_write_fd = os.pipe()

            pid = os.fork()

            if pid == 0:
                try:
                    os.close(stdout_read_fd)
                    os.close(stderr_read_fd)

                    if redirect_stdout_file:
                        file_fd = os.open(redirect_stdout_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
                        os.dup2(file_fd, sys.stdout.fileno())
                        os.close(file_fd)
                    else:
                        os.dup2(stdout_write_fd, sys.stdout.fileno())

                    os.dup2(stderr_write_fd, sys.stderr.fileno())

                    os.close(stdout_write_fd)
                    os.close(stderr_write_fd)

                    os.execvp(command, parts)
                except OSError as e:
                    os.write(sys.stderr.fileno(), f"execvp error: {e.strerror}\n".encode())
                    os._exit(1)
                except Exception as e:
                    os.write(sys.stderr.fileno(), f"Child process error: {e}\n".encode())
                    os._exit(1)

            else:
                os.close(stdout_write_fd)
                os.close(stderr_write_fd)

                if is_background:
                    self.background_processes.append((pid, stdout_read_fd, stderr_read_fd))
                    self.gui.write_to_output(f"[+] Background process started: {pid}\n", 'background')
                    self.gui.gui_queue.put((self.gui.re_enable_input, [], {}))
                else:
                    stdout_thread = threading.Thread(target=self._pipe_reader_thread, args=(stdout_read_fd, 'default'))
                    stderr_thread = threading.Thread(target=self._pipe_reader_thread, args=(stderr_read_fd, 'error'))
                    
                    stdout_thread.start()
                    stderr_thread.start()

                    pid_waited, status = os.waitpid(pid, 0) 
                    
                    stdout_thread.join()
                    stderr_thread.join()

                    os.close(stdout_read_fd)
                    os.close(stderr_read_fd)

                    self.gui.gui_queue.put((self.gui.re_enable_input, [], {}))
                    self.gui.gui_queue.put((self.gui.refresh_all_gui_components, [], {}))

        except OSError as e:
            self.gui.write_to_output(f"Shell error: {e.strerror}\n", 'error')
            self.gui.gui_queue.put((self.gui.re_enable_input, [], {}))
        except Exception as e:
            self.gui.write_to_output(f"Execution error: {e}\n", 'error')
            self.gui.gui_queue.put((self.gui.re_enable_input, [], {}))

    def monitor_background_processes(self):
        for i, (pid, stdout_fd, stderr_fd) in enumerate(self.background_processes[:]):
            try:
                pid_waited, status = os.waitpid(pid, os.WNOHANG)
                if pid_waited == pid:
                    output = f"\n[+] Background process {pid} finished.\n"
                    self.gui.write_to_output(output, 'background')
                    
                    try:
                        with os.fdopen(stdout_fd, 'r', encoding='utf-8', errors='ignore') as f:
                            remaining_stdout = f.read()
                            if remaining_stdout:
                                self.gui.write_to_output(f"[Output from {pid}]:\n{remaining_stdout}", 'default')
                        with os.fdopen(stderr_fd, 'r', encoding='utf-8', errors='ignore') as f:
                            remaining_stderr = f.read()
                            if remaining_stderr:
                                self.gui.write_to_output(f"[Error from {pid}]:\n{remaining_stderr}", 'error')
                    except Exception as e:
                        self.gui.write_to_output(f"Error reading background process output for {pid}: {e}\n", 'error')
                    finally:
                        try: os.close(stdout_fd)
                        except OSError: pass
                        try: os.close(stderr_fd)
                        except OSError: pass

                    self.background_processes.pop(i)
                    self.gui.gui_queue.put((self.gui.refresh_all_gui_components, [], {}))
            except ChildProcessError:
                self.gui.write_to_output(f"Background process {pid} already reaped.\n", 'info')
                self.background_processes.pop(i)
            except Exception as e:
                self.gui.write_to_output(f"Error monitoring background process {pid}: {e}\n", 'error')
        self.gui.gui_queue.put((self.gui.update_status_bar, [], {}))
        self.gui.root.after(2000, self.monitor_background_processes)

if __name__ == "__main__":
    root = tk.Tk()
    logic_handler = ShellLogic(None)
    gui_app = ShellGUI(root, logic_handler)
    logic_handler.gui = gui_app
    root.after(2000, logic_handler.monitor_background_processes)
    root.mainloop()
