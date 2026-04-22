from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import date, timedelta
from sqlalchemy import create_engine, Column, String, Date, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import httpx
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = "sqlite:///./habits.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class HabitEntry(Base):
    __tablename__ = "habits"
    id = Column(String, primary_key=True)
    date = Column(Date, primary_key=True)
    completed = Column(Boolean, default=False)

Base.metadata.create_all(bind=engine)

class MarkRequest(BaseModel):
    habit: str
    date: str

# AI Motivation endpoint
QWEN_API_URL = os.getenv("QWEN_API_URL", "http://localhost:42005/v1/chat/completions")
QWEN_API_KEY = os.getenv("QWEN_API_KEY", "my-secret-qwen-key")

@app.get("/motivation")
async def get_motivation():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                QWEN_API_URL,
                headers={"Authorization": f"Bearer {QWEN_API_KEY}"},
                json={
                    "model": "coder-model",
                    "messages": [
                        {"role": "system", "content": "You are a motivational coach. Give ONE short, powerful sentence (max 10 words) to encourage someone building a daily habit."},
                        {"role": "user", "content": "Give me a motivational quote for habit tracking"}
                    ],
                    "temperature": 0.8,
                    "max_tokens": 50
                },
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                message = data["choices"][0]["message"]["content"].strip()
                return {"quote": message}
            else:
                return {"quote": "💪 Keep going! Every day counts."}
    except Exception as e:
        print(f"AI error: {e}")
        return {"quote": "🔥 Stay consistent! You've got this."}

@app.get("/streak")
def get_streak(habit: str):
    session = SessionLocal()
    today = date.today()
    streak = 0
    today_entry = session.query(HabitEntry).filter_by(id=habit, date=today).first()
    if today_entry and today_entry.completed:
        streak = 1
        for i in range(1, 100):
            check_date = today - timedelta(days=i)
            entry = session.query(HabitEntry).filter_by(id=habit, date=check_date).first()
            if entry and entry.completed:
                streak += 1
            else:
                break
    session.close()
    return {"streak": streak}

@app.get("/history")
def get_history(habit: str):
    session = SessionLocal()
    today = date.today()
    history = []
    for i in range(7):
        d = today - timedelta(days=6 - i)
        entry = session.query(HabitEntry).filter_by(id=habit, date=d).first()
        completed = 1 if (entry and entry.completed) else 0
        history.append({"date": d.isoformat(), "completed": completed})
    session.close()
    return history

@app.post("/mark")
def mark(request: MarkRequest):
    session = SessionLocal()
    d = date.fromisoformat(request.date)
    entry = session.query(HabitEntry).filter_by(id=request.habit, date=d).first()
    if entry:
        entry.completed = True
    else:
        entry = HabitEntry(id=request.habit, date=d, completed=True)
        session.add(entry)
    session.commit()
    session.close()
    return {"status": "ok"}