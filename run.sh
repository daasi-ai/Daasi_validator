#!/bin/bash
main_dir=$(pwd)

# Function to check if the script is run as root (Linux only)
check_root() {
    if [[ "$OSTYPE" != "darwin"* && "$(id -u)" -ne 0 ]]; then
        echo "This script must be run as root. Please run it with sudo or as root."
        exit 1
    fi
}

# Only execute this section on Linux systems
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Check Ubuntu version
    UBUNTU_VERSION=$(lsb_release -rs)

    install_python3_11_linux() {
        if ! command -v python3.11 &> /dev/null; then
            echo "Installing Python 3.11 on Linux..."

            # Check for Ubuntu 24.04
            if [[ "$UBUNTU_VERSION" == "24.04" ]]; then
                # Manual installation for Ubuntu 24.04
                sudo apt-get update
                sudo apt-get install wget build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev curl libbz2-dev -y

                wget https://www.python.org/ftp/python/3.11.0/Python-3.11.0.tgz
                tar -xf Python-3.11.0.tgz
                cd Python-3.11.0

                ./configure --enable-optimizations
                make -j $(nproc)
                sudo make altinstall
            else
                # For other versions, try deadsnakes PPA
                sudo apt-get update
                sudo apt-get install software-properties-common -y
                sudo add-apt-repository ppa:deadsnakes/ppa
                sudo apt-get update
                sudo apt-get install python3.11 python3.11-venv python3.11-dev python3.11-distutils -y
            fi
        else
            echo "Python 3.11 is already installed."
        fi
    }

    # Call the function to install Python 3.11
    install_python3_11_linux

    # Function to check for missing packages on Linux
    check_missing_packages_linux() {
        echo "Checking for missing packages on Linux..."
        packages=("ssh" "curl" "wget" "git" "build-essential" "vim" "net-tools" "sudo" "python3-pip")
        missing_packages=()
        for pkg in "${packages[@]}"; do
            if ! dpkg -l | grep -q "^ii  $pkg "; then
                missing_packages+=("$pkg")
            fi
        done

        # Check for Python 3.11
        if ! command -v python3.11 &> /dev/null; then
            missing_packages+=("Python 3.11")
        fi

        if [ ${#missing_packages[@]} -eq 0 ]; then
            echo "All necessary packages are already installed."
            return 1
        else
            echo "The following packages are missing and will be installed: ${missing_packages[*]}"
            return 0
        fi
    }

    # Install missing packages for Ubuntu/Debian
    install_packages_linux() {
        echo "Installing missing packages on Linux..."
        for pkg in "${missing_packages[@]}"; do
            if [[ "$pkg" == "Python 3.11" ]]; then
                install_python3_11_linux
            else
                echo "Installing $pkg..."
                sudo apt-get install -y $pkg
            fi
        done
        echo "Package installation complete."
    }
fi

# Function to kill the verifier and python3.11 processes
cleanup() {
    echo "Cleaning up processes..."
    pkill -f target/debug/verifier
    pkill -f python3.11
    exit 0
}

# Trap signals and execute the cleanup function
trap cleanup SIGINT SIGTERM EXIT

# Function to ensure Rust is installed and environment variables are loaded
setup_rust_env() {
    # Check if rustc is available and in PATH
    if command -v rustc &> /dev/null; then
        echo "Rust is already installed."
    else
        echo "Rust is not installed. Installing Rust..."
        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    fi

    # Load Rust environment variables
    if [ -f "$HOME/.cargo/env" ]; then
        source "$HOME/.cargo/env"
    elif [ -f "$HOME/.cargo/env.fish" ]; then
        source "$HOME/.cargo/env.fish"  # For fish shell users
    else
        echo "Rust environment file not found. Please ensure Rust is correctly installed."
        exit 1
    fi
}

# Function to check for missing packages on macOS
check_missing_packages_macos() {
    echo "Checking for missing packages on macOS..."
    packages=("curl" "wget" "git" "python3" "pip3")
    missing_packages=()
    for pkg in "${packages[@]}"; do
        if ! brew list --formula | grep -q "^$pkg\$"; then
            missing_packages+=("$pkg")
        fi
    done

    # Check for Python 3.11
    if ! command -v python3.11 &> /dev/null; then
        missing_packages+=("Python 3.11")
    fi

    if [ ${#missing_packages[@]} -eq 0 ]; then
        echo "All necessary packages are already installed."
        return 1
    else
        echo "The following packages are missing and will be installed: ${missing_packages[*]}"
        return 0
    fi
}

# Function to prompt user for installation confirmation
prompt_install_all() {
    read -p "Do you want to install the missing packages, Python 3.11, and Rust? (y/n): " choice
    case "$choice" in
        y|Y ) return 0;;
        n|N ) return 1;;
        * ) echo "Invalid input. Please enter y or n."; prompt_install_all;;
    esac
}

# Prompt user for wallet name and hotkey
prompt_wallet_info() {
    read -e -p "Please enter the wallet name coldkey: " WALLET_NAME
    read -e -p "Please enter the wallet hotkey: " WALLET_HOTKEY
}

# Install missing packages for macOS
install_packages_macos() {
    echo "Installing missing packages on macOS..."
    for pkg in "${missing_packages[@]}"; do
        if [[ "$pkg" == "Python 3.11" ]]; then
            install_python3_11_macos
        else
            echo "Installing $pkg..."
            brew install $pkg
        fi
    done
    echo "Package installation complete."
}

# Function to install Python 3.11 and pip3.11 on macOS
install_python3_11_macos() {
    if ! command -v python3.11 &> /dev/null; then
        echo "Installing Python 3.11 on macOS..."
        brew install python@3.11
        echo "Python 3.11 installed successfully."
    else
        echo "Python 3.11 is already installed."
    fi
}

# Function to prompt user for Python dependency installation
prompt_install_python_dependencies() {
    read -p "Do you want to install the Python dependencies using pip3.11? (y/n): " choice
    case "$choice" in
        y|Y ) install_python_dependencies ;;
        n|N ) echo "Skipping Python dependency installation." ;;
        * ) echo "Invalid input. Please enter y or n."; prompt_install_python_dependencies ;;
    esac
}

