// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract CarbonCredit is ERC721, Ownable {

    uint256 private _tokenIdCounter;

    struct CreditData {
        string  nodeId;
        uint256 timestamp;
        int256  socPercent;    // scaled x1000 (e.g. 1250 = 1.250%)
        int256  previousSoc;
        bytes32 dataHash;
        uint256 co2Tonnes;     // scaled x1000
    }

    mapping(uint256 => CreditData) public credits;
    mapping(address => bool)       public registeredDevices;
    mapping(address => int256)     public lastSOC;

    event CreditMinted(uint256 indexed tokenId, address indexed farmer, uint256 co2Tonnes);
    event DeviceRegistered(address indexed device);

    constructor() ERC721("AgriChain Carbon Credit", "AGCC") Ownable(msg.sender) {}

    function registerDevice(address device) external onlyOwner {
        registeredDevices[device] = true;
        emit DeviceRegistered(device);
    }

    function verify(
        bytes32 dataHash,
        bytes memory signature,
        address device
    ) public pure returns (bool) {
        bytes32 ethHash = keccak256(abi.encodePacked("\x19Ethereum Signed Message:\n32", dataHash));
        (bytes32 r, bytes32 s, uint8 v) = splitSignature(signature);
        return ecrecover(ethHash, v, r, s) == device;
    }

    function mint(
        address farmer,
        address device,
        string  memory nodeId,
        int256  socPercent,
        bytes32 dataHash,
        bytes   memory signature
    ) external {
        require(registeredDevices[device], "Device not registered");
        require(verify(dataHash, signature, device), "Invalid signature");

        int256 prevSoc = lastSOC[device];
        require(socPercent > prevSoc, "SOC has not increased");

        // CO2 = SOC increase * 10000 kg/ha simplified factor, scaled x1000
        uint256 co2 = uint256((socPercent - prevSoc) * 10);

        uint256 tokenId = _tokenIdCounter++;
        _safeMint(farmer, tokenId);

        credits[tokenId] = CreditData({
            nodeId:      nodeId,
            timestamp:   block.timestamp,
            socPercent:  socPercent,
            previousSoc: prevSoc,
            dataHash:    dataHash,
            co2Tonnes:   co2
        });

        lastSOC[device] = socPercent;
        emit CreditMinted(tokenId, farmer, co2);
    }

    function splitSignature(bytes memory sig) internal pure returns (bytes32 r, bytes32 s, uint8 v) {
        require(sig.length == 65, "Invalid signature length");
        assembly {
            r := mload(add(sig, 32))
            s := mload(add(sig, 64))
            v := byte(0, mload(add(sig, 96)))
        }
    }
}