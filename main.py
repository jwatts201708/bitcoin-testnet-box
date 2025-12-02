import subprocess
import os
import json
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
# Default to the temp location we set up, but allow override
BITCOIN_BIN_DIR = os.getenv("BITCOIN_BIN_DIR", "/tmp/bitcoin_setup/bitcoin-0.21.0/bin")
BITCOIND = os.path.join(BITCOIN_BIN_DIR, "bitcoind")
BITCOIN_CLI = os.path.join(BITCOIN_BIN_DIR, "bitcoin-cli")
DATA_DIR_1 = os.getenv("DATA_DIR_1", "1")
DATA_DIR_2 = os.getenv("DATA_DIR_2", "2")

class GenerateRequest(BaseModel):
    blocks: int = 1

class SendRequest(BaseModel):
    address: str
    amount: float

def run_command(cmd_list):
    try:
        result = subprocess.run(
            cmd_list,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        # Include stderr in error
        raise Exception(f"Command failed: {e.stderr}")

def ensure_wallet(datadir, wallet_name="default_wallet"):
    # Check if wallet loaded
    try:
        wallets = json.loads(run_command([BITCOIN_CLI, f"-datadir={datadir}", "listwallets"]))
        if wallet_name in wallets:
            return
    except:
        pass # Maybe not running or auth failure

    # Try to load or create
    try:
        run_command([BITCOIN_CLI, f"-datadir={datadir}", "loadwallet", wallet_name])
    except:
        try:
             run_command([BITCOIN_CLI, f"-datadir={datadir}", "createwallet", wallet_name])
        except Exception as e:
             # Ignore if it says "Database already exists" and just wasn't loaded (though loadwallet should have caught it)
             # or if it really failed
             pass

@app.get("/")
def read_root():
    return {"status": "ok", "service": "Bitcoin Testnet Box API"}

@app.post("/start")
def start_nodes():
    # Start Node 1 & 2
    if not os.path.exists(DATA_DIR_1):
         raise HTTPException(status_code=500, detail=f"Data directory 1 missing: {DATA_DIR_1}")

    try:
        subprocess.Popen([BITCOIND, f"-datadir={DATA_DIR_1}", "-daemon"])
        subprocess.Popen([BITCOIND, f"-datadir={DATA_DIR_2}", "-daemon"])

        return {"message": "Nodes started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stop")
def stop_nodes():
    try:
        run_command([BITCOIN_CLI, f"-datadir={DATA_DIR_1}", "stop"])
        run_command([BITCOIN_CLI, f"-datadir={DATA_DIR_2}", "stop"])
        return {"message": "Nodes stopping"}
    except Exception as e:
        return {"message": f"Error stopping (maybe already stopped): {str(e)}"}

@app.get("/info")
def get_info():
    info1 = {}
    info2 = {}

    def get_node_info(datadir):
        cli = [BITCOIN_CLI, f"-datadir={datadir}"]
        try:
            # Ensure wallet exists if we can talk to the node
            ensure_wallet(datadir)

            blockchain = json.loads(run_command(cli + ["getblockchaininfo"]))
            wallet = json.loads(run_command(cli + ["getwalletinfo"]))
            network = json.loads(run_command(cli + ["getnetworkinfo"]))
            return {
                "blocks": blockchain.get("blocks"),
                "balance": wallet.get("balance"),
                "connections": network.get("connections"),
                "difficulty": blockchain.get("difficulty"),
                "version": network.get("version"),
                "status": "online"
            }
        except Exception as e:
            return {"status": "offline/starting", "error": str(e)}

    info1 = get_node_info(DATA_DIR_1)
    info2 = get_node_info(DATA_DIR_2)

    return {"node1": info1, "node2": info2}

@app.post("/generate")
def generate_blocks(req: GenerateRequest):
    try:
        ensure_wallet(DATA_DIR_1)
        # Get address to mine to
        addr = run_command([BITCOIN_CLI, f"-datadir={DATA_DIR_1}", "getnewaddress"])

        # Generate
        res = run_command([BITCOIN_CLI, f"-datadir={DATA_DIR_1}", "generatetoaddress", str(req.blocks), addr])
        # res is a list of block hashes
        return {"message": f"Generated {req.blocks} blocks", "hashes": json.loads(res)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/wallet/address/{node}")
def get_new_address(node: int):
    datadir = DATA_DIR_1 if node == 1 else DATA_DIR_2
    try:
        ensure_wallet(datadir)
        addr = run_command([BITCOIN_CLI, f"-datadir={datadir}", "getnewaddress"])
        return {"address": addr}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/send")
def send_coins(req: SendRequest):
    try:
        ensure_wallet(DATA_DIR_1)
        txid = run_command([BITCOIN_CLI, f"-datadir={DATA_DIR_1}", "sendtoaddress", req.address, str(req.amount)])
        return {"txid": txid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
