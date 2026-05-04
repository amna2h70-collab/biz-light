import requests, re

s = requests.Session()
login_page = s.get("http://127.0.0.1:8000/login/")
csrf = re.search(r'csrfmiddlewaretoken.*?value="(.*?)"', login_page.text)
token = csrf.group(1) if csrf else ""

r = s.post("http://127.0.0.1:8000/login/", data={
    "csrfmiddlewaretoken": token,
    "username": "ibrahimnasir436@gmail.com",
    "password": "admin123"
}, headers={"Referer": "http://127.0.0.1:8000/login/"})

r = s.get("http://127.0.0.1:8000/dashboard/")
print(f"Status: {r.status_code}")

if "TemplateSyntaxError" in r.text:
    match = re.search(r"Could not parse the remainder.*", r.text)
    print(f"TEMPLATE ERROR: {match.group(0)[:200] if match else 'unknown'}")
elif "Business Overview" in r.text:
    print("Dashboard loaded successfully!")
    if "floatformat" in r.text.lower():
        print("WARNING: Raw floatformat text in page!")
    else:
        print("All template tags rendering correctly.")
else:
    print("Unexpected page. Title area:")
    title = re.search(r"<title>(.*?)</title>", r.text)
    print(title.group(1) if title else "no title found")
