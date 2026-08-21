// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title MERCURY incident decision receipts
/// @notice Emits tamper-evident commitments only. No incident details are stored on-chain.
contract IncidentReceipts {
    event IncidentRecorded(
        bytes32 indexed incidentId,
        bytes32 memoryContextHash,
        bytes32 decisionHash,
        bytes32 outcomeHash,
        address indexed recorder
    );

    function recordIncident(
        bytes32 incidentId,
        bytes32 memoryContextHash,
        bytes32 decisionHash,
        bytes32 outcomeHash
    ) external {
        emit IncidentRecorded(incidentId, memoryContextHash, decisionHash, outcomeHash, msg.sender);
    }
}

