import boto3
from langdetect import detect_langs, DetectorFactory
from extensions import get_logger

# Ensure consistent language detection
DetectorFactory.seed = 0


class TranslationService:
    allowed_langs = {"en", "fr", "ar"}
    max_bytes = 10000

    def __init__(self):
        self.translate_client = boto3.client("translate", region_name="us-east-1")
        self.get_logger = get_logger()

    def split_text(self, text):
        """
        Splits text into chunks within the AWS Translate size limit.
        """
        chunks = []
        current_chunk = []

        for line in text.splitlines(keepends=True):
            if (
                sum(len(s.encode("utf-8")) for s in current_chunk)
                + len(line.encode("utf-8"))
                > self.max_bytes
            ):
                chunks.append("".join(current_chunk))
                current_chunk = [line]
            else:
                current_chunk.append(line)

        if current_chunk:
            chunks.append("".join(current_chunk))

        return chunks

    def translate_text(self, text, source_lang, target_lang):
        chunks = self.split_text(text)
        translated_chunks = []

        for chunk in chunks:
            response = self.translate_client.translate_text(
                Text=chunk,
                SourceLanguageCode=source_lang,
                TargetLanguageCode=target_lang,
            )
            translated_chunks.append(response.get("TranslatedText"))

        return "".join(translated_chunks)

    def detect_language(self, text, confidence_threshold=0.6):
        """
        Detect language using langdetect with confidence check.
        Falls back to heuristics for Arabic and French.
        """
        detected_lang = "en"  # default fallback
        try:
            langs = detect_langs(text)
            if langs and langs[0].prob >= confidence_threshold:
                detected_lang = langs[0].lang[:2].lower()
        except Exception:
            detected_lang = "en"

        # Heuristic fallback if detected language is not allowed
        if detected_lang not in self.allowed_langs:
            if any("\u0600" <= c <= "\u06ff" for c in text):
                detected_lang = "ar"
            elif any(c in "éèàç" for c in text):
                detected_lang = "fr"
            else:
                detected_lang = "en"

        return detected_lang

    def translate_to_all_languages(self, text):
        detected_lang = self.detect_language(text)
        self.get_logger.info(f"Detected language: {detected_lang}")

        translations = {detected_lang: text}

        for lang in self.allowed_langs - {detected_lang}:
            translations[lang] = self.translate_text(text, detected_lang, lang)

        return translations["en"], translations["fr"], translations["ar"]


    def _translate_and_assign(self, text):
        if not text:
            return {"en": None, "fr": None, "ar": None}
        en, fr, ar = self.translate_to_all_languages(text)
        return {"en": en, "fr": fr, "ar": ar}