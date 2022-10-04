import asyncio
import hashlib
import json
import sys
import traceback
from typing import Union, TYPE_CHECKING

import base64

from electrum.plugin import BasePlugin, hook
from electrum.crypto import aes_encrypt_with_iv, aes_decrypt_with_iv
from electrum.i18n import _
from electrum.util import log_exceptions, ignore_exceptions, make_aiohttp_session, BitcoinException
from electrum.network import Network
from pathlib import Path
import json

import os

if TYPE_CHECKING:
    from electrum.wallet import Abstract_Wallet


class ChecksigConfig:

    def __init__(self, config):
        self.config = config
        if self.config.get('checksig') is None:
            self.config.set_key('checksig', {})
        self.checksig_config = self.config.get('checksig')

    def set(self, wallet, key, value):
        if str(wallet) not in self.checksig_config:
            self.checksig_config[str(wallet)] = {}
        self.checksig_config[str(wallet)][key] = value
        self.config.save_user_config()

    def get(self, wallet, key):
        if str(wallet) not in self.checksig_config:
            self.checksig_config[str(wallet)] = {}
        if key not in self.checksig_config[str(wallet)]:
            if key == "env":
                self.checksig_config[str(wallet)][key] = "test01"
            if key == "enabled":
                self.checksig_config[str(wallet)][key] = False
            if key == "whitelist_path":
                self.checksig_config[str(wallet)][key] = "/"
            if key == "transactions_path":
                self.checksig_config[str(wallet)][key] = "/"
        return self.checksig_config[str(wallet)][key]


class ChecksigPlugin(BasePlugin):

    def __init__(self, parent, config, name):
        BasePlugin.__init__(self, parent, config, name)

        self.checksig_config = ChecksigConfig(self.config)
    
        self.base_dir = os.path.join(config.electrum_path(), 'checksig')


    def load_env(self, wallet: 'Abstract_Wallet'):

        env = self.checksig_config.get(wallet, 'env')
        whitelist_path = Path(self.checksig_config.get(wallet, 'whitelist_path'))
        transaction_csv = Path(self.checksig_config.get(wallet, 'transactions_path')) / env / f"{env}.csv"
        for i in range(100):
            p = Path(whitelist_path, f"{env}-frzn0-block{i:02}.json")
            if not p.exists():
                break
            with open(p, encoding="utf-8") as f:
                data = json.load(f)["frzn_0"]
            for address in data:
                try:
                    wallet.import_address(address)
                except BitcoinException:
                    pass
        p = Path(whitelist_path, f"{env}-whitelist.json")
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        for key in ("frzn_whitelist", "cold_whitelist", "cold_1"):
            for address in data[key]:
                try:
                    wallet.import_address(address)
                except BitcoinException:
                    pass