from setuptools import setup, find_packages
import os

here = os.path.abspath(os.path.dirname(__file__))

# Read the long description from README.md
long_description = ""
readme_path = os.path.join(here, "README.md")
if os.path.exists(readme_path):
    with open(readme_path, "r", encoding="utf-8") as f:
        long_description = f.read()

setup(
    name="douyin-sign",
    version="1.0.0",
    description="抖音全算法签名包 - TikTok/Douyin All-in-One Signature Package",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="douyin-sign contributors",
    url="https://github.com/7452323/douyin-sign",
    packages=["sign", "sign.tests"],
    include_package_data=True,
    install_requires=[
        "pycryptodome",
        "gmssl",
    ],
    python_requires=">=3.11",
    entry_points={
        "console_scripts": [
            "douyin-sign=sign.__init__:sign_all",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Topic :: Security :: Cryptography",
    ],
    license="MIT",
    keywords="tiktok douyin sign signature gorgon argus ladon khronos bogus ttencrypt",
)
