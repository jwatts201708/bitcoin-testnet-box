import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [info, setInfo] = useState(null)
  const [logs, setLogs] = useState([])
  const [amount, setAmount] = useState(10)
  const [genBlocks, setGenBlocks] = useState(1)
  const [targetAddress, setTargetAddress] = useState('')

  const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

  const log = (msg) => setLogs(prev => [msg, ...prev].slice(0, 50))

  const fetchInfo = async () => {
    try {
      const res = await fetch(`${API}/info`)
      const data = await res.json()
      setInfo(data)
    } catch (e) {
      // log(`Error fetching info: ${e}`)
    }
  }

  useEffect(() => {
    fetchInfo()
    const interval = setInterval(fetchInfo, 5000)
    return () => clearInterval(interval)
  }, [])

  const startNodes = async () => {
    log('Starting nodes...')
    try {
      await fetch(`${API}/start`, { method: 'POST' })
      log('Start command sent')
      setTimeout(fetchInfo, 2000)
    } catch (e) { log(`Error: ${e}`) }
  }

  const stopNodes = async () => {
    log('Stopping nodes...')
    try {
      await fetch(`${API}/stop`, { method: 'POST' })
      log('Stop command sent')
    } catch (e) { log(`Error: ${e}`) }
  }

  const generate = async () => {
    log(`Generating ${genBlocks} blocks...`)
    try {
      const res = await fetch(`${API}/generate`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ blocks: parseInt(genBlocks) })
      })
      const data = await res.json()
      log(`Generated: ${data.message}`)
      fetchInfo()
    } catch (e) { log(`Error: ${e}`) }
  }

  const getAddress = async (node) => {
    try {
      const res = await fetch(`${API}/wallet/address/${node}`)
      const data = await res.json()
      log(`Node ${node} New Address: ${data.address}`)
      if (node === 2) setTargetAddress(data.address)
    } catch (e) { log(`Error: ${e}`) }
  }

  const send = async () => {
    if (!targetAddress) {
      log("Error: No target address (generate one for Node 2 first)")
      return
    }
    log(`Sending ${amount} BTC to ${targetAddress}...`)
    try {
      const res = await fetch(`${API}/send`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ address: targetAddress, amount: parseFloat(amount) })
      })
      const data = await res.json()
      if (data.txid) log(`Sent! TXID: ${data.txid}`)
      else log(`Error: ${JSON.stringify(data)}`)
      fetchInfo()
    } catch (e) { log(`Error: ${e}`) }
  }

  return (
    <div className="container">
      <h1>Bitcoin Testnet Box</h1>

      <div className="controls">
        <button onClick={startNodes}>Start Nodes</button>
        <button onClick={stopNodes}>Stop Nodes</button>
      </div>

      <div className="status-grid">
        <div className="card">
          <h2>Node 1 (Miner)</h2>
          {info?.node1 ? (
             <pre>{JSON.stringify(info.node1, null, 2)}</pre>
          ) : "Loading..."}
          <div className="actions">
            <input type="number" value={genBlocks} onChange={e => setGenBlocks(e.target.value)} />
            <button onClick={generate}>Generate Blocks</button>
            <br/>
            <button onClick={() => getAddress(1)}>Get New Address</button>
          </div>
        </div>

        <div className="card">
          <h2>Node 2</h2>
          {info?.node2 ? (
             <pre>{JSON.stringify(info.node2, null, 2)}</pre>
          ) : "Loading..."}
           <div className="actions">
             <button onClick={() => getAddress(2)}>Get New Address</button>
           </div>
        </div>
      </div>

      <div className="card">
        <h2>Transactions</h2>
        <div className="actions">
           <input type="text" placeholder="Target Address" value={targetAddress} onChange={e => setTargetAddress(e.target.value)} style={{width: '300px'}}/>
           <input type="number" placeholder="Amount" value={amount} onChange={e => setAmount(e.target.value)} />
           <button onClick={send}>Send from Node 1</button>
        </div>
      </div>

      <div className="logs">
        <h3>Logs</h3>
        {logs.map((l, i) => <div key={i}>{l}</div>)}
      </div>
    </div>
  )
}

export default App
