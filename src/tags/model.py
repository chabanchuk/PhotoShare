from pydantic import BaseModel

class TagModel(BaseModel):
    tag: str

    class Config:
        orm_mode = True

class TagResponseModel(BaseModel):
    id: int
    tag: str

    class Config:
        orm_mode = True
