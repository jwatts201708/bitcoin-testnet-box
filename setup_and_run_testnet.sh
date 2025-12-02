#!/bin/bash
set -e

# Configuration
BITCOIN_VERSION="0.21.0"
BITCOIN_TAR="bitcoin-${BITCOIN_VERSION}-x86_64-linux-gnu.tar.gz"
BITCOIN_URL="https://bitcoincore.org/bin/bitcoin-core-${BITCOIN_VERSION}/${BITCOIN_TAR}"
LOCAL_BIN_DIR="$(pwd)/bin"
TEMP_DIR="temp_bitcoin"

# Ensure temp and bin directories exist
mkdir -p "$TEMP_DIR"
mkdir -p "$LOCAL_BIN_DIR"

# Check if bitcoind is available
if ! command -v bitcoind &> /dev/null; then
    # check if it is in our local bin
    if [ ! -f "$LOCAL_BIN_DIR/bitcoind" ]; then
        echo "bitcoind not found. Downloading Bitcoin Core $BITCOIN_VERSION..."
        cd "$TEMP_DIR"
        if [ ! -f "$BITCOIN_TAR" ]; then
            wget "$BITCOIN_URL"
        fi
        tar xzf "$BITCOIN_TAR"

        echo "Installing binaries to $LOCAL_BIN_DIR..."
        cp bitcoin-${BITCOIN_VERSION}/bin/* "$LOCAL_BIN_DIR/"
        cd ..
    fi
    export PATH="$LOCAL_BIN_DIR:$PATH"
fi

echo "Bitcoin Core version:"
bitcoind --version | head -n 1

echo "Cleaning up previous run..."
make stop >/dev/null 2>&1 || true

# Wait for bitcoind to stop
echo "Waiting for bitcoind to stop..."
while pgrep bitcoind > /dev/null; do
    sleep 1
done

make clean

echo "Starting Testnet..."
make start

echo "Waiting for nodes to start..."
# Wait until we can connect to the nodes
until bitcoin-cli -datadir=1 getnetworkinfo >/dev/null 2>&1; do
  sleep 1
done
until bitcoin-cli -datadir=2 getnetworkinfo >/dev/null 2>&1; do
  sleep 1
done
sleep 2

echo "Creating wallets..."
bitcoin-cli -datadir=1 createwallet wallet1
bitcoin-cli -datadir=2 createwallet wallet2

echo "Generating 101 blocks to mature coinbase..."
make generate BLOCKS=101

echo "Node 1 Info:"
make getinfo

echo "Generating address for Node 2..."
ADDR2=$(bitcoin-cli -datadir=2 getnewaddress)
echo "Address 2: $ADDR2"

echo "Sending 10 BTC from Node 1 to Node 2..."
# Using -named arguments for clarity and to set fee_rate if needed
TXID=$(bitcoin-cli -datadir=1 -named sendtoaddress address="$ADDR2" amount=10 fee_rate=20)
echo "Transaction ID: $TXID"

echo "Generating 1 block to confirm transaction..."
make generate BLOCKS=1

echo "Verifying Balances..."
echo "Node 1 Balance: $(bitcoin-cli -datadir=1 getbalance)"
echo "Node 2 Balance: $(bitcoin-cli -datadir=2 getbalance)"

echo "Testnet check complete. Stopping nodes..."
make stop
