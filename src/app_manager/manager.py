import os
import subprocess

import psutil
import streamlit as st
import yaml

APP_MANIFEST_PATH: str = "./apps.yml"
ACTIVATE_PATH: str = "/Users/sbetko/mambaforge/bin/activate"
DISPLAY_URL: str = "localhost"
DEFAULT_PORT: int = 14982

# TODO: Add a "kill all" and "start all" button.
# TODO: Add option in app configuration for enabling hot reloading


def kill_app(app_info):
    # TODO: It seems that calling kill on the psutil process object doesn't work
    # to kill subprocesses (seems to be an issue for FastAPI apps), so we need to
    # use the PID instead, which subprocesses share.
    # app_info["Process"].kill()
    os.kill(app_info["PID"], 9)


def main():
    st.set_page_config(page_title="Streamlit App Manager")
    st.title("Streamlit App Manager")

    # with st.sidebar:
    #     st.button(
    #         "Edit config in VSCode",
    #         on_click=subprocess.Popen,
    #         args=(["code", APP_MANIFEST_PATH],),
    #     )

    #     st.button(
    #         "Edit this app in VSCode",
    #         on_click=subprocess.Popen,
    #         args=(["code", __file__],),
    #     )

    try:
        with open(APP_MANIFEST_PATH, "r") as f:
            apps = yaml.safe_load(f)
    except FileNotFoundError:
        st.error(f"Application manifest not found at {APP_MANIFEST_PATH}")
        st.stop()

    self_cwd = os.getcwd()

    # Get the system state
    for app_name, app_info in apps.items():
        for p in psutil.process_iter():
            cmdline = " ".join(p.cmdline())

            port_in_proc = str(app_info["Port"]) in cmdline
            file_in_proc = app_info["File"] in cmdline

            if app_info.get("Type", "streamlit").lower() == "streamlit":
                app_running = port_in_proc and "streamlit" in cmdline
            elif app_info.get("Type").lower() == "fastapi":
                app_running = port_in_proc and "uvicorn" in cmdline

            if app_running:
                app_info["Running"] = app_running
                app_info["PID"] = p.pid
                app_info["Process"] = p
                break
        else:
            app_info["Running"] = False

    # Display the system state
    for app_name, app_info in apps.items():
        col1, col2, col3 = st.columns([8, 1, 1])
        info_col = col1.empty()
        col3.button(
            "Edit",
            on_click=subprocess.Popen,
            args=(["code", app_info["WorkingDirectory"]],),
            key=f"{app_name}_edit_button",
        )

        start_stop = col2.empty()
        if app_info["Running"]:
            info_col.info(
                f"RUNNING (PID: {app_info['PID']}) {app_name} at http://{DISPLAY_URL}:{app_info['Port']}"
            )
            start_stop.button(
                "Toggle",
                key=f"stop_button_{app_name}",
                on_click=kill_app,
                args=[app_info],
            )

        else:
            info_col.warning(f"STOPPED: {app_name}")
            start_sig = start_stop.button("Toggle", key=f"start_button_{app_name}")

            if start_sig:
                nohup_out = '"' + self_cwd + "/" + app_name + ".out" + '"'
                app_file = '"' + app_info["File"] + '"'
                app_wd = '"' + app_info["WorkingDirectory"] + '"'
                startup_script_shebang = "#! /bin/bash\n"

                environment_type = app_info.get("EnvironmentType", "conda").lower()
                app_type = app_info.get("Type", "streamlit").lower()

                flags = app_info.get("Flags", [])

                startup_script = []
                if environment_type == "conda":
                    app_env = app_info["Environment"]
                    startup_script.extend(["source", ACTIVATE_PATH, "&&"])
                    startup_script.extend(["conda", "activate", app_env, "&&"])
                    startup_script.extend(["cd", app_wd, "&&"])

                elif environment_type == "venv":
                    app_env = '"' + app_info["Environment"] + '"'
                    startup_script.extend(["source", app_env, "&&", "cd", app_wd, "&&"])

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
                    uvicorn_launch_token = (
                        os.path.split(app_file)[1].split(".")[0] + ":app"
                    )
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

                # TODO: Make safe for file names
                # TODO: Make option for nohup file location
                run_script_name = app_name.replace(" ", "") + ".sh"
                with open(run_script_name, "w") as f:
                    f.write(startup_script_shebang + " ".join(startup_script))

                subprocess.Popen(["chmod", "u+rx", f"{run_script_name}"])
                subprocess.call(f"./{run_script_name}")

                info_col.info(
                    f"RUNNING: {app_name} at http://localhost:{app_info['Port']}"
                )

    st.button("Refresh")


if __name__ == "__main__":
    if st._is_running_with_streamlit:
        main()
    else:
        import sys

        from streamlit import cli

        if len(sys.argv) > 1:
            port_str = sys.argv[1]
            try:
                port_int = int(port_str)
            except ValueError:
                port_int = DEFAULT_PORT

        sys.argv = ["streamlit", "run", __file__, f"--server.port={port_int}"]
        sys.exit(cli.main())
