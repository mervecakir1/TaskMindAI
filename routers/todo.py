from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Path, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from starlette import status
from ..models import ToDo
from ..database import SessionLocal
from ..routers.auth import get_current_user
from fastapi.templating import Jinja2Templates
from starlette.responses import RedirectResponse
from dotenv import load_dotenv
import os
from pathlib import Path as FilePath

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
import markdown
from bs4 import BeautifulSoup

templates = Jinja2Templates(directory="app/templates")

load_dotenv(dotenv_path=FilePath(__file__).parent.parent / ".env")

router = APIRouter(
    prefix="/todos",
    tags=["ToDo"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


class ToDoRequest(BaseModel):
    title: str = Field(min_length=3)
    description: str = Field(min_length=3, max_length=2000)
    priority: int = Field(gt=0, lt=6)
    complete: bool = False


def redirect_to_login():
    redirect_response = RedirectResponse(
        url="/auth/login-page",
        status_code=status.HTTP_302_FOUND
    )
    redirect_response.delete_cookie("access_token")
    return redirect_response


@router.get("/todo-page")
async def render_todo_page(request: Request, db: db_dependency):
    try:
        user = await get_current_user(request.cookies.get("access_token"))
        if user is None:
            return redirect_to_login()

        todos = db.query(ToDo).filter(ToDo.owner_id == user.get("id")).all()
        return templates.TemplateResponse(
            "todo.html",
            {"request": request, "todos": todos, "user": user}
        )
    except Exception:
        return redirect_to_login()


@router.get("/add-todo-page")
async def render_add_todo_page(request: Request):
    try:
        user = await get_current_user(request.cookies.get("access_token"))
        if user is None:
            return redirect_to_login()

        return templates.TemplateResponse(
            "add-todo.html",
            {"request": request, "user": user}
        )
    except Exception:
        return redirect_to_login()


@router.get("/edit-todo-page/{todo_id}")
async def render_edit_todo_page(request: Request, todo_id: int, db: db_dependency):
    try:
        user = await get_current_user(request.cookies.get("access_token"))
        if user is None:
            return redirect_to_login()

        todo = db.query(ToDo).filter(
            ToDo.id == todo_id,
            ToDo.owner_id == user.get("id")
        ).first()

        return templates.TemplateResponse(
            "edit-todo.html",
            {"request": request, "todo": todo, "user": user}
        )
    except Exception:
        return redirect_to_login()


@router.get("/", status_code=status.HTTP_200_OK)
async def read_all(user: user_dependency, db: db_dependency):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return db.query(ToDo).filter(ToDo.owner_id == user.get("id")).all()


@router.get("/todo/{todo_id}", status_code=status.HTTP_200_OK)
async def read_by_id(
    user: user_dependency,
    db: db_dependency,
    todo_id: int = Path(gt=0)
):
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication Failed")

    todo_model = db.query(ToDo).filter(
        ToDo.id == todo_id,
        ToDo.owner_id == user.get("id")
    ).first()

    if todo_model is not None:
        return todo_model

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Todo not found"
    )


def markdown_to_text(markdown_string: str) -> str:
    html = markdown.markdown(markdown_string)
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text()


def create_todo_with_gemini(todo_title: str, todo_description: str) -> str:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables.")

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=api_key
    )

    prompt = f"""
You are helping improve a to-do item description.

Task title:
{todo_title}

Current description:
{todo_description}

Please rewrite the description so it becomes:
- clear
- practical
- slightly more detailed
- still concise
- suitable for a to-do list

Only return the improved description text.
"""

    response = llm.invoke([HumanMessage(content=prompt)])
    return markdown_to_text(response.content).strip()


@router.post("/todo", status_code=status.HTTP_201_CREATED)
async def create_todo(user: user_dependency, db: db_dependency, todo_request: ToDoRequest):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    final_description = todo_request.description

    try:
        final_description = create_todo_with_gemini(
            todo_title=todo_request.title,
            todo_description=todo_request.description
        )
    except Exception as e:
        print(f"Gemini error: {e}")

    todo_model = ToDo(
        title=todo_request.title,
        description=final_description,
        priority=todo_request.priority,
        complete=todo_request.complete,
        owner_id=user.get("id")
    )

    db.add(todo_model)
    db.commit()
    db.refresh(todo_model)

    return todo_model


@router.put("/todo/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_todo(
    user: user_dependency,
    db: db_dependency,
    todo_request: ToDoRequest,
    todo_id: int = Path(gt=0)
):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    todo_model = db.query(ToDo).filter(
        ToDo.id == todo_id,
        ToDo.owner_id == user.get("id")
    ).first()

    if todo_model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found"
        )

    todo_model.title = todo_request.title
    todo_model.description = todo_request.description
    todo_model.priority = todo_request.priority
    todo_model.complete = todo_request.complete

    db.commit()


@router.delete("/todo/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(user: user_dependency, db: db_dependency, todo_id: int = Path(gt=0)):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    todo_model = db.query(ToDo).filter(
        ToDo.id == todo_id,
        ToDo.owner_id == user.get("id")
    ).first()

    if todo_model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found"
        )

    db.delete(todo_model)
    db.commit()