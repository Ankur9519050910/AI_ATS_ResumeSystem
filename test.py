import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv("backend/.env")

url = os.getenv("SUPABASE_URL")
anon_key = os.getenv("SUPABASE_ANON_KEY")

supabase = create_client(url, anon_key)

email = input("Email: ")
password = input("Password: ")

response = supabase.auth.sign_in_with_password({
    "email": email,
    "password": password
})

session = response.session

if session:
    print("\nLOGIN SUCCESS")
    print("\nAccess token:\n")
    print(session.access_token)
else:
    print("Login failed")