with open("src/tavily_tool.py", "r") as f:
    lines = f.readlines()
with open("src/tavily_tool.py", "w") as f:
    skip = False
    for line in lines:
        if line.startswith("    def extract("):
            skip = True
        if skip and line.startswith("    def "):
            if not line.startswith("    def extract("):
                skip = False
        if not skip:
            f.write(line)
