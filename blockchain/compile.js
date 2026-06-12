// Compilazione del contratto STHAnchor.
// Struttura fedele a compile.js del Lab 5 (solc + outputSelection, evmVersion paris).
const solc = require('solc');
const path = require('path');
const fs = require('fs');

const contractName = 'STHAnchor';
const fileName = `${contractName}.sol`;

const contractPath = path.join(__dirname, fileName);
const sourceCode = fs.readFileSync(contractPath, 'utf8');

const input = {
    language: 'Solidity',
    sources: { [fileName]: { content: sourceCode } },
    settings: {
        evmVersion: 'paris',
        outputSelection: { '*': { '*': ['*'] } },
    },
};

const compiled = JSON.parse(solc.compile(JSON.stringify(input)));

if (compiled.errors) {
    compiled.errors.forEach(e => console.log(e.formattedMessage));
}

const bytecode = compiled.contracts[fileName][contractName].evm.bytecode.object;
const abi = compiled.contracts[fileName][contractName].abi;

fs.writeFileSync(path.join(__dirname, 'STHAnchorBytecode.bin'), bytecode);
fs.writeFileSync(path.join(__dirname, 'STHAnchorAbi.json'), JSON.stringify(abi, null, '\t'));

console.log('Bytecode e ABI di STHAnchor generati.');
