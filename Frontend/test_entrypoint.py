import importlib
import unittest


class EntrypointTests(unittest.TestCase):
    def test_app_import(self) -> None:
        module = importlib.import_module("app")
        self.assertTrue(hasattr(module, "demo"))


if __name__ == "__main__":
    unittest.main()
