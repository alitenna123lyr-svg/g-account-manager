"""
Tests for the import service.
"""

import pytest

from src.services.import_service import ImportService


class TestImportService:
    """Tests for ImportService."""

    @pytest.fixture
    def import_service(self) -> ImportService:
        """Create an import service instance."""
        return ImportService()

    def test_detect_separator_four_dashes(self, import_service):
        """Test detection of ---- separator."""
        lines = [
            "email1@test.com----pass1----backup@test.com----SECRET1",
            "email2@test.com----pass2----backup2@test.com----SECRET2",
        ]
        sep = import_service.detect_separator(lines)
        assert sep == "----"

    def test_detect_separator_three_dashes(self, import_service):
        """Test detection of --- separator."""
        lines = [
            "email1@test.com---pass1---backup@test.com---SECRET1",
            "email2@test.com---pass2---backup2@test.com---SECRET2",
        ]
        sep = import_service.detect_separator(lines)
        assert sep == "---"

    def test_detect_separator_tab(self, import_service):
        """Test detection of tab separator."""
        lines = [
            "email1@test.com\tpass1\tbackup@test.com\tSECRET1",
            "email2@test.com\tpass2\tbackup2@test.com\tSECRET2",
        ]
        sep = import_service.detect_separator(lines)
        assert sep == "\t"

    def test_detect_separator_comma(self, import_service):
        """Test detection of comma separator."""
        lines = [
            "email1@test.com,pass1,backup@test.com,SECRET1",
            "email2@test.com,pass2,backup2@test.com,SECRET2",
        ]
        sep = import_service.detect_separator(lines)
        assert sep == ","

    def test_detect_separator_empty_lines(self, import_service):
        """Test that empty lines return default separator."""
        sep = import_service.detect_separator([])
        assert sep == "----"

    def test_parse_line_full(self, import_service):
        """Test parsing a complete line."""
        line = "test@example.com----password123----backup@test.com----SECRETKEY"
        account = import_service.parse_line(line, "----")

        assert account is not None
        assert account.email == "test@example.com"
        assert account.password == "password123"
        assert account.backup == "backup@test.com"
        assert account.secret == "SECRETKEY"

    def test_parse_line_minimal(self, import_service):
        """Test parsing a line with only email."""
        line = "test@example.com"
        account = import_service.parse_line(line, "----")

        assert account is not None
        assert account.email == "test@example.com"
        assert account.password == ""
        assert account.backup == ""
        assert account.secret == ""

    def test_parse_line_partial(self, import_service):
        """Test parsing a line with some fields."""
        line = "test@example.com----password123"
        account = import_service.parse_line(line, "----")

        assert account is not None
        assert account.email == "test@example.com"
        assert account.password == "password123"
        assert account.backup == ""
        assert account.secret == ""

    def test_parse_line_empty(self, import_service):
        """Test that empty line returns None."""
        account = import_service.parse_line("", "----")
        assert account is None

    def test_parse_line_whitespace(self, import_service):
        """Test that whitespace-only line returns None."""
        account = import_service.parse_line("   ", "----")
        assert account is None

    def test_parse_line_strips_whitespace(self, import_service):
        """Test that fields are stripped of whitespace."""
        line = "  test@example.com  ----  password123  "
        account = import_service.parse_line(line, "----")

        assert account.email == "test@example.com"
        assert account.password == "password123"

    def test_parse_text_multiline(self, import_service):
        """Test parsing multi-line text."""
        text = """test1@example.com----pass1----backup1@test.com----SECRET1
test2@example.com----pass2----backup2@test.com----SECRET2
test3@example.com----pass3----backup3@test.com----SECRET3"""

        accounts = import_service.parse_text(text)

        assert len(accounts) == 3
        assert accounts[0].email == "test1@example.com"
        assert accounts[1].email == "test2@example.com"
        assert accounts[2].email == "test3@example.com"

    def test_parse_text_with_empty_lines(self, import_service):
        """Test that empty lines are skipped."""
        text = """test1@example.com----pass1

test2@example.com----pass2

"""
        accounts = import_service.parse_text(text)
        assert len(accounts) == 2

    def test_parse_text_empty(self, import_service):
        """Test parsing empty text."""
        accounts = import_service.parse_text("")
        assert len(accounts) == 0

    def test_validate_email_valid(self, import_service):
        """Test email validation with valid emails."""
        assert ImportService.validate_email("test@example.com") is True
        assert ImportService.validate_email("user.name@domain.co.uk") is True

    def test_validate_email_invalid(self, import_service):
        """Test email validation with invalid emails."""
        assert ImportService.validate_email("notanemail") is False
        assert ImportService.validate_email("@nodomain.com") is False
        assert ImportService.validate_email("no@") is False
        assert ImportService.validate_email("") is False
