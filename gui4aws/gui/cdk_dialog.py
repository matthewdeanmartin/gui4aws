"""CdkDialog: interactive CDK launcher with subcommand sidebar, form, output, and help panels."""

from __future__ import annotations

import contextlib
import os
import queue
import shlex
import subprocess
import threading
import tkinter as tk
from functools import partial
from tkinter import filedialog, messagebox, ttk
from typing import Any, cast

__all__ = ["CdkDialog"]

# ---------------------------------------------------------------------------
# CDK subcommand definitions
# ---------------------------------------------------------------------------

# Each entry: (name, description, flags)
# flags: list of (flag, label, kind, default, help)
#   kind: "string" | "bool" | "choice"
_CDK_SUBCOMMANDS: list[dict[str, Any]] = [
    {
        "name": "list",
        "label": "list",
        "description": "List all stacks in the app.",
        "flags": [
            (
                "--long",
                "Long format (show full details)",
                "bool",
                False,
                "Display environment information for each stack",
            ),
            ("--context", "Context key=value", "string", "", "Add contextual string parameter (-c KEY=VALUE)"),
        ],
    },
    {
        "name": "synth",
        "label": "synth",
        "description": "Synthesize and print the CloudFormation template.",
        "flags": [
            (
                "--output",
                "Output directory",
                "string",
                "cdk.out",
                "Emits the synthesized cloud assembly into a directory (default: cdk.out)",
            ),
            ("--quiet", "Quiet (suppress output)", "bool", False, "Do not output CloudFormation template to stdout"),
            (
                "--exclusively",
                "Exclusively synth selected stacks",
                "bool",
                False,
                "Only synthesize requested stacks, don't include dependencies",
            ),
            ("--context", "Context key=value", "string", "", "Add contextual string parameter (-c KEY=VALUE)"),
            ("STACKS", "Stack names (space-separated)", "string", "", "Stacks to synthesize (leave empty for all)"),
        ],
    },
    {
        "name": "bootstrap",
        "label": "bootstrap",
        "description": "Deploy the CDK toolkit stack (required once per account/region).",
        "flags": [
            ("--profile", "AWS profile", "string", "", "Use the indicated AWS profile as the default environment"),
            (
                "--toolkit-stack-name",
                "Toolkit stack name",
                "string",
                "",
                "The name of the CDK toolkit stack (default: CDKToolkit)",
            ),
            (
                "--qualifier",
                "Qualifier",
                "string",
                "",
                "String which must be unique per bootstrap stack name & target environment",
            ),
            (
                "--trust",
                "Trust accounts (comma-sep)",
                "string",
                "",
                "Account IDs that should be trusted to perform deployments into this environment",
            ),
            (
                "--cloudformation-execution-policies",
                "CF execution policies",
                "string",
                "",
                "ARNs of managed policies to attach to the deployment role",
            ),
            (
                "ENVIRONMENTS",
                "Environments (e.g. aws://123456789012/us-east-1)",
                "string",
                "",
                "Environments to bootstrap",
            ),
        ],
    },
    {
        "name": "deploy",
        "label": "deploy",
        "description": "Deploy stacks to AWS.",
        "flags": [
            (
                "--require-approval",
                "Require approval",
                "choice",
                "broadening",
                "What security-sensitive changes need manual approval (never/any/broadening)",
            ),
            (
                "--exclusively",
                "Exclusively deploy selected stacks",
                "bool",
                False,
                "Only deploy requested stacks, don't include dependencies",
            ),
            (
                "--parameters",
                "Parameters (KEY=VALUE)",
                "string",
                "",
                "Additional parameters passed to CloudFormation at deploy time",
            ),
            ("--context", "Context key=value", "string", "", "Add contextual string parameter (-c KEY=VALUE)"),
            (
                "--outputs-file",
                "Outputs file",
                "string",
                "",
                "Path to file where stack outputs will be written as JSON",
            ),
            ("--profile", "AWS profile", "string", "", "Use the indicated AWS profile"),
            ("--no-rollback", "Disable rollback", "bool", False, "Disable automatic rollback on failure"),
            (
                "--hotswap",
                "Hotswap (Lambda/ECS only)",
                "bool",
                False,
                "Attempts to perform a 'hotswap' deployment for faster iteration on code changes",
            ),
            (
                "--watch",
                "Watch mode",
                "bool",
                False,
                "Continuously observe your code and assets, and deploy the smallest possible change",
            ),
            ("STACKS", "Stack names (space-separated)", "string", "", "Stacks to deploy (leave empty for all)"),
        ],
    },
    {
        "name": "destroy",
        "label": "destroy",
        "description": "Destroy stacks from AWS (deletes all resources).",
        "flags": [
            (
                "--force",
                "Force (no confirmation)",
                "bool",
                False,
                "Do not ask for confirmation before destroying the stacks",
            ),
            (
                "--exclusively",
                "Exclusively destroy selected stacks",
                "bool",
                False,
                "Only destroy requested stacks, don't include dependents",
            ),
            ("--profile", "AWS profile", "string", "", "Use the indicated AWS profile"),
            ("STACKS", "Stack names (space-separated)", "string", "", "Stacks to destroy (leave empty for all)"),
        ],
    },
    {
        "name": "diff",
        "label": "diff",
        "description": "Compare deployed stack with current state.",
        "flags": [
            (
                "--exclusively",
                "Only specified stacks",
                "bool",
                False,
                "Only diff requested stacks, don't include dependencies",
            ),
            (
                "--context-lines",
                "Context lines",
                "string",
                "3",
                "Number of context lines to include in arbitrary JSON diff",
            ),
            ("--security-only", "Security changes only", "bool", False, "Only diff for broadened security changes"),
            ("--profile", "AWS profile", "string", "", "Use the indicated AWS profile"),
            ("STACKS", "Stack names (space-separated)", "string", "", "Stacks to diff (leave empty for all)"),
        ],
    },
    {
        "name": "import",
        "label": "import",
        "description": "Import existing resources into a CDK stack.",
        "flags": [
            (
                "--record-resource-mapping",
                "Record resource mapping",
                "string",
                "",
                "If specified, CDK will generate a mapping of existing physical resources to CDK resources",
            ),
            (
                "--resource-mapping",
                "Resource mapping file",
                "string",
                "",
                "If specified, CDK will use the mapping file to import resources into the CDK stack",
            ),
            ("--force", "Force import", "bool", False, "Do not ask for confirmation before importing"),
            ("STACK", "Stack name", "string", "", "Stack to import resources into"),
        ],
    },
    {
        "name": "watch",
        "label": "watch",
        "description": "Continuously watch for changes and deploy (shortcut for deploy --watch).",
        "flags": [
            ("--hotswap", "Hotswap (Lambda/ECS only)", "bool", False, "Attempts to perform a 'hotswap' deployment"),
            ("--context", "Context key=value", "string", "", "Add contextual string parameter (-c KEY=VALUE)"),
            ("STACKS", "Stack names (space-separated)", "string", "", "Stacks to watch (leave empty for all)"),
        ],
    },
    {
        "name": "doctor",
        "label": "doctor",
        "description": "Check your setup for potential problems.",
        "flags": [],
    },
    {
        "name": "acknowledge",
        "label": "acknowledge",
        "description": "Acknowledge a notice, silencing it in the future.",
        "flags": [
            ("ID", "Notice ID", "string", "", "Notice ID to acknowledge"),
        ],
    },
    {
        "name": "notices",
        "label": "notices",
        "description": "Show the list of relevant notices.",
        "flags": [
            ("--unacknowledged", "Unacknowledged only", "bool", False, "Show only unacknowledged notices"),
        ],
    },
    {
        "name": "metadata",
        "label": "metadata",
        "description": "Returns all metadata associated with this stack.",
        "flags": [
            ("STACK", "Stack name", "string", "", "Stack to show metadata for"),
        ],
    },
    {
        "name": "context",
        "label": "context",
        "description": "Manage cached context values.",
        "flags": [
            ("--reset", "Reset context key", "string", "", "The context key (or its index) to reset"),
            ("--clear", "Clear all context", "bool", False, "Clear all context"),
        ],
    },
    {
        "name": "docs",
        "label": "docs",
        "description": "Opens the reference documentation in your browser.",
        "flags": [
            (
                "--browser",
                "Browser command",
                "string",
                "",
                "the command to use to open the browser, using %u as a placeholder for the path of the file to open",
            ),
        ],
    },
    {
        "name": "init",
        "label": "init",
        "description": "Create a new CDK project from a template.",
        "flags": [
            (
                "--language",
                "Language",
                "choice",
                "typescript",
                "The language to be used for the new project (javascript/typescript/python/java/csharp/go)",
            ),
            ("--list", "List templates", "bool", False, "List the available templates"),
            ("--generate-only", "Generate only (no install)", "bool", False, "Do not call hooks, just generate"),
            ("TEMPLATE", "Template name", "string", "", "The template to instantiate (default: app)"),
        ],
    },
]

