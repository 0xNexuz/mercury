// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script} from "forge-std/Script.sol";
import {IncidentReceipts} from "../src/IncidentReceipts.sol";

contract DeployIncidentReceipts is Script {
    function run() external returns (IncidentReceipts receipts) {
        vm.startBroadcast();
        receipts = new IncidentReceipts();
        vm.stopBroadcast();
    }
}

