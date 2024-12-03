import os
import subprocess
import app_manager


def main():
    manager_path = os.path.join(os.path.dirname(app_manager.__file__), "manager.py")
    subprocess.run(["python", "-m", "streamlit", "run", manager_path])


if __name__ == "__main__":
    main()
