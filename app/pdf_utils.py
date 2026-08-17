import io

from pypdf import PdfReader


def extract_text_from_pdf(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))
    if reader.is_encrypted:
        # площадки закупок обычно ставят пустой пароль владельца, а не пользовательский
        try:
            reader.decrypt("")
        except Exception as exc:
            raise ValueError("PDF защищён паролем") from exc

    pages_text = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages_text)
