import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont
import queue
import os
from config import DEFAULT_FONT_CONFIG, THEMES

class ShellGUI:
    
    def __init__(self, root, logic_handler):
        self.root = root
        self.logic_handler = logic_handler
        self.root.title("Python Shell GUI")
        self.root.geometry("1100x700")

        self.default_font = tkfont.Font(**DEFAULT_FONT_CONFIG)
        self.themes = THEMES
        self.current_theme = "dark"
        self.gui_queue = queue.Queue()

        self._setup_layout()
        self._setup_widgets()
        self.apply_theme()
        self.process_gui_queue()
        self.refresh_all_gui_components()

    def _setup_layout(self):
       
        self.status_bar = tk.Frame(self.root)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 5))
        self.status_dir_label = tk.Label(self.status_bar, text="Directory: ", font=self.default_font, anchor='w')
        self.status_dir_label.pack(side=tk.LEFT)

        self.paned_window = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashwidth=8)
        self.paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 0))

        self.left_frame = tk.Frame(self.paned_window)
        self.paned_window.add(self.left_frame, width=250)

        self.right_frame = tk.Frame(self.paned_window)
        self.paned_window.add(self.right_frame)

    def _setup_widgets(self):
        
        self.tree = ttk.Treeview(self.left_frame, show='tree')
        tree_scrollbar = ttk.Scrollbar(self.left_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scrollbar.set)
        
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree.bind("<Double-1>", self._on_treeview_select)

        self.top_frame = tk.Frame(self.right_frame)
        self.top_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.top_buttons = []
        quick_commands = [
            ("List Files", "ls -l" if os.name != "nt" else "dir"),
            ("Current Dir", "pwd"), 
            ("Clear", "clear"),
            ("Help", "help")
        ]

        for text, command in quick_commands:
            btn = tk.Button(self.top_frame, text=text, font=self.default_font, relief=tk.FLAT,
                            command=lambda c=command: self.execute_from_button(c))
            btn.pack(side=tk.LEFT, padx=5)
            self.top_buttons.append(btn)

        self.theme_button = tk.Button(self.top_frame, text="🎨", font=self.default_font, relief=tk.FLAT,
                                      command=self.toggle_theme)
        self.theme_button.pack(side=tk.RIGHT, padx=5)
        self.top_buttons.append(self.theme_button)

        self.input_frame = tk.Frame(self.right_frame)
        self.input_frame.pack(fill=tk.X, side=tk.TOP, padx=10, pady=(5,0))

        self.prompt_label = tk.Label(self.input_frame, text="$", font=self.default_font)
        self.prompt_label.pack(side=tk.LEFT)

        self.command_entry = tk.Entry(self.input_frame, font=self.default_font, relief=tk.FLAT,
                                      bd=0, highlightthickness=0)
        self.command_entry.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=5)
        self.command_entry.bind("<Return>", self.on_execute)
        self.command_entry.bind("<Up>", self.navigate_history)
        self.command_entry.bind("<Down>", self.navigate_history)
        self.command_entry.focus_set()

        terminal_frame = tk.Frame(self.right_frame)
        terminal_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5,5))

        self.scrollbar = tk.Scrollbar(terminal_frame)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.terminal_output = tk.Text(
            terminal_frame, font=self.default_font, relief=tk.FLAT, wrap=tk.WORD, 
            borderwidth=0, padx=10, pady=10, yscrollcommand=self.scrollbar.set
        )
        self.terminal_output.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.scrollbar.config(command=self.terminal_output.yview)
        self.terminal_output.config(state=tk.DISABLED)

    def _populate_file_explorer(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        
        path = os.getcwd()
        try:
            self.tree.insert('', 'end', text="..", values=[os.path.dirname(path), 'dir'])
            for item in sorted(os.scandir(path), key=lambda e: not e.is_dir()):
                icon = "📁" if item.is_dir() else "📄"
                node_type = "dir" if item.is_dir() else "file"
                self.tree.insert('', 'end', text=f" {icon} {item.name}", values=[item.path, node_type])
        except OSError as e:
            self.tree.insert('', 'end', text=f"Error: {e.strerror}")

    def _on_treeview_select(self, event):
        item_id = self.tree.focus()
        if not item_id: return
        
        item = self.tree.item(item_id)
        path, node_type = item['values']

        if node_type == 'dir':
            self.execute_from_button(f'cd "{path}"')

    def refresh_all_gui_components(self):
        self.prompt_label.config(text=f"{os.getcwd()} $")
        self._populate_file_explorer()
        self.update_status_bar()

    def update_status_bar(self):
        self.status_dir_label.config(text=f"Current Directory: {os.getcwd()}")
        
    def on_execute(self, event=None):
        if self.command_entry['state'] == tk.DISABLED: return "break"
        command_line = self.command_entry.get().strip()
        prompt_text = f"\n{self.prompt_label['text']} "
        self.write_to_output(f"{prompt_text}{command_line}\n", 'command')
        self.command_entry.delete(0, tk.END)
        self.command_entry.config(state=tk.DISABLED)
        self.logic_handler.start_command_execution(command_line)
        return "break"

    def execute_from_button(self, command_line):
        if self.command_entry['state'] == tk.DISABLED: return
        self.command_entry.delete(0, tk.END)
        self.command_entry.insert(0, command_line)
        self.on_execute()

    def navigate_history(self, event):
        new_text = self.logic_handler.get_history_entry(event.keysym)
        if new_text is not None:
            self.command_entry.delete(0, tk.END)
            self.command_entry.insert(0, new_text)
        return "break"

    def re_enable_input(self):
        self.command_entry.config(state=tk.NORMAL)
        self.command_entry.focus_set()

    def apply_theme(self):
        theme = self.themes[self.current_theme]
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background=theme["output_bg"], foreground=theme["output_fg"], fieldbackground=theme["output_bg"])
        style.configure("Treeview.Heading", background=theme["button_bg"], foreground=theme["button_fg"])
        style.map('Treeview', background=[('selected', theme["button_active_bg"])])

        self.root.config(bg=theme["bg"])
        self.paned_window.config(bg=theme["bg"])
        self.left_frame.config(bg=theme["output_bg"])
        self.right_frame.config(bg=theme["bg"])
        self.top_frame.config(bg=theme["bg"])
        self.input_frame.config(bg=theme["output_bg"])
        self.status_bar.config(bg=theme["button_bg"])
        self.status_dir_label.config(bg=theme["button_bg"], fg=theme["button_fg"])

        for btn in self.top_buttons:
            btn.config(bg=theme["button_bg"], fg=theme["button_fg"],
                       activebackground=theme["button_active_bg"],
                       activeforeground=theme["button_fg"])
        self.prompt_label.config(bg=theme["output_bg"], fg=theme["prompt_fg"])
        self.command_entry.config(bg=theme["output_bg"], fg=theme["fg"],
                                  insertbackground=theme["fg"],
                                  disabledbackground=theme["output_bg"],
                                  disabledforeground=theme["disabled_fg"])
        self.terminal_output.config(bg=theme["output_bg"], fg=theme["output_fg"],
                                    insertbackground=theme["fg"],
                                    selectbackground=theme["button_active_bg"])
        self.scrollbar.config(bg=theme["button_bg"], troughcolor=theme["bg"])
        self.define_tags()
        
    def toggle_theme(self):
        self.current_theme = "light" if self.current_theme == "dark" else "dark"
        self.apply_theme()

    def define_tags(self):
        theme = self.themes[self.current_theme]
        tags_to_define = {
            'prompt': theme["prompt_fg"], 'error': theme["error_fg"],
            'info': theme["info_fg"], 'background': theme["background_fg"],
            'command': theme["prompt_fg"], 'default': theme["output_fg"]
        }
        for tag_name, color in tags_to_define.items():
            self.terminal_output.tag_config(tag_name, foreground=color)
        self.terminal_output.tag_config('command', font=tkfont.Font(family="Consolas", size=10, weight="bold"))

    def write_to_output(self, text, tag='default'):
        if text:
            self.gui_queue.put((self._write_to_output_task, [text, tag], {}))

    def _write_to_output_task(self, text, tag):
        self.terminal_output.config(state=tk.NORMAL)
        self.terminal_output.insert(tk.END, text, tag)
        self.terminal_output.see(tk.END)
        self.terminal_output.config(state=tk.DISABLED)

    def process_gui_queue(self):
        try:
            while True:
                task, args, kwargs = self.gui_queue.get_nowait()
                task(*args, **kwargs)
        except queue.Empty:
            pass
        self.root.after(10, self.process_gui_queue) 
    
    def set_default_text_color(self, color):
       
        self.terminal_output.config(fg=color)
        self.terminal_output.tag_config('default', foreground=color)
        self.terminal_output.tag_config('command', foreground=color)
        self.prompt_label.config(fg=color)
