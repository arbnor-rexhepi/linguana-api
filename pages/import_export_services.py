import csv
import io
import logging
from commons.utils import clean_csv_string
from pages.consts import ATTRIBUTES_AI_TRANSLATE_NOT_INCLUDE
from pages.enums import CsvHeaderColumn
from pages.services import (
    get_page_parsed_elements_with_translations,
    get_page_version_by_guid_or_404,
)
from rest_framework.exceptions import APIException, ValidationError
from django.db import transaction

from translations.service import create_or_update_text_translation

CSV_HEADERS = [
    CsvHeaderColumn.TEXT.value,
    CsvHeaderColumn.AI_TRANSLATION.value,
    CsvHeaderColumn.MANUAL_TRANSLATION.value,
    CsvHeaderColumn.TEXT_TYPE.value,
    CsvHeaderColumn.ATTRIBUTE_NAME.value,
    CsvHeaderColumn.PARSED_ELEMENT_TYPE.value,
]


def export_csv_page_version_translations(page_version_guid):
    try:
        page_version = get_page_version_by_guid_or_404(page_version_guid)
        page_translation_elements = get_page_parsed_elements_with_translations(
            page_guid=page_version.page.guid, page_version_guid=page_version_guid
        )

        buffer = io.StringIO()
        writer = csv.writer(buffer, delimiter='|')
        csv_data = []
        for item in page_translation_elements:
            if item.get('attribute') in ATTRIBUTES_AI_TRANSLATE_NOT_INCLUDE:
                continue
            csv_data.append(
                [
                    item.get('text')
                    or item.get('attribute_value')
                    or item.get('element'),
                    item.get('translation').get('ai_translation', None)
                    if item.get('translation') is not None
                    else None,
                    item.get('translation').get('manual_translation', None)
                    if item.get('translation') is not None
                    else None,
                    item.get('element_type'),
                    item.get('attribute', None) or None,
                    item.get('element_name', None) or None,
                ]
            )
        writer.writerow(CSV_HEADERS)
        writer.writerows(csv_data)
        return buffer.getvalue()
    except Exception as e:
        logging.error(
            f'Failed to export translations for page with guid:{page_version_guid}. Error:{repr(e)}!'
        )
        raise APIException('Failed to export translations, try again later!')


@transaction.atomic()
def import_csv_page_version_translations(page_version_guid, file):
    try:
        page_version = get_page_version_by_guid_or_404(page_version_guid)
        page_elements = get_page_parsed_elements_with_translations(
            page_guid=page_version.page.guid, page_version_guid=page_version_guid
        )
        dict_of_page_elements = {}
        for element in page_elements:
            text = (
                element.get('text')
                or element.get('attribute_value')
                or element.get('element')
            )
            text_type = element.get('element_type')
            attribute = element.get('attribute', '')
            key = f'{text}-{text_type}-{attribute}'
            dict_of_page_elements[key] = key

        if file.content_type != 'text/csv':
            raise ValidationError('Your file must be a CSV type!')

        # Read the CSV file content
        csv_data = file.read().decode('utf-8')
        csv_reader = csv.reader(io.StringIO(csv_data), delimiter='|')

        actual_headers = next(csv_reader, [])
        validate_csv_headers(actual_headers=actual_headers)

        translation_objects = []
        for row in csv_reader:
            text = clean_csv_string(row[0])
            ai_translation = clean_csv_string(row[1])
            manual_translation = clean_csv_string(row[2])
            text_type = clean_csv_string(row[3])
            attribute_name = clean_csv_string(row[4])
            parsed_element_type = clean_csv_string(row[5])
            key = f'{text}-{text_type}-{attribute_name}'

            if (
                attribute_name in ATTRIBUTES_AI_TRANSLATE_NOT_INCLUDE
                or dict_of_page_elements.get(key, None) is None
            ):
                continue

            translation = create_or_update_text_translation(
                page_lang_version=page_version,
                text=text,
                ai_translation=ai_translation,
                manual_translation=manual_translation,
                text_type=text_type,
                attribute_name=attribute_name,
                parsed_element_type=parsed_element_type,
            )
            translation_objects.append(translation)
        return translation_objects
    except Exception as e:
        if isinstance(e, ValidationError):
            raise
        logging.error(
            f'Failed to import translations for page with guid:{page_version_guid}. Error:{repr(e)}!'
        )
        raise APIException('Failed to import translations, try again later!')


def validate_csv_headers(actual_headers):
    normalized_actual_headers = [
        clean_csv_string(header.strip().lower()) for header in actual_headers
    ]

    if normalized_actual_headers != CSV_HEADERS:
        message = 'CSV headers do not match with expected headers.'
        logging.error(message)
        raise ValidationError(message)
