"""Telegram webhook endpoint."""
from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.types import Update
from fastapi import APIRouter, Request

router = APIRouter()


@router.post("/webhook/telegram")
async def telegram_webhook(request: Request) -> dict:
    bot: Bot = request.app.state.bot
    dp: Dispatcher = request.app.state.dp
    data = await request.json()
    update = Update.model_validate(data, context={"bot": bot})
    await dp.feed_update(bot, update)
    return {"ok": True}