# Function to install Python dependencies using pip3.11 on macOS
install_python_dependencies_macos() {
    echo "Installing Python dependencies using pip3.11..."
    cd $main_dir || { echo "Failed to change directory to validator_prod"; exit 1; }
    python3.11 -m pip install -r requirements.txt --break-system-packages || { echo "pip installation failed"; exit 1; }
    echo "Python dependencies installed."
    cd .. # Return to the previous directory after installation
}

# Function to install Python dependencies using pip3.11 on Linux
install_python_dependencies_linux() {
    echo "Installing Python dependencies using pip3.11..."
    cd $main_dir || { echo "Failed to change directory to validator_prod"; exit 1; }
    python3.11 -m pip install -r requirements.txt || { echo "First pip installation failed, retrying with --break-system-packages"; python3.11 -m pip install -r requirements.txt --break-system-packages || { echo "Second pip installation failed"; exit 1; } }
    echo "Python dependencies installed."
    cd .. # Return to the previous directory after installation
}

# Function to install Python dependencies based on OS
install_python_dependencies() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        install_python_dependencies_linux
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        install_python_dependencies_macos
    fi
}

# Function to check if the Rust application port is free
check_port_free() {
    PORT=your_port_here  # Replace with the actual port number
    if lsof -i:$PORT; then
        echo "Port $PORT is already in use. Please free the port or use a different one."
        exit 1
    fi
}

# Check if the script is run as root (Linux only)
#check_root

# Check for missing packages and prompt for installation only if packages are missing
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if check_missing_packages_linux; then
        if prompt_install_all; then
            install_packages_linux
        fi
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    if check_missing_packages_macos; then
        if prompt_install_all; then
            install_packages_macos
        fi
    fi
fi

# Prompt for Python dependency installation
prompt_install_python_dependencies

# Set up the Rust environment
setup_rust_env

# Check if the required port is free before starting the Rust application
#check_port_free

# Navigate to the attestation directory
cd $main_dir/attestation || { echo "Failed to change directory to attestation"; exit 1; }

# Run cargo in the background
cargo run &

# Capture the PID of the cargo process (verifier)
CARGO_PID=$!

# Wait for a short period to ensure cargo starts correctly
sleep 5

# Return to the previous directory
cd ..

# Prompt the user for wallet name and hotkey before running the Rust application
prompt_wallet_info

# Set the PYTHONPATH to the current directory
export PYTHONPATH=$(pwd)

# Print and run the validator command
echo "Your command is: python3.11 validators/validator.py --netuid 77 --subtensor.network test --wallet.name \"$WALLET_NAME\" --wallet.hotkey \"$WALLET_HOTKEY\" --logging.debug"

python3.11 validators/validator.py --netuid 77 --subtensor.network test --wallet.name "$WALLET_NAME" --wallet.hotkey "$WALLET_HOTKEY" --logging.debug &
PYTHON_PID=$!

# Wait for both background processes to finish
wait $CARGO_PID
wait $PYTHON_PID
