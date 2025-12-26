#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
pcoカメラによる計測用アプリケーション「pco_experiment_manager」の計測結果保存周りの機能を実装するファイル
"""

__author__ = 'Tao Muto'
__version__ = '0.1.0'
__date__ = '2025.12.24'


import os
import queue
import datetime
import cv2
from PyQt6.QtCore import QThread, pyqtSignal, pyqtSlot, Qt, QTimer


BASE_DIR = "../out/" # 画像保存先フォルダ
FORMAT = "tif"

class Saver(QThread):
    """
    キューに溜まった画像データをディスクに保存するクラス。
    GUIやカメラ撮影とは非同期で動く。
    """

    def __init__(self, data_queue):
        super().__init__()
        self.data_queue = data_queue
        self.is_running = False
        self.is_new_recording = False

        self.trial_num = 0  # 現在何トライアル目であるかを把握するためのメソッド
        self.fram_in_trial_num = 0  # トライアル内で何フレーム目かを把握するためのメソッド


    def run(self):
        current_trial = -1

        while self.is_running or not self.data_queue.empty():
            if current_trial != self.trial_num:
                current_trial = self.trial_num
                trial_dir = os.path.join(self.path, str(current_trial))
                if not os.path.exists(trial_dir):
                    try:
                        os.makedirs(trial_dir)
                    except OSError as e:
                        print(f"Saver Error in function \"run\": {e}")
                    self.fram_in_trial_num = 0

            try:
                image_data, frame_num = self.data_queue.get(timeout=0.1)  # キューからデータを取り出す (ビジーウェイト軽減のために、タイムアウト付きでブロック)。data = (image_array, frame_number)。

                # 画像保存
                filename = os.path.join(trial_dir, f"{frame_num:06d}.{FORMAT}")  # ファイル名を生成
                cv2.imwrite(filename, image_data)  # pcoのrawデータはuint16が多く、cv2.imwriteはuint16のTIFF保存に対応しているので、OpenCVを使用。

                # 保存したフレーム数を更新
                self.fram_in_trial_num += 1

                # タスク完了を通知 (キューの管理用)
                self.data_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                print(f"Saver Error in function \"run\": {e}")

    def stop(self):
        self.is_running = False

    def make_memo():
        """
        実験の背景情報の記録用メモを作成するメソッド
        """

    def next_trial(self):
        """
        トライアル管理のためのメソッド
        このメソッドが呼び出されると、インスタンス内の何トライアル目かの情報が更新される。
        """

        self.trial_num += 1
        self.fram_in_trial_num = 0

def start_new_recording(self):
    """
    新しいレコーディングを始めるためのメソッド
    レコーディングごとの保存ディレクトリを作成し、レコーディングを始める。
    """

    today = datetime.datetime.now()
    self.path = os.path.join(BASE_DIR, today.strftime('%Y%m%d%H%M%S'))

    if not os.path.exists(self.path):  # 保存用ディレクトリが存在しない場合は作成する。
        try:
            os.makedirs(self.path)
        except OSError as e:
            print(f"Saver Error in function \"__init__\": {e}")