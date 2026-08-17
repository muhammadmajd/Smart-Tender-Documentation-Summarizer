# test_pdf_utils.py

import pytest
from unittest.mock import patch, MagicMock

from app.pdf_utils import extract_text_from_pdf

@pytest.mark.usefixtures("mock_pdfreader")
class TestExtractTextFromPdf:
    # --- Happy Path Tests ---

    @pytest.mark.happy_path
    def test_extract_text_single_page(self, mock_pdfreader):
        """
        Test extracting text from a single-page, non-encrypted PDF.
        """
        mock_reader = MagicMock()
        mock_reader.is_encrypted = False
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Hello, PDF!"
        mock_reader.pages = [mock_page]
        mock_pdfreader.return_value = mock_reader

        result = extract_text_from_pdf(b"dummy bytes")
        assert result == "Hello, PDF!"

    @pytest.mark.happy_path
    def test_extract_text_multi_page(self, mock_pdfreader):
        """
        Test extracting text from a multi-page, non-encrypted PDF.
        """
        mock_reader = MagicMock()
        mock_reader.is_encrypted = False
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "Page 1"
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "Page 2"
        mock_reader.pages = [mock_page1, mock_page2]
        mock_pdfreader.return_value = mock_reader

        result = extract_text_from_pdf(b"dummy bytes")
        assert result == "Page 1\nPage 2"

    @pytest.mark.happy_path
    def test_extract_text_encrypted_pdf_success(self, mock_pdfreader):
        """
        Test extracting text from an encrypted PDF that can be decrypted with an empty password.
        """
        mock_reader = MagicMock()
        mock_reader.is_encrypted = True
        mock_reader.decrypt.return_value = True
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Secret text"
        mock_reader.pages = [mock_page]
        mock_pdfreader.return_value = mock_reader

        result = extract_text_from_pdf(b"dummy bytes")
        mock_reader.decrypt.assert_called_once_with("")
        assert result == "Secret text"

    # --- Edge Case Tests ---

    @pytest.mark.edge_case
    def test_extract_text_encrypted_pdf_fail(self, mock_pdfreader):
        """
        Test extracting text from an encrypted PDF that cannot be decrypted (raises exception).
        """
        mock_reader = MagicMock()
        mock_reader.is_encrypted = True
        mock_reader.decrypt.side_effect = Exception("decryption failed")
        mock_pdfreader.return_value = mock_reader

        with pytest.raises(ValueError) as excinfo:
            extract_text_from_pdf(b"dummy bytes")
        assert "PDF защищён паролем" in str(excinfo.value)

    @pytest.mark.edge_case
    def test_extract_text_page_returns_none(self, mock_pdfreader):
        """
        Test extracting text from a PDF where extract_text returns None for a page.
        """
        mock_reader = MagicMock()
        mock_reader.is_encrypted = False
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = None
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "Text on page 2"
        mock_reader.pages = [mock_page1, mock_page2]
        mock_pdfreader.return_value = mock_reader

        result = extract_text_from_pdf(b"dummy bytes")
        assert result == "\nText on page 2"

    @pytest.mark.edge_case
    def test_extract_text_empty_pdf(self, mock_pdfreader):
        """
        Test extracting text from a PDF with zero pages.
        """
        mock_reader = MagicMock()
        mock_reader.is_encrypted = False
        mock_reader.pages = []
        mock_pdfreader.return_value = mock_reader

        result = extract_text_from_pdf(b"dummy bytes")
        assert result == ""

    @pytest.mark.edge_case
    def test_extract_text_all_pages_none(self, mock_pdfreader):
        """
        Test extracting text from a PDF where all pages return None for extract_text.
        """
        mock_reader = MagicMock()
        mock_reader.is_encrypted = False
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = None
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = None
        mock_reader.pages = [mock_page1, mock_page2]
        mock_pdfreader.return_value = mock_reader

        result = extract_text_from_pdf(b"dummy bytes")
        assert result == "\n"

    @pytest.mark.edge_case
    def test_extract_text_pdfreader_raises(self, mock_pdfreader):
        """
        Test behavior when PdfReader itself raises an exception (e.g., invalid PDF bytes).
        """
        mock_pdfreader.side_effect = Exception("invalid PDF")
        with pytest.raises(Exception) as excinfo:
            extract_text_from_pdf(b"not a real pdf")
        assert "invalid PDF" in str(excinfo.value)

    # --- Fixtures ---

    @pytest.fixture(autouse=True)
    def mock_pdfreader(self):
        """
        Patch PdfReader in app.pdf_utils for all tests in this class.
        """
        with patch("app.pdf_utils.PdfReader") as mock:
            yield mock