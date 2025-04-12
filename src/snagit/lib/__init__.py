class DataProxy:
    def __init__(self, data):
        self._data = data.decode() if isinstance(data, bytes) else data

    def __str__(self):
        return self._data

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __getattr__(self, attr):
        return getattr(self._data, attr)

    @classmethod
    def merge(cls, all_data):
        return cls("\n".join(str(data) for data in all_data))
