#!/bin/bash

# ============================================================================
# Trading Bot Linux/macOS Installer
# ============================================================================
# This script automates the setup of the trading bot on a Linux or macOS system.
# It performs the following steps:
# 1. Checks for Python 3.
# 2. Creates a virtual environment in ".venv".
# 3. Detects the Python version and system architecture.
# 4. Downloads the correct TA-Lib wheel from Christoph Gohlke's repository.
# 5. Installs the TA-Lib wheel.
# 6. Installs all other dependencies from requirements.txt.
# ============================================================================

echo "================================================="
echo " Trading Bot Environment Setup for Linux/macOS "
echo "================================================="
echo

# --- Step 1: Check for Python ---
echo "[1/6] Checking for Python 3 installation..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 could not be found."
    echo "Please install Python 3.8 or higher to continue."
    exit 1
fi
echo "Python 3 found."
echo

# --- Step 2: Create Virtual Environment ---
echo "[2/6] Setting up virtual environment..."
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
echo "[3/6] Detecting Python version and system architecture..."
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

# --- Step 4: Download the correct TA-Lib wheel ---
echo "[4/6] Downloading TA-Lib..."
TA_LIB_VERSION="0.6.4"
TA_LIB_WHEEL="ta_lib-${TA_LIB_VERSION}-cp${PY_VERSION}-cp${PY_VERSION}-${ARCH_TAG}.whl"
DOWNLOAD_URL="https://github.com/cgohlke/talib-build/releases/download/v${TA_LIB_VERSION}/${TA_LIB_WHEEL}"

echo "Downloading from: ${DOWNLOAD_URL}"
if command -v wget &> /dev/null; then
    wget -O "${TA_LIB_WHEEL}" "${DOWNLOAD_URL}"
elif command -v curl &> /dev/null; then
    curl -L -o "${TA_LIB_WHEEL}" "${DOWNLOAD_URL}"
else
    echo "ERROR: Neither wget nor curl found. Please install one of them to download TA-Lib."
    exit 1
fi

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to download TA-Lib."
    echo "Please check your internet connection or manually download the file from the URL above."
    exit 1
fi
echo "TA-Lib downloaded successfully."
echo

# --- Step 5: Install TA-Lib ---
echo "[5/6] Installing TA-Lib..."
pip install "${TA_LIB_WHEEL}"
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install TA-Lib from the wheel file."
    rm -f "${TA_LIB_WHEEL}" 2>/dev/null
    exit 1
fi
# Clean up the wheel file after installation
rm -f "${TA_LIB_WHEEL}"
echo "TA-Lib installed successfully."
echo

# --- Step 6: Install other dependencies ---
echo "[6/6] Installing dependencies from requirements.txt..."
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