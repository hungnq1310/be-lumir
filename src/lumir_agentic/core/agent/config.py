from pydantic import BaseModel  


class UserInfo(BaseModel):
    user_id: str
    full_user_name:str = None
    birthday:str = None
    account_trading_id:str = None
    session_id: str= None

