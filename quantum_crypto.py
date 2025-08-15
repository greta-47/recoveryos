import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime
import numpy as np
import hashlib
import secrets
from dataclasses import dataclass
from enum import Enum
import json

logger = logging.getLogger("recoveryos")


class QuantumAlgorithm(Enum):
    KYBER = "kyber"  # Lattice-based KEM
    DILITHIUM = "dilithium"  # Lattice-based signatures
    SPHINCS = "sphincs"  # Hash-based signatures
    NTRU = "ntru"  # Lattice-based encryption


@dataclass
class QuantumKeyPair:
    algorithm: QuantumAlgorithm
    public_key: bytes
    private_key: bytes
    key_id: str
    created_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "algorithm": self.algorithm.value,
            "public_key": self.public_key.hex(),
            "key_id": self.key_id,
            "created_at": self.created_at.isoformat() + "Z",
            "key_size": len(self.public_key),
        }


class LatticeBasedCrypto:
    def __init__(self, dimension: int = 512, modulus: int = 3329):
        self.dimension = dimension
        self.modulus = modulus
        self.noise_bound = 2

    def generate_lattice_keypair(self) -> Tuple[np.ndarray, np.ndarray]:
        A = np.random.randint(0, self.modulus, (self.dimension, self.dimension))
        s = np.random.randint(-self.noise_bound, self.noise_bound + 1, self.dimension)
        e = np.random.randint(-self.noise_bound, self.noise_bound + 1, self.dimension)
        b = (A @ s + e) % self.modulus

        public_key = np.concatenate([A.flatten(), b])
        private_key = s

        return public_key, private_key

    def encrypt_lattice(self, public_key: np.ndarray, message: bytes) -> bytes:
        A_flat = public_key[: -self.dimension]
        A = A_flat.reshape(self.dimension, self.dimension)
        b = public_key[-self.dimension :]

        r = np.random.randint(-self.noise_bound, self.noise_bound + 1, self.dimension)
        e1 = np.random.randint(-self.noise_bound, self.noise_bound + 1, self.dimension)
        e2 = np.random.randint(-self.noise_bound, self.noise_bound + 1)

        m = int.from_bytes(message[:4].ljust(4, b"\x00"), "big") % (self.modulus // 2)

        u = (A.T @ r + e1) % self.modulus
        v = (b @ r + e2 + m * (self.modulus // 2)) % self.modulus

        ciphertext = np.concatenate([u, [v]]).astype(np.int32).tobytes()
        return ciphertext

    def decrypt_lattice(self, private_key: np.ndarray, ciphertext: bytes) -> bytes:
        ct_array = np.frombuffer(ciphertext, dtype=np.int32)
        u = ct_array[:-1]
        v = ct_array[-1]

        m_prime = (v - private_key @ u) % self.modulus

        if m_prime > self.modulus // 2:
            m_prime -= self.modulus

        m = int(round(m_prime / (self.modulus // 2))) % 256
        return m.to_bytes(1, "big")


class QuantumResistantCrypto:
    def __init__(self):
        self.lattice_crypto = LatticeBasedCrypto()
        self.key_store: Dict[str, QuantumKeyPair] = {}
        self.encryption_log: List[Dict[str, Any]] = []

    def generate_keypair(
        self, algorithm: QuantumAlgorithm = QuantumAlgorithm.KYBER
    ) -> str:
        public_key, private_key = self.lattice_crypto.generate_lattice_keypair()
        public_key_bytes = public_key.astype(np.int32).tobytes()
        private_key_bytes = private_key.astype(np.int32).tobytes()

        key_id = hashlib.sha256(public_key_bytes).hexdigest()[:16]

        keypair = QuantumKeyPair(
            algorithm=algorithm,
            public_key=public_key_bytes,
            private_key=private_key_bytes,
            key_id=key_id,
            created_at=datetime.utcnow(),
        )

        self.key_store[key_id] = keypair
        logger.info(
            f"Generated quantum-resistant keypair | Algorithm={algorithm.value} | KeyID={key_id}"
        )

        return key_id

    def encrypt(
        self, key_id: str, plaintext: Union[str, bytes]
    ) -> Optional[Dict[str, Any]]:
        if key_id not in self.key_store:
            logger.error(f"Key not found | KeyID={key_id}")
            return None

        keypair = self.key_store[key_id]

        if isinstance(plaintext, str):
            plaintext = plaintext.encode("utf-8")

        try:
            public_key = np.frombuffer(keypair.public_key, dtype=np.int32)
            ciphertext = self.lattice_crypto.encrypt_lattice(public_key, plaintext)

            result = {
                "key_id": key_id,
                "algorithm": keypair.algorithm.value,
                "ciphertext": ciphertext.hex(),
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }

            self.encryption_log.append(
                {
                    "operation": "encrypt",
                    "key_id": key_id,
                    "data_size": len(plaintext),
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }
            )

            return result

        except Exception as e:
            logger.error(f"Quantum encryption failed | Error={str(e)}")
            return None

    def decrypt(self, key_id: str, ciphertext_hex: str) -> Optional[bytes]:
        if key_id not in self.key_store:
            logger.error(f"Key not found | KeyID={key_id}")
            return None

        keypair = self.key_store[key_id]

        try:
            private_key = np.frombuffer(keypair.private_key, dtype=np.int32)
            ciphertext = bytes.fromhex(ciphertext_hex)
            plaintext = self.lattice_crypto.decrypt_lattice(private_key, ciphertext)

            self.encryption_log.append(
                {
                    "operation": "decrypt",
                    "key_id": key_id,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }
            )

            return plaintext

        except Exception as e:
            logger.error(f"Quantum decryption failed | Error={str(e)}")
            return None


def create_quantum_crypto() -> QuantumResistantCrypto:
    return QuantumResistantCrypto()
