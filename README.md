# Streamlit App Manager

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)

Streamlit App Manager is a minimalistic tool designed to help you run and manage multiple Streamlit, FastAPI, Flask, and arbitrary Python scripts seamlessly. It simplifies the process of starting, stopping, and monitoring your applications from a single interface.

---

## Installation

Install the package directly from the Git repository:

```bash
pip install git+https://github.com/sbetko/app_manager.git
```

---

## Usage

Start the app manager with:

```shell
app-manager
```

You can also pass arguments/flags to Streamlit:

```shell
app-manager --server.port 8501 --server.headless true
```

---

## Configuration

### `apps.yml`

Define your applications in the `apps.yml` file. Below is an example configuration:

```yaml
# apps.yml
# Example configuration file for Streamlit App Manager
# Each app should be a new entry in the yaml file

Test App:
  File: /path/to/test_app.py  # Path to the application script
  Port: 8501                 # Required for Streamlit, FastAPI, and Flask apps
  Environment: conda|venv env_name | path/to/venv/bin/activate
  EnvironmentType: [conda|venv]  # Specify the environment type
  Type: [streamlit|fastapi|flask|python]  # Type of application
  Category: Uncategorized     # Optional, defaults to 'Uncategorized'
  Flags: []                   # Optional command-line flags
  EnvironmentVariables: {}    # Optional environment variables
  WorkingDirectory: /path/to/working/directory  # Defaults to app's directory
  PublicURL: https://yourdomain.com/test-app  # Optional public-facing URL
```

### `.env` File

The `.env` file stores environment-specific variables. Use the `.env.example` file as a template:

```bash
cp .env.example .env
```

Edit the `.env` file to match your environment. When using the `app-manager` entry point, ensure variables are set as environment variables to take effect.

**Available Variables:**

- `LOCAL_IP`: Local address for accessing apps (e.g., `http://localhost`).
- `LAN_IP`: LAN address for accessing apps within your local network (e.g., `http://192.168.1.10`).
- `WAN_IP`: WAN address for accessing apps over the internet (e.g., `http://your_public_ip`).
- `CONDA_ACTIVATE_SCRIPT`: Path to the Conda activation script (e.g., `~/mambaforge/etc/profile.d/conda.sh`).

**Example `.env` file:**

```env
# IP Addresses
LOCAL_IP=http://localhost
LAN_IP=http://192.168.1.10
WAN_IP=http://your_public_ip

# Conda Activate Script Path
CONDA_ACTIVATE_SCRIPT=~/mambaforge/etc/profile.d/conda.sh
```

---

## Development

Clone the repository and install dependencies:

```shell
git clone https://github.com/sbetko/app_manager.git
cd app_manager
pip install -r requirements.txt
```

Run the manager locally:

```shell
python -m app_manager.run_manager
```

---

## Running with Test Apps

To quickly run the app manager with the included test apps, use the provided script:

```shell
python run_with_tests.py
```

This script will:

1. Create `./startup_scripts` and `./logs` directories.
2. Copy the test apps and `apps.yml` to the current directory.
3. Start the app manager.

---

## License

This project is licensed under the [MIT License](LICENSE).
