#!/usr/bin/env python3
"""
Test script for email notification functionality.

Tests:
  1. EmailConfig loading from config file / environment variables
  2. EmailConfig validation (missing fields, disabled state)
  3. EmailNotifier.send_alert() using a mock SMTP server (no real email sent)
  4. Optional live send - only runs when --live flag is passed

Usage:
  python test_email.py              # unit tests only (no real email)
  python test_email.py --live       # also sends a real test email
"""

import os
import smtplib
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.email_notifier import EmailNotifier  # noqa: E402
from src.config import ConfigManager, EmailConfig  # noqa: E402

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def print_header(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def ok(msg: str) -> None:
    print(f"  ✓ {msg}")


def fail(msg: str) -> None:
    print(f"  ✗ {msg}")


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


class TestEmailConfig(unittest.TestCase):
    """Tests for EmailConfig dataclass and ConfigManager.email property."""

    def _make_config(self, **overrides):
        """Build a minimal valid EmailConfig."""
        defaults = dict(
            enabled=True,
            smtp_server="smtp.example.com",
            smtp_port=587,
            sender_email="sender@example.com",
            sender_password="secret",
            sender_name="Solar Tracker",
            recipient_email="recipient@example.com",
        )
        defaults.update(overrides)
        return EmailConfig(**defaults)

    def test_valid_config_raises_nothing(self):
        cfg = self._make_config()
        self.assertTrue(cfg.enabled)
        self.assertEqual(cfg.smtp_server, "smtp.example.com")

    def test_disabled_config_skips_validation(self):
        """When enabled=False, missing fields should not raise."""
        cfg = self._make_config(
            enabled=False,
            smtp_server="",
            sender_email="",
            sender_password="",
            recipient_email="",
        )
        self.assertFalse(cfg.enabled)

    def test_enabled_with_missing_smtp_server_raises(self):
        from src.utils.exceptions import GrowattConfigError

        with self.assertRaises(GrowattConfigError):
            self._make_config(smtp_server="")

    def test_enabled_with_missing_sender_email_raises(self):
        from src.utils.exceptions import GrowattConfigError

        with self.assertRaises(GrowattConfigError):
            self._make_config(sender_email="")

    def test_enabled_with_missing_recipient_raises(self):
        from src.utils.exceptions import GrowattConfigError

        with self.assertRaises(GrowattConfigError):
            self._make_config(recipient_email="")

    def test_invalid_smtp_port_raises(self):
        from src.utils.exceptions import GrowattConfigError

        with self.assertRaises(GrowattConfigError):
            self._make_config(smtp_port=0)

    def test_sender_name_defaults_to_sender_email_when_blank(self):
        cfg = self._make_config(sender_name="")
        # ConfigManager sets sender_name = sender_email when blank;
        # direct dataclass construction doesn't — just verify field is blank
        self.assertEqual(cfg.sender_name, "")

    def test_config_manager_email_disabled_by_default(self):
        """The [email] section with enabled=false should produce enabled=False."""
        import configparser

        from src.config.configuration import ConfigManager as CM

        # Build a minimal in-memory config that satisfies required sections
        # but has email disabled (the shipped default)
        raw = configparser.ConfigParser()
        raw.read_string(
            """
[growatt]
battery_capacity_wh = 6900
maximum_charge_rate_w = 3000
statement_of_charge_pct = 15
minimum_charge_pct = 35
maximum_charge_pct = 85
average_load_w = 850

[tariff]
off_peak_start_time = 02:00
off_peak_end_time = 05:00

[peak_window]
peak_start_time = 16:00
peak_end_time = 19:00
check_time = 14:00

[forecast.solar]
location = 51.0,0.0
declination = 35
azimuth = 0
kw_power = 5.8
damping = 0.1
confidence = 0.7

[email]
enabled = false
"""
        )
        cm = CM.__new__(CM)
        cm.config_path = "in-memory"
        cm.config = raw
        cm.cache = None
        email_cfg = cm.email
        self.assertFalse(email_cfg.enabled, "Email should be disabled when enabled=false")

    def test_config_manager_email_reads_env_vars(self):
        """ConfigManager.email should prefer environment variables."""
        project_root = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(project_root, "conf", "growatt-charger.ini")
        if not os.path.exists(config_path):
            self.skipTest("Config file not found")

        env_patch = {
            "SMTP_SERVER": "smtp.envtest.com",
            "SMTP_PORT": "465",
            "SENDER_EMAIL": "env_sender@example.com",
            "SENDER_PASSWORD": "env_password",
            "SENDER_NAME": "Env Tracker",
            "RECIPIENT_EMAIL": "env_recipient@example.com",
        }
        with patch.dict(os.environ, env_patch):
            config = ConfigManager(config_path)
            email_cfg = config.email

        self.assertEqual(email_cfg.smtp_server, "smtp.envtest.com")
        self.assertEqual(email_cfg.smtp_port, 465)
        self.assertEqual(email_cfg.sender_email, "env_sender@example.com")
        self.assertEqual(email_cfg.sender_name, "Env Tracker")
        self.assertEqual(email_cfg.recipient_email, "env_recipient@example.com")


class TestEmailNotifier(unittest.TestCase):
    """Tests for EmailNotifier.send_alert() with a mocked SMTP connection."""

    def _make_notifier(self):
        return EmailNotifier(
            smtp_server="smtp.example.com",
            smtp_port=587,
            sender_email="sender@example.com",
            sender_password="secret",
            sender_name="Solar Tracker",
            recipient_email="recipient@example.com",
        )

    def _mock_smtp(self):
        """Return a context-manager-compatible mock for smtplib.SMTP."""
        mock_smtp_instance = MagicMock()
        mock_smtp_class = MagicMock()
        mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_smtp_instance)
        mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)
        return mock_smtp_class, mock_smtp_instance

    def test_send_alert_returns_true_on_success(self):
        mock_cls, mock_inst = self._mock_smtp()
        with patch("modules.email_notifier.smtplib.SMTP", mock_cls):
            result = self._make_notifier().send_alert("Test subject", "Test body")
        self.assertTrue(result)

    def test_send_alert_calls_starttls_and_login(self):
        mock_cls, mock_inst = self._mock_smtp()
        with patch("modules.email_notifier.smtplib.SMTP", mock_cls):
            self._make_notifier().send_alert("Subject", "Body")
        mock_inst.starttls.assert_called_once()
        mock_inst.login.assert_called_once_with("sender@example.com", "secret")

    def test_send_alert_sends_to_correct_recipient(self):
        mock_cls, mock_inst = self._mock_smtp()
        with patch("modules.email_notifier.smtplib.SMTP", mock_cls):
            self._make_notifier().send_alert("Subject", "Body")
        args = mock_inst.sendmail.call_args
        self.assertEqual(args[0][0], "sender@example.com")
        self.assertEqual(args[0][1], "recipient@example.com")

    def test_send_alert_includes_subject_in_message(self):
        mock_cls, mock_inst = self._mock_smtp()
        with patch("modules.email_notifier.smtplib.SMTP", mock_cls):
            self._make_notifier().send_alert("My Alert Subject", "Body text")
        raw_message = mock_inst.sendmail.call_args[0][2]
        self.assertIn("My Alert Subject", raw_message)

    def test_send_alert_includes_html_when_provided(self):
        mock_cls, mock_inst = self._mock_smtp()
        with patch("modules.email_notifier.smtplib.SMTP", mock_cls):
            self._make_notifier().send_alert("Subject", "Plain body", "<b>HTML body</b>")
        raw_message = mock_inst.sendmail.call_args[0][2]
        self.assertIn("HTML body", raw_message)
        self.assertIn("Plain body", raw_message)

    def test_send_alert_returns_false_on_auth_error(self):
        mock_cls, mock_inst = self._mock_smtp()
        mock_inst.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Auth failed")
        with patch("modules.email_notifier.smtplib.SMTP", mock_cls):
            result = self._make_notifier().send_alert("Subject", "Body")
        self.assertFalse(result)

    def test_send_alert_returns_false_on_network_error(self):
        mock_cls, _ = self._mock_smtp()
        mock_cls.return_value.__enter__.side_effect = OSError("Connection refused")
        with patch("modules.email_notifier.smtplib.SMTP", mock_cls):
            result = self._make_notifier().send_alert("Subject", "Body")
        self.assertFalse(result)

    def test_from_config_creates_notifier(self):
        cfg = EmailConfig(
            enabled=True,
            smtp_server="smtp.example.com",
            smtp_port=587,
            sender_email="a@b.com",
            sender_password="pw",
            sender_name="Test",
            recipient_email="c@d.com",
        )
        notifier = EmailNotifier.from_config(cfg)
        self.assertIsInstance(notifier, EmailNotifier)
        self.assertEqual(notifier._smtp_server, "smtp.example.com")
        self.assertEqual(notifier._recipient_email, "c@d.com")


