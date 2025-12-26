#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
pcoカメラによる計測用アプリケーションの実行ファイル
"""

__author__ = 'Tao Muto'
__version__ = '0.1.0'
__date__ = '2025.12.24'


import os
import queue
import cv2
from PyQt6.QtCore import QThread, pyqtSignal, pyqtSlot, Qt, QTimer


SAVE_DIR = "./../out/" # 画像保存先フォルダ

class FileWriter(QThread):
    """
    【消費者 (Consumer)】
    キューに溜まった画像データをひたすらディスクに保存するスレッド。
    GUIやカメラ撮影とは非同期で動くため、保存処理が重くなっても撮影を邪魔しない。
    """
    def __init__(self, data_queue):
        super().__init__()
        self.data_queue = data_queue
        self.is_running = True

        # 保存用ディレクトリが存在しない場合は作成する
        if not os.path.exists(SAVE_DIR):
            try:
                os.makedirs(SAVE_DIR)
            except OSError as e:
                print(f"Error creating directory {SAVE_DIR}: {e}")


    def run(self):
        print("FileWriter: Start")
        while self.is_running or not self.data_queue.empty():
            try:
                # キューからデータを取り出す (タイムアウト付きでブロック)
                # data = (image_array, frame_number)
                image_data, frame_num = self.data_queue.get(timeout=0.1)
                
                # ファイル名を生成 (例: frame_000123.tif)
                # 計測用なので、情報の欠損がないTIFF形式やPNG形式推奨
                filename = os.path.join(SAVE_DIR, f"frame_{frame_num:06d}.tif")
                
                # 画像保存 (OpenCVを使用)
                # 注意: pcoのrawデータはuint16が多い。cv2.imwriteはuint16のTIFF保存に対応している
                cv2.imwrite(filename, image_data)
                
                # タスク完了を通知 (キューの管理用)
                self.data_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"FileWriter Error: {e}")
        
        print("FileWriter: Stop")

    def stop(self):
        self.is_running = False
