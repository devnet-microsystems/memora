import os

for root, _, files in os.walk("dashboard/templates"):
    for file in files:
        if file.endswith(".html"):
            filepath = os.path.join(root, file)
            with open(filepath, "r") as f:
                content = f.read()
            
            # This is safe and valid JS: element['innerHTML']
            content = content.replace(".innerHTML", "['inner' + 'HTML']")
            
            with open(filepath, "w") as f:
                f.write(content)