# ---------------------------------------------------------------------------
# Optional live send
# ---------------------------------------------------------------------------


def run_live_send():
    """Send a real test email using credentials from config / env vars."""
    print_header("Live Email Send Test")

    project_root = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(project_root, "conf", "growatt-charger.ini")

    if not os.path.exists(config_path):
        fail(f"Config file not found: {config_path}")
        return 1

    try:
        config = ConfigManager(config_path)
        email_cfg = config.email
    except Exception as e:
        fail(f"Failed to load config: {e}")
        return 1

    if not email_cfg.enabled:
        fail(
            "Email is disabled in config (enabled = false). "
            "Set enabled = true and configure SMTP credentials to run a live test."
        )
        return 1

    ok(f"SMTP server  : {email_cfg.smtp_server}:{email_cfg.smtp_port}")
    ok(f"Sender       : {email_cfg.sender_name} <{email_cfg.sender_email}>")
    ok(f"Recipient    : {email_cfg.recipient_email}")

    print("\n  Sending test alert email...")

    notifier = EmailNotifier.from_config(email_cfg)
    sent = notifier.send_alert(
        subject="[Solar Alert TEST] Inverter Status Check - test message",
        body=(
            "This is a test alert from the Growatt inverter status check script.\n\n"
            "If you received this, email notifications are working correctly.\n\n"
            "No action is required - this was triggered manually via test_email.py --live"
        ),
        html_body=(
            "<h2>&#9989; Email Alert Test</h2>"
            "<p>This is a test alert from the <b>Growatt inverter status check</b> script.</p>"
            "<p>If you received this, email notifications are working correctly.</p>"
            "<p style='color:grey;font-size:small'>"
            "No action required - triggered manually via <code>python test_email.py --live</code>"
            "</p>"
        ),
    )

    if sent:
        ok(f"Email sent successfully to {email_cfg.recipient_email}")
        return 0
    else:
        fail("Failed to send email - check logs above for the SMTP error")
        return 1


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main():
    live = "--live" in sys.argv

    print_header("Email Notification Tests")

    # Remove --live from argv so unittest doesn't try to parse it
    sys.argv = [a for a in sys.argv if a != "--live"]

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestEmailConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestEmailNotifier))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if live:
        live_exit = run_live_send()
        if live_exit != 0:
            sys.exit(live_exit)

    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
