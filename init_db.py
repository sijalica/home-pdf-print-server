"""Idempotent migration: preserves all historical rows."""
from common import initialize
if __name__ == '__main__':
    initialize()
    print('Database migrated and private configuration initialized.')
