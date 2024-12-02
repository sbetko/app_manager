from __future__ import annotations

import itertools
import os
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

import psutil
import streamlit as st
import yaml
from streamlit.components.v1 import html

try:
    import gpustat

    GPUSTAT_AVAILABLE = True
except ImportError:
    GPUSTAT_AVAILABLE = False

CONDA_ACTIVATE_SCRIPT = os.path.expanduser("~/mambaforge/etc/profile.d/conda.sh")
LOCAL_IP = "http://localhost"
LAN_IP = "http://192.168.40.191"
WAN_IP = "http://24.239.193.76"

STARTUP_SCRIPTS_FOLDER = os.path.abspath("./startup_scripts")
LOGS_FOLDER = os.path.abspath("./logs")
CONFIG_FILE = os.path.abspath("apps.yml")

os.makedirs(STARTUP_SCRIPTS_FOLDER, exist_ok=True)
os.makedirs(LOGS_FOLDER, exist_ok=True)


class AppType(Enum):
    STREAMLIT = "streamlit"
    FASTAPI = "fastapi"
    PYTHON = "python"  # For arbitrary Python scripts
    FLASK = "flask"


class EnvironmentType(Enum):
    CONDA = "conda"
    VENV = "venv"


@dataclass
class AppConfig:
    name: str
    file_path: str
    port: Optional[int]
    environment_name: str
    environment_type: EnvironmentType = EnvironmentType.CONDA
    app_type: AppType = AppType.STREAMLIT
    category: str = "Uncategorized"
    flags: List[str] = field(default_factory=list)
    environment_variables: Dict[str, str] = field(default_factory=dict)
    working_directory: Optional[str] = None

    @staticmethod
    def from_dict(name: str, config: Dict) -> AppConfig:
        return AppConfig(
            name=name,
            file_path=config["File"],
            port=config.get("Port"),
            environment_name=config["Environment"],
            environment_type=EnvironmentType(config.get("EnvironmentType", "conda").lower()),
            app_type=AppType(config.get("Type", "streamlit").lower()),
            category=config.get("Category", "Uncategorized"),
            flags=config.get("Flags", []),
            environment_variables=config.get("EnvironmentVariables", {}),
            working_directory=config.get("WorkingDirectory"),
        )


@dataclass
class ManagedProcess:
    pid: int
    cmdline: List[str]
    name: Optional[str] = None
    status: Optional[str] = None
    started: Optional[float] = None
    memory_percent: float = 0.0
    gpu_memory: int = 0
    process: Optional[psutil.Process] = field(default=None, repr=False)

    @classmethod
    def from_psutil_process(cls, p: psutil.Process) -> ManagedProcess:
        with p.oneshot():
            gpu_mem = 0
            if GPUSTAT_AVAILABLE:
                try:
                    gpu = gpustat.new_query().jsonify()["gpus"][0]
                    for proc in gpu["processes"]:
                        if proc["pid"] == p.pid:
                            gpu_mem = proc["gpu_memory_usage"]
                            break
                except Exception:
                    pass
            return cls(
                pid=p.pid,
                cmdline=p.cmdline(),
                name=p.name(),
                status=p.status(),
                started=p.create_time(),
                memory_percent=p.memory_percent(),
                gpu_memory=gpu_mem,
                process=p,
            )


class ConfigManager:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.apps: List[AppConfig] = []

    def load_config(self) -> None:
        if not os.path.exists(self.config_path):
            st.error("No apps.yml file found. Please create one.")
            example_config = """\
# apps.yml
# Example configuration file for Streamlit App Manager
# Each app should be a new entry in the yaml file
Test App:
  File: /path/to/test_app.py
  Port: 8501
  Environment: [conda|venv] env_name | path/to/venv/bin/activate
  EnvironmentType: [conda|venv]
  Type: [streamlit|fastapi|flask|python]
  Category: Uncategorized
  Flags: []
  EnvironmentVariables: {}
  WorkingDirectory: /path/to/working/directory
"""
            st.code(example_config, language="yaml")
            st.stop()

        with open(self.config_path, "r") as f:
            raw_apps = yaml.safe_load(f)

        self.apps = [AppConfig.from_dict(name, cfg) for name, cfg in raw_apps.items()]


