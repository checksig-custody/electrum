from functools import partial
import traceback
import sys
from typing import TYPE_CHECKING

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QGridLayout, QLineEdit, QPushButton, QFileDialog, QCheckBox

from electrum.plugin import hook
from electrum.i18n import _
from electrum.gui.qt.util import ThreadedButton, Buttons, EnterButton, WindowModalDialog, OkButton, CloseButton, read_QIcon
from electrum.gui.qt.main_window import StatusBarButton

from .checksig import ChecksigPlugin

if TYPE_CHECKING:
    from electrum.gui.qt import ElectrumGui
    from electrum.gui.qt.main_window import ElectrumWindow
    from electrum.wallet import Abstract_Wallet


class Plugin(ChecksigPlugin):

    def __init__(self, *args):
        ChecksigPlugin.__init__(self, *args)
        self._init_qt_received = False
        self.status_bar_created = False

    def requires_settings(self):
        return True

    def settings_widget(self, window: WindowModalDialog):
        if not self.status_bar_created:
            window.parent().show_warning(_("Restart electrum to finalize the changes"))
        return QLabel(_(''))

    @hook
    def create_status_bar(self, parent):
        self.status_bar_created = True
        b = StatusBarButton(read_QIcon('checksig.png'), "Checksig", partial(self.settings_dialog, parent))
        parent.addPermanentWidget(b)

    def settings_dialog(self, window: WindowModalDialog):
        wallet = window.parent().wallet
        d = WindowModalDialog(window, "Checksig " + _("Settings"))
        vbox = QVBoxLayout(d)
        vbox.addWidget(QLabel(_("Description")))
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
        
        sync_button = QPushButton(_("Sync"))
        sync_button.clicked.connect(partial(self.load_env, wallet))
        if not self.checksig_config.get(wallet, 'enabled'):
            sync_button.setDisabled(True)
        grid.addWidget(sync_button, 4, 0)

        def save_settings():
            self.checksig_config.set(wallet, 'enabled', enabled.isChecked())
            if enabled.isChecked():
                sync_button.setDisabled(False)
            else:
                sync_button.setDisabled(True)
            self.checksig_config.set(wallet, 'env', env_linedit.text())
            self.checksig_config.set(wallet, 'whitelist_path', whitelist_path_linedit.text())
            self.checksig_config.set(wallet, 'transactions_path', transactions_path_linedit.text())

        save_button = QPushButton(_("Save"))
        save_button.clicked.connect(save_settings)

        # grid.addLayout(Buttons(save_button, CloseButton(d), OkButton(d)), 4, 1)
        grid.addLayout(Buttons(save_button), 4, 1)

        return d.exec_()

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