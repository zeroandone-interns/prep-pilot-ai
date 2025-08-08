import boto3

def translate_text(text, source_lang='en', target_lang='fr'):
    # Allowed languages for your project
    allowed_langs = {'en', 'fr', 'ar'}
    
    if source_lang not in allowed_langs:
        raise ValueError(f"Unsupported source language: {source_lang}")
    if target_lang not in allowed_langs:
        raise ValueError(f"Unsupported target language: {target_lang}")
    if source_lang == target_lang:
        # No translation needed if source and target are the same
        return text

    translate = boto3.client('translate')

    response = translate.translate_text(
        Text=text,
        SourceLanguageCode=source_lang,
        TargetLanguageCode=target_lang
    )
    
    return response.get('TranslatedText')
