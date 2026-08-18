import tkinter as tk
import threading
import ctypes
import sys
import os
import re

from PIL import Image, ImageTk
from tkinter import ttk, messagebox

from winget_service import get_available_updates, update_all, check_winget_connectivity

# ---------------------------------------------------------
# Application information
# ---------------------------------------------------------
APP_NAME = "Simple PC Updater"
APP_VERSION = "1.0.0"
COMPANY_NAME = "RevTek Studios LLC"
COPYRIGHT = "Copyright © 2026 RevTek Studios LLC"


# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------
def parse_winget_updates(output):
    """
    Convert WinGet's fixed-width text table into a list of dictionaries.

    Expected columns generally resemble:

    Name    Id    Version    Available    Source
    """

    lines = output.splitlines()

    header_index = None

    for index, line in enumerate(lines):
        if (
            "Name" in line
            and "Id" in line
            and "Version" in line
            and "Available" in line
        ):
            header_index = index
            break

    if header_index is None:
        return []

    header = lines[header_index]

    try:
        name_start = header.index("Name")
        id_start = header.index("Id")
        version_start = header.index("Version")
        available_start = header.index("Available")

        source_start = None

        if "Source" in header:
            source_start = header.index("Source")

    except ValueError:
        return []

    packages = []

    for line in lines[header_index + 1:]:
        stripped = line.strip()

        if not stripped:
            continue

        if set(stripped) == {"-"}:
            continue

        if stripped.lower().startswith("no installed package"):
            continue

        if stripped.lower().startswith("the following packages"):
            continue

        if stripped.lower().startswith("upgrades available"):
            continue

        try:
            name = line[name_start:id_start].strip()
            package_id = line[id_start:version_start].strip()

            if source_start is not None:
                installed = line[
                    version_start:available_start
                ].strip()

                available = line[
                    available_start:source_start
                ].strip()

                source = line[source_start:].strip()

            else:
                installed = line[
                    version_start:available_start
                ].strip()

                available = line[
                    available_start:
                ].strip()

                source = ""

        except Exception:
            continue

        if not name or not package_id:
            continue

        packages.append({
            "name": name,
            "id": package_id,
            "installed": installed,
            "available": available,
            "source": source
        })

    return packages

def resource_path(relative_path):
    """
    Get the correct path to an application resource.

    Works during normal Python development and when the
    application is later packaged as an executable.
    """
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False

def run_as_admin():
    if is_admin():
        return True

    script = os.path.abspath(sys.argv[0])
    python_exe = sys.executable

    if python_exe.lower().endswith("python.exe"):
        python_exe = python_exe[:-10] + "pythonw.exe"

    params = f'"{script}"'

    result = ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        python_exe,
        params,
        None,
        1
    )

    # Windows returns 5 when the user declines the UAC prompt.
    if result == 5:
        return False

    # Any other ShellExecute error is an actual launch failure.
    if result <= 32:
        messagebox.showerror(
            "Administrator Required",
            f"{APP_NAME} could not obtain administrator privileges.\n\n"
            f"Windows error code: {result}"
        )

    return False

def load_custom_font(font_path):
    """
    Load a font for the current application session without
    permanently installing it in Windows.
    """
    try:
        FR_PRIVATE = 0x10

        result = ctypes.windll.gdi32.AddFontResourceExW(
            font_path,
            FR_PRIVATE,
            0
        )

        return result > 0

    except Exception:
        return False


