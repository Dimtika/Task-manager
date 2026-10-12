from contextlib import asynccontextmanager
from typing import Annotated
from fastapi import FastAPI, Cookie, Response, Form, HTTPException, status
from sqlmodel import Field, DateTime, Column, Session, SQLModel, create_engine, select
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt

class User(SQLModel, table=True):
    id: int | None = Field(default=None,primary_key=True)
    username: str
    password: str

class Task(SQLModel, table=True):
    id: int | None = Field(default=None,primary_key=True)
    title: str
    description: str
    status: str
    priority: int
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)))
    
    updated_at: datetime | None = Field(default=None, 
        sa_column=Column(DateTime(timezone=True)))

    owner_id: int | None = Field(default=None, foreign_key='user.id')

engine = create_engine("mysql://task:task@db/task", echo=True)

jwt_key = '8QEWgTjyiO8KN1L9.YkzRl6wM0;&gHTBO`cdyz!0a!Q>Gl6!hxI$7f@vzVM'

@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    yield

app = FastAPI(lifespan=lifespan)

@app.get('/')
async def read_root(token: Annotated[str | None, Cookie()] = None):
    try:
        id = jwt.decode(token,jwt_key, algorithms=['HS256'])

    except jwt.ExpiredSignatureError:
        id = 'Expired'
    
    return {'user_id': id}

@app.post('/login')
async def log_user(username: Annotated[str, Form()], password: Annotated[str, Form()], response: Response):
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).first()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Неверное имя пользователя или пароль'
            )

        password_bytes = password.encode('utf-8')
        hashed_bytes = user.password.encode('utf-8') 
        
        if not bcrypt.checkpw(password_bytes, hashed_bytes):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверное имя пользователя или пароль"
            )

        now = datetime.now(timezone.utc)

        response.set_cookie('token',jwt.encode({"user_id": user.id, "exp": now + timedelta(minutes=30)}, jwt_key, algorithm='HS256'))
        
        return 'You are logged in'
        
@app.post('/register', status_code=status.HTTP_201_CREATED)
async def reg_user(username: Annotated[str, Form()], password: Annotated[str, Form()]):
    statement = select(User).where(User.username == username)
    
    with Session(engine) as session:
        existing_user = session.exec(statement).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким именем уже зарегистрирован"
            )

        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed_pwd_bytes = bcrypt.hashpw(password_bytes, salt)
        
        hashed_pwd_str = hashed_pwd_bytes.decode('utf-8')
        
        new_user = User(username=username, password=hashed_pwd_str)
        
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
    
    return 'User registered!'

@app.get('/task')
async def get_task(token: Annotated[str | None, Cookie()] = None):
    try:
        user_data = jwt.decode(token,jwt_key, algorithms=['HS256'])
    
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
             detail='User is not authorized'
        )

    except jwt.exceptions.DecodeError:
        raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                     detail='User is not authorized'
        )

    user_id = user_data['user_id']

    with Session(engine) as session:
        tasks = session.scalars(select(Task).where(Task.owner_id == user_id)).all()

    return tasks

@app.post('/task')
async def create_task(title: Annotated[str, Form()], description: Annotated[str, Form()], token: Annotated[str | None, Cookie()] = None):
    try:
        user_data = jwt.decode(token,jwt_key, algorithms=['HS256'])
    
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
             detail='User is not authorized'
        )

    except jwt.exceptions.DecodeError:
        raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                     detail='User is not authorized'
        )


    user_id = user_data['user_id']

    with Session(engine) as session:
        session.add(Task(title=title, description=description, owner_id=user_id))
        session.commit()

    return 'Task created!'

@app.put('/task')
async def change_task(task_id: Annotated[int, Form()], name: Annotated[str, Form()], description: Annotated[str, Form()], token: Annotated[str | None, Cookie()] = None):
    try:
        user_data = jwt.decode(token,jwt_key, algorithms=['HS256'])
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='User is not authorized'
        )
    
    except jwt.exceptions.DecodeError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='User is not authorized'
        )

    user_id = user_data['user_id']

    with Session(engine) as session:
        result = session.exec(select(Task).where(Task.owner_id == user_id).where(Task.id == task_id))
        task = result.one()

        if name is not None:
            task.name = name
        
        if description is not None:
            task.description = description

        task.updated_at = datetime.now

        session.add(task)
        session.commit()

    return "Task's data changed"

@app.delete('/task')
async def delete_task(task_id: Annotated[int, Form()], token: Annotated[str | None, Cookie()] = None):
    try:
        user_data = jwt.decode(token,jwt_key, algorithms=['HS256'])
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='User is not authorized'
        )
    
    except jwt.exceptions.DecodeError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='User is not authorized'
        )

    user_id = user_data['user_id']

    with Session(engine) as session:
        result = session.exec(select(Task).where(Task.owner_id == user_id).where(Task.id == task_id))
        task = result.one()
       
        session.delete(task)
        session.commit()

    return "Task deleted"


if __name__ == '__main__':
    SQLModel.metadata.create_all(engine)