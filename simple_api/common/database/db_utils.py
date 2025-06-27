def get_postgres_uri(user: str, password: str, host: str, port: str, database: str) -> str:
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"


def get_mongo_uri(port: int = 27017, local: bool = True) -> str:
    host = "localhost" if local else "mongodb"
    return f"mongodb://{host}:{port}"
