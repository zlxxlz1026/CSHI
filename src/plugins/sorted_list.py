import bisect

class SortedList(list):
    def __init__(self, *args, reverse=False):
        super().__init__()
        self.reverse = reverse
        for item in args:
            self.append(item)

    def add(self, priority, name):
        index = bisect.bisect_left(self, (priority, name))
        if self.reverse:
            index = len(self) - index
        self.insert(index, (priority, name))

    def remove(self, name):
        self[:] = [(priority, n) for priority, n in self if n != name]

    def get_sorted_list(self):
        return [name for priority, name in self]

    def append(self, item):
        self.add(item[0], item[1])

    def __contains__(self, item):
        return item in self