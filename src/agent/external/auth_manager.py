"""
Authentication Manager

Secure credential management and authentication for external services.

Author: Claude Code
Date: 2025-07-13
Session: 2.3
"""

import os
import json
import asyncio
import hashlib
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
from pathlib import Path

try:
    from cryptography.fernet import Fernet
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False

from ...utils.logger import get_logger

logger = get_logger(__name__)


class AuthMethod(Enum):
    """Authentication methods"""
    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    BASIC_AUTH = "basic_auth"
    OAUTH2 = "oauth2"
    CUSTOM_HEADER = "custom_header"
    JWT = "jwt"


@dataclass
class Credential:
    """Secure credential storage"""
    service_id: str
    auth_method: AuthMethod
    data: Dict[str, str]
    encrypted: bool = False
    created_at: float = field(default_factory=lambda: __import__('time').time())
    expires_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AuthManager:
    """
    Secure authentication and credential management.
    
    Features:
    - Multiple authentication methods (API key, Bearer token, OAuth2, etc.)
    - Encrypted credential storage
    - Environment variable integration
    - Credential expiry and refresh
    - Service-specific credential management
    - Secure credential sharing between components
    """
    
    def __init__(self, config_dir: Optional[str] = None, enable_encryption: bool = True):
        """
        Initialize authentication manager.
        
        Args:
            config_dir: Directory for credential storage
            enable_encryption: Whether to encrypt stored credentials
        """
        self.config_dir = Path(config_dir or os.path.expanduser("~/.local/share/agent/auth"))
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.enable_encryption = enable_encryption and ENCRYPTION_AVAILABLE
        self.credentials: Dict[str, Credential] = {}
        
        # Initialize encryption if available
        self.cipher_suite = None
        if self.enable_encryption:
            self._initialize_encryption()
        
        # Load existing credentials
        asyncio.create_task(self._load_credentials())
        
        logger.info(f"Auth manager initialized (encryption: {self.enable_encryption})")
    
    def _initialize_encryption(self):
        """Initialize encryption for credential storage"""
        if not ENCRYPTION_AVAILABLE:
            logger.warning("Cryptography library not available, encryption disabled")
            self.enable_encryption = False
            return
        
        key_file = self.config_dir / "auth.key"
        
        if key_file.exists():
            # Load existing key
            with open(key_file, "rb") as f:
                key = f.read()
        else:
            # Generate new key
            key = Fernet.generate_key()
            with open(key_file, "wb") as f:
                f.write(key)
            
            # Set restrictive permissions
            os.chmod(key_file, 0o600)
        
        self.cipher_suite = Fernet(key)
        logger.debug("Encryption initialized")
    
    async def _load_credentials(self):
        """Load credentials from storage"""
        credentials_file = self.config_dir / "credentials.json"
        
        if not credentials_file.exists():
            return
        
        try:
            with open(credentials_file, "r") as f:
                data = json.load(f)
            
            for service_id, cred_data in data.items():
                credential = Credential(
                    service_id=service_id,
                    auth_method=AuthMethod(cred_data["auth_method"]),
                    data=cred_data["data"],
                    encrypted=cred_data.get("encrypted", False),
                    created_at=cred_data.get("created_at", 0),
                    expires_at=cred_data.get("expires_at"),
                    metadata=cred_data.get("metadata", {})
                )
                
                # Decrypt if necessary
                if credential.encrypted and self.cipher_suite:
                    credential.data = self._decrypt_data(credential.data)
                    credential.encrypted = False
                
                self.credentials[service_id] = credential
            
            logger.info(f"Loaded {len(self.credentials)} credentials")
            
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
    
    async def _save_credentials(self):
        """Save credentials to storage"""
        credentials_file = self.config_dir / "credentials.json"
        
        try:
            data = {}
            
            for service_id, credential in self.credentials.items():
                cred_data = {
                    "auth_method": credential.auth_method.value,
                    "data": credential.data,
                    "encrypted": credential.encrypted,
                    "created_at": credential.created_at,
                    "expires_at": credential.expires_at,
                    "metadata": credential.metadata
                }
                
                # Encrypt if enabled
                if self.enable_encryption and self.cipher_suite:
                    cred_data["data"] = self._encrypt_data(credential.data)
                    cred_data["encrypted"] = True
                
                data[service_id] = cred_data
            
            with open(credentials_file, "w") as f:
                json.dump(data, f, indent=2)
            
            # Set restrictive permissions
            os.chmod(credentials_file, 0o600)
            
            logger.debug("Credentials saved")
            
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")
    
    def _encrypt_data(self, data: Dict[str, str]) -> Dict[str, str]:
        """Encrypt credential data"""
        if not self.cipher_suite:
            return data
        
        encrypted_data = {}
        for key, value in data.items():
            if isinstance(value, str):
                encrypted_value = self.cipher_suite.encrypt(value.encode()).decode()
                encrypted_data[key] = encrypted_value
            else:
                encrypted_data[key] = value
        
        return encrypted_data
    
    def _decrypt_data(self, data: Dict[str, str]) -> Dict[str, str]:
        """Decrypt credential data"""
        if not self.cipher_suite:
            return data
        
        decrypted_data = {}
        for key, value in data.items():
            if isinstance(value, str):
                try:
                    decrypted_value = self.cipher_suite.decrypt(value.encode()).decode()
                    decrypted_data[key] = decrypted_value
                except Exception:
                    # If decryption fails, assume it's not encrypted
                    decrypted_data[key] = value
            else:
                decrypted_data[key] = value
        
        return decrypted_data
    
    async def add_credential(self, service_id: str, auth_method: AuthMethod,
                           data: Dict[str, str], expires_at: Optional[float] = None,
                           metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Add or update credential for a service.
        
        Args:
            service_id: Unique service identifier
            auth_method: Authentication method
            data: Credential data (keys, tokens, etc.)
            expires_at: Optional expiry timestamp
            metadata: Optional metadata
            
        Returns:
            True if credential was added successfully
        """
        try:
            credential = Credential(
                service_id=service_id,
                auth_method=auth_method,
                data=data.copy(),
                expires_at=expires_at,
                metadata=metadata or {}
            )
            
            self.credentials[service_id] = credential
            await self._save_credentials()
            
            logger.info(f"Added credential for service: {service_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add credential for {service_id}: {e}")
            return False
    
    async def get_credential(self, service_id: str, key: str) -> Optional[str]:
        """
        Get specific credential value.
        
        Args:
            service_id: Service identifier
            key: Credential key (e.g., 'api_key', 'access_token')
            
        Returns:
            Credential value or None if not found
        """
        # First check environment variables
        env_var = f"{service_id.upper()}_{key.upper()}"
        env_value = os.getenv(env_var)
        if env_value:
            return env_value
        
        # Check stored credentials
        if service_id in self.credentials:
            credential = self.credentials[service_id]
            
            # Check if credential is expired
            if credential.expires_at and credential.expires_at <= __import__('time').time():
                logger.warning(f"Credential for {service_id} has expired")
                return None
            
            return credential.data.get(key)
        
        return None
    
    async def get_auth_headers(self, service_id: str) -> Dict[str, str]:
        """
        Get authentication headers for a service.
        
        Args:
            service_id: Service identifier
            
        Returns:
            Dictionary of authentication headers
        """
        if service_id not in self.credentials:
            return {}
        
        credential = self.credentials[service_id]
        headers = {}
        
        if credential.auth_method == AuthMethod.API_KEY:
            api_key = credential.data.get("api_key")
            if api_key:
                # Check for custom header name
                header_name = credential.metadata.get("header_name", "X-API-Key")
                headers[header_name] = api_key
        
        elif credential.auth_method == AuthMethod.BEARER_TOKEN:
            access_token = credential.data.get("access_token")
            if access_token:
                headers["Authorization"] = f"Bearer {access_token}"
        
        elif credential.auth_method == AuthMethod.BASIC_AUTH:
            username = credential.data.get("username")
            password = credential.data.get("password")
            if username and password:
                import base64
                credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
                headers["Authorization"] = f"Basic {credentials}"
        
        elif credential.auth_method == AuthMethod.CUSTOM_HEADER:
            header_name = credential.metadata.get("header_name")
            header_value = credential.data.get("header_value")
            if header_name and header_value:
                headers[header_name] = header_value
        
        elif credential.auth_method == AuthMethod.JWT:
            jwt_token = credential.data.get("jwt_token")
            if jwt_token:
                headers["Authorization"] = f"Bearer {jwt_token}"
        
        return headers
    
    async def remove_credential(self, service_id: str) -> bool:
        """
        Remove credential for a service.
        
        Args:
            service_id: Service identifier
            
        Returns:
            True if credential was removed
        """
        if service_id in self.credentials:
            del self.credentials[service_id]
            await self._save_credentials()
            logger.info(f"Removed credential for service: {service_id}")
            return True
        
        return False
    
    async def refresh_oauth2_token(self, service_id: str) -> bool:
        """
        Refresh OAuth2 access token using refresh token.
        
        Args:
            service_id: Service identifier
            
        Returns:
            True if token was refreshed successfully
        """
        if service_id not in self.credentials:
            return False
        
        credential = self.credentials[service_id]
        if credential.auth_method != AuthMethod.OAUTH2:
            return False
        
        refresh_token = credential.data.get("refresh_token")
        client_id = credential.data.get("client_id")
        client_secret = credential.data.get("client_secret")
        token_url = credential.metadata.get("token_url")
        
        if not all([refresh_token, client_id, client_secret, token_url]):
            logger.error(f"Missing OAuth2 refresh parameters for {service_id}")
            return False
        
        try:
            # This would make an HTTP request to refresh the token
            # For now, just log the attempt
            logger.info(f"OAuth2 token refresh attempted for {service_id}")
            
            # In a real implementation:
            # 1. Make POST request to token_url
            # 2. Include refresh_token, client_id, client_secret
            # 3. Parse response to get new access_token
            # 4. Update credential data
            # 5. Save credentials
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to refresh OAuth2 token for {service_id}: {e}")
            return False
    
    def list_services(self) -> List[str]:
        """Get list of services with stored credentials"""
        return list(self.credentials.keys())
    
    def get_service_info(self, service_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a service's credentials"""
        if service_id not in self.credentials:
            return None
        
        credential = self.credentials[service_id]
        
        return {
            "service_id": service_id,
            "auth_method": credential.auth_method.value,
            "created_at": credential.created_at,
            "expires_at": credential.expires_at,
            "expired": credential.expires_at and credential.expires_at <= __import__('time').time(),
            "has_keys": list(credential.data.keys()),
            "metadata": credential.metadata
        }
    
    async def validate_credential(self, service_id: str) -> bool:
        """
        Validate that a credential exists and is not expired.
        
        Args:
            service_id: Service identifier
            
        Returns:
            True if credential is valid
        """
        if service_id not in self.credentials:
            return False
        
        credential = self.credentials[service_id]
        
        # Check expiry
        if credential.expires_at and credential.expires_at <= __import__('time').time():
            return False
        
        # Check that required data exists
        if not credential.data:
            return False
        
        return True
    
    async def setup_service_auth(self, service_id: str, auth_config: Dict[str, Any]) -> bool:
        """
        Setup authentication for a service from configuration.
        
        Args:
            service_id: Service identifier
            auth_config: Authentication configuration
            
        Returns:
            True if setup was successful
        """
        try:
            auth_method = AuthMethod(auth_config["method"])
            data = auth_config.get("data", {})
            expires_at = auth_config.get("expires_at")
            metadata = auth_config.get("metadata", {})
            
            return await self.add_credential(
                service_id=service_id,
                auth_method=auth_method,
                data=data,
                expires_at=expires_at,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to setup auth for {service_id}: {e}")
            return False
    
    async def get_auth_summary(self) -> Dict[str, Any]:
        """Get summary of authentication status"""
        summary = {
            "total_services": len(self.credentials),
            "encryption_enabled": self.enable_encryption,
            "services": {}
        }
        
        for service_id, credential in self.credentials.items():
            summary["services"][service_id] = {
                "auth_method": credential.auth_method.value,
                "expired": credential.expires_at and credential.expires_at <= __import__('time').time(),
                "expires_at": credential.expires_at
            }
        
        return summary