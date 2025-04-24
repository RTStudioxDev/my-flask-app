import secrets

# สร้างคีย์แบบสุ่มความยาว 48 ตัวอักษร
secret_key = secrets.token_hex(24)  
print(secret_key)