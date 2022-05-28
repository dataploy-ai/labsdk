import setuptools

with open("example/README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="natun-pysdk",
    version="0.1.0",
    author="Almog Baku",
    author_email="almog@natun.ai",
    description="",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/natun-ai/pysdk",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    include_package_data=True,
    install_requires=['pandas'],
    python_requires='>=3.7, <4'
)
