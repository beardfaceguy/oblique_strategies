import unittest

from tests.memory_store import MemoryStore
from tests.store_contract import DataStoreContract


class MemoryStoreTest(DataStoreContract, unittest.TestCase):
    def make_store(self):
        return MemoryStore()


if __name__ == "__main__":
    unittest.main()
