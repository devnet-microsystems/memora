import os
import re

def test_no_unsafe_innerhtml():
    """
    Scans HTML and JS files in dashboard/templates and dashboard/static
    for unsafe innerHTML, outerHTML, insertAdjacentHTML or document.write
    assignments containing template literals with unescaped interpolation (${...}).
    """
    target_dirs = [
        "dashboard/templates",
        "dashboard/static"
    ]
    
    # We look for dangerous DOM sinks
    # The regex checks for .innerHTML, .outerHTML, .insertAdjacentHTML, document.write
    # followed by an assignment or call, and capturing the string that follows.
    # It specifically targets backticks containing ${...} that don't have esc( before them.
    
    # A simpler approach: Just find any line with innerHTML/insertAdjacentHTML/outerHTML
    # and if it has `${`, it MUST have `esc(` or be in the explicit exceptions list.
    
    exceptions = [
        # util.js handles innerHTML explicitly via the key name 'innerHTML' 
        # which is trusted if used correctly.
        "element.innerHTML = value;" 
    ]
    
    unsafe_patterns = [
        r'\.innerHTML\s*\+?=',
        r'\.outerHTML\s*\+?=',
        r'\.insertAdjacentHTML\(',
        r'document\.write\('
    ]
    
    violations = []
    
    for d in target_dirs:
        for root, _, files in os.walk(d):
            for file in files:
                if file.endswith(".html") or file.endswith(".js"):
                    path = os.path.join(root, file)
                    with open(path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        
                    for i, line in enumerate(lines):
                        # skip exceptions
                        if any(exc in line for exc in exceptions):
                            continue
                            
                        for pat in unsafe_patterns:
                            if re.search(pat, line):
                                # If it contains a template literal interpolation
                                if '${' in line:
                                    # And doesn't use esc( or escapeHTML(
                                    if not re.search(r'(esc|escapeHTML)\(', line):
                                        violations.append(f"{path}:{i+1} -> {line.strip()}")
                                else:
                                    # Even if it doesn't have ${, maybe it concatenates with + ?
                                    # Just to be safe, we check for string concatenation as well,
                                    # but the prompt specifically says:
                                    # "con un template literal che contiene ${...} non avvolto in esc(...)"
                                    pass

    assert not violations, f"Found unsafe HTML insertions:\\n" + "\\n".join(violations)

