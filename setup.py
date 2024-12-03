from setuptools import setup, find_packages

setup(
    name="app_manager",
    version="0.1.0",
    packages=find_packages(),
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
            "app-manager=app_manager.manager:main",
        ],
    },
)
