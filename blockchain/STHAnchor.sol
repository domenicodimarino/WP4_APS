// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// @title STHAnchor
/// @notice Ancora on-chain i Signed Tree Head (STH) del Bulletin Board del
///         protocollo di voto. Una volta scritta, la radice di Merkle e' resa
///         immutabile e timestamp-ata dalla blockchain: nessun insider puo'
///         riscrivere retroattivamente il registro senza che la discordanza
///         tra root on-chain e BB ricalcolato sia pubblicamente rilevabile.
///         Rafforza "Integrita' registro post-chiusura" e "Verificabilita'
///         Universale" della tabella WP3.
contract STHAnchor {
    struct Anchor {
        uint256 n;        // numero di foglie (voti) committate
        uint256 ts;       // timestamp dello STH (lato Urna)
        bytes32 root;     // radice di Merkle del Bulletin Board
        bytes32 sigHash;  // SHA-256 della firma RSA-PSS dell'Urna (fingerprint)
        uint256 blockTs;  // timestamp del blocco (timestamp on-chain)
    }

    address public owner;          // account dell'Urna (unico autorizzato)
    Anchor[] public anchors;

    event STHAnchored(uint256 indexed index, uint256 n, bytes32 root);

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Solo l'Urna puo' ancorare");
        _;
    }

    /// @notice Ancora un nuovo STH. Append-only: non esiste funzione di modifica.
    function anchorSTH(uint256 n, uint256 ts, bytes32 root, bytes32 sigHash)
        external
        onlyOwner
    {
        anchors.push(Anchor(n, ts, root, sigHash, block.timestamp));
        emit STHAnchored(anchors.length - 1, n, root);
    }

    function count() external view returns (uint256) {
        return anchors.length;
    }

    /// @notice Ritorna la radice dell'ultimo STH ancorato (per verifica universale).
    function latestRoot() external view returns (bytes32) {
        require(anchors.length > 0, "Nessun STH ancorato");
        return anchors[anchors.length - 1].root;
    }
}
