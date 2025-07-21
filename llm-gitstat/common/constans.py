import platform

ON_LINUX = platform.system() == "Linux"
ON_WIN = platform.system() == "Windows"

FIND_CMD = "find /c /v \"\"" if ON_WIN else "wc -l"
GREP_CMD = "findstr" if ON_WIN else "grep"


WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
