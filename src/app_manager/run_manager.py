import os
import subprocess
import sys
import app_manager


def main():
    manager_path = os.path.join(os.path.dirname(app_manager.__file__), "manager.py")
    streamlit_args = sys.argv[1:]  # Capture all arguments passed to the script
    subprocess.run(["streamlit", "run", manager_path] + streamlit_args)


if __name__ == "__main__":
    main()
