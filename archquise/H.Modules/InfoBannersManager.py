# Proprietary License Agreement

# Copyright (c) 2024-29 CodWiz

# Permission is hereby granted to any person obtaining a copy of this software and associated documentation files (the "Software"), to use the Software for personal and non-commercial purposes, subject to the following conditions:

# 1. The Software may not be modified, altered, or otherwise changed in any way without the explicit written permission of the author.

# 2. Redistribution of the Software, in original or modified form, is strictly prohibited without the explicit written permission of the author.

# 3. The Software is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and non-infringement. In no event shall the author or copyright holder be liable for any claim, damages, or other liability, whether in an action of contract, tort, or otherwise, arising from, out of, or in connection with the Software or the use or other dealings in the Software.

# 4. Any use of the Software must include the above copyright notice and this permission notice in all copies or substantial portions of the Software.

# 5. By using the Software, you agree to be bound by the terms and conditions of this license.

# For any inquiries or requests for permissions, please contact archquise@gmail.com.

# ---------------------------------------------------------------------------------
# Name: InfoBannersManager
# Description: Автоматически меняет баннеры на случайные из выбранного списка через заданный промежуток времени
# Author: @hikka_mods
# ---------------------------------------------------------------------------------
# meta developer: @hikka_mods

import logging
import random

from .. import loader

logger = logging.getLogger(__name__)


@loader.tds
class InfoBannersManagerMod(loader.Module):
    """Автоматически меняет баннеры на случайные из выбранного списка через заданный промежуток времени"""

    strings = {"name": "InfoBannersManager"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "enabled",
                False,
                "Включить автоматическую смену баннеров",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "delay",
                60,
                "Задержка между изменениями баннеров в секундах",
                validator=loader.validators.Integer(minimum=1),
            ),
            loader.ConfigValue(
                "bannerslist",
                None,
                "Список ссылок на баннеры",
                validator=loader.validators.Series(validator=loader.validators.Link()),
            ),
        )

    async def banner_changer(self):
        """Change banner periodically"""
        try:
            if not self.config["bannerslist"]:
                logger.warning("Banners list is empty!")
                return

            banner = random.choice(self.config["bannerslist"])
            instance = self.lookup("HerokuInfo")
            if not instance:
                instance = self.lookup("HikkaInfo")
            
            if instance:
                instance.config["banner_url"] = banner
                logger.info(f"Banner changed to: {banner}")
            else:
                logger.warning("Info module not found!")

        except Exception as e:
            logger.exception(f"Error changing banner: {e}")

    @loader.loop(interval=60, autostart=False)
    async def banner_loop(self):
        """Main banner changing loop"""
        if not self.config["enabled"]:
            return
            
        await self.banner_changer()
        
        # Update interval from config
        self.banner_loop.set_interval(self.config["delay"])

    async def client_ready(self):
        """Initialize the banner changer loop"""
        if self.config["enabled"]:
            self.banner_loop.start()

    def on_config_update(self, config_key, new_value):
        """Handle config updates"""
        if config_key == "enabled":
            if new_value:
                self.banner_loop.start()
            else:
                self.banner_loop.stop()
        elif config_key == "delay":
            # Update interval immediately
            self.banner_loop.set_interval(new_value)
