from setuptools import setup, find_packages

setup(
    name="app_manager",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    include_package_data=True,
    package_data={
        'app_manager': ['tests/apps/*.py', 'tests/apps/apps.yml'],
    },
    install_requires=[
        "streamlit",
        "fastapi",
        "flask",
        "psutil",
        "pyyaml",
        "uvicorn",
        "gunicorn",
    ],
    entry_points={
        "console_scripts": [
            "app-manager=run_manager:main",
        ],
    },
)
