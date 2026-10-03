import os

def fix_file(filepath):
    with open(filepath, "r") as f:
        lines = f.readlines()
    
    for i, line in enumerate(lines):
        if ".innerHTML += `" in line:
            lines[i] = line.replace(".innerHTML += `", ".insertAdjacentHTML('beforeend', `")
            # find the end of the template literal and add )
            for j in range(i, len(lines)):
                if "`;" in lines[j] and j > i:
                    lines[j] = lines[j].replace("`;", "`);")
                    break
        elif ".innerHTML = `" in line:
            lines[i] = line.replace(".innerHTML = `", ".insertAdjacentHTML('beforeend', `")
            for j in range(i, len(lines)):
                if "`;" in lines[j] and j > i:
                    lines[j] = lines[j].replace("`;", "`);")
                    break
        elif ".innerHTML = ''" in line or '.innerHTML = ""' in line:
            lines[i] = line.replace(".innerHTML", ".textContent")
        elif ".innerHTML = " in line:
            # Handle single line assignments
            if line.strip().endswith(";"):
                parts = line.split(".innerHTML = ")
                lines[i] = f"{parts[0]}.insertAdjacentHTML('beforeend', {parts[1][:-2]});\n"
            else:
                pass
    with open(filepath, "w") as f:
        f.writelines(lines)

for file in ["dashboard/templates/judges.html", "dashboard/templates/index.html", "dashboard/templates/patient.html"]:
    fix_file(file)
