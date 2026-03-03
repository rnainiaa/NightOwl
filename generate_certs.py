#!/usr/bin/env python3
"""
Générateur de certificats SSL auto-signés pour NightOwl
"""

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from datetime import datetime, timedelta
import os

def generate_self_signed_cert():
    """Génère un certificat SSL auto-signé"""
    
    # Création de la clé privée
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    # Création du sujet (émetteur et destinataire identiques pour auto-signé)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "FR"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Ile-de-France"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Paris"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "NightOwl Test"),
        x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
    ])
    
    # Création du certificat
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.utcnow()
    ).not_valid_after(
        datetime.utcnow() + timedelta(days=365)
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName("localhost"),
            x509.DNSName("127.0.0.1"),
        ]),
        critical=False,
    ).sign(private_key, hashes.SHA256(), default_backend())
    
    return private_key, cert

def save_certificates():
    """Sauvegarde les certificats dans les fichiers"""
    
    # Création du répertoire certs s'il n'existe pas
    os.makedirs("certs", exist_ok=True)
    
    # Génération des certificats
    private_key, cert = generate_self_signed_cert()
    
    # Sauvegarde de la clé privée
    with open("certs/server.key", "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    
    # Sauvegarde du certificat
    with open("certs/server.crt", "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    
    print("✅ Certificats générés avec succès:")
    print("   - certs/server.key (clé privée)")
    print("   - certs/server.crt (certificat)")
    print("\n⚠️  Ces certificats sont auto-signés et destinés au développement uniquement")

if __name__ == "__main__":
    save_certificates()