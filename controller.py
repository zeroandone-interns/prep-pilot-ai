from flask import request, jsonify
from service import translate_text

def translate_controller():
    text = request.form.get('text')
    source_lang = request.form.get('source_lang', 'en').lower()
    target_lang = request.form.get('target_lang', 'fr').lower()

    allowed_langs = {'en', 'fr', 'ar'}

    # Fallback test paragraph if no text provided
    if not text:
        text = (
            "Cloud computing is the on-demand delivery of IT resources over the internet. "
            "Instead of buying, owning, and maintaining physical data centers and servers, "
            "you can access technology services, such as computing power, storage, and databases, on an as-needed basis."
        )

    if source_lang not in allowed_langs:
        return jsonify({'error': f'Unsupported source language: {source_lang}'}), 400

    if target_lang not in allowed_langs:
        return jsonify({'error': f'Unsupported target language: {target_lang}'}), 400

    try:
        translated = translate_text(text, source_lang, target_lang)
        return jsonify({'translated_text': translated})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