# ---------------------------------------------------------
# Application
# ---------------------------------------------------------
class UpdaterApp:
    def __init__(self, root):
        self.root = root

        try:
            self.root.iconbitmap(resource_path("assets/app.ico"))
        except Exception:
            pass

        if is_admin():
            self.root.title(f"{APP_NAME} - Administrator")
        else:
            self.root.title(f"{APP_NAME}")

        self.root.geometry("1000x650")
        self.root.minsize(850, 550)

        self.updates = []

        self.build_styles()
        self.build_ui()

        self.check_connection()

    # Connection Check to Server
    def check_connection(self):
        self.connection_label.config(
            text="● Checking connection..."
        )

        thread = threading.Thread(
            target=self.connection_worker,
            daemon=True
        )

        thread.start()

    def connection_worker(self):
        try:
            connected, details = check_winget_connectivity()

            self.root.after(
                0,
                lambda: self.handle_connection_result(
                    connected,
                    details
                )
            )

        except Exception as error:
            self.root.after(
                0,
                lambda: self.handle_connection_result(
                    False,
                    str(error)
                )
            )

    def handle_connection_result(self, connected, details):
        if connected:
            self.connection_label.config(
                text="● Connected",
                style="ConnectionGood.TLabel"
            )
        else:
            self.connection_label.config(
                text="● Offline",
                style="ConnectionBad.TLabel"
            )


    # -----------------------------------------------------
    # Styles / UI
    # -----------------------------------------------------
    def build_styles(self):
        style = ttk.Style()

        style.configure(
            "Title.TLabel",
            font=("Armed", 24, "bold")
        )

        style.configure(
            "Section.TLabel",
            font=("Segoe UI", 11, "bold")
        )

        style.configure(
            "Action.TButton",
            font=("Segoe UI", 10),
            padding=(14, 8)
        )

        style.configure(
            "Treeview",
            font=("Segoe UI", 10),
            rowheight=28
        )

        style.configure(
            "Treeview.Heading",
            font=("Segoe UI", 10, "bold")
        )

        style.configure(
            "ConnectionGood.TLabel",
            font=("Segoe UI", 9, "bold"),
            foreground="#198754"
        )

        style.configure(
            "ConnectionCheck.TLabel",
            font=("Segoe UI", 9),
            foreground="#6c757d"
        )

        style.configure(
            "ConnectionBad.TLabel",
            font=("Segoe UI", 9, "bold"),
            foreground="#dc3545"
        )

    def build_ui(self):
        main_frame = ttk.Frame(
            self.root,
            padding=20
        )

        main_frame.pack(
            fill="both",
            expand=True
        )

        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(
            fill="x",
            pady=(0, 18)
        )

        # Branding area
        brand_frame = ttk.Frame(header_frame)
        brand_frame.pack(side="left")

        # App logo
        try:
            logo_path = resource_path(
                "assets/SPCU.png"
            )

            logo_image = Image.open(logo_path)

            logo_image.thumbnail(
                (65, 65),
                Image.Resampling.LANCZOS
            )

            self.main_logo_image = ImageTk.PhotoImage(
                logo_image
            )

            logo_label = ttk.Label(
                brand_frame,
                image=self.main_logo_image
            )

            logo_label.pack(
                side="left",
                padx=(0, 12)
            )

        except Exception as error:
            messagebox.showerror(
                "Logo Error",
                f"Could not load app logo:\n\n{error}"
            )

        # Title area
        title_group = ttk.Frame(
            brand_frame
        )

        title_group.pack(
            side="left"
        )

        title = ttk.Label(
            title_group,
            text=APP_NAME,
            style="Title.TLabel"
        )

        title.pack(anchor="w")

        brand_label = ttk.Label(
            title_group,
            text=f"by {COMPANY_NAME}  •  v{APP_VERSION}",
            font=("Segoe UI", 8)
        )

        brand_label.pack(anchor="w")

        # Window title
        self.root.title(
            f"{APP_NAME} v{APP_VERSION}"
        )

        # Search button
        self.search_button = ttk.Button(
            header_frame,
            text="Search for Updates",
            command=self.search_updates,
            style="Action.TButton"
        )

        self.search_button.pack(
            side="right"
        )

        # Connection status
        self.connection_label = ttk.Label(
            header_frame,
            text="● Checking...",
            style="ConnectionCheck.TLabel"
        )

        self.connection_label.pack(
            side="right",
            padx=(0, 15)
        )

        # Summary
        summary_frame = ttk.Frame(main_frame)
        summary_frame.pack(
            fill="x",
            pady=(0, 8)
        )

        self.summary_label = ttk.Label(
            summary_frame,
            text="No scan performed yet.",
            style="Section.TLabel"
        )

        self.summary_label.pack(side="left")

        # Update table
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(
            fill="both",
            expand=True
        )

        columns = (
            "name",
            "installed",
            "available",
            "source"
        )

        self.update_tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            selectmode="browse"
        )

        self.update_tree.heading(
            "name",
            text="Application"
        )

        self.update_tree.heading(
            "installed",
            text="Installed"
        )

        self.update_tree.heading(
            "available",
            text="Available"
        )

        self.update_tree.heading(
            "source",
            text="Source"
        )

        self.update_tree.column(
            "name",
            width=430,
            minwidth=250,
            anchor="w"
        )

        self.update_tree.column(
            "installed",
            width=150,
            minwidth=100,
            anchor="center"
        )

        self.update_tree.column(
            "available",
            width=150,
            minwidth=100,
            anchor="center"
        )

        self.update_tree.column(
            "source",
            width=100,
            minwidth=80,
            anchor="center"
        )

        scrollbar = ttk.Scrollbar(
            tree_frame,
            orient="vertical",
            command=self.update_tree.yview
        )

        self.update_tree.configure(
            yscrollcommand=scrollbar.set
        )

        self.update_tree.pack(
            side="left",
            fill="both",
            expand=True
        )

        scrollbar.pack(
            side="right",
            fill="y"
        )

        # Progress
        self.progress_bar = ttk.Progressbar(
            main_frame,
            mode="indeterminate"
        )

        self.progress_bar.pack(
            fill="x",
            pady=(15, 8)
        )

        self.progress_bar.pack_forget()

        # Footer
        footer_frame = ttk.Frame(main_frame)
        footer_frame.pack(
            fill="x",
            pady=(8, 0)
        )

        self.status_label = ttk.Label(
            footer_frame,
            text="Status: Ready"
        )

        self.status_label.pack(
            side="left"
        )

        self.about_button = ttk.Button(
            footer_frame,
            text="About",
            command=self.show_about
        )

        self.about_button.pack(
            side="right",
            padx=(0, 10)
        )

        self.update_button = ttk.Button(
            footer_frame,
            text="Update All",
            command=self.run_update_all,
            state="disabled",
            style="Action.TButton"
        )

        self.update_button.pack(
            side="right"
        )

    def show_about(self):
        about = tk.Toplevel(self.root)

        about.title(f"About {APP_NAME}")
        about.geometry("520x560")
        about.resizable(False, False)

        # Keep the About window associated with the main window
        about.transient(self.root)
        about.grab_set()

        container = ttk.Frame(
            about,
            padding=25
        )
        container.pack(
            fill="both",
            expand=True
        )

        # RevTek logo
        try:
            logo_path = resource_path(
                "assets/revtek_logo.png"
            )

            image = Image.open(logo_path)

            image.thumbnail(
                (220, 140),
                Image.Resampling.LANCZOS
            )

            self.about_logo_image = ImageTk.PhotoImage(image)

            logo_label = ttk.Label(
                container,
                image=self.about_logo_image
            )

            logo_label.pack(
                pady=(0, 15)
            )

        except Exception:
            pass

        # Application name
        app_label = ttk.Label(
            container,
            text=APP_NAME,
            font=("Segoe UI", 20, "bold")
        )

        app_label.pack()

        # Version
        version_label = ttk.Label(
            container,
            text=f"Version {APP_VERSION}",
            font=("Segoe UI", 10)
        )

        version_label.pack(
            pady=(3, 15)
        )

        # Developer
        developer_label = ttk.Label(
            container,
            text=f"Developed by {COMPANY_NAME}",
            font=("Segoe UI", 10, "bold")
        )

        developer_label.pack(
            pady=(0, 5)
        )

        copyright_label = ttk.Label(
            container,
            text=COPYRIGHT,
            font=("Segoe UI", 9)
        )

        copyright_label.pack(
            pady=(0, 20)
        )

        separator = ttk.Separator(
            container,
            orient="horizontal"
        )

        separator.pack(
            fill="x",
            pady=(0, 15)
        )

        description = ttk.Label(
            container,
            text=(
                f"{APP_NAME} is a lightweight Windows application "
                "designed to simplify software updates using the "
                "Windows Package Manager (WinGet)."
            ),
            wraplength=450,
            justify="center"
        )

        description.pack(
            pady=(0, 20)
        )

        license_title = ttk.Label(
            container,
            text="Licensing",
            font=("Segoe UI", 10, "bold")
        )

        license_title.pack(
            pady=(0, 5)
        )

        license_text = ttk.Label(
            container,
            text=(
                f"{APP_NAME} is proprietary software developed by "
                "RevTek Studios LLC. All rights reserved.\n\n"
                "Windows Package Manager (WinGet) is a Microsoft "
                "technology and is not developed or owned by "
                "RevTek Studios LLC.\n\n"
                "RevTek Studios LLC is not affiliated with or "
                "endorsed by Microsoft Corporation."
            ),
            wraplength=450,
            justify="center"
        )

        license_text.pack(
            pady=(0, 20)
        )

        close_button = ttk.Button(
            container,
            text="Close",
            command=about.destroy
        )

        close_button.pack()

    # -----------------------------------------------------
    # UI helpers
    # -----------------------------------------------------
    def clear_update_tree(self):
        for item in self.update_tree.get_children():
            self.update_tree.delete(item)

    def show_progress(self):
        self.progress_bar.pack(
            fill="x",
            pady=(15, 8),
            before=self.status_label.master
        )

        self.progress_bar.start(10)

    def hide_progress(self):
        self.progress_bar.stop()
        self.progress_bar.pack_forget()

    # -----------------------------------------------------
    # Search
    # -----------------------------------------------------
    def search_updates(self):
        self.connection_label.config(text="● Checking connection...")
        self.status_label.config(text="Status: Searching for updates...")
        self.summary_label.config(text="Searching...")
        self.search_button.config(state="disabled")
        self.update_button.config(state="disabled")
        self.clear_update_tree()
        self.show_progress()

        thread = threading.Thread(
            target=self.search_updates_worker, daemon=True)
        thread.start()

    def search_updates_worker(self):
        try:
            connected, details = check_winget_connectivity()

            if not connected:
                self.root.after(
                    0,
                    lambda: self.handle_offline(details)
                )
                return

            output = get_available_updates()

            self.root.after(
                0,
                lambda: self.handle_search_results(output)
            )

        except Exception as error:
            self.root.after(
                0,
                lambda: self.handle_search_error(
                    str(error)
                )
            )

    def handle_offline(self, details):
        self.hide_progress()

        self.connection_label.config(
            text="● Offline",
            style="ConnectionBad.TLabel"
        )

        self.summary_label.config(
            text="Unable to reach update sources."
        )

        self.status_label.config(
            text="Status: No connection"
        )

        self.search_button.config(
            state="normal"
        )

        self.update_button.config(
            state="disabled"
        )

        messagebox.showwarning(
            "No Connection",
            "Simple PC Updater could not reach the "
            "WinGet update sources.\n\n"
            "Check your internet connection and try again."
        )

    def handle_search_results(self, output):
        self.hide_progress()

        self.updates = parse_winget_updates(output)

        self.connection_label.config(
            text="● Connected",
            style="ConnectionGood.TLabel"
        )
        self.clear_update_tree()
        if not self.updates:
            self.summary_label.config(
                text="Everything is up to date."
            )

            self.status_label.config(
                text="Status: No updates available"
            )

            self.update_button.config(
                state="disabled"
            )

        else:
            for package in self.updates:
                self.update_tree.insert(
                    "",
                    tk.END,
                    values=(
                        package["name"],
                        package["installed"],
                        package["available"],
                        package["source"]
                    )
                )

            count = len(self.updates)

            if count == 1:
                summary = "1 update available"
            else:
                summary = f"{count} updates available"

            self.summary_label.config(
                text=summary
            )

            self.status_label.config(
                text="Status: Updates found"
            )

            self.update_button.config(
                state="normal"
            )

        self.search_button.config(
            state="normal"
        )

    def handle_search_error(self, error):
        self.hide_progress()

        messagebox.showerror(
            "WinGet Error",
            error
        )

        self.summary_label.config(
            text="Unable to complete scan."
        )

        self.status_label.config(
            text="Status: Search failed"
        )

        self.search_button.config(
            state="normal"
        )

        self.update_button.config(
            state="disabled"
        )

    # -----------------------------------------------------
    # Update all
    # -----------------------------------------------------
    def run_update_all(self):
        count = len(self.updates)

        if count == 0:
            return

        if count == 1:
            message = (
                "Install the available update?"
            )
        else:
            message = (
                f"Install all {count} available updates?"
            )

        confirm = messagebox.askyesno(
            "Update All",
            message
        )

        if not confirm:
            return

        self.status_label.config(
            text="Status: Installing updates..."
        )

        self.summary_label.config(
            text="Installing updates..."
        )

        self.search_button.config(
            state="disabled"
        )

        self.update_button.config(
            state="disabled"
        )

        self.show_progress()

        thread = threading.Thread(
            target=self.update_all_worker,
            daemon=True
        )

        thread.start()

    def update_all_worker(self):
        try:
            output = update_all()

            self.root.after(
                0,
                lambda: self.handle_update_results(
                    output
                )
            )

        except Exception as error:
            self.root.after(
                0,
                lambda: self.handle_update_error(
                    str(error)
                )
            )

    def handle_update_results(self, output):
        self.hide_progress()

        self.status_label.config(
            text="Status: Updates complete"
        )

        messagebox.showinfo(
            f"{APP_NAME}",
            "The update process completed."
        )

        self.search_updates()

    def handle_update_error(self, error):
        self.hide_progress()

        messagebox.showerror(
            "WinGet Error",
            error
        )

        self.summary_label.config(
            text="Update process encountered an error."
        )

        self.status_label.config(
            text="Status: Update failed"
        )

        self.search_button.config(
            state="normal"
        )

        if self.updates:
            self.update_button.config(
                state="normal"
            )


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------
def main():
    if not run_as_admin():
        sys.exit()

    # Load the custom font
    font_path = resource_path("assets/fonts/Armed-wM48.ttf")
    font_loaded = load_custom_font(font_path)
    if not font_loaded:
        messagebox.showerror("Font Error", "Could not load custom font.")
        sys.exit()

    # Create the main window
    root = tk.Tk()
    app = UpdaterApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()