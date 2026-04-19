from aiogram import Router

from . import admin, advertiser, shop, start


def build_root_router() -> Router:
    router = Router()
    router.include_router(start.router)
    router.include_router(shop.router)
    router.include_router(advertiser.router)
    router.include_router(admin.router)
    return router
