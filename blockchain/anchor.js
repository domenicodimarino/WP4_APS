// Ancora on-chain lo STH finale prodotto dalla simulazione Python e lo rilegge.
// Pattern fedele a interact.js del Lab 5 (web3 + contract.methods).
//
// Prerequisito: run_election.py ha scritto blockchain/sth_final.json e
// deploy.js ha scritto deployed_address.txt.
const { Web3 } = require('web3');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const GANACHE_URL = process.env.GANACHE_URL || 'http://127.0.0.1:7545';
const web3 = new Web3(GANACHE_URL);

async function anchor() {
    const abi = JSON.parse(fs.readFileSync(path.join(__dirname, 'STHAnchorAbi.json'), 'utf8'));
    const address = fs.readFileSync(path.join(__dirname, 'deployed_address.txt'), 'utf8').trim();
    const sth = JSON.parse(fs.readFileSync(path.join(__dirname, 'sth_final.json'), 'utf8'));

    const accounts = await web3.eth.getAccounts();
    const urna = accounts[0];
    const contract = new web3.eth.Contract(abi, address);

    const root = '0x' + sth.root;                                   // bytes32
    const sigHash = '0x' + crypto.createHash('sha256')              // fingerprint firma
        .update(Buffer.from(sth.sig, 'hex')).digest('hex');

    console.log('Ancoraggio STH:', { n: sth.n, ts: sth.ts, root });
    await contract.methods
        .anchorSTH(sth.n, sth.ts, root, sigHash)
        .send({ from: urna, gas: 300000 });
    console.log('STH ancorato on-chain.');

    // Rilettura per verifica universale
    const onchainRoot = await contract.methods.latestRoot().call();
    const count = await contract.methods.count().call();
    console.log('Root on-chain:', onchainRoot);
    console.log('Coerenza root locale == on-chain:', onchainRoot.toLowerCase() === root.toLowerCase());
    console.log('STH ancorati totali:', count.toString());
}

anchor().catch(err => console.error('Anchoring fallito:', err));
