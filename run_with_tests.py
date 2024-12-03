import os
import shutil
import subprocess


def setup_test_environment():
    pkg_dir = os.path.dirname(__file__)
    test_apps_dir = os.path.join(pkg_dir, "tests", "apps")

    # Copy test apps and apps.yml to the current directory
    shutil.copytree(test_apps_dir, ".", dirs_exist_ok=True)


def run_manager():
    pkg_dir = os.path.dirname(__file__)
    manager_path = os.path.join(pkg_dir, "src", "app_manager", "manager.py")
    subprocess.run(["python", "-m", "streamlit", "run", manager_path])


if __name__ == "__main__":
    setup_test_environment()
    run_manager()
