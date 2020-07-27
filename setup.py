import setuptools


with open("README.md") as readme:
    long_description = readme.read()

with open("requirements.txt") as reqs:
    install_requires = reqs.read().splitlines()

setuptools.setup(
    name="cdk_cicd",
    version="1.0.17",
    description="Utility for generating CICD artifacts.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(),
    install_requires=install_requires,
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Utilities",
        "Typing :: Typed",
    ],
)
