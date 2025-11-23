"""Bandicoot: RMAB-based vaccination adherence optimization."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="bandicoot",
    version="0.1.0",
    author="Bandicoot Team",
    description="RMAB-based vaccination adherence optimization for healthcare",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/bhi5hmaraj/bandicoot",
    packages=find_packages(exclude=["tests", "experiments"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Healthcare Industry",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.10",
    install_requires=[
        "numpy>=1.24.0",
        "pandas>=2.0.0",
        "scikit-learn>=1.3.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "jupyter>=1.0.0",
            "jupytext>=1.14.0",
            "matplotlib>=3.5.0",
            "seaborn>=0.12.0",
            "black>=23.0.0",
            "ruff>=0.1.0",
        ]
    },
)
