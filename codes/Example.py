#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
pcoカメラによる計測用アプリケーション「pco_experiment_manager」の実行ファイル
"""

__author__ = 'Tao Muto'
__version__ = '0.1.2'
__date__ = '2025.12.26'


import sys
import queue

from PyQt6.QtWidgets import QApplication

from UIer import UIer
from CameraHandler import CameraHandler
from Saver import Saver
from Conductor import Conductor
from TriggerHandler import TriggerHandler


def run():
    app = QApplication(sys.argv)
    
    # スレッド間通信用のキュー
    data_queue = queue.Queue(maxsize=200)
    
    # 各スレッドのインスタンス化
    a_camera_handler = CameraHandler(data_queue)
    a_conductor = Conductor()
    a_trigger_handler = TriggerHandler()
    a_saver = Saver(data_queue, a_camera_handler, a_conductor)
    a_window = UIer(a_camera_handler, a_saver, a_trigger_handler)
    
    # スレッド開始
    a_camera_handler.start()
    a_saver.start()
    
    # 描画開始
    a_window.show()

    # 終了操作
    exit_code = app.exec()
    a_trigger_handler.close()  # 終了時にデバイスを切断
    sys.exit(exit_code)


if __name__ == '__main__':
    run()