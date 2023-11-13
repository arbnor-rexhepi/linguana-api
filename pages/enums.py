import enum


class PageType(enum.Enum):
    Home = ''
    Page404 = '404'
    Sitemap = 'sitemap.xml'


class PageOrderBy(enum.Enum):
    PUBLISHED_STAGING_DOMAIN = 'staging'
    NOT_PUBLISHED_STAGING_DOMAIN = '-staging'
    PUBLISHED_CUSTOM_DOMAIN = 'custom'
    NOT_PUBLISHED_CUSTOM_DOMAIN = '-custom'


class PageViewActionName(enum.Enum):
    SYNC_CONTENT = 'sync_selected_page_versions'
    SYNC_LINKS_AND_CONTENT = 'sync_links_and_content_of_page_versions'
    AI_TRANSLATE = 'ai_translate_page_versions'


class PageFilter(enum.Enum):
    PUBLISHED = 'published'
    UNPUBLISHED = 'unpublished'
    NOT_PUBLISHED = 'not_published'


class CsvHeaderColumn(enum.Enum):
    TEXT = 'text'
    AI_TRANSLATION = 'ai_translation'
    MANUAL_TRANSLATION = 'manual_translation'
    TEXT_TYPE = 'text_type'
    ATTRIBUTE_NAME = 'attribute_name'
    PARSED_ELEMENT_TYPE = 'parsed_element_type'
