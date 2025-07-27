import secrets

# Generate a secure random key
secret_key = secrets.token_hex(16)  # Generates a random key of 32 hexadecimal characters
print(secret_key)