# --require-approval choices
_APPROVAL_CHOICES = ["never", "any", "broadening"]
_LANGUAGE_CHOICES = ["typescript", "javascript", "python", "java", "csharp", "go"]


def size_and_center(win: tk.Toplevel) -> None:
    """Size the dialog to 90% of the screen and center it."""
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    w = int(sw * 0.90)
    h = int(sh * 0.90)
    x = max(0, (sw - w) // 2)
    y = max(0, (sh - h) // 2)
    win.geometry(f"{w}x{h}+{x}+{y}")


class CdkDialog(tk.Toplevel):
    """CDK launcher window.

    Layout (3-column):
      Left  — vertical stack of subcommand buttons
      Center — top: cwd + form; bottom: output text
      Right  — --help output for the active subcommand
    """

    def __init__(self, parent: tk.Misc, *, stack_name: str = "") -> None:
        """Initialize the CDK launcher dialog."""
        super().__init__(parent)
        self.title("CDK Launcher")
        self.resizable(True, True)
        self.transient(parent.winfo_toplevel())
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.bind("<Escape>", lambda _e: self.on_close())

        self.stack_name = stack_name
        self.current_subcommand: dict[str, Any] = _CDK_SUBCOMMANDS[0]
        self.field_vars: dict[str, tk.Variable] = {}
        self.proc: subprocess.Popen[str] | None = None
        self.output_queue: queue.Queue[str | None] = queue.Queue()
        self.help_cache: dict[str, str] = {}

        size_and_center(self)
        self.build_ui()
        self.select_subcommand(_CDK_SUBCOMMANDS[3])  # default: deploy

    # ── UI construction ──────────────────────────────────────────────────────

    def build_ui(self) -> None:
        """Construct the three-pane layout."""
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=3)
        self.grid_columnconfigure(2, weight=2)
        self.grid_rowconfigure(0, weight=1)

        # Left sidebar
        self.left = ttk.Frame(self, width=140)
        self.left.grid(row=0, column=0, sticky="nsew", padx=(4, 0), pady=4)
        self.left.grid_propagate(False)
        self.build_sidebar()

        ttk.Separator(self, orient="vertical").grid(row=0, column=0, sticky="nse", padx=(140, 0))

        # Center pane
        center = ttk.Frame(self)
        center.grid(row=0, column=1, sticky="nsew", padx=4, pady=4)
        center.grid_columnconfigure(0, weight=1)
        center.grid_rowconfigure(1, weight=1)
        self.build_center(center)

        ttk.Separator(self, orient="vertical").grid(row=0, column=1, sticky="nse")

        # Right pane: --help
        right = ttk.Frame(self)
        right.grid(row=0, column=2, sticky="nsew", padx=(4, 4), pady=4)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)
        ttk.Label(right, text="CDK --help", font=("", 10, "bold")).grid(
            row=0, column=0, sticky="w", padx=4, pady=(0, 2)
        )
        self.help_text = tk.Text(
            right, wrap="word", state="disabled", font=("Courier", 9), background="#1e1e1e", foreground="#d4d4d4"
        )
        help_scroll = ttk.Scrollbar(right, orient="vertical", command=self.help_text.yview)
        self.help_text.configure(yscrollcommand=help_scroll.set)
        self.help_text.grid(row=1, column=0, sticky="nsew")
        help_scroll.grid(row=1, column=1, sticky="ns")

    def build_sidebar(self) -> None:
        """Populate the left sidebar with subcommand buttons."""
        ttk.Label(self.left, text="Subcommands", font=("", 9, "bold")).pack(fill="x", padx=4, pady=(4, 2))
        self.sidebar_buttons: dict[str, ttk.Button] = {}
        for sub in _CDK_SUBCOMMANDS:
            btn = ttk.Button(
                self.left,
                text=sub["label"],
                width=14,
                command=partial(self.select_subcommand, sub),
            )
            btn.pack(fill="x", padx=4, pady=1)
            self.sidebar_buttons[sub["name"]] = btn

    def build_center(self, parent: ttk.Frame) -> None:
        """Construct the center pane with working directory, form, and output."""
        # Top: cwd + subcommand title + form
        top = ttk.Frame(parent)
        top.grid(row=0, column=0, sticky="nsew")
        top.grid_columnconfigure(0, weight=1)

        # CWD row
        cwd_frame = ttk.LabelFrame(top, text="Working directory (CDK project root)")
        cwd_frame.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        cwd_frame.grid_columnconfigure(0, weight=1)
        self.cwd_var = tk.StringVar(value=os.getcwd())
        ttk.Entry(cwd_frame, textvariable=self.cwd_var).grid(row=0, column=0, sticky="ew", padx=4, pady=4)
        ttk.Button(cwd_frame, text="Browse…", command=self.browse_cwd).grid(row=0, column=1, padx=4, pady=4)

        # Subcommand title + description
        self.cmd_title = ttk.Label(top, text="", font=("", 12, "bold"))
        self.cmd_title.grid(row=1, column=0, sticky="w", padx=4)
        self.cmd_desc = ttk.Label(top, text="", wraplength=600, foreground="gray")
        self.cmd_desc.grid(row=2, column=0, sticky="w", padx=4, pady=(0, 4))

        # Form area (scrollable)
        form_outer = ttk.LabelFrame(top, text="Options")
        form_outer.grid(row=3, column=0, sticky="nsew", pady=(0, 4))
        form_outer.grid_columnconfigure(0, weight=1)
        form_outer.grid_rowconfigure(0, weight=1)
        top.grid_rowconfigure(3, weight=1)

        self.form_canvas = tk.Canvas(form_outer, highlightthickness=0, borderwidth=0)
        self.form_canvas.grid(row=0, column=0, sticky="nsew")
        form_scroll = ttk.Scrollbar(form_outer, orient="vertical", command=self.form_canvas.yview)
        form_scroll.grid(row=0, column=1, sticky="ns")
        self.form_canvas.configure(yscrollcommand=form_scroll.set)

        self.form_inner = ttk.Frame(self.form_canvas)
        self.form_inner.grid_columnconfigure(1, weight=1)
        _win_id = self.form_canvas.create_window((0, 0), window=self.form_inner, anchor="nw")

        def sync(_e: Any) -> None:
            self.form_canvas.configure(scrollregion=self.form_canvas.bbox("all"))

        def stretch(_e: Any) -> None:
            self.form_canvas.itemconfigure(_win_id, width=_e.width)

        self.form_inner.bind("<Configure>", sync)
        self.form_canvas.bind("<Configure>", stretch)

        # Buttons
        btn_frame = ttk.Frame(top)
        btn_frame.grid(row=4, column=0, sticky="ew", pady=(0, 4))
        self.dry_run_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(btn_frame, text="Dry run (--dry-run / synth only)", variable=self.dry_run_var).pack(
            side="left", padx=4
        )
        self.run_btn = ttk.Button(btn_frame, text="Run", command=self.on_run)
        self.run_btn.pack(side="right", padx=4)
        self.stop_btn = ttk.Button(btn_frame, text="Stop", command=self.on_stop, state="disabled")
        self.stop_btn.pack(side="right", padx=4)
        ttk.Button(btn_frame, text="Clear output", command=self.clear_output).pack(side="right", padx=4)
        ttk.Button(btn_frame, text="Copy command", command=self.copy_command).pack(side="right", padx=4)

        # Preview label
        self.cmd_preview = ttk.Label(top, text="", foreground="#005599", font=("Courier", 9), anchor="w")
        self.cmd_preview.grid(row=5, column=0, sticky="ew", padx=4, pady=(0, 2))

        # Bottom: output
        output_frame = ttk.LabelFrame(parent, text="Output")
        output_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 4))
        output_frame.grid_columnconfigure(0, weight=1)
        output_frame.grid_rowconfigure(0, weight=1)
        self.output_text = tk.Text(
            output_frame, wrap="none", state="disabled", font=("Courier", 9), background="#1e1e1e", foreground="#d4d4d4"
        )
        out_scroll_y = ttk.Scrollbar(output_frame, orient="vertical", command=self.output_text.yview)
        out_scroll_x = ttk.Scrollbar(output_frame, orient="horizontal", command=self.output_text.xview)
        self.output_text.configure(yscrollcommand=out_scroll_y.set, xscrollcommand=out_scroll_x.set)
        self.output_text.grid(row=0, column=0, sticky="nsew")
        out_scroll_y.grid(row=0, column=1, sticky="ns")
        out_scroll_x.grid(row=1, column=0, sticky="ew")

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(parent, textvariable=self.status_var, anchor="w", foreground="gray").grid(
            row=2, column=0, sticky="ew", padx=4
        )

    # ── Subcommand selection ─────────────────────────────────────────────────

    def select_subcommand(self, sub: dict[str, Any]) -> None:
        """Switch to the given CDK subcommand and update the form and help."""
        self.current_subcommand = sub
        # Highlight selected button
        for name, btn in self.sidebar_buttons.items():
            btn.state(["pressed"] if name == sub["name"] else ["!pressed"])
        self.cmd_title.configure(text=f"cdk {sub['label']}")
        self.cmd_desc.configure(text=sub["description"])
        self.rebuild_form(sub)
        self.update_preview()
        self.load_help(sub["name"])

    def rebuild_form(self, sub: dict[str, Any]) -> None:
        """Recreate the options form for the current subcommand."""
        for child in self.form_inner.winfo_children():
            child.destroy()
        self.field_vars.clear()

        flags = sub.get("flags", [])
        if not flags:
            ttk.Label(self.form_inner, text="No options for this subcommand.", foreground="gray").grid(
                row=0, column=0, columnspan=3, padx=8, pady=8, sticky="w"
            )
            return

        for row_idx, flag_def in enumerate(flags):
            flag_name, label, kind, default, help_text = flag_def

            lbl = ttk.Label(self.form_inner, text=label, anchor="e", width=30)
            lbl.grid(row=row_idx, column=0, sticky="e", padx=(8, 4), pady=3)

            if kind == "bool":
                var: tk.Variable = tk.BooleanVar(value=default)
                widget: tk.Widget = ttk.Checkbutton(self.form_inner, variable=var, command=self.update_preview)
                widget.grid(row=row_idx, column=1, sticky="w", padx=4, pady=3)
            elif kind == "choice":
                var = tk.StringVar(value=str(default))
                choices = _APPROVAL_CHOICES if flag_name == "--require-approval" else _LANGUAGE_CHOICES
                widget = ttk.Combobox(self.form_inner, textvariable=var, values=choices, state="readonly", width=20)
                widget.bind("<<ComboboxSelected>>", lambda _e: self.update_preview())
                widget.grid(row=row_idx, column=1, sticky="w", padx=4, pady=3)
            else:
                var = tk.StringVar(value=str(default))
                # Pre-fill STACKS / STACK with the selected stack name if available
                if flag_name in ("STACKS", "STACK") and self.stack_name:
                    var.set(self.stack_name)
                widget = ttk.Entry(self.form_inner, textvariable=var, width=40)
                widget.bind("<KeyRelease>", lambda _e: self.update_preview())
                widget.grid(row=row_idx, column=1, sticky="ew", padx=4, pady=3)

            if help_text:
                ttk.Label(self.form_inner, text=help_text, foreground="gray", wraplength=300).grid(
                    row=row_idx, column=2, sticky="w", padx=(0, 8), pady=3
                )

            self.field_vars[flag_name] = var

    # ── Command construction ─────────────────────────────────────────────────

    def build_command(self, *, dry_run: bool = False) -> list[str]:
        """Construct the full npx cdk command list from form values."""
        sub = self.current_subcommand
        cmd = ["npx", "cdk", sub["name"]]

        positional_args: list[str] = []

        for flag_name, var in self.field_vars.items():
            # Positional-style args (ALL_CAPS)
            if flag_name.isupper():
                val = str(cast(Any, var).get()).strip()
                if val:
                    positional_args.extend(shlex.split(val))
                continue

            val = cast(Any, var).get()
            if isinstance(val, bool):
                if val:
                    cmd.append(flag_name)
            else:
                val_str = str(val).strip()
                if val_str:
                    cmd.extend([flag_name, val_str])

        if dry_run and sub["name"] == "deploy":
            # CDK doesn't have --dry-run; redirect to synth for a dry preview
            cmd = ["npx", "cdk", "synth", *positional_args]
        else:
            cmd.extend(positional_args)

        return cmd

    def update_preview(self, _event: Any = None) -> None:
        """Update the command preview label based on current form state."""
        with contextlib.suppress(Exception):
            cmd = self.build_command(dry_run=self.dry_run_var.get())
            self.cmd_preview.configure(text="$ " + " ".join(shlex.quote(a) for a in cmd))

    def copy_command(self) -> None:
        """Copy the current command to the system clipboard."""
        try:
            cmd = self.build_command(dry_run=self.dry_run_var.get())
            line = " ".join(shlex.quote(a) for a in cmd)
            self.clipboard_clear()
            self.clipboard_append(line)
            self.status_var.set("Command copied to clipboard")
        except Exception as exc:
            self.status_var.set(f"Error building command: {exc}")

    # ── Execution ────────────────────────────────────────────────────────────

    def on_run(self) -> None:
        """Start the CDK process in the background."""
        if self.proc is not None:
            messagebox.showwarning(
                "CDK already running", "A CDK process is already running. Stop it first.", parent=self
            )
            return
        cwd = self.cwd_var.get().strip() or os.getcwd()
        if not os.path.isdir(cwd):
            messagebox.showerror("Invalid directory", f"Directory not found: {cwd}", parent=self)
            return
        dry_run = self.dry_run_var.get()
        cmd = self.build_command(dry_run=dry_run)
        self.append_output(f"$ {' '.join(shlex.quote(a) for a in cmd)}\n", tag="cmd")
        self.status_var.set(f"Running: {cmd[2]}…")
        self.run_btn.state(["disabled"])
        self.stop_btn.state(["!disabled"])

        def reader(proc: subprocess.Popen[str]) -> None:
            assert proc.stdout is not None
            for line in proc.stdout:
                self.output_queue.put(line)
            proc.wait()
            self.output_queue.put(None)  # sentinel

        try:
            self.proc = subprocess.Popen(
                cmd,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except FileNotFoundError:
            self.append_output("Error: 'npx' not found. Make sure Node.js is installed and in PATH.\n", tag="err")
            self.status_var.set("Error: npx not found")
            self.run_btn.state(["!disabled"])
            self.stop_btn.state(["disabled"])
            return

        threading.Thread(target=reader, args=(self.proc,), daemon=True).start()
        self.after(50, self.poll_output)

    def on_stop(self) -> None:
        """Terminate the running CDK process."""
        if self.proc is not None:
            with contextlib.suppress(Exception):
                self.proc.terminate()
            self.status_var.set("Process terminated")

    def poll_output(self) -> None:
        """Check the output queue and update the output text widget."""
        try:
            while True:
                item = self.output_queue.get_nowait()
                if item is None:
                    # Process finished
                    rc = self.proc.returncode if self.proc else -1
                    self.proc = None
                    self.run_btn.state(["!disabled"])
                    self.stop_btn.state(["disabled"])
                    if rc == 0:
                        self.status_var.set("Completed successfully")
                        self.append_output("\n[Done — exit code 0]\n", tag="ok")
                    else:
                        self.status_var.set(f"Failed (exit code {rc})")
                        self.append_output(f"\n[Failed — exit code {rc}]\n", tag="err")
                    return
                self.append_output(item)
        except queue.Empty:
            pass
        self.after(50, self.poll_output)

    def append_output(self, text: str, tag: str = "") -> None:
        """Add text to the output widget and auto-scroll."""
        self.output_text.configure(state="normal")
        if tag:
            self.output_text.insert("end", text, tag)
        else:
            self.output_text.insert("end", text)
        self.output_text.see("end")
        self.output_text.configure(state="disabled")
        # Configure tags lazily
        self.output_text.tag_configure("cmd", foreground="#569cd6")
        self.output_text.tag_configure("ok", foreground="#4ec9b0")
        self.output_text.tag_configure("err", foreground="#f44747")

    def clear_output(self) -> None:
        """Clear all text from the output widget."""
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.configure(state="disabled")

    # ── Help pane ────────────────────────────────────────────────────────────

    def load_help(self, subcommand: str) -> None:
        """Fetch and display --help for the given subcommand in a background thread."""
        if subcommand in self.help_cache:
            self.set_help(self.help_cache[subcommand])
            return
        self.set_help(f"Loading help for 'cdk {subcommand}'…")

        def fetch() -> None:
            try:
                result = subprocess.run(
                    ["npx", "cdk", subcommand, "--help"],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                text = result.stdout or result.stderr or "(no help output)"
            except FileNotFoundError:
                text = "npx not found — install Node.js to use the CDK launcher."
            except subprocess.TimeoutExpired:
                text = "Timed out fetching help."
            except Exception as exc:
                text = f"Error: {exc}"
            self.help_cache[subcommand] = text
            self.after(0, lambda: self.set_help(text) if self.current_subcommand["name"] == subcommand else None)

        threading.Thread(target=fetch, daemon=True).start()

    def set_help(self, text: str) -> None:
        """Update the help text widget with the given content."""
        self.help_text.configure(state="normal")
        self.help_text.delete("1.0", "end")
        self.help_text.insert("1.0", text)
        self.help_text.configure(state="disabled")

    # ── Misc ─────────────────────────────────────────────────────────────────

    def browse_cwd(self) -> None:
        """Open a directory browser to select the CDK project root."""
        chosen = filedialog.askdirectory(
            title="Select CDK project directory",
            initialdir=self.cwd_var.get() or os.getcwd(),
            parent=self,
        )
        if chosen:
            self.cwd_var.set(chosen)

    def on_close(self) -> None:
        """Handle dialog closure, prompting to terminate any running process."""
        if self.proc is not None:
            if messagebox.askyesno("Process running", "A CDK process is still running. Terminate it?", parent=self):
                self.on_stop()
            else:
                return
        self.destroy()
