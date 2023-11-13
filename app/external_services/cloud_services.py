import six
from google.cloud import translate_v2 as translate

TEXT_LIST_CHUNK_NUMBER = 120


def translate_text(text, src, dest, disable_word_translations=[]):
    """
    Target must be an ISO 639-1 language code.
    See https://g.co/cloud/translate/v2/translate-reference#supported_languages
    """

    translate_client = translate.Client()

    if isinstance(text, six.binary_type):
        text = text.decode('utf-8')

    if disable_word_translations:
        text = add_no_translate_class_to_disable_word_translations(
            text=text, disable_word_translations=disable_word_translations
        )

    result = translate_client.translate(text, target_language=dest, source_language=src)
    translated_text = result.get('translatedText')

    if disable_word_translations:
        translated_text, _ = remove_no_translate_class_from_translated_text(
            translated_text=translated_text,
            disable_word_translations=disable_word_translations,
        )
    return {'translated_text': translated_text}


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i : i + n]  # noqa


def translate_text_list(texts, src, dest, disable_word_translations=[]):
    """
    Target must be an ISO 639-1 language code.
    See https://g.co/cloud/translate/v2/translate-reference#supported_languages
    """

    translate_client = translate.Client()
    results = []
    # TODO: handle this limit
    if len(texts) > 1000:
        texts = []
    text_chunks = chunks(texts, TEXT_LIST_CHUNK_NUMBER)
    for chunk in text_chunks:
        if disable_word_translations:
            chunk = disable_words_from_translations_in_chunk(
                chunk=chunk, disable_word_translations=disable_word_translations
            )

        result = translate_client.translate(
            chunk, target_language=dest, source_language=src
        )

        if disable_word_translations:
            result = remove_no_translate_class_from_translations_in_chunk(
                chunk=result, disable_word_translations=disable_word_translations
            )
        results += result

    return results


def disable_words_from_translations_in_chunk(chunk, disable_word_translations):
    new_chunk = []
    for item in chunk:
        text = add_no_translate_class_to_disable_word_translations(
            text=item, disable_word_translations=disable_word_translations
        )
        new_chunk.append(text)
    return new_chunk


def add_no_translate_class_to_disable_word_translations(
    text, disable_word_translations
):
    for word in disable_word_translations:
        text = text.replace(word, f'<span translate="no">{word}</span>')
    return text


def remove_no_translate_class_from_translations_in_chunk(
    chunk, disable_word_translations
):
    new_chunk = []
    for item in chunk:
        translated_text, input = remove_no_translate_class_from_translated_text(
            translated_text=item.get('translatedText'),
            input=item.get('input'),
            disable_word_translations=disable_word_translations,
        )
        new_chunk.append({'translatedText': translated_text, 'input': input})
    return new_chunk


def remove_no_translate_class_from_translated_text(
    translated_text,
    disable_word_translations,
    input='',
):
    for word in disable_word_translations:
        translated_text = translated_text.replace(
            f'<span translate="no">{word}</span>', word
        )
        input = input.replace(f'<span translate="no">{word}</span>', word)
    return translated_text, input
