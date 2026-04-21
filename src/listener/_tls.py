import tempfile

import docker

from src.models.docker_host import DockerHost


def build_tls_config(host: DockerHost):
    """Build a docker.tls.TLSConfig from PEM strings stored in the DB row.

    Returns None if TLS is not enabled. Writes certs to tempfiles that are
    not cleaned up (acceptable at portfolio scale; production would manage
    tempfile lifetimes explicitly).
    """
    if not host.tls_enabled:
        return None

    def _write(pem: str) -> str:
        f = tempfile.NamedTemporaryFile(delete=False, suffix=".pem", mode="w")
        f.write(pem)
        f.close()
        return f.name

    return docker.tls.TLSConfig(
        ca_cert=_write(host.tls_ca) if host.tls_ca else None,
        client_cert=(
            (_write(host.tls_cert), _write(host.tls_key))
            if host.tls_cert and host.tls_key
            else None
        ),
        verify=True,
    )
