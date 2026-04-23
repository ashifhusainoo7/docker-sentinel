from src.services.oauth_client import oauth


def test_oauth_client_registers_google_with_correct_scope():
    google = oauth.google  # AttributeError if not registered
    assert google is not None
    assert google.client_kwargs["scope"] == "openid email profile"


def test_oauth_client_uses_google_discovery_url():
    google = oauth.google
    # Authlib 1.7.0 stores the discovery URL under _server_metadata_url.
    assert (
        google._server_metadata_url
        == "https://accounts.google.com/.well-known/openid-configuration"
    )
