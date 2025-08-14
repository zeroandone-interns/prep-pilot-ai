import boto3
from langdetect import detect, DetectorFactory

# Ensure consistent language detection
DetectorFactory.seed = 0

class TranslationService:
    allowed_langs = {'en', 'fr', 'ar'}
    max_bytes = 10000

    def __init__(self):
        self.translate_client = boto3.client('translate')

    def split_text(self, text):
        """
        Splits text into chunks within the AWS Translate size limit.
        """
        chunks = []
        current_chunk = []

        for line in text.splitlines(keepends=True):
            if sum(len(s.encode("utf-8")) for s in current_chunk) + len(line.encode("utf-8")) > self.max_bytes:
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
                TargetLanguageCode=target_lang
            )
            translated_chunks.append(response.get('TranslatedText'))

        return "".join(translated_chunks)

    def translate_to_all_languages(self, text):
        detected_lang = detect(text)[:2].lower()

        if detected_lang not in self.allowed_langs:
            raise ValueError(f"Detected language '{detected_lang}' is not supported")

        translations = {detected_lang: text}

        for lang in self.allowed_langs - {detected_lang}:
            translations[lang] = self.translate_text(text, detected_lang, lang)

        return translations['en'], translations['fr'], translations['ar']

