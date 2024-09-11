# DAASI Validator Setup

Run the following script to set up the environment and install dependencies:

```bash
#!/bin/bash

# Update and install dependencies
sudo apt update
sudo apt install python3-pip python3-venv nodejs npm -y

# Install Rust and Cargo
sudo apt install rustc cargo -y

# Verify Rust and Cargo installation
rustc --version
cargo --version

# Create and activate virtual environment
python3 -m venv bit
source bit/bin/activate

# Install PM2
sudo npm i -g pm2

# Clone repository (replace with your actual repo URL)
git clone https://github.com/daasi-ai/Daasi_validator
cd Daasi_validator

# Install Python requirements
pip install -e .

# Run Rust Attestation Server
cd attestation
cargo run
```

## Running the Validator

After installation, run the validator with your hotkey and coldkey:

```bash
# Run validator (replace 'your_hotkey' and 'your_coldkey' with your actual keys)
export PYTHONPATH=$PYTHONPATH:/root/Daasi_validator
pm2 start validators/validator.py --interpreter python3 -- --netuid 36 --subtensor.network test --wallet.name your_coldkey --wallet.hotkey your_hotkey --logging.debug
```