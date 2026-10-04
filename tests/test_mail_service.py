from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from resources.errors import ServiceUnavailableError
from services.mail_service import send_email


def test_provider_receives_text_and_html(app, monkeypatch):
    app.config.update(MAIL_SENDER=None, SEND_GRID_KEY="test-key")
    provider = Mock()
    provider.send.return_value = SimpleNamespace(status_code=202)
    monkeypatch.setattr("services.mail_service.SendGridAPIClient", Mock(return_value=provider))
    with app.app_context():
        send_email("Subject", "sender@example.test", ["recipient@example.test"], "Text", "<p>HTML</p>")
    content = provider.send.call_args.args[0].get()["content"]
    assert content == [
        {"type": "text/plain", "value": "Text"},
        {"type": "text/html", "value": "<p>HTML</p>"},
    ]


@pytest.mark.parametrize("key,status", [(None, 202), ("test-key", 500)])
def test_missing_configuration_and_failed_delivery_are_explicit(app, monkeypatch, key, status):
    app.config.update(MAIL_SENDER=None, SEND_GRID_KEY=key)
    provider = Mock()
    provider.send.return_value = SimpleNamespace(status_code=status)
    monkeypatch.setattr("services.mail_service.SendGridAPIClient", Mock(return_value=provider))
    with app.app_context(), pytest.raises(ServiceUnavailableError):
        send_email("Subject", "sender@example.test", ["recipient@example.test"], "Text", "<p>HTML</p>")
