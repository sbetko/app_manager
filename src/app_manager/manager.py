from __future__ import annotations

import itertools
import os
import subprocess
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import psutil  # conda install psutil -c conda-forge
import streamlit as st
import yaml  # conda install pyyaml -c conda-forge
from streamlit.components.v1 import html

try:
    import gpustat  # conda install gpustat -c conda-forge
except ImportError:
    _gpustat_available = False
else:
    _gpustat_available = True

conda_activate = "~/mambaforge/etc/profile.d/conda.sh"

local_ip = "http://localhost"
lan_ip = "http://192.168.40.191"
wan_ip = "http://24.239.193.76"

startup_scripts_folder = "./startup_scripts"
logs_folder = "./logs"

os.makedirs(startup_scripts_folder, exist_ok=True)
os.makedirs(logs_folder, exist_ok=True)


def app_kill(app_info):
    # TODO: It seems that calling kill on the psutil process object doesn't work
    # to kill subprocesses (seems to be an issue for FastAPI apps), so we need to
    # use the PID instead, which subprocesses share.
    # app_info["Process"].kill()
    os.kill(app_info["PID"], 9)


@dataclass
class Process:
    pid: int
    cmdline: list[str]
    name: Optional[str] = None
    status: Optional[str] = None
    started: Optional[float] = None
    _memory_percent: Optional[float] = None
    _connections: Optional[list[psutil._common.pconn]] = None
    # Preserve a reference to the psutil process object in case we need it
    psutil_proc: Optional[psutil.Process] = None

    @classmethod
    def from_psutil_process(cls, p: psutil.Process):
        # Considerably speeds up the retrieval of multiple process information
        # at the same time.
        with p.oneshot():
            return cls(
                pid=p.pid,
                cmdline=p.cmdline(),
                name=p.name(),
                status=p.status(),
                started=p.create_time(),
                psutil_proc=p,
            )

    @property
    def connections(self):
        if self._connections is None:
            if self.psutil_proc is not None:
                try:
                    self._connections = self.psutil_proc.connections()
                except psutil.AccessDenied:
                    self._connections = []
            else:
                self._connections = []

        return self._connections

    @property
    def memory_percent(self):
        if self._memory_percent is None:
            if self.psutil_proc is not None:
                self._memory_percent = self.psutil_proc.memory_percent()
            else:
                self._memory_percent = 0

        return self._memory_percent

    @property
    def gpu_memory(self):
        if _gpustat_available:
            try:
                gpu = gpustat.new_query().jsonify()["gpus"][0]
                processes = gpu["processes"]
                for process in processes:
                    if process["pid"] == self.pid:
                        return process["gpu_memory_usage"]
            except Exception:
                return 0
        else:
            return 0


class AppType(Enum):
    STREAMLIT = "Streamlit"
    FASTAPI = "FastAPI"


class EnvironmentType(Enum):
    CONDA = "Conda"
    VENV = "venv"


@dataclass
class AppConfig:
    app_name: str
    file_path: str
    port: int
    environment_name: str
    environment_type: EnvironmentType = EnvironmentType.CONDA
    app_type: AppType = AppType.STREAMLIT
    working_dir: Optional[str] = None


