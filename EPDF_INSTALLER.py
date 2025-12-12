import os
import sys
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import winreg

# ================================
# Installer Configuration
# ================================
FILES_TO_INSTALL = ["epdf.py", "EPDF_scaled_7x_pngcrushed.ico"]
DEFAULT_INSTALL_PATH = r"C:\Program Files\EPDF"
EXTENSION = ".epdf"
FILETYPE = "EPDFScript"
DISPLAY_NAME = "EPDF Script"
EXE_NAME = "epdf.exe"  # final EXE name

# ================================
# Registry Helpers
# ================================
def set_registry_key(path, value):
    key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, path)
    winreg.SetValueEx(key, "", 0, winreg.REG_SZ, value)
    winreg.CloseKey(key)

# ================================
# Convert Python script to EXE
# ================================
def build_exe(install_folder):
    py_file = os.path.join(install_folder, "epdf.py")
    exe_file = os.path.join(install_folder, EXE_NAME)

    # Remove old build if exists
    if os.path.exists(exe_file):
        os.remove(exe_file)

    # Use PyInstaller
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        f"--name={EXE_NAME.replace('.exe','')}",
        f"--icon={os.path.join(install_folder,'EPDF_scaled_7x_pngcrushed.ico')}",
        py_file
    ]
    subprocess.run(cmd, check=True)

    # Move EXE from dist to install_folder
    dist_exe = os.path.join(os.getcwd(), "dist", EXE_NAME)
    if os.path.exists(dist_exe):
        shutil.move(dist_exe, exe_file)
        shutil.rmtree("dist")
        shutil.rmtree("build")
        spec_file = EXE_NAME.replace(".exe",".spec")
        if os.path.exists(spec_file):
            os.remove(spec_file)
    return exe_file

# ================================
# Installer Function
# ================================
def install(epdf_folder):
    try:
        os.makedirs(epdf_folder, exist_ok=True)

        # Copy files
        for file in FILES_TO_INSTALL:
            shutil.copy(file, epdf_folder)

        # Build EXE
        exe_path = build_exe(epdf_folder)

        # Add to PATH
        current_path = os.environ.get("PATH", "")
        if epdf_folder not in current_path:
            os.environ["PATH"] += ";" + epdf_folder
            reg_key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
                0, winreg.KEY_SET_VALUE
            )
            winreg.SetValueEx(reg_key, "Path", 0, winreg.REG_EXPAND_SZ, current_path + ";" + epdf_folder)
            winreg.CloseKey(reg_key)

        # Register file type
        set_registry_key(EXTENSION, FILETYPE)
        set_registry_key(FILETYPE, DISPLAY_NAME)
        set_registry_key(f"{FILETYPE}\\DefaultIcon", os.path.join(epdf_folder, "EPDF_scaled_7x_pngcrushed.ico"))
        set_registry_key(f"{FILETYPE}\\shell\\open\\command", f'"{exe_path}" "%1"')

        messagebox.showinfo("EPDF Installer", f"Installation complete!\nInstall folder: {epdf_folder}")

    except Exception as e:
        messagebox.showerror("EPDF Installer", f"Error: {e}")

# ================================
# Tkinter GUI
# ================================
def select_folder():
    folder = filedialog.askdirectory(initialdir=DEFAULT_INSTALL_PATH)
    if folder:
        install(folder)

root = tk.Tk()
root.title("EPDF Installer")
root.geometry("450x220")

tk.Label(root, text="EPDF Installer", font=("Arial", 18, "bold")).pack(pady=15)
tk.Label(root, text="Select installation folder:").pack(pady=5)

tk.Button(root, text="Choose Folder", command=select_folder, width=25).pack(pady=10)
tk.Label(root, text=f"(Default: {DEFAULT_INSTALL_PATH})").pack(pady=5)

root.mainloop()
