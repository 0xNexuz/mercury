# Base incident receipts

`contracts/src/IncidentReceipts.sol` emits four `bytes32` commitments plus the operator address. It stores no sensitive incident data and imposes no unnecessary ownership or registry state.

After resolution, FastAPI computes Keccak-256 over versioned, canonical JSON for:

- incident ID;
- the exact retrieved memory snapshots used;
- baseline/informed decisions and policy result;
- final outcome.

The connected operator wallet calls `recordIncident` on Base Sepolia (`84532`) using wagmi/viem. The backend only displays `VERIFIED` after fetching the receipt, checking the chain, success status, configured contract address, event signature, and all four decoded commitments.

Configure `BASE_RECEIPTS_CONTRACT` and `NEXT_PUBLIC_BASE_RECEIPTS_CONTRACT` to the same deployed address. Without them, the UI truthfully displays `NOT ANCHORED`.

Deploy with Foundry after funding the operator/deployer wallet with Base Sepolia ETH:

```bash
cd contracts
forge install foundry-rs/forge-std --no-git
forge script script/Deploy.s.sol:DeployIncidentReceipts --rpc-url base_sepolia --broadcast
```

