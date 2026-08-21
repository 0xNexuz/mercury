// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {IncidentReceipts} from "../src/IncidentReceipts.sol";

contract IncidentReceiptsTest is Test {
    IncidentReceipts private receipts;
    event IncidentRecorded(bytes32 indexed incidentId, bytes32 memoryContextHash, bytes32 decisionHash, bytes32 outcomeHash, address indexed recorder);

    function setUp() public { receipts = new IncidentReceipts(); }

    function testEmitsExactCommitments() public {
        bytes32 incidentId = keccak256("INC-104");
        bytes32 memoryHash = keccak256("memory");
        bytes32 decisionHash = keccak256("decision");
        bytes32 outcomeHash = keccak256("outcome");
        vm.expectEmit(true, false, false, true);
        emit IncidentRecorded(incidentId, memoryHash, decisionHash, outcomeHash, address(this));
        receipts.recordIncident(incidentId, memoryHash, decisionHash, outcomeHash);
    }

    function testAllowsIndependentDuplicateReceiptsForAudit() public {
        bytes32 value = keccak256("same");
        receipts.recordIncident(value, value, value, value);
        receipts.recordIncident(value, value, value, value);
    }
}

