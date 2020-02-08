import fnmatch

class Ignore:
    def __init__(self):
        self.defaultIgnore = ['.umetaignore/*', '.umetaderiv/']

    def filterIgnored(self, files):
        for f in files:
            if not any(fnmatch.fnmatch(f, p) for p in self.defaultIgnore):
                yield f
