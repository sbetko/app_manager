# Streamlit App Manager

A minimalistic app manager for running and managing Streamlit, FastAPI, Flask, and arbitrary Python scripts.

## Installation

You can install the package directly from the Git repository:

```bash
pip install git+https://github.com/sbetko/app_manager.git
```

## Usage

To start the app manager, run:

```shell
streamlit-app-manager
```

## Development

Clone the repository and install the dependencies:

```shell
git clone https://github.com/sbetko/app_manager.git
cd app_manager
pip install -r requirements.txt
```

You can then run the manager locally:

```shell
python -m app_manager.manager
```

## Running with Test Apps

To quickly run the app manager with the included test apps, use the provided script:

```shell
python run_with_tests.py
```

This will:

- Create the `./startup_scripts` and `./logs` directories.
- Copy the test apps and `apps.yml` to the current directory.
- Start the app manager.