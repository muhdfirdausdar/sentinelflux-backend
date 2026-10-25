"""
Centralized Azure Key Vault client for DNFlux
Handles all secret retrieval with proper fallbacks
"""
import os
from typing import Optional
from utils.async_log import get_logger

logger = get_logger("azure_vault")

class AzureVaultClient:
    """Centralized Azure Key Vault client"""
    
    def __init__(self):
        self.vault_url = os.getenv('AZURE_KEYVAULT_URL')
        self._client = None
        
    def _get_client(self):
        """Get or create Azure Key Vault client"""
        if self._client is None and self.vault_url:
            try:
                from azure.keyvault.secrets import SecretClient
                from azure.identity import ManagedIdentityCredential
                
                credential = ManagedIdentityCredential()
                self._client = SecretClient(vault_url=self.vault_url, credential=credential)
                logger.info(f"✅ Azure Key Vault client initialized: {self.vault_url}")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Azure Key Vault client: {e}")
                self._client = None
        return self._client
    
    async def get_secret(self, vault_secret_name: str, fallback_env: str = None) -> Optional[str]:
        """
        Get secret from Azure Key Vault with environment fallback
        
        Args:
            vault_secret_name: Secret name in Azure Key Vault
            fallback_env: Environment variable name for fallback
            
        Returns:
            Secret value or None if not found
        """
        # Try Azure Key Vault first
        if self.vault_url:
            try:
                client = self._get_client()
                if client:
                    secret = client.get_secret(vault_secret_name)
                    logger.info(f"✅ Retrieved secret from Azure Key Vault: {vault_secret_name}")
                    return secret.value
            except Exception as e:
                logger.warning(f"⚠️ Could not retrieve from Azure Key Vault ({vault_secret_name}): {e}")
        
        # Fallback to environment variable
        if fallback_env:
            env_value = os.getenv(fallback_env)
            if env_value:
                logger.info(f"✅ Using environment variable: {fallback_env}")
                return env_value
        
        logger.error(f"❌ Secret '{vault_secret_name}' not found in vault or environment")
        return None
    
    async def get_database_password(self) -> str:
        """Get database password (sf-dbpass)"""
        password = await self.get_secret('sf-dbpass', 'DB_PASSWORD') or ''
        logger.info("🔑 Database password fetched successfully")
        return password
    
    async def get_redis_password(self) -> str:
        """Get Redis password (sf-redispass)"""
        password = await self.get_secret('sf-redispass', 'REDIS_PASSWORD') or ''
        if password:
            logger.info("🔑 Redis password fetched successfully")
        return password
    
    async def get_api_key(self) -> str:
        """Get SentinelFlux API key (sf-apikey)"""
        api_key = await self.get_secret('sf-apikey', 'API_KEY') or ''
        if api_key:
            logger.info("🔑 SF API key fetched successfully")
        return api_key
    
    async def get_dnflux_apikey(self) -> str:
        """Get DNFlux VM2 API key (dnflux-apikey)"""
        api_key = await self.get_secret('dnflux-apikey', 'DNFLUX_INTERNAL_TOKEN') or ''
        if api_key:
            logger.info("🔑 DNFlux API key fetched successfully")
        return api_key

    async def get_brevo_api_key(self) -> Optional[str]:
        """Get Brevo API key from Azure Key Vault (secret name: brevo-api-key).

        Falls back to environment variable `BREVO_API` if not present in vault.
        Returns None if not found.
        """
        api_key = await self.get_secret('brevo-api-key', 'BREVO_API') or None
        if api_key:
            logger.info("🔑 Brevo API key fetched successfully")
        else:
            logger.warning("⚠️ Brevo API key not found in vault or environment")
        return api_key

# Global instance
vault_client = AzureVaultClient()
