#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
pcoカメラによる計測用アプリケーション「pco_experiment_manager」の計測結果保存周りの機能を実装するファイル
"""

__author__ = 'Tao Muto'
__version__ = '0.1.3'
__date__ = '2025.12.27'


import os
import queue
import datetime
import cv2
import numpy as np
import time
from PyQt6.QtCore import QThread, pyqtSignal, pyqtSlot, Qt, QTimer


BASE_DIR = "../out/" # 画像保存先フォルダ
ROW_FORMAT = "tif"
IMG_FORMAT = "jpg"

class Saver(QThread):
    """
    キューに溜まった画像データをディスクに保存するクラス。
    """

    def __init__(self, data_queue, a_camera_handler, a_conductor):
        super().__init__()
        self.data_queue = data_queue
        self.is_running = True
        self.is_new_recording = False

        self.path = None
        self.trial_num = 0  # 現在何トライアル目であるかを把握するためのメソッド
        self.fram_in_trial_num = 0  # トライアル内で何フレーム目かを把握するためのメソッド
        self.a_camera_handler = a_camera_handler
        self.a_conductor = a_conductor


    def run(self):
        current_trial = -1
        #######################
        # -1をもちいるやり方をやめる。保存画像の最初の一枚の名前がおかしくなる。
        #######################


        #######################
        # トライアル間の時間が短い場合には、データをトライアル事にわけてディレクトリに保存することをしっぱいして、境目の画像が本来はいるべきディレクトリでないところにはいってしまうのでは？それをどう避ける。
        #######################

        while self.is_running or not self.data_queue.empty():
            if self.path is None:
                time.sleep(0.1)
                continue

            if current_trial != self.trial_num:
                current_trial = self.trial_num
                trial_dir = os.path.join(self.path, str(current_trial))

                if not os.path.exists(trial_dir):
                    try:
                        os.makedirs(trial_dir)
                    except OSError as e:
                        print(f"Saver Error in function \"run\": {e}")

                row_format_dir = os.path.join(trial_dir, ROW_FORMAT)
                if not os.path.exists(row_format_dir):
                    try:
                        os.makedirs(row_format_dir)
                    except OSError as e:
                        print(f"Saver Error in function \"run\": {e}")

                img_format_dir = os.path.join(trial_dir, IMG_FORMAT)
                if not os.path.exists(img_format_dir):
                    try:
                        os.makedirs(img_format_dir)
                    except OSError as e:
                        print(f"Saver Error in function \"run\": {e}")

            try:
                image_data, frame_num = self.data_queue.get(timeout=0.1)  # キューからデータを取り出す (ビジーウェイト軽減のために、タイムアウト付きでブロック)。data = (image_array, frame_number)。

                # 圧縮なしデータを保存
                row_format_filename = os.path.join(row_format_dir, f"{self.fram_in_trial_num:06d}.{ROW_FORMAT}")  # ファイル名を生成
                cv2.imwrite(row_format_filename, image_data)  # pcoのrawデータはuint16が多く、cv2.imwriteはuint16のTIFF保存に対応しているので、OpenCVを使用。

                # 画像保存
                img_format_filename = os.path.join(img_format_dir, f"{self.fram_in_trial_num:06d}.{IMG_FORMAT}")  # ファイル名を生成
                cv2.imwrite(img_format_filename, self._trans_img(image_data))

                #######################
                # 画像のフレーム番号を確認し続け、そこに飛びがあったら、テキストファイルにそのことを記録する。
                # レコーディング全体を司るメモに、何トライアル目でそれがあったかを記録する。
                #######################

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

    def reset_trial(self):
        """
        トライアル管理のためのメソッド
        このメソッドが呼び出されると、インスタンス内の何トライアル目かの情報がリセットされる。
        """

        self.trial_num = 0
        self.fram_in_trial_num = 0

    def next_trial(self):
        """
        トライアル管理のためのメソッド
        このメソッドが呼び出されると、インスタンス内の何トライアル目かの情報が更新される。
        """

        self.trial_num += 1
        self.fram_in_trial_num = 0

    @pyqtSlot()
    def start_new_recording(self):
        """
        新しいレコーディングを始めるためのメソッド
        """

        # 変数のリセット
        self.reset_trial()

        # レコーディングごとの保存ディレクトリを作成
        start_time = datetime.datetime.now()
        self.path = os.path.join(BASE_DIR, start_time.strftime('%Y%m%d%H%M%S'))

        if not os.path.exists(self.path):  # 保存用ディレクトリが存在しない場合は作成する。
            try:
                os.makedirs(self.path)
            except OSError as e:
                print(f"Saver Error in function \"start_new_recording\": {e}")

    def make_memo(self):
        """
        実験の背景情報の記録用メモを作成するメソッド
        """

        # メモの内容を作成
        content = (
            f"---------- Basic Information ----------"
            f"Date and Time: {datetime.datetime.now()}" + "\n"
            f"Recording Method: {self.a_camera_handler.camera_mode}" + "\n"
            )
        if self.a_camera_handler.camera_mode == "program":
            content += f"    program file: {self.a_conductor.desc['file name']}" + "\n"
        content += (
            f"Camera Settings:" + "\n"
            f"    camera name: {self.a_camera_handler.desc['name']}" + "\n"
        )
        if self.a_camera_handler.camera_mode == "manual":
            content += (
                f"    exposure time: not static because recording method is \"manual\"" + "\n"
                f"    delay time: not static because recording method is \"manual\"" + "\n"
                f"    fps: not static because recording method is \"manual\"" + "\n"
            )
        elif self.a_camera_handler.camera_mode == "program":
            content += (
                f"    exposure time: {self.a_camera_handler.desc['exposure time']}" + "\n"
                f"    delay time: {self.a_camera_handler.desc['delay time']}" + "\n"
                f"    fps: {self.a_camera_handler.desc['fps']}" + "\n"
            )
        content += (
            f"    bit scale: {self.a_camera_handler.desc['bit scale']}" + "\n"
            f"" + "\n"
            f"---------- Recording Information ----------"
        )

        # ファイルへの書き出し
        memo_path = os.path.join(self.path, "memo")
        try:
            with open(memo_path) as f:
                f.write(content)


        except Exception as e:
            print(f"Saver Error in function \"make_memo\": {e}")


    def _trans_img(self, image_data):
        """
        画像をUI用に8ビット表示にするメソッド
        カメラの撮影ビットスケールに合わせて変換する。
        """
        
        if image_data.dtype == np.uint16:  # 形式が16bit(uint16)なら画面表示用に8bit (uint8) に変換
            display_img = (image_data / self.a_camera_handler["bit scale"] * 255).astype(np.uint8)
        elif image_data.dtype == np.uint8:
            display_img = image_data
        else:  # その他の型の場合は正規化
            display_img = cv2.normalize(image_data, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

        return display_img
