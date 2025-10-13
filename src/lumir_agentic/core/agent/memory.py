import asyncio
import os
from typing import Optional, Dict, Any, ClassVar
from dotenv import load_dotenv
from agents.extensions.memory import EncryptedSession, SQLAlchemySession
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

load_dotenv()


class EncryptedMemoryManager:
    """
    Enhanced encrypted memory manager that supports both SQLite and PostgreSQL
    with proper configuration management and security features.
    """
    
    # Class-level engine cache to ensure persistence
    _engines: ClassVar[Dict[str, AsyncEngine]] = {}
    
    def __init__(self, session_id: str, encryption_key: 
        Optional[str] = None, 
        ttl: int = int(os.getenv("TTL"))):

        self.session_id = session_id
        self.encryption_key = encryption_key or self._generate_encryption_key()
        self.ttl = ttl
        
    def _generate_encryption_key(self) -> str:
        """Generate a deterministic encryption key based on session_id"""
        import hashlib
        # Create a deterministic key based on session_id
        # This ensures the same session_id always gets the same encryption key
        key_material = f"lumir_agentic_session_{self.session_id}".encode('utf-8')
        hash_digest = hashlib.sha256(key_material).digest()
        # Fernet keys must be 32 bytes, base64-encoded
        from base64 import urlsafe_b64encode
        return urlsafe_b64encode(hash_digest).decode()
    
    def _get_database_config(self, db_type: str = "sqlite") -> Dict[str, Any]:
        """Get database configuration based on type"""
        if db_type.lower() == "sqlite":
            url = f"sqlite+aiosqlite:///{os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'cache', 'conversations.db'))}"
            return {
                "url": url,
                "description": "SQLite local database"
            }
        elif db_type.lower() == "postgresql":
            # Use environment variables for PostgreSQL configuration
            host = os.getenv("POSTGRES_HOST")
            port = os.getenv("POSTGRES_PORT")
            user = os.getenv("POSTGRES_USER")
            password = os.getenv("POSTGRES_PASSWORD")
            database = os.getenv("POSTGRES_DB")
            
            if not all([host, port, user, password, database]):
                raise ValueError("PostgreSQL environment variables are not properly set")
            
            return {
                "url": f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}",
                "description": f"PostgreSQL database at {host}:{port}/{database}"
            }
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
    
    async def create_encrypted_session(self, db_type: str = "sqlite") -> EncryptedSession:
        """
        Create an encrypted session with the specified database type
        
        Args:
            db_type: Either 'sqlite' or 'postgresql'
            
        Returns:
            EncryptedSession: Configured encrypted session
        """
        db_config = self._get_database_config(db_type)
        
        print(f"Creating {db_config['description']} session...")
        print(f"Session ID: {self.session_id}")
        print(f"TTL: {self.ttl} seconds")
        
        # Get or create persistent engine
        engine_key = f"{db_type}_{db_config['url']}"
        if engine_key not in self._engines:
            self._engines[engine_key] = create_async_engine(db_config["url"])
        
        engine = self._engines[engine_key]
        
        # Create underlying SQLAlchemy session with persistent engine
        underlying_session = SQLAlchemySession(
            session_id=self.session_id,
            engine=engine,
            create_tables=True,
        )
        
        # Wrap with encryption
        encrypted_session = EncryptedSession(
            session_id=self.session_id,
            underlying_session=underlying_session,
            encryption_key=self.encryption_key,
            ttl=self.ttl,
        )
        
        return encrypted_session
