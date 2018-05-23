from setuptools import setup

with open("README.md") as f:
    readme = f.read()

with open("requirements.txt") as f:
    requires = [line.strip() for line in f if line]

with open("edi/__init__.py") as f:
    for line in f:
        if line.startswith("__version__"):
            version = line.split('"')[1]

setup(
    name="edi-slack",
    description="Simple and elegant Slack bot",
    long_description=readme,
    long_description_content_type="text/markdown",
    version=version,
    author="John Reese",
    author_email="john@noswap.com",
    url="https://github.com/jreese/edi",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Topic :: Utilities",
        "Development Status :: 3 - Alpha",
    ],
    license="MIT License",
    setup_requires=["setuptools>=38.6.0"],
    install_requires=requires,
    packages=["edi"],
    entry_points={"console_scripts": ["edi = edi.__main__:init_from_cli"]},
)
