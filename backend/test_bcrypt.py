import bcrypt

password = 'AgentTest!'
password_bytes = password.encode('utf-8')

# Create a hash
salt = bcrypt.gensalt()
hashed = bcrypt.hashpw(password_bytes, salt)
print(f'Created hash: {hashed.decode("utf-8")}')

# Verify it
result = bcrypt.checkpw(password_bytes, hashed)
print(f'Verification with same password: {result}')

# Now test with the hash from DB
db_hash = '$2b$12$892uHZ4bw6Q5FJpFgUgT0O7Dh..qdzud.hLPJvGFBDuitpsz1D4FW'
result2 = bcrypt.checkpw(password_bytes, db_hash.encode('utf-8'))
print(f'Verification with DB hash: {result2}')