class ProcessManager:
    def __init__(self):
        self.processes: List[ManagedProcess] = self._get_managed_processes()

    def _get_managed_processes(self) -> List[ManagedProcess]:
        managed = []
        for p in psutil.process_iter(['pid', 'cmdline', 'name', 'status', 'create_time']):
            try:
                managed.append(ManagedProcess.from_psutil_process(p))
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return managed

    def find_app_process(self, app: AppConfig) -> Optional[ManagedProcess]:
        for proc in self.processes:
            cmdline_str = " ".join(proc.cmdline).lower()
            # If the app has a port, use it to identify the process
            if app.port and str(app.port) in cmdline_str:
                if (
                    app.app_type == AppType.STREAMLIT
                    and "streamlit" in cmdline_str
                    and os.path.basename(app.file_path).lower() in cmdline_str
                ):
                    return proc
                elif app.app_type == AppType.FASTAPI and "uvicorn" in cmdline_str:
                    return proc
                elif app.app_type == AppType.FLASK and "gunicorn" in cmdline_str:
                    return proc
            else:
                # For apps without ports, use the file path to identify the process
                if (
                    app.app_type == AppType.PYTHON
                    and os.path.abspath(app.file_path) in [os.path.abspath(arg) for arg in proc.cmdline]
                ):
                    return proc
                elif (
                    app.app_type == AppType.PYTHON
                    and os.path.basename(app.file_path).lower() in cmdline_str
                ):
                    return proc
        return None

    def kill_process(self, proc: ManagedProcess) -> bool:
        try:
            proc.process.terminate()
            proc.process.wait(timeout=5)
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
            try:
                proc.process.kill()
                return True
            except Exception:
                return False


class AppLauncher:
    def __init__(self, startup_folder: str, logs_folder: str):
        self.startup_folder = startup_folder
        self.logs_folder = logs_folder

    def build_startup_script(self, app: AppConfig) -> str:
        script_lines = ["#!/bin/bash\n"]

        # Export environment variables
        for key, value in app.environment_variables.items():
            script_lines.append(f"export {key}={value}\n")

        # Activate environment
        if app.environment_type == EnvironmentType.CONDA:
            script_lines.append(f"source {CONDA_ACTIVATE_SCRIPT} && conda activate {app.environment_name} && \\\n")
        elif app.environment_type == EnvironmentType.VENV:
            script_lines.append(f"source {app.environment_name} && \\\n")

        # Change working directory
        working_dir = app.working_directory or os.path.dirname(app.file_path)
        script_lines.append(f"cd {working_dir} && \\\n")

        # Construct command based on app type
        if app.app_type == AppType.STREAMLIT:
            cmd = (
                f"streamlit run {app.file_path} "
                f"--server.port={app.port} "
                f"--server.fileWatcherType=none "
                f"--server.headless=true "
                f"--browser.gatherUsageStats=false"
            )
        elif app.app_type == AppType.FASTAPI:
            module_name = os.path.splitext(os.path.basename(app.file_path))[0]
            cmd = f"uvicorn {module_name}:app --host 0.0.0.0 --port {app.port}"
        elif app.app_type == AppType.FLASK:
            module_name = os.path.splitext(os.path.basename(app.file_path))[0]
            cmd = f"gunicorn {module_name}:app --bind 0.0.0.0:{app.port} --workers 4"
        elif app.app_type == AppType.PYTHON:
            # Derive the path to the Python executable within the virtual environment
            python_executable = self.get_virtualenv_python(app)
            if not python_executable:
                st.error(f"Unable to determine Python executable for {app.name}.")
                return ""
            cmd = f"{python_executable} {app.file_path}"
        else:
            cmd = f"python {app.file_path}"  # Default fallback

        # Append flags if any
        if app.flags:
            cmd += " " + " ".join(app.flags)

        # Redirect output to log file
        nohup_out = os.path.join(self.logs_folder, f"{app.name}.out")
        cmd += f" &> \"{nohup_out}\" &\n"

        script_lines.append(cmd)
        return "".join(script_lines)

    def get_virtualenv_python(self, app: AppConfig) -> Optional[str]:
        """
        Derive the path to the Python executable based on the environment activation script.
        Assumes that for venv, the Python executable is located in the same directory as the activate script.
        """
        if app.environment_type == EnvironmentType.VENV:
            activate_path = os.path.expanduser(app.environment_name)
            # Replace 'bin/activate' with 'bin/python'
            if activate_path.endswith("bin/activate"):
                python_path = activate_path.replace("bin/activate", "bin/python")
                if os.path.exists(python_path):
                    return python_path
            elif activate_path.endswith("Scripts/activate"):  # For Windows
                python_path = activate_path.replace("Scripts/activate", "Scripts/python.exe")
                if os.path.exists(python_path):
                    return python_path
        elif app.environment_type == EnvironmentType.CONDA:
            # For conda environments, use 'conda run' to execute the Python script within the environment
            return f"conda run -n {app.environment_name} python"
        return None

    def start_app(self, app: AppConfig) -> bool:
        script_content = self.build_startup_script(app)
        if not script_content:
            return False  # Error has already been handled in build_startup_script
        script_path = os.path.join(self.startup_folder, f"{app.name.replace(' ', '_')}.sh")

        try:
            with open(script_path, "w") as f:
                f.write(script_content)
            os.chmod(script_path, 0o755)
            subprocess.Popen([script_path], shell=True)
            return True
        except Exception as e:
            st.error(f"Failed to start {app.name}: {e}")
            return False


