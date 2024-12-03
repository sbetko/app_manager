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
app-manager
```

You can also pass arguments/flags to Streamlit:

```shell
app-manager --server.port 8501 --server.headless true
```

## Setup Environment Variables

Create a `.env` file in the project root based on the `.env.example`:

```bash
cp .env.example .env
```

Update the .env file with your specific configurations.

## Development

Clone the repository and install the dependencies:

```shell
git clone https://github.com/sbetko/app_manager.git
cd app_manager
pip install -r requirements.txt
```

You can then run the manager locally:

```shell
python -m app_manager.run_manager
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
