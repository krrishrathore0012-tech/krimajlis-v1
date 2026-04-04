import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

_client = None


def get_db():
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
        from supabase import create_client
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


def safe_db_write(table: str, data: dict) -> bool:
    try:
        db = get_db()
        db.table(table).insert(data).execute()
        return True
    except Exception as e:
        print(f"DB write failed for {table}: {e}")
        return False


def safe_db_update(table: str, match: dict, data: dict) -> bool:
    try:
        db = get_db()
        query = db.table(table).update(data)
        for key, value in match.items():
            query = query.eq(key, value)
        query.execute()
        return True
    except Exception as e:
        print(f"DB update failed for {table}: {e}")
        return False


def safe_db_read(table: str, filters: dict = None, limit: int = 1000) -> list:
    try:
        db = get_db()
        query = db.table(table).select('*').limit(limit).order('created_at', desc=True)
        if filters:
            for key, value in filters.items():
                query = query.eq(key, value)
        result = query.execute()
        return result.data or []
    except Exception as e:
        print(f"DB read failed for {table}: {e}")
        return []
