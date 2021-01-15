import os
import json
from datetime import datetime, timedelta


def make_ssl_cert(file_path):
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )

    name = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, 'mdb_autogen'),
        x509.NameAttribute(NameOID.COUNTRY_NAME, 'US'),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, 'California'),
        x509.NameAttribute(NameOID.LOCALITY_NAME, 'Berkeley'),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'MindsDB')
    ])

    now = datetime.utcnow()
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(1)
        .not_valid_before(now - timedelta(days=10 * 365))
        .not_valid_after(now + timedelta(days=10 * 365))
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=0),
            False
        )
        .sign(key, hashes.SHA256(), default_backend())
    )
    cert_pem = cert.public_bytes(encoding=serialization.Encoding.PEM)
    key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )

    with open(file_path, 'wb') as f:
        f.write(key_pem + cert_pem)


def gen_default_config(config_path):
    config = {
            "debug": False,
            "config_version": "1.4",
            "api": {
                'http': {
                    'host': '127.0.0.1',
                    'port': '47334'
                },
                'mysql': {
                    'host': '127.0.0.1',
                    'port': '47335',
                    'user': 'mindsdb',
                    'password': ''
                },
                'mongodb': {
                    'host': '127.0.0.1',
                    'port': '47336'
                }
            },
            "integrations": {},
            'storage_dir': storage_dir
        }

    config_path = os.path.join(config_dir, 'config.json')
    with open(config_path, 'w') as fp:
        json.dump(config, fp, indent=4, sort_keys=True)
