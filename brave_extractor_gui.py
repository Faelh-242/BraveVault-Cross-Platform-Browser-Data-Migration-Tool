#!/usr/bin/env python3
"""
Brave Browser Data Extractor and Importer GUI
--------------------------------------------
A graphical user interface for the Brave browser data extractor and importer.
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import subprocess
import platform
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('brave_extractor_gui')

class RedirectText:
    """Redirect stdout to a tkinter Text widget."""
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.buffer = ""

    def write(self, string):
        self.buffer += string
        # Only update every newline to avoid flicker
        if "\n" in self.buffer:
            lines = self.buffer.split("\n")
            self.buffer = lines.pop()  # Keep the last incomplete line
            for line in lines:
                self.text_widget.insert(tk.END, line + "\n")
                self.text_widget.see(tk.END)
                self.text_widget.update()

    def flush(self):
        if self.buffer:
            self.text_widget.insert(tk.END, self.buffer)
            self.text_widget.see(tk.END)
            self.buffer = ""

class BraveExtractorGUI:
    """GUI for Brave Browser Data Extractor and Importer."""
    def __init__(self, root):
        self.root = root
        self.root.title("Brave Browser Data Transfer Tool")
        self.root.geometry("700x500")
        self.root.minsize(600, 400)
        
        # Set up the main frame
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create the notebook (tabs)
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Export tab
        self.export_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.export_frame, text="Export")
        
        # Import tab
        self.import_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.import_frame, text="Import")
        
        # Log tab
        self.log_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.log_frame, text="Log")
        
        # Set up the export tab
        self.setup_export_tab()
        
        # Set up the import tab
        self.setup_import_tab()
        
        # Set up the log tab
        self.setup_log_tab()
        
        # Set the icon if available
        try:
            if platform.system() == "Windows":
                self.root.iconbitmap("brave.ico")
            else:
                # Not supported directly on Linux/macOS
                pass
        except:
            pass
    
    def setup_export_tab(self):
        """Set up the Export tab."""
        # Output file selection
        ttk.Label(self.export_frame, text="Output File:").grid(column=0, row=0, sticky=tk.W, pady=5)
        
        self.export_file_var = tk.StringVar()
        self.export_file_entry = ttk.Entry(self.export_frame, textvariable=self.export_file_var, width=50)
        self.export_file_entry.grid(column=1, row=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        self.export_browse_button = ttk.Button(self.export_frame, text="Browse...", command=self.browse_export_file)
        self.export_browse_button.grid(column=2, row=0, sticky=tk.W, padx=5, pady=5)
        
        # Checkboxes for options
        self.export_passwords_var = tk.BooleanVar(value=True)
        self.export_passwords_check = ttk.Checkbutton(self.export_frame, text="Export Passwords", variable=self.export_passwords_var)
        self.export_passwords_check.grid(column=0, row=1, columnspan=3, sticky=tk.W, pady=2)
        
        self.export_bookmarks_var = tk.BooleanVar(value=True)
        self.export_bookmarks_check = ttk.Checkbutton(self.export_frame, text="Export Bookmarks", variable=self.export_bookmarks_var)
        self.export_bookmarks_check.grid(column=0, row=2, columnspan=3, sticky=tk.W, pady=2)
        
        self.export_history_var = tk.BooleanVar(value=True)
        self.export_history_check = ttk.Checkbutton(self.export_frame, text="Export History", variable=self.export_history_var)
        self.export_history_check.grid(column=0, row=3, columnspan=3, sticky=tk.W, pady=2)
        
        # History days limit
        ttk.Label(self.export_frame, text="Export history from last:").grid(column=0, row=4, sticky=tk.W, pady=5)
        
        history_frame = ttk.Frame(self.export_frame)
        history_frame.grid(column=1, row=4, sticky=(tk.W, tk.E), pady=5)
        
        self.history_days_var = tk.StringVar(value="30")
        self.history_days_entry = ttk.Entry(history_frame, textvariable=self.history_days_var, width=5)
        self.history_days_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(history_frame, text="days (leave empty for all)").pack(side=tk.LEFT)
        
        # Export button
        button_frame = ttk.Frame(self.export_frame)
        button_frame.grid(column=0, row=5, columnspan=3, sticky=(tk.E, tk.W), pady=20)
        
        self.export_button = ttk.Button(button_frame, text="Export", command=self.export_data)
        self.export_button.pack(side=tk.RIGHT, padx=5)
        
        # Configure grid
        self.export_frame.columnconfigure(1, weight=1)
    
    def setup_import_tab(self):
        """Set up the Import tab."""
        # Input file selection
        ttk.Label(self.import_frame, text="Input File:").grid(column=0, row=0, sticky=tk.W, pady=5)
        
        self.import_file_var = tk.StringVar()
        self.import_file_entry = ttk.Entry(self.import_frame, textvariable=self.import_file_var, width=50)
        self.import_file_entry.grid(column=1, row=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        self.import_browse_button = ttk.Button(self.import_frame, text="Browse...", command=self.browse_import_file)
        self.import_browse_button.grid(column=2, row=0, sticky=tk.W, padx=5, pady=5)
        
        # Checkboxes for options
        self.import_passwords_var = tk.BooleanVar(value=True)
        self.import_passwords_check = ttk.Checkbutton(self.import_frame, text="Import Passwords", variable=self.import_passwords_var)
        self.import_passwords_check.grid(column=0, row=1, columnspan=3, sticky=tk.W, pady=2)
        
        self.import_bookmarks_var = tk.BooleanVar(value=True)
        self.import_bookmarks_check = ttk.Checkbutton(self.import_frame, text="Import Bookmarks", variable=self.import_bookmarks_var)
        self.import_bookmarks_check.grid(column=0, row=2, columnspan=3, sticky=tk.W, pady=2)
        
        self.import_history_var = tk.BooleanVar(value=True)
        self.import_history_check = ttk.Checkbutton(self.import_frame, text="Import History", variable=self.import_history_var)
        self.import_history_check.grid(column=0, row=3, columnspan=3, sticky=tk.W, pady=2)
        
        # Warning message
        warning_frame = ttk.Frame(self.import_frame)
        warning_frame.grid(column=0, row=4, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        warning_label = ttk.Label(
            warning_frame, 
            text="IMPORTANT: Close Brave browser before importing data!",
            foreground="red",
            font=("TkDefaultFont", 10, "bold")
        )
        warning_label.pack(fill=tk.X)
        
        # Import button
        button_frame = ttk.Frame(self.import_frame)
        button_frame.grid(column=0, row=5, columnspan=3, sticky=(tk.E, tk.W), pady=20)
        
        self.import_button = ttk.Button(button_frame, text="Import", command=self.import_data)
        self.import_button.pack(side=tk.RIGHT, padx=5)
        
        # Configure grid
        self.import_frame.columnconfigure(1, weight=1)
    
    def setup_log_tab(self):
        """Set up the Log tab."""
        # Log text widget
        self.log_text = tk.Text(self.log_frame, wrap=tk.WORD, width=80, height=20)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.log_text, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        # Redirect stdout to the log widget
        self.old_stdout = sys.stdout
        sys.stdout = RedirectText(self.log_text)
    
    def browse_export_file(self):
        """Open a file dialog to select the export file."""
        filename = filedialog.asksaveasfilename(
            defaultextension=".zip",
            filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")],
            title="Save Brave data as..."
        )
        if filename:
            self.export_file_var.set(filename)
    
    def browse_import_file(self):
        """Open a file dialog to select the import file."""
        filename = filedialog.askopenfilename(
            filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")],
            title="Select Brave data file..."
        )
        if filename:
            self.import_file_var.set(filename)
    
    def export_data(self):
        """Export Brave browser data."""
        output_file = self.export_file_var.get()
        
        if not output_file:
            messagebox.showerror("Error", "Please specify an output file.")
            return
        
        # Get options
        include_passwords = self.export_passwords_var.get()
        include_bookmarks = self.export_bookmarks_var.get()
        include_history = self.export_history_var.get()
        
        history_days = None
        if self.history_days_var.get():
            try:
                history_days = int(self.history_days_var.get())
                if history_days <= 0:
                    raise ValueError("Days must be positive")
            except ValueError:
                messagebox.showerror("Error", "History days must be a positive number.")
                return
        
        # Disable buttons during export
        self.export_button.configure(state=tk.DISABLED)
        self.import_button.configure(state=tk.DISABLED)
        
        # Switch to log tab
        self.notebook.select(2)  # Log tab index
        
        # Run in a thread to avoid freezing UI
        def run_export():
            cmd = [
                sys.executable,
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "brave_extractor.py"),
                "export",
                "--output", output_file
            ]
            
            if not include_passwords:
                cmd.append("--no-passwords")
            if not include_bookmarks:
                cmd.append("--no-bookmarks")
            if not include_history:
                cmd.append("--no-history")
            if history_days is not None:
                cmd.extend(["--history-days", str(history_days)])
            
            print(f"Running command: {' '.join(cmd)}")
            
            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                
                # Display output in real-time
                for line in process.stdout:
                    print(line.strip())
                
                process.wait()
                
                if process.returncode == 0:
                    messagebox.showinfo("Success", f"Brave data exported successfully to {output_file}")
                else:
                    messagebox.showerror("Error", "Failed to export Brave data.")
            except Exception as e:
                messagebox.showerror("Error", f"An error occurred: {str(e)}")
                print(f"Error: {str(e)}")
            finally:
                # Re-enable buttons
                self.root.after(0, lambda: self.export_button.configure(state=tk.NORMAL))
                self.root.after(0, lambda: self.import_button.configure(state=tk.NORMAL))
        
        threading.Thread(target=run_export, daemon=True).start()
    
    def import_data(self):
        """Import Brave browser data."""
        input_file = self.import_file_var.get()
        
        if not input_file:
            messagebox.showerror("Error", "Please specify an input file.")
            return
        
        # Check if file exists
        if not os.path.exists(input_file):
            messagebox.showerror("Error", f"File not found: {input_file}")
            return
        
        # Get options
        import_passwords = self.import_passwords_var.get()
        import_bookmarks = self.import_bookmarks_var.get()
        import_history = self.import_history_var.get()
        
        # Confirm import
        if not messagebox.askyesno(
            "Confirm Import",
            "WARNING: This will replace your current Brave browser data. Make sure Brave is closed.\n\n"
            "Do you want to continue?"
        ):
            return
        
        # Disable buttons during import
        self.export_button.configure(state=tk.DISABLED)
        self.import_button.configure(state=tk.DISABLED)
        
        # Switch to log tab
        self.notebook.select(2)  # Log tab index
        
        # Run in a thread to avoid freezing UI
        def run_import():
            cmd = [
                sys.executable,
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "brave_extractor.py"),
                "import",
                "--input", input_file
            ]
            
            if not import_passwords:
                cmd.append("--no-passwords")
            if not import_bookmarks:
                cmd.append("--no-bookmarks")
            if not import_history:
                cmd.append("--no-history")
            
            print(f"Running command: {' '.join(cmd)}")
            
            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                
                # Display output in real-time
                for line in process.stdout:
                    print(line.strip())
                
                process.wait()
                
                if process.returncode == 0:
                    messagebox.showinfo(
                        "Success", 
                        "Brave data imported successfully.\n\nYou should restart Brave browser to see the imported data."
                    )
                else:
                    messagebox.showerror("Error", "Failed to import Brave data.")
            except Exception as e:
                messagebox.showerror("Error", f"An error occurred: {str(e)}")
                print(f"Error: {str(e)}")
            finally:
                # Re-enable buttons
                self.root.after(0, lambda: self.export_button.configure(state=tk.NORMAL))
                self.root.after(0, lambda: self.import_button.configure(state=tk.NORMAL))
        
        threading.Thread(target=run_import, daemon=True).start()
    
    def on_close(self):
        """Handle window close event."""
        # Restore stdout
        sys.stdout = self.old_stdout
        self.root.destroy()

def main():
    """Run the GUI application."""
    root = tk.Tk()
    app = BraveExtractorGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()

if __name__ == "__main__":
    main()