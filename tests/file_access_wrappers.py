# file: tests/file_access_wrappers.py
# author: Andrew Jarcho
# date: 2017-01-22

# python: 3.5  pytest: 3.0.7

import io


class FileReadAccessWrapper:

    def __init__(self, filename):
        self.filename = filename

    def open(self):
        return open(self.filename, 'r')


class FakeFileReadWrapper:
    def __init__(self, text):
        self.text = text
        self.start_ix = 0

    def open(self):
        return io.StringIO(self.text)

    def input(self):
        return self.open()

    def __iter__(self):  # TODO: not in use -- needs testing
        return self

    def __next__(self):  # TODO: not in use -- needs testing
        next_newline_ix = self.text.find('\n', self.start_ix)
        if next_newline_ix == -1:
            raise StopIteration
        else:
            ret_str = self.text[self.start_ix: next_newline_ix]
            self.start_ix = next_newline_ix + 1
            return ret_str
