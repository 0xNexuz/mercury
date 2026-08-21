from __future__ import annotations

import json
import os
from typing import Any

import httpx
from Crypto.Hash import keccak

CHAIN_ID = 84532
EVENT_SIGNATURE = "IncidentRecorded(bytes32,bytes32,bytes32,bytes32,address)"


class ReceiptVerificationError(RuntimeError):
    pass


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def keccak256(value: Any) -> str:
    digest = keccak.new(digest_bits=256)
    digest.update(value if isinstance(value, bytes) else canonical_json(value))
    return "0x" + digest.hexdigest()


def commitments(incident: dict[str, Any]) -> dict[str, str | int]:
    if incident.get("status") != "resolved" or not incident.get("outcome"):
        raise ValueError("incident must be resolved before commitments are created")
    analysis = incident.get("last_analysis") or {}
    evidence_ids = analysis.get("memory_informed_decision", {}).get("memory_evidence", [])
    evidence = [item for item in analysis.get("relevant_memories", []) if item.get("incident_id") in evidence_ids]
    return {
        "version": 1,
        "chain_id": CHAIN_ID,
        "incident_id_hash": keccak256({"version": 1, "incident_id": incident["incident_id"]}),
        "memory_context_hash": keccak256({"version": 1, "memories": evidence}),
        "decision_hash": keccak256({"version": 1, "baseline": analysis.get("baseline_decision"), "informed": analysis.get("memory_informed_decision"), "policy": analysis.get("policy")}),
        "outcome_hash": keccak256({"version": 1, "outcome": incident["outcome"]}),
    }


async def verify_receipt(transaction_hash: str, expected: dict[str, Any]) -> dict[str, Any]:
    rpc_url = os.getenv("BASE_SEPOLIA_RPC_URL", "https://sepolia.base.org")
    contract = os.getenv("BASE_RECEIPTS_CONTRACT", "").lower()
    if not contract or len(contract) != 42:
        raise ReceiptVerificationError("BASE_RECEIPTS_CONTRACT is not configured")
    async with httpx.AsyncClient(timeout=15) as client:
        chain_resp = await client.post(rpc_url, json={"jsonrpc": "2.0", "id": 1, "method": "eth_chainId", "params": []})
        receipt_resp = await client.post(rpc_url, json={"jsonrpc": "2.0", "id": 2, "method": "eth_getTransactionReceipt", "params": [transaction_hash]})
    if int(chain_resp.json().get("result", "0x0"), 16) != CHAIN_ID:
        raise ReceiptVerificationError("RPC is not Base Sepolia")
    receipt = receipt_resp.json().get("result")
    if not receipt or receipt.get("status") != "0x1":
        raise ReceiptVerificationError("transaction is missing, pending, or failed")
    if receipt.get("to", "").lower() != contract:
        raise ReceiptVerificationError("transaction target does not match the configured contract")
    event_topic = keccak256(EVENT_SIGNATURE.encode())
    matching = [log for log in receipt.get("logs", []) if log.get("address", "").lower() == contract and log.get("topics", [""])[0].lower() == event_topic]
    if not matching:
        raise ReceiptVerificationError("IncidentRecorded event was not emitted")
    log = matching[0]
    topics = log["topics"]
    data = log["data"][2:]
    actual = {"incident_id_hash": topics[1].lower(), "memory_context_hash": "0x" + data[0:64].lower(), "decision_hash": "0x" + data[64:128].lower(), "outcome_hash": "0x" + data[128:192].lower()}
    for key, value in actual.items():
        if value != str(expected[key]).lower():
            raise ReceiptVerificationError(f"{key} does not match the resolved incident")
    return {"status": "VERIFIED", "network": "Base Sepolia", "chain_id": CHAIN_ID, "contract_address": contract, "transaction_hash": transaction_hash, "block_number": int(receipt["blockNumber"], 16), **actual}

