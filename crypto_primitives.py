"""
Primitive crittografiche del WP4.

Tutte le primitive replicano fedelmente quelle viste nei laboratori del corso:
  - RSA-2048 OAEP(MGF1-SHA256) e PSS(salt MAX_LENGTH, SHA-256)  -> Lab 2 (1_authenticated_encryption_rsa.py)
  - AES-256-CBC + PKCS#7(128)                                   -> Lab 1 / 3_padding_oracle.py
  - HMAC-SHA256                                                 -> Lab 1
  - SHA-256                                                     -> 0_merkle_tree.py

Nessuna primitiva avanzata fuori programma. La sicurezza dipende solo dalla
segretezza delle chiavi (Kerckhoffs).
"""
from __future__ import annotations

import os

from cryptography.hazmat.primitives import hashes, hmac, serialization
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7

RSA_KEY_SIZE = 2048
SYM_KEY_LEN = 32   # AES-256
IV_LEN = 16        # blocco AES
BLOCK_BITS = 128

# ---------------------------------------------------------------------------
# RSA: generazione, OAEP, PSS  (identici al Lab 2)
# ---------------------------------------------------------------------------

def generate_keypair():
    """Gen(1^n): genera una coppia RSA-2048 (e = 65537)."""
    sk = rsa.generate_private_key(public_exponent=65537, key_size=RSA_KEY_SIZE)
    return sk, sk.public_key()


def rsa_encrypt(public_key, plaintext: bytes) -> bytes:
    """E_pk(.) — RSA-OAEP. Cifra k_enc||k_mac per la Commissione (C_key)."""
    return public_key.encrypt(
        plaintext,
        asym_padding.OAEP(
            mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )


def rsa_decrypt(private_key, ciphertext: bytes) -> bytes:
    """D_sk(.) — RSA-OAEP. Usata dalla Commissione in Fase 4."""
    return private_key.decrypt(
        ciphertext,
        asym_padding.OAEP(
            mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )


def rsa_sign(private_key, data: bytes) -> bytes:
    """Sign_sk(.) — RSA-PSS su SHA-256. IdP (Token) e Urna (ricevuta/STH)."""
    return private_key.sign(
        data,
        asym_padding.PSS(
            mgf=asym_padding.MGF1(hashes.SHA256()),
            salt_length=asym_padding.PSS.MAX_LENGTH,
        ),
        hashes.SHA256(),
    )


def rsa_verify(public_key, data: bytes, signature: bytes) -> bool:
    """Verify_pk(.) — verifica RSA-PSS. Ritorna True/False senza sollevare."""
    try:
        public_key.verify(
            signature,
            data,
            asym_padding.PSS(
                mgf=asym_padding.MGF1(hashes.SHA256()),
                salt_length=asym_padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# AES-256-CBC + PKCS#7  (identico a 3_padding_oracle.py)
# ---------------------------------------------------------------------------

def aes_cbc_encrypt(k_enc: bytes, iv: bytes, plaintext: bytes) -> bytes:
    """E_{k_enc}(IV, V) -> C_sym. AES-256-CBC con padding PKCS#7."""
    padder = PKCS7(BLOCK_BITS).padder()
    padded = padder.update(plaintext) + padder.finalize()
    enc = Cipher(algorithms.AES(k_enc), modes.CBC(iv)).encryptor()
    return enc.update(padded) + enc.finalize()


def aes_cbc_decrypt(k_enc: bytes, iv: bytes, ciphertext: bytes) -> bytes:
    """D_{k_enc}(IV, C_sym) -> V. Esegue l'unpad PKCS#7 (puo' sollevare ValueError).

    NB: nel protocollo questo passo viene raggiunto SOLO dopo che l'HMAC e'
    stato verificato (Encrypt-then-MAC), per cui l'unpad non e' mai un oracle.
    """
    dec = Cipher(algorithms.AES(k_enc), modes.CBC(iv)).decryptor()
    raw = dec.update(ciphertext) + dec.finalize()
    unpadder = PKCS7(BLOCK_BITS).unpadder()
    return unpadder.update(raw) + unpadder.finalize()


# ---------------------------------------------------------------------------
# HMAC-SHA256 e SHA-256
# ---------------------------------------------------------------------------

def hmac_sha256(k_mac: bytes, data: bytes) -> bytes:
    """T = HMAC-SHA256_{k_mac}(data). data = IV || C_sym."""
    h = hmac.HMAC(k_mac, hashes.SHA256())
    h.update(data)
    return h.finalize()


def hmac_verify(k_mac: bytes, data: bytes, tag: bytes) -> bool:
    """Verifica del tag in tempo costante (h.verify usa confronto sicuro)."""
    h = hmac.HMAC(k_mac, hashes.SHA256())
    h.update(data)
    try:
        h.verify(tag)
        return True
    except Exception:
        return False


def sha256(data: bytes) -> bytes:
    """H(.) — SHA-256, output 32 byte."""
    d = hashes.Hash(hashes.SHA256())
    d.update(data)
    return d.finalize()


def sha256_hex(data: bytes) -> str:
    return sha256(data).hex()


# ---------------------------------------------------------------------------
# Utilita': entropia, serializzazione chiavi
# ---------------------------------------------------------------------------

def random_bytes(n: int) -> bytes:
    return os.urandom(n)


def pubkey_to_pem(public_key) -> bytes:
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def privkey_to_pem(private_key) -> bytes:
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def pem_to_pubkey(pem: bytes):
    return serialization.load_pem_public_key(pem)


def pem_to_privkey(pem: bytes):
    return serialization.load_pem_private_key(pem, password=None)
