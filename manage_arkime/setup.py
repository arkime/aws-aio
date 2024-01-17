import setuptools

setuptools.setup(
    name="manage_arkime",
    version="1.0.0",
    description=("Tooling and configuration to install/manage Arkime Clusters in an AWS account"),
    author="Chris Helma",
    package_dir={"": "."},
    packages=setuptools.find_packages(where="."),
    install_requires=[
        "boto3",
        "click",
        "coloredlogs",
        "cryptography",
        "pexpect",
        "pytest",
        "pytest-cov",
        "ruff",
        "requests",
    ],
    python_requires=">=3.9",
)
