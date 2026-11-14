def pytest_configure(config):
    config.addinivalue_line('markers', 'slow: large benchmark skipped when CI is set')
