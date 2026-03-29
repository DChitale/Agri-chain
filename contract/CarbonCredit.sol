// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title CarbonCredit
 * @dev Solidity contract for managing carbon credits based on verified SOC (Soil Organic Carbon) data.
 */
contract CarbonCredit {
    address public oracle;
    
    struct FarmData {
        uint256 timestamp;
        uint256 socPercentage; // SOC percentage (scaled, e.g., 250 = 2.50%)
        bytes32 dataHash;      // SHA-256 hash of the daily raw data
        uint256 carbonCredits; // Issued credits
    }

    mapping(string => FarmData[]) public farmRecords; // Maps "node_id" to their records
    mapping(string => uint256) public totalCredits;   // Maps "node_id" to total accrued credits

    event DataAttested(string nodeId, uint256 socPercentage, uint256 creditsIssued, bytes32 dataHash);

    modifier onlyOracle() {
        require(msg.sender == oracle, "Only the authorized oracle can submit data");
        _;
    }

    constructor() {
        // The deployer of the contract becomes the authorized oracle
        oracle = msg.sender;
    }

    /**
     * @dev Oracle submits daily SOC data. The contract simple calculation mints credits 
     *      based on SOC percentage thresholds.
     */
    function attestData(string memory nodeId, uint256 socPercentage, bytes32 dataHash) external onlyOracle {
        uint256 creditsToIssue = 0;

        // Example logic: if SOC > 3.00% (represented as 300), issue 1 credit. 
        // If SOC > 5.00% (represented as 500), issue 2 credits.
        if (socPercentage > 500) {
            creditsToIssue = 2;
        } else if (socPercentage > 300) {
            creditsToIssue = 1;
        }

        farmRecords[nodeId].push(FarmData({
            timestamp: block.timestamp,
            socPercentage: socPercentage,
            dataHash: dataHash,
            carbonCredits: creditsToIssue
        }));

        totalCredits[nodeId] += creditsToIssue;

        emit DataAttested(nodeId, socPercentage, creditsToIssue, dataHash);
    }

    /**
     * @dev Gets the total number of records for a specific node
     */
    function getRecordCount(string memory nodeId) external view returns (uint256) {
        return farmRecords[nodeId].length;
    }
}