class AppManagerUI:
    def __init__(
        self,
        config_manager: ConfigManager,
        process_manager: ProcessManager,
        launcher: AppLauncher,
    ):
        self.config_manager = config_manager
        self.process_manager = process_manager
        self.launcher = launcher

    def display_system_info(self):
        st.title("Streamlit App Manager")

        # RAM Info
        memory = psutil.virtual_memory()
        memory_used = memory.used / 1024**3
        memory_total = memory.total / 1024**3
        memory_free = memory_total - memory_used
        st.write(
            f"**RAM:** {memory_used:.2f} / {memory_total:.2f} GB ({memory_free:.2f} GB free)"
        )

        # GPU Info
        if GPUSTAT_AVAILABLE:
            try:
                gpu = gpustat.new_query().jsonify()["gpus"][0]
                gpu_memory_used = gpu["memory.used"]
                gpu_memory_total = gpu["memory.total"]
                gpu_memory_free = gpu_memory_total - gpu_memory_used
                st.write(
                    f"**VRAM:** {gpu_memory_used} / {gpu_memory_total} MB ({gpu_memory_free} MB free)"
                )
            except Exception:
                st.write("**VRAM:** Unable to retrieve GPU information.")

    def display_apps(self):
        apps_by_category = itertools.groupby(
            sorted(self.config_manager.apps, key=lambda app: app.category),
            key=lambda app: app.category,
        )

        for category, apps in apps_by_category:
            expanded = category not in ["Archive", "Miscellaneous"]
            with st.expander(category, expanded=expanded):
                for app in apps:
                    self.display_app_card(app)

    def display_app_card(self, app: AppConfig):
        proc = self.process_manager.find_app_process(app)
        is_running = proc is not None

        col1, col2, col3 = st.columns([6, 1, 1])
        info_col = col1.empty()
        start_stop_col = col2
        log_col = col3

        if is_running:
            local = f"[Local]({LOCAL_IP}:{app.port})" if LOCAL_IP else ""
            lan = f"[LAN]({LAN_IP}:{app.port})" if LAN_IP else ""
            wan = f"[WAN]({WAN_IP}:{app.port})" if WAN_IP else ""
            mem_info = f"RAM: {proc.memory_percent:.2f}%"
            if proc.gpu_memory:
                mem_info += f", GPU: {proc.gpu_memory} MB"

            info_col.info(
                f"**{app.name}** (Port {app.port})\n{local}, {lan}, {wan}\n{mem_info}"
            )
            if start_stop_col.button(
                "Stop", key=f"stop_{app.name}", use_container_width=True, type="primary"
            ):
                success = self.process_manager.kill_process(proc)
                if success:
                    st.success(f"Stopped {app.name}")
                    st.rerun()
                else:
                    st.error(f"Failed to stop {app.name}")
        else:
            info_col.warning(f"**{app.name}**\nPort: {app.port}")
            if start_stop_col.button(
                "Start", key=f"start_{app.name}", use_container_width=True
            ):
                success = self.launcher.start_app(app)
                if success:
                    st.success(f"Started {app.name}")
                    st.rerun()
                else:
                    st.error(f"Failed to start {app.name}")

        # Logs
        show_logs = log_col.checkbox("Logs", key=f"logs_{app.name}")
        if show_logs:
            log_file = os.path.join(LOGS_FOLDER, f"{app.name}.out")
            if os.path.exists(log_file):
                with open(log_file, "r") as f:
                    log_content = f.read()
                html_content = f"<pre>{log_content}</pre>"
                html(html_content, height=300, scrolling=True)
            else:
                st.write("No logs available.")

    def run(self):
        self.display_system_info()
        self.display_apps()
        if st.button("Refresh"):
            st.rerun()


def main():
    config_manager = ConfigManager(CONFIG_FILE)
    config_manager.load_config()

    process_manager = ProcessManager()
    launcher = AppLauncher(STARTUP_SCRIPTS_FOLDER, LOGS_FOLDER)

    ui = AppManagerUI(config_manager, process_manager, launcher)
    ui.run()


if __name__ == "__main__":
    main()
