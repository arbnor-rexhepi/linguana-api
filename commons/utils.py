from urllib.parse import urlparse
import tldextract


def normalize_domain(domain, remove_www=True):
    domain = domain.strip().replace('https://', '').replace('http://', '').split('/')[0]
    if domain.startswith('www.') and remove_www:
        return domain.replace('www.', '').lower()
    return domain.lower()


def split_domain(domain):
    result = tldextract.extract(domain)
    return result.subdomain, f'{result.domain}.{result.suffix}'


def check_www(url):
    if url.startswith('http://www.') or url.startswith('https://www.'):
        return True
    return False


def normalize_page_url(url):
    return urlparse(url).path.strip('/')


def get_page_path_from_url(url):
    return urlparse(url).path.strip('/')


def clean_string(string):
    # Function to clean string before matching elements with translations
    return string.strip().replace('\xa0', '')


def clean_csv_string(string):
    return string.strip().strip(';').replace('\xa0', '')


def clean_subfolder_path(string):
    return string.strip().split('/')[0].strip()


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
