from setuptools import setup, find_packages
import pathlib

HERE = pathlib.Path(__file__).parent
README = (HERE / "README.md").read_text()

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
        "python-dotenv",
        "gpustat",
    ],
    entry_points={
        "console_scripts": [
            "app-manager=app_manager.run_manager:main",
        ],
    },
    long_description=README,
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
)
