import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'biz_light.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User

def test_dashboard():
    client = Client()
    user = User.objects.get(id=7)
    client.force_login(user)
    response = client.get('/dashboard/')
    print("Response status code:", response.status_code)
    if response.status_code == 200:
        with open('test_output.html', 'w', encoding='utf-8') as f:
            f.write(response.content.decode('utf-8'))
        print("Saved to test_output.html")
    elif response.status_code == 500:
        print("Error content:")
        # print first 1000 chars of error
        print(response.content.decode('utf-8')[:1000])

if __name__ == '__main__':
    test_dashboard()
