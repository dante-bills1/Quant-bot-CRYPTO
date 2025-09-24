#!/bin/bash

# ============================================================================
# Trading Bot Linux/macOS Installer
# ============================================================================
# This script automates the setup of the trading bot on a Linux or macOS system.
# It performs the following steps:
# 1. Checks for Python 3.
# 2. Creates a virtual environment in ".venv".
# 3. Detects the Python version and system architecture.
# 4. Installs TA-Lib (tries PyPI first, falls back to system dependencies).
# 5. Installs all other dependencies from requirements.txt.
# ============================================================================

echo "================================================="
echo " Trading Bot Environment Setup for Linux/macOS "
echo "================================================="
echo

# --- Step 1: Check for Python ---
echo "[1/5] Checking for Python 3 installation..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 could not be found."
    echo "Please install Python 3.8 or higher to continue."
    exit 1
fi
echo "Python 3 found."
echo

# --- Step 2: Create Virtual Environment ---
echo "[2/5] Setting up virtual environment..."
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment in '.venv'..."
    python3 -m venv .venv
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to create the virtual environment."
        exit 1
    fi
else
    echo "Virtual environment '.venv' already exists."
fi
echo

# --- Activate Virtual Environment ---
source .venv/bin/activate

# --- Step 3: Get Python Version and Architecture ---
echo "[3/5] Detecting Python version and system architecture..."
PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}{sys.version_info.minor}')")
ARCH=$(python3 -c "import platform; print(platform.architecture()[0])")

# Determine platform-specific architecture tag
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    if [[ "$ARCH" == "64bit" ]]; then
        ARCH_TAG="macosx_10_9_x86_64"
    else
        ARCH_TAG="macosx_10_9_universal2"
    fi
    PLATFORM_TAG="macosx"
elif [[ "$ARCH" == "64bit" ]]; then
    # Linux 64-bit
    ARCH_TAG="linux_x86_64"
    PLATFORM_TAG="linux"
else
    # Linux 32-bit
    ARCH_TAG="linux_i686"
    PLATFORM_TAG="linux"
fi

echo "Python version code: cp${PY_VERSION}"
echo "Architecture: ${ARCH_TAG}"
echo "Platform: ${PLATFORM_TAG}"
echo

# --- Step 4: Install TA-Lib ---
echo "[4/5] Installing TA-Lib..."

# First, try to install from PyPI (this works if build tools are available)
echo "Attempting to install TA-Lib from PyPI..."
pip install TA-Lib
if [ $? -eq 0 ]; then
    echo "TA-Lib installed successfully from PyPI."
else
    echo "PyPI installation failed. Installing system dependencies and trying again..."
    
    # Install system dependencies based on the platform
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            echo "Installing TA-Lib dependencies with Homebrew..."
            brew install ta-lib
        else
            echo "ERROR: Homebrew not found. Please install Homebrew or install TA-Lib manually."
            echo "You can install Homebrew from: https://brew.sh/"
            exit 1
        fi
    else
        # Linux - try different package managers
        if command -v apt-get &> /dev/null; then
            echo "Installing TA-Lib dependencies with apt-get..."
            echo "You may be prompted for your password to install system packages."
            sudo apt-get update
            sudo apt-get install -y libta-lib-dev build-essential
        elif command -v dnf &> /dev/null; then
            echo "Installing TA-Lib dependencies with dnf..."
            echo "You may be prompted for your password to install system packages."
            sudo dnf install -y ta-lib-devel gcc gcc-c++ make
        elif command -v yum &> /dev/null; then
            echo "Installing TA-Lib dependencies with yum..."
            echo "You may be prompted for your password to install system packages."
            sudo yum install -y ta-lib-devel gcc gcc-c++ make
        else
            echo "ERROR: Could not detect package manager (apt, dnf, yum, or brew)."
            echo "Please install the TA-Lib C library and build tools manually:"
            echo "- TA-Lib development headers (libta-lib-dev or ta-lib-devel)"
            echo "- Build tools (build-essential, gcc, gcc-c++, make)"
            exit 1
        fi
    
        # Try installing from PyPI again after installing dependencies
        echo "Retrying TA-Lib installation from PyPI..."
        pip install TA-Lib
        if [ $? -ne 0 ]; then
            echo "ERROR: Failed to install TA-Lib even after installing system dependencies."
            echo "Please check the error messages above and try installing manually."
            exit 1
        fi
    fi
fi
echo "TA-Lib installed successfully."
echo

# --- Step 5: Install other dependencies ---
echo "[5/5] Installing dependencies from requirements.txt..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install dependencies from requirements.txt."
    exit 1
fi
echo "All dependencies installed."
echo

# --- Final Message ---
echo "================================================="
echo " Setup Complete!                                "
echo "================================================="
echo
echo "To activate the environment in the future, run:"
echo "source .venv/bin/activate"
echo
echo "To run the bot, use:"
echo "python3 main.py"
echo 