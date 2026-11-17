import argparse
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


REQUESTS_COUNT = 10
CHUNK_SIZE = 64 * 1024
DEFAULT_TIMEOUT = 30


def validate_url(value: str) -> str:
    """Валидация переданного адресса картиники."""
    parsed = urlsplit(value)

    if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
        raise argparse.ArgumentTypeError(
            'Укажите полный URL, начинающийся с http:// или https://'
        )

    return value


def format_bytes(value: int) -> str:
    """Переобразование байтов в десятичный формат."""
    units = ('B', 'kB', 'MB', 'GB', 'TB')
    size = float(value)

    for unit in units:

        if size < 1000 or unit == units[-1]:
            return f'{size:.2f} {unit}'

        size /= 1000

    return f'{size:.2f} TB'


def download_once(url: str, timeout: int) -> tuple[float, int, int]:
    """Загрузка ответа, возврат времени байтов и статуса."""
    request = Request(
        url,
        headers={
            'User-Agent': 'internet-speed-checker/1.0',
            'Cache-Control': 'no-cache',
        },
    )

    started_at = time.perf_counter()
    downloaded_bytes = 0

    with urlopen(request, timeout=timeout) as response:
        status_code = response.status

        while True:
            chunk = response.read(CHUNK_SIZE)

            if not chunk:
                break

            downloaded_bytes += len(chunk)

    elapsed = time.perf_counter() - started_at
    return elapsed, downloaded_bytes, status_code


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Последовательно скачивает URL 10 раз и измеряет скорость.'
    )
    parser.add_argument('url', type=validate_url, help='Полный HTTP(S)-адрес')
    parser.add_argument(
        '--timeout',
        type=int,
        default=DEFAULT_TIMEOUT,
        help=(
            'Таймаут одного запроса в секундах '
            f'(по умолчанию: {DEFAULT_TIMEOUT})'
        ),
    )
    args = parser.parse_args()

    if args.timeout <= 0:
        parser.error('--timeout должен быть положительным числом')

    total_bytes = 0
    total_elapsed = 0.0

    print(f'URL: {args.url}')
    print(f'Количество запросов: {REQUESTS_COUNT}')
    print()

    try:
        for request_number in range(1, REQUESTS_COUNT + 1):
            elapsed, downloaded_bytes, status_code = download_once(
                args.url,
                args.timeout,
            )
            total_elapsed += elapsed
            total_bytes += downloaded_bytes

            print(
                f'[{request_number:02d}/{REQUESTS_COUNT}] '
                f'HTTP {status_code} | '
                f'{format_bytes(downloaded_bytes)} | '
                f'{elapsed:.3f} с'
            )
    except HTTPError as error:
        print(
            f'\nОшибка HTTP: {error.code} {error.reason} '
            f'(запрос {request_number}/{REQUESTS_COUNT})',
            file=sys.stderr,
        )
        return 1
    except (URLError, TimeoutError, OSError, ValueError) as error:
        print(
            '\nНе удалось выполнить запрос '
            f'{request_number}/{REQUESTS_COUNT}: '
            f'{error}',
            file=sys.stderr,
        )
        return 1

    average_request_time = total_elapsed / REQUESTS_COUNT
    speed_bytes_per_second = (
        total_bytes / total_elapsed
        if total_elapsed
        else 0.0
    )
    speed_mb_per_second = speed_bytes_per_second / 1_000_000
    speed_mbps = speed_bytes_per_second * 8 / 1_000_000

    print('\n--- Результат ---')
    print(f'Среднее время одного запроса: {average_request_time:.3f} с')
    print((
            f'Общий объём скачанных данных: {format_bytes(total_bytes)}' 
            f'({total_bytes:,} B)'
        ))
    print(f'Общее время загрузки: {total_elapsed:.3f} с')
    print(f'Скорость скачивания: {speed_mb_per_second:.2f} MB/s')
    print(f'Скорость скачивания: {speed_mbps:.2f} Mbps')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
