import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import jwt
from jwt import InvalidTokenError
from passlib.context import CryptContext


class JWTManager:
    def __init__(self, secret_key: Optional[str] = None, algorithm: str = "HS256"):
        self.secret_key = secret_key or os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        self.algorithm = algorithm
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def create_access_token(
        self,
        subject: str,
        roles: List[str] = None,
        tenant_id: Optional[str] = None,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=24)
        
        payload = {
            "sub": subject,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access",
            "roles": roles or [],
            "tenant_id": tenant_id
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(
        self,
        subject: str,
        tenant_id: Optional[str] = None,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=30)
        
        payload = {
            "sub": subject,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh",
            "tenant_id": tenant_id
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> Dict[str, Any]:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except InvalidTokenError as e:
            raise ValueError(f"Invalid token: {str(e)}")

    def get_token_subject(self, token: str) -> str:
        payload = self.verify_token(token)
        return payload.get("sub")

    def get_token_roles(self, token: str) -> List[str]:
        payload = self.verify_token(token)
        return payload.get("roles", [])

    def get_token_tenant(self, token: str) -> Optional[str]:
        payload = self.verify_token(token)
        return payload.get("tenant_id")

    def is_token_expired(self, token: str) -> bool:
        try:
            payload = self.verify_token(token)
            exp = payload.get("exp")
            if exp:
                return datetime.utcnow() > datetime.fromtimestamp(exp)
            return True
        except ValueError:
            return True

    def hash_password(self, password: str) -> str:
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.pwd_context.verify(plain_password, hashed_password)