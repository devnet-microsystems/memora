import urllib.parse

def tavily_extract(url: str):
    parsed = urllib.parse.urlparse(url)
    allowed_domains = ["wikipedia.org", "nih.gov", "mayoclinic.org", "salute.gov.it"]
    if not any(parsed.netloc.endswith(d) for d in allowed_domains):
        return {"error": "Domain not in whitelist for security reasons."}
    
    return {"success": f"Extraction proceeding for {url}"}

# Proof of Concept
attacker_url = "http://attacker-wikipedia.org/exfiltrate"
print(f"Testing URL: {attacker_url}")
result = tavily_extract(attacker_url)
print(f"Result: {result}")

