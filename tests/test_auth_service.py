from app.database.database import SessionLocal
from app.auth.service import AuthService


db = SessionLocal()

try:
    user = AuthService.authenticate_user(
        db,
        email="testuser@example.com",
        password="TestPassword123!",
    )

    if not user:
        print("Authentication failed.")
    else:
        token = AuthService.create_user_access_token(user)

        print("Authentication successful!")
        print("JWT created successfully!")
        print()
        print("Token:")
        print(token)

finally:
    db.close()