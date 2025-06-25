def read_latest_commit() -> str:
    with open("assets/latest_commit.txt") as f:
        return f.read().strip()
