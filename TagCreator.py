#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
import shutil
import threading
import time
import sys

# Add Hardware_Layer to sys.path to allow importing pn532
current_dir = os.path.dirname(os.path.abspath(__file__))
hardware_dir = os.path.join(current_dir, 'Hardware_Layer')
if hardware_dir not in sys.path:
    sys.path.append(hardware_dir)

# Attempt to import hardware libraries, fallback to mock if not available (e.g. on Mac)
try:
    import RPi.GPIO as GPIO
    from pn532 import *
    HARDWARE_AVAILABLE = True
except (ImportError, RuntimeError):
    HARDWARE_AVAILABLE = False

# Paths (Relative to where the script is run, assuming root of project)
ASSETS_DIR = os.path.join("frontend", "src", "assets")
JSON_PATH = os.path.join(ASSETS_DIR, "testdata.json")
ARTIFACTS_DIR = os.path.join(ASSETS_DIR, "artifacts")

class TagManager:
    """Handles database (JSON) interactions and file management."""
    def __init__(self, json_path=JSON_PATH, artifacts_dir=ARTIFACTS_DIR):
        self.json_path = json_path
        self.artifacts_dir = artifacts_dir
        self.data = self.load_data()

    def load_data(self):
        if not os.path.exists(self.json_path):
            return []
        try:
            with open(self.json_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []

    def save_data(self):
        with open(self.json_path, 'w') as f:
            json.dump(self.data, f, indent=4)

    def get_tag_by_id(self, tag_id):
        tag_id = str(tag_id) # Ensure string comparison
        for item in self.data:
            if str(item.get("id")) == tag_id:
                return item
        return None

    def get_all_organs(self):
        return [item.get("name") for item in self.data]

    def get_tag_by_name(self, name):
        for item in self.data:
            if item.get("name") == name:
                return item
        return None

    def create_tag(self, tag_id, name, video_paths):
        """
        Creates a new tag entry.
        video_paths: dict with keys 'en', 'es', 'te' and values as source file paths.
        """
        # 1. Create directory
        target_dir = os.path.join(self.artifacts_dir, name)
        os.makedirs(target_dir, exist_ok=True)

        # 2. Copy files and build path dict
        relative_paths = {}
        for lang, src_path in video_paths.items():
            if src_path and os.path.exists(src_path):
                filename = f"{lang}.mp4" # Standardize name
                dst_path = os.path.join(target_dir, filename)
                shutil.copy2(src_path, dst_path)
                # Store relative path for JSON
                relative_paths[lang] = f"artifacts/{name}/{filename}"
            else:
                relative_paths[lang] = ""

        # 3. Update Data
        new_entry = {
            "id": str(tag_id),
            "name": name,
            "path": relative_paths
        }
        self.data.append(new_entry)
        self.save_data()
        return new_entry

    def update_tag_files(self, tag_id, name, video_paths):
        """
        Updates an existing tag's name or files. 
        """
        tag = self.get_tag_by_id(tag_id)
        if not tag:
            return False

        # If name changed, we might need to move folder (optional, but good practice)
        # For simplicity, we'll keep the foldernames consistent with the NEW name if changed
        old_name = tag['name']
        if old_name != name:
            old_dir = os.path.join(self.artifacts_dir, old_name)
            new_dir = os.path.join(self.artifacts_dir, name)
            if os.path.exists(old_dir):
                os.rename(old_dir, new_dir)
            tag['name'] = name
            
            # Update paths in the existing dict to reflect new folder name
            for lang in tag['path']:
                if tag['path'][lang]:
                    tag['path'][lang] = tag['path'][lang].replace(f"artifacts/{old_name}/", f"artifacts/{name}/")

        # Process new video files if provided
        target_dir = os.path.join(self.artifacts_dir, name)
        os.makedirs(target_dir, exist_ok=True)

        for lang, src_path in video_paths.items():
            if src_path: # Only update if a new file is selected
                 if os.path.exists(src_path):
                    filename = f"{lang}.mp4"
                    dst_path = os.path.join(target_dir, filename)
                    shutil.copy2(src_path, dst_path)
                    tag['path'][lang] = f"artifacts/{name}/{filename}"

        self.save_data()
        return True

    def replace_broken_tag(self, old_organ_name, new_tag_id):
        """
        Assigns an existing organ entry to a new ID.
        Effective for "Swapping" a broken tag.
        """
        tag = self.get_tag_by_name(old_organ_name)
        if tag:
            tag['id'] = str(new_tag_id)
            self.save_data()
            return True
        return False

    def delete_tag(self, tag_id):
        tag = self.get_tag_by_id(tag_id)
        if tag:
            # Optional: Delete files? 
            # For safety, maybe just remove from JSON for now, or ask user. 
            # Implementation Plan said "optional file deletion". Let's stick to JSON for safety first.
            self.data.remove(tag)
            self.save_data()
            return True
        return False

class NFCReader:
    def __init__(self, callback):
        self.callback = callback
        self.running = False
        self.thread = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False

    def _run(self):
        if HARDWARE_AVAILABLE:
            self._run_hardware()
        else:
            self._run_mock()

    def _run_mock(self):
        """Simulates NFC reading for development/testing."""
        print("Starting Mock NFC Reader...")
        # In a real mock, we might wait for keypress or something, 
        # but for a GUI app, we might just rely on manual input or a "Simulate Scan" button.
        # However, to simulate the *thread* sending data:
        while self.running:
             time.sleep(1) 
             # We won't auto-generate scans in the mock to avoid annoying popups.
             # The GUI will have a "Manual Entry / Sim Scan" button.

    def _run_hardware(self):
        try:
            pn532 = PN532_SPI(debug=False, reset=20, cs=4)
            ic, ver, rev, support = pn532.get_firmware_version()
            pn532.SAM_configuration()

            previous_uid = None
            last_scan = 0

            while self.running:
                uid = pn532.read_passive_target(timeout=0.5)
                if uid is None:
                    continue
                
                # Debounce logic
                if uid == previous_uid and time.time() - last_scan < 3:
                     continue

                if len(uid) != 7:
                    continue

                final_val = int.from_bytes(uid, byteorder='big')
                self.callback(final_val)
                
                previous_uid = uid
                last_scan = time.time()
                
        except Exception as e:
            print(f"NFC Hardware Error: {e}")
        finally:
            GPIO.cleanup()

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("NFC Tag Creator")
        self.geometry("600x700")
        
        self.tag_manager = TagManager()
        self.nfc_reader = NFCReader(self.on_tag_scanned)
        
        self.current_scan_id = None
        
        self.setup_ui()
        self.nfc_reader.start()
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        print("Shutting down... Cleaning up GPIO.")
        self.nfc_reader.stop()
        # Give the thread a moment to finish its loop and clean up
        # In a real app we might join() the thread, but since it's daemon 
        # and we just want the finally block to hopefully run, we can just wait a bit 
        # or rely on the thread checking 'running'. 
        # Actually, best practice is to stop the thread and join it.
        # But for this simple script, stopping is enough.
        self.destroy()

    def setup_ui(self):
        # Header
        header = tk.Label(self, text="Ready to Scan...", font=("Helvetica", 24))
        header.pack(pady=20)
        self.header_label = header

        # Manual Entry (For testing without NFC)
        manual_frame = tk.Frame(self)
        manual_frame.pack(pady=10)
        tk.Label(manual_frame, text="Manual ID:").pack(side=tk.LEFT)
        self.manual_entry = tk.Entry(manual_frame)
        self.manual_entry.pack(side=tk.LEFT, padx=5)
        tk.Button(manual_frame, text="Simulate Scan", command=self.manual_scan).pack(side=tk.LEFT)

        # Dynamic Content Area
        self.content_frame = tk.Frame(self)
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Initial State
        self.show_waiting_state()

    def manual_scan(self):
        val = self.manual_entry.get()
        if val:
            self.on_tag_scanned(val)

    def on_tag_scanned(self, tag_id):
        # Ensure thread safety for GUI updates
        self.after(0, lambda: self.process_scan(tag_id))

    def process_scan(self, tag_id):
        self.current_scan_id = tag_id
        self.header_label.config(text=f"Scanned Tag: {tag_id}", fg="green")
        
        existing_tag = self.tag_manager.get_tag_by_id(tag_id)
        
        if existing_tag:
            self.show_edit_mode(existing_tag)
        else:
            self.show_new_tag_mode()

    def clear_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def show_waiting_state(self):
        self.clear_content()
        tk.Label(self.content_frame, text="Please scan an NFC tag to begin.", font=("Arial", 14)).pack(pady=50)

    # --- Mode: New Tag ---
    def show_new_tag_mode(self):
        self.clear_content()
        tk.Label(self.content_frame, text="New Tag Detected", font=("Arial", 16, "bold")).pack(pady=10)
        
        # Mode Selection
        self.mode_var = tk.StringVar(value="new")
        
        frame = tk.LabelFrame(self.content_frame, text="Action")
        frame.pack(fill=tk.X, pady=10)
        
        tk.Radiobutton(frame, text="Create New Organ Entry", variable=self.mode_var, value="new", command=self.toggle_new_mode).pack(anchor=tk.W)
        tk.Radiobutton(frame, text="Replace/Link to Existing Organ (Fix Broken Tag)", variable=self.mode_var, value="replace", command=self.toggle_new_mode).pack(anchor=tk.W)

        # Form Container
        self.form_frame = tk.Frame(self.content_frame)
        self.form_frame.pack(fill=tk.BOTH, expand=True)
        
        self.show_create_form() # Default

    def toggle_new_mode(self):
        for widget in self.form_frame.winfo_children():
            widget.destroy()
            
        if self.mode_var.get() == "new":
            self.show_create_form()
        else:
            self.show_replace_form()

    def show_create_form(self):
        tk.Label(self.form_frame, text="Organ Name:").pack(anchor=tk.W)
        self.name_entry = tk.Entry(self.form_frame)
        self.name_entry.pack(fill=tk.X, pady=5)
        
        self.video_files = {"en": None, "es": None, "te": None}
        self.file_labels = {}
        
        for lang in ["English (en)", "Spanish (es)", "Telugu (te)"]:
            code = lang.split('(')[1].strip(')')
            
            f_frame = tk.Frame(self.form_frame)
            f_frame.pack(fill=tk.X, pady=5)
            
            tk.Button(f_frame, text=f"Select {lang} Video", command=lambda c=code: self.select_video(c)).pack(side=tk.LEFT)
            lbl = tk.Label(f_frame, text="No file selected", fg="gray")
            lbl.pack(side=tk.LEFT, padx=10)
            self.file_labels[code] = lbl

        tk.Button(self.form_frame, text="Process New Tag", bg="blue", fg="white", command=self.submit_new_tag).pack(pady=20)

    def show_replace_form(self):
        tk.Label(self.form_frame, text="Select Existing Organ to Re-assign to this Tag:").pack(anchor=tk.W, pady=10)
        
        organs = self.tag_manager.get_all_organs()
        self.organ_combo = ttk.Combobox(self.form_frame, values=organs)
        self.organ_combo.pack(fill=tk.X, pady=5)
        
        tk.Button(self.form_frame, text="Link Tag to Organ", command=self.submit_replacement).pack(pady=20)

    # --- Mode: Edit Existing ---
    def show_edit_mode(self, tag_data):
        self.clear_content()
        tk.Label(self.content_frame, text=f"Editing: {tag_data['name']}", font=("Arial", 16, "bold")).pack(pady=10)
        
        # Name Edit
        tk.Label(self.content_frame, text="Name:").pack(anchor=tk.W)
        self.name_entry = tk.Entry(self.content_frame)
        self.name_entry.insert(0, tag_data['name'])
        self.name_entry.pack(fill=tk.X, pady=5)

        # Video Edits
        self.video_files = {"en": None, "es": None, "te": None} # Stores only NEWLY selected files
        self.file_labels = {}
        
        for lang in ["en", "es", "te"]:
            current_path = tag_data['path'].get(lang, "None")
            f_frame = tk.Frame(self.content_frame)
            f_frame.pack(fill=tk.X, pady=5)
            
            tk.Label(f_frame, text=f"{lang.upper()}:").pack(side=tk.LEFT, width=5)
            
            tk.Button(f_frame, text="Change", command=lambda c=lang: self.select_video(c)).pack(side=tk.LEFT)
            lbl = tk.Label(f_frame, text=f"Current: {os.path.basename(current_path)}", fg="black")
            lbl.pack(side=tk.LEFT, padx=10)
            self.file_labels[lang] = lbl
            
        btn_frame = tk.Frame(self.content_frame)
        btn_frame.pack(pady=20, fill=tk.X)
        
        tk.Button(btn_frame, text="Save Changes", command=lambda: self.submit_edit(tag_data['id'])).pack(side=tk.LEFT, expand=True)
        tk.Button(btn_frame, text="DELETE TAG", fg="red", command=lambda: self.submit_delete(tag_data['id'])).pack(side=tk.RIGHT, expand=True)

    # --- Actions ---
    def select_video(self, lang_code):
        path = filedialog.askopenfilename(filetypes=[("MP4 files", "*.mp4"), ("All files", "*.*")])
        if path:
            self.video_files[lang_code] = path
            self.file_labels[lang_code].config(text=os.path.basename(path), fg="black")

    def submit_new_tag(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Name is required")
            return
            
        # Basic validation: ensure at least one video? Or allow empty?
        # Let's start with flexible
        
        try:
            self.tag_manager.create_tag(self.current_scan_id, name, self.video_files)
            messagebox.showinfo("Success", f"Tag '{name}' created successfully!")
            self.show_waiting_state()
            self.header_label.config(text="Ready to Scan...", fg="black")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def submit_replacement(self):
        selected_organ = self.organ_combo.get()
        if not selected_organ:
            messagebox.showerror("Error", "Please select an organ")
            return
            
        if self.tag_manager.replace_broken_tag(selected_organ, self.current_scan_id):
            messagebox.showinfo("Success", f"Tag linked to '{selected_organ}' successfully!")
            self.show_waiting_state()
            self.header_label.config(text="Ready to Scan...", fg="black")
        else:
            messagebox.showerror("Error", "Failed to find organ")

    def submit_edit(self, tag_id):
        name = self.name_entry.get().strip()
        if not name:
             messagebox.showerror("Error", "Name is required")
             return

        try:
            self.tag_manager.update_tag_files(tag_id, name, self.video_files)
            messagebox.showinfo("Success", "Tag updated successfully!")
            self.show_waiting_state()
            self.header_label.config(text="Ready to Scan...", fg="black")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def submit_delete(self, tag_id):
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this tag?"):
            self.tag_manager.delete_tag(tag_id)
            messagebox.showinfo("Deleted", "Tag deleted.")
            self.show_waiting_state()
            self.header_label.config(text="Ready to Scan...", fg="black")

if __name__ == "__main__":
    app = App()
    app.mainloop()
