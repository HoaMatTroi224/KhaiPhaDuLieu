import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .config import settings
from .database import get_db
from .models import User
from uuid import UUID

security = HTTPBearer()

jwks_url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"
jwks_client = PyJWKClient(jwks_url, cache_jwk_set=True)

async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    try:
        token = credentials.credentials

        signing_key = jwks_client.get_signing_key_from_jwt(token)

        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            audience="authenticated",
            issuer=f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1",
            options={"verify_exp": True}
        )

        return payload
        
    except jwt.exceptions.PyJWKClientError as e:
        raise HTTPException(status_code=401, detail=f"JWKS verification failed: {str(e)}")
    except jwt.exceptions.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired. Please log in again.")
    except jwt.exceptions.DecodeError as e:
        raise HTTPException(status_code=401, detail=f"Token decode error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))
    

# async def get_current_user(
#     payload: dict = Depends(verify_token),
#     db: AsyncSession = Depends(get_db)
# ) -> User:
#     result = await db.execute(select(User).where(User.id == payload["user_id"]))
#     user = result.scalar_one_or_none()
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")
    
#     return user
      

async def get_current_user_id(
    payload: dict = Depends(verify_token)
) -> User:
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid toke: missing user ID")
    
    return UUID(user_id)
