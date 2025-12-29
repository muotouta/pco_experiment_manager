#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
pcoカメラによる計測用アプリケーション「pco_experiment_manager」のカメラ制御周りの機能を実装するファイル
"""

__author__ = 'Tao Muto'
__version__ = '0.1.2'
__date__ = '2025.12.26'


import pco
import numpy as np
import queue
import time
import cv2
from PyQt6.QtCore import QThread, pyqtSignal, pyqtSlot, Qt, QTimer


class CameraHandler(QThread):
    """
    概要
        pcoカメラを操作するクラス
    機能
        ・二つの撮影モード
            ・一枚撮像するごとにシグナルを出す
            ・撮影画像をキューに追加し続ける
        ・カメラ情報を返す
    """

    # 調整用デベロッパ入力項目
    time_unit = {
        "s" : 1,
        "ms" : 1000,
        "μs" : 1000000
    }
    time_unit_id = "ms"

    DATA_FORMAT = 'mono8'

    # 並列処理用フィールド
    new_frame_signal = pyqtSignal(np.ndarray, dict)  # GUIに画像を送るためのシグナル
    status_signal = pyqtSignal(str)  # エラーやステータスをGUIに送るシグナル
    params_updated_signal = pyqtSignal()  # パラメータ更新通知用シグナル
    record_started_signal = pyqtSignal()  # 録画開始通知用シグナル


    def __init__(self, data_queue):
        """
        コンストラクタ
        """

        super().__init__()
        self.data_queue = data_queue
        self.is_running = True
        self.is_recording = False # 録画中かどうかのフラグ


        # カメラを設定
        self.a_cam = pco.Camera()
        self.desc = {
            "name" : self.a_cam.camera_name,
            "bit resolution" : self.a_cam.description['bit resolution'],  # カメラのADCビット数（画像に使用するビット数）
            "bit scale" : 2 ** self.a_cam.description['bit resolution'] - 1,  # 画像のスケーリングに用いる数値（諧調数）をあらかじめ算出。
            "exposure time" : 25 / self.time_unit[self.time_unit_id],
            "min exposure time" : self.a_cam.description["min exposure time"],
            "max exposure time" : self.a_cam.description["max exposure time"],
            "current min exposure time" : self.a_cam.description["min exposure time"],
            "current max exposure time" : self.a_cam.description["max exposure time"],
            "fps" : 40,
            "min fps" : 1 / (self.a_cam.description["max exposure time"] + self.a_cam.description["min delay time"]),
            "max fps" : self._get_max_fps(),
            "current max fps" : self._get_max_fps(),
            "current min fps" : 1 / (self.a_cam.description["max exposure time"] + self.a_cam.description["min delay time"]),
            "delay time" : 0.0 / self.time_unit[self.time_unit_id],
            "min delay time" : self.a_cam.description["min delay time"],
            "max delay time" : self.a_cam.description["max delay time"]
        }

        # パラメータ変更を非同期処理下で安全に行うための制御変数
        self._update_params_flag = False  # パラメータ変更要求フラグ
        self.camera_mode = "shot"  # 撮影モード区別用変数"shot"が一枚撮影、"queue"がキューに保存

    def run(self):
        try:
            self.a_cam.configuration = {'timestamp': 'binary'}
            self._apply_camera_settings(self.a_cam)

            # リングバッファで録画開始
            buffer_size = int(self.desc["fps"])
            if buffer_size < 1: buffer_size = 1 # 安全策
            self.a_cam.record(mode='ring buffer', number_of_images=int(self.desc["fps"]))  # 1秒分は保存するようにリングバッファのサイズを設定
            self.a_cam.wait_for_first_image()
            frame_count = -1

            while self.is_running:
                # パラメータの変更が要請されていたらそれを反映する。
                if self._update_params_flag:
                    self._apply_camera_settings(self.a_cam)
                    self._update_params_flag = False

                # 画像取得
                image, meta = self.a_cam.image(data_format=self.DATA_FORMAT, image_index=-1)
                new_frame_count = meta['recorder image number']

                # 撮影モードに合わせて画像の扱いを変更
                if self.camera_mode == "shot":
                    display_img = self._trans_img(image)
                    self.new_frame_signal.emit(display_img, meta)
                
                elif self.camera_mode == "queue":
                    display_img = self._trans_img(image)
                    self.new_frame_signal.emit(display_img, meta)  # GUIに画像を送る。

                    if new_frame_count > frame_count:  # 同じ画像を複数回保存しないようにする。
                        try:
                            self.data_queue.put_nowait((image.copy(), frame_count))  # 待たずに画像の登録を試みる。
                        except queue.Full:  # queueがいっぱいなら、登録を諦める。そこで実験を中断するわけにいかないので、それは諦める。諦めたこと、どれくらいの枚数を諦めたかの記録はSaverに任せる。
                            pass

                        frame_count = new_frame_count
                
            self.a_cam.stop()
                
        except Exception as e:
            self.status_signal.emit(f"Camera Error: {e}")
            print(f"CameraWorker Error in function \"run\": {e}")

    def _apply_camera_settings(self, cam):
        """
        カメラの設定を適用する内部メソッド
        """

        try:
            # ユーザーが設定した値をカメラの設定値にすることを試みる
            cam.exposure_time = self.desc["exposure time"]
            cam.delay_time = self.desc["delay time"]
            
            # 実際の値を反映
            self.desc["exposure time"] = cam.exposure_time
            self.desc["delay time"] = cam.delay_time
            self.desc["fps"] = 1 / (self.desc["exposure time"] + self.desc["delay time"])

            # 設定が完了し、descが更新されたことをUIに通知
            self.params_updated_signal.emit()
            
        except Exception as e:
            print(f"CameraHandler Error: {e}")


    # --- GUIから操作するためのスロット群 ---
    def set_exposure(self, value):
        self.desc["exposure time"] = value
        self._update_params_flag = True

    def set_fps(self, value):
        self._fps = value
        self._update_params_flag = True

    def set_delay(self, value):
        self.desc["delay time"] = value
        self._update_params_flag = True

    def set_camera_mode(self, value: str):
        self.camera_mode = value

    def start_recording(self):
        self.is_recording = True
        self.record_started_signal.emit()  # 録画開始シグナルを発信

    def stop_recording(self):
        self.is_recording = False

    def stop(self):
        self.is_running = False
        self.wait()


    def _trans_img(self, image_data):
        """
        画像をUI用に8ビット表示にするメソッド
        カメラの撮影ビットスケールに合わせて変換する。
        """
        
        if image_data.dtype == np.uint16:  # 形式が16bit(uint16)なら画面表示用に8bit (uint8) に変換
            display_img = (image_data / self.desc['bit scale'] * 255).astype(np.uint8)
        elif image_data.dtype == np.uint8:
            display_img = image_data
        else:  # その他の型の場合は正規化
            display_img = cv2.normalize(image_data, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

        return display_img

    def _get_max_fps(self):
        """
        実際に撮影を行うことで、理論値でない、実際の最大fpsを算出する内部メソッド。
        """
        
        self.a_cam.configuration = {'exposure time': self.a_cam.description['min exposure time']} 
        self.a_cam.record(number_of_images=1, mode='sequence')
        image, meta = self.a_cam.image()

        return meta['framerate']

    def __del__(self):
        """
        デストラクタ
        """

        self.a_cam.close()  # カメラを開放
