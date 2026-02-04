from setuptools import setup, find_packages

setup(
    name="mcp-cli",
    version="1.0.0",
    description="MCP (Model Context Protocol) CLI client",
    packages=find_packages(),
    install_requires=[
        "click>=8.0.0",
        "requests>=2.25.0",
        "sseclient-py>=1.7.0",
        "pydantic>=2.0.0",
        "rich>=10.0.0",
        "pyyaml>=6.0.0",
    ],
    entry_points={
        'console_scripts': [
            'mcp-cli=mcp_cli.cli:cli',
        ],
    },
    python_requires=">=3.11",
)