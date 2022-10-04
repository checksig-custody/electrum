from functools import partial
import traceback
import sys
from typing import TYPE_CHECKING

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QGridLayout, QLineEdit, QPushButton, QFileDialog, QCheckBox

from electrum.plugin import hook
from electrum.i18n import _
from electrum.gui.qt.util import ThreadedButton, Buttons, EnterButton, WindowModalDialog, OkButton, CloseButton

from .checksig import ChecksigPlugin

if TYPE_CHECKING:
    from electrum.gui.qt import ElectrumGui
    from electrum.gui.qt.main_window import ElectrumWindow
    from electrum.wallet import Abstract_Wallet


class Plugin(ChecksigPlugin):

    def __init__(self, *args):
        ChecksigPlugin.__init__(self, *args)
        self._init_qt_received = False

    def requires_settings(self):
        return True

    def settings_widget(self, window: WindowModalDialog):
        return EnterButton(_('Settings'),
                           partial(self.settings_dialog, window))

    def settings_dialog(self, window: WindowModalDialog):
        wallet = window.parent().wallet
        d = WindowModalDialog(window, _("Checksig Settings"))
        vbox = QVBoxLayout(d)
        vbox.addWidget(QLabel("Description"))
        grid = QGridLayout()
        vbox.addLayout(grid)
        
        grid.addWidget(QLabel(_('Enabled')), 0, 0)
        enabled = QCheckBox("")
        enabled.setChecked(self.checksig_config.get(wallet, 'enabled'))
        grid.addWidget(enabled, 0, 1)

        grid.addWidget(QLabel(_('Env')), 1, 0)
        env_linedit = QLineEdit()
        env_linedit.setMinimumWidth(300)
        env_linedit.setText(self.checksig_config.get(wallet, 'env'))
        grid.addWidget(env_linedit, 1, 1)

        whitelist_path_button = QPushButton("Whitelist path")
        grid.addWidget(whitelist_path_button, 2, 0)
        whitelist_path_linedit = QLineEdit()
        whitelist_path_linedit.setText(self.checksig_config.get(wallet, 'whitelist_path'))
        whitelist_path_button.clicked.connect(lambda: self.choose_file(window, whitelist_path_linedit, "Whitelist directory"))
        grid.addWidget(whitelist_path_linedit, 2, 1)

        transactions_path_button = QPushButton("Transactions path")
        grid.addWidget(transactions_path_button, 3, 0)
        transactions_path_linedit = QLineEdit()
        transactions_path_linedit.setText(self.checksig_config.get(wallet, 'transactions_path'))
        transactions_path_button.clicked.connect(lambda: self.choose_file(window, transactions_path_linedit, "Transactions directory"))
        grid.addWidget(transactions_path_linedit, 3, 1)

        vbox.addLayout(Buttons(CloseButton(d), OkButton(d)))

        if not d.exec_():
            return False

        self.checksig_config.set(wallet, 'enabled', enabled.isChecked())
        self.checksig_config.set(wallet, 'env', env_linedit.text())
        self.checksig_config.set(wallet, 'whitelist_path', whitelist_path_linedit.text())
        self.checksig_config.set(wallet, 'transactions_path', transactions_path_linedit.text())

        return True

    def choose_file(self, parent, linedit, title):
        dirname = QFileDialog.getExistingDirectory(
            parent=parent,
            caption=_(title),
            directory=linedit.text(),
        )
        if dirname:
            linedit.setText(dirname)

    @hook
    def init_qt(self, gui: 'ElectrumGui'):
        # see init_qt in label sync plugin for explanation
        if self._init_qt_received:  
            return
        self._init_qt_received = True
        for window in gui.windows:
            self.load_wallet(window.wallet, window)

    @hook
    def load_wallet(self, wallet: 'Abstract_Wallet', window: 'ElectrumWindow'):
        if self.checksig_config.get(wallet, 'enabled'):
            self.load_env(wallet)