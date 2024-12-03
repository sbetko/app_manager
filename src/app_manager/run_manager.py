import os
import subprocess


def main():
    manager_path = os.path.join(os.path.dirname(__file__), "src", "app_manager", "manager.py")
    subprocess.run(["python", "-m", "streamlit", "run", manager_path])


if __name__ == "__main__":
    main()
