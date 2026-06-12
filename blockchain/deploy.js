// Deploy di STHAnchor su Ganache. Fedele a deploy.js del Lab 5.
// L'URL di Ganache e' configurabile via env GANACHE_URL.
// (Nel Lab era http://172.27.0.1:7545 — IP WSL; default qui 127.0.0.1:7545.)
const { Web3 } = require('web3');
const fs = require('fs');
const path = require('path');

const GANACHE_URL = process.env.GANACHE_URL || 'http://127.0.0.1:7545';
const web3 = new Web3(GANACHE_URL);

async function deploy() {
    const abi = JSON.parse(fs.readFileSync(path.join(__dirname, 'STHAnchorAbi.json'), 'utf8'));
    const bytecode = fs.readFileSync(path.join(__dirname, 'STHAnchorBytecode.bin'), 'utf8');

    const accounts = await web3.eth.getAccounts();
    const deployer = accounts[0]; // l'account dell'Urna

    console.log('Deploy da account (Urna):', deployer);

    const contract = new web3.eth.Contract(abi);
    const deployed = await contract
        .deploy({ data: '0x' + bytecode })
        .send({ from: deployer, gas: 1500000, gasPrice: '30000000000' });

    console.log('STHAnchor deployato a:', deployed.options.address);
    // Salva l'indirizzo per anchor.js
    fs.writeFileSync(path.join(__dirname, 'deployed_address.txt'), deployed.options.address);
}

deploy().catch(err => console.error('Deploy fallito:', err));
