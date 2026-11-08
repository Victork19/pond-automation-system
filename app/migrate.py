"""Apply the checked-in SQL schema during container startup."""
from pathlib import Path
from sqlalchemy import create_engine, text
from .core import settings

def main() -> None:
    if settings.database_url.startswith('sqlite'):
        print('SQLite development mode: schema is created by the application.')
        return
    root = Path(__file__).resolve().parent.parent / 'migrations' / 'versions'
    files = sorted(root.glob('*.sql'))
    if not files:
        raise RuntimeError('No migration files found')
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    with engine.begin() as connection:
        for path in files:
            sql = path.read_text(encoding='utf-8')
            sql = '\n'.join(line for line in sql.splitlines() if not line.lstrip().startswith('--'))
            statements = [part.strip() for part in sql.split(';') if part.strip()]
            for statement in statements:
                connection.execute(text(statement))
            print(f'Applied {path.name}')

if __name__ == '__main__':
    main()
