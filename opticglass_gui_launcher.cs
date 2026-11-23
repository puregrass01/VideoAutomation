// opticglass_gui.exe: opens opticglass_gui.py (next to this exe) with the Python launcher, so the window always matches
// the current Python source. The GUI's commands run with the same Python (`py`, the PC's default: PYTHON_MANAGER_DEFAULT / PY_PYTHON), so Python is required either way.
// Build (Windows' built-in compiler, no install):
//   C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe /nologo /target:winexe /out:opticglass_gui.exe
//     /win32icon:video-automation\assets\logos\opticglass.ico /r:System.Windows.Forms.dll opticglass_gui_launcher.cs
using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

static class OpticGlassGuiLauncher
{
    [STAThread]
    static void Main()
    {
        string dir = AppDomain.CurrentDomain.BaseDirectory;
        string script = Path.Combine(dir, "opticglass_gui.py");
        if (!File.Exists(script))
        {
            MessageBox.Show("opticglass_gui.py not found next to this exe:\n" + dir, "opticglass-gui");
            return;
        }
        // pyw has no console window; py is the fallback when only the console launcher is installed
        foreach (string exe in new[] { "pyw", "py" })
        {
            try
            {
                var psi = new ProcessStartInfo(exe, "\"" + script + "\"") { WorkingDirectory = dir, UseShellExecute = false };
                psi.EnvironmentVariables["PYTHONUTF8"] = "1";
                Process.Start(psi);
                return;
            }
            catch (System.ComponentModel.Win32Exception) { }
        }
        MessageBox.Show("Python launcher (pyw/py) not found. Run setup.bat first.", "opticglass-gui");
    }
}