def main():
    st.set_page_config(page_title="Streamlit App Manager")
    st.title("Streamlit App Manager")
    memory = psutil.virtual_memory()
    memory_used = memory.used / 1024**3
    memory_total = memory.total / 1024**3
    memory_free = memory_total - memory_used
    st.write(f"RAM: {memory_used:.2f} / {memory_total:.2f} GB ({memory_free:.2f} GB free)")

    if _gpustat_available:
        try:
            gpu_memory = gpustat.new_query().jsonify()["gpus"][0]
            gpu_memory_used = gpu_memory["memory.used"]  # / 1024 ** 3
            gpu_memory_total = gpu_memory["memory.total"]  # / 1024 ** 3
            gpu_memory_free = gpu_memory_total - gpu_memory_used
            st.write(f"VRAM: {gpu_memory_used} / {gpu_memory_total} MB ({gpu_memory_free} MB free)")
        except Exception:
            pass

    if not os.path.exists("apps.yml"):
        st.error("No apps.yml file found. Please create one.")
        st.stop()

    with open("apps.yml", "r") as f:
        apps = yaml.safe_load(f)

    processes = [Process.from_psutil_process(p) for p in psutil.process_iter()]

    for app in list(apps.keys()):
        if apps[app].get("Category") is None:
            apps[app]["Category"] = "Uncategorized"

    apps = {k: v for k, v in sorted(apps.items(), key=lambda item: item[1].get("Category", ""))}
    apps = {
        k: list(g)
        for k, g in itertools.groupby(apps.items(), key=lambda item: item[1].get("Category", ""))
    }

    for category, apps in apps.items():
        expanded = category != "Archive" and category != "Miscellaneous"
        with st.expander(category, expanded=expanded):
            for app_name, app_info in apps:
                for p in processes:
                    cmdline = " ".join(p.cmdline)

                    if not cmdline:
                        continue

                    port_in_proc = str(app_info["Port"]) in cmdline
                    file_in_proc = os.path.basename(app_info["File"]) in cmdline

                    if app_info.get("Type", "streamlit").lower() == "streamlit":
                        app_running = port_in_proc and file_in_proc and "streamlit" in cmdline
                    elif app_info.get("Type").lower() == "fastapi":
                        app_running = port_in_proc and "uvicorn" in cmdline

                    if app_running:
                        app_info["Running"] = app_running
                        app_info["PID"] = p.pid
                        app_info["Process"] = p
                        app_info["Memory"] = p.memory_percent
                        app_info["GPU"] = p.gpu_memory
                        break
                else:
                    app_info["Running"] = False

            self_cwd = os.getcwd()

            for app_name, app_info in apps:
                col1, col2, col3 = st.columns([6, 1, 1])
                info_col = col1.empty()
                view_logs = col3.checkbox("Logs", key=f"view_logs_{app_name}")

                start_stop = col2.empty()

                if app_info["Running"]:
                    port = app_info["Port"]

                    local = f"[Local]({local_ip}:{port}), " if local_ip else ""
                    lan = f"[LAN]({lan_ip}:{port}), " if lan_ip else ""
                    wan = f"[WAN]({wan_ip}:{port})"
                    mem_info = f"RAM: {app_info['Memory']:.2f}%"
                    if app_info["GPU"] is not None:
                        mem_info += f", GPU: {app_info['GPU']} MB"

                    info_col.info(
                        f"{app_name} (Port {app_info['Port']}) at {local} {lan} {wan} ({mem_info})"
                    )
                    stop_sig = start_stop.button(
                        "Toggle",
                        key=f"stop_button_{app_name}",
                        on_click=app_kill,  # app_info["Process"].kill,
                        args=[app_info],
                    )

                else:
                    info_col.warning(f"{app_name}")
                    start_sig = start_stop.button("Toggle", key=f"start_button_{app_name}")

                    if start_sig:
                        nohup_out = (
                            '"' + os.path.join(self_cwd, logs_folder, app_name + ".out") + '"'
                        )
                        app_file = '"' + app_info["File"] + '"'
                        if app_info.get("WorkingDirectory"):
                            app_wd = '"' + app_info["WorkingDirectory"] + '"'
                        else:
                            app_wd = '"' + os.path.dirname(app_info["File"]) + '"'
                        startup_script_shebang = "#! /bin/bash\n"

                        environment_type = app_info.get("EnvironmentType", "conda").lower()
                        app_type = app_info.get("Type", "streamlit").lower()

                        flags = app_info.get("Flags", [])
                        env_vars = app_info.get("EnvironmentVariables", {})

                        startup_script = []

                        if env_vars is not None:
                            for env_var in env_vars:
                                startup_script.append(f"export {env_var}\n")

                        if environment_type == "conda":
                            app_env = app_info["Environment"]
                            startup_script += [
                                "source",
                                conda_activate,
                                "&&",
                                "conda",
                                "activate",
                                app_env,
                                "&&",
                                "cd",
                                app_wd,
                                "&&",
                            ]
                        elif environment_type == "venv":
                            app_env = '"' + app_info["Environment"] + '"'
                            startup_script += [
                                "source",
                                app_env,
                                "&&",
                                "cd",
                                app_wd,
                                "&&",
                            ]

                        if app_type == "streamlit":
                            app_port_config = f"--server.port={app_info['Port']}"
                            startup_script.extend(
                                [
                                    "nohup",
                                    "streamlit",
                                    "run",
                                    app_file,
                                    app_port_config,
                                    "--server.fileWatcherType=none",
                                    "--server.headless=true",
                                    "--browser.gatherUsageStats=false",
                                ]
                            )
                        elif app_type == "fastapi":
                            app_port_config = f"--port {app_info['Port']}"
                            uvicorn_launch_token = os.path.split(app_file)[1].split(".")[0] + ":app"
                            startup_script.extend(
                                [
                                    "nohup",
                                    "uvicorn",
                                    uvicorn_launch_token,
                                    "--host 0.0.0.0",
                                    app_port_config,
                                    # "--reload",
                                ]
                            )

                        startup_script.extend(flags)
                        startup_script.extend(["&>", nohup_out, "&"])

                        run_script_name = app_name.replace(" ", "_") + ".sh"
                        run_script_path = os.path.join(startup_scripts_folder, run_script_name)
                        with open(run_script_path, "w") as f:
                            f.write(startup_script_shebang + " ".join(startup_script))

                        subprocess.Popen(["chmod", "u+rx", f"{run_script_path}"])
                        subprocess.call(f"{run_script_path}")

                        port = app_info["Port"]
                        local = f"[Local]({local_ip}:{port}), " if local_ip else ""
                        lan = f"[LAN]({lan_ip}:{port}), " if lan_ip else ""
                        wan = f"[WAN]({wan_ip}:{port})"
                        info_col.info(f"{app_name} (Port: {port}) at {local} {lan} {wan}")

                if view_logs:
                    log_file = os.path.join(self_cwd, logs_folder, app_name + ".out")
                    if os.path.exists(log_file):
                        with open(log_file, "r") as f:
                            log_text = f.read()
                            log_html = "<pre>" + log_text + "</pre>"
                            html(log_html, height=200, scrolling=True)

    st.button("Refresh")


if __name__ == "__main__":
    main()
