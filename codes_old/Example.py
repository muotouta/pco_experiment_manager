#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
pcoカメラによる計測用アプリケーションの実行ファイル
"""

__author__ = 'Tao Muto'
__version__ = '0.1.0'
__date__ = '2025.12.24'


import sys
from PyQt6.QtWidgets import QApplication

from UIer import UIer


def run():
    pass
    


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = UIer()
    window.show()
    sys.exit(app.exec())