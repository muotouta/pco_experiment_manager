#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
pcoカメラによる計測用アプリケーションの実行ファイル
"""

__author__ = 'Tao Muto'
__version__ = '0.1.0'
__date__ = '2025.12.24'


import pco
import numpy as np
import time
import queue

from PyQt6.QtCore import QThread, pyqtSignal, pyqtSlot, Qt, QTimer


DEFAULT_EXPOSURE = 0.01  # 秒
DEFAULT_FPS = 30.0       # frames per second


class CameraWorker(QThread):
    """    【生産者 (Producer)】
    PCOカメラを制御し、画像を連続して取得するスレッド。
    取得した画像は「保存用キュー」と「表示用シグナル」の2方向に送られる。
    """
    # GUIに画像を送るためのシグナル
    new_frame_signal = pyqtSignal(np.ndarray, dict)
    # エラーやステータスをGUIに送るシグナル
    status_signal = pyqtSignal(str)

    def __init__(self, data_queue):
        super().__init__()
        self.data_queue = data_queue
        self.is_running = True
        self.is_recording = False # 録画中かどうかのフラグ
        
        # カメラ設定値 (スレッドセーフに扱うための初期値)
        self._exposure_time = DEFAULT_EXPOSURE
        self._target_fps = DEFAULT_FPS
        self._delay_time = 0.0
        self._update_params_flag = False # パラメータ変更要求フラグ

        self.last_display_time = 0
        self.display_interval = 1.0 / 30.0  # 画面表示は最大30fpsに制限

    def run(self):
        try:
            print("CameraWorker: Connecting to camera...")
            with pco.Camera() as cam:
                self.status_signal.emit(f"Connected: {cam.camera_name}")
                
                cam.configuration = {'timestamp': 'binary'}
                self._apply_camera_settings(cam)
                
                # リングバッファで録画開始
                cam.record(mode='ring buffer', number_of_images=40)
                cam.wait_for_first_image()
                
                print("CameraWorker: Acquisition loop started.")
                
                while self.is_running:
                    if self._update_params_flag:
                        self._apply_camera_settings(cam)
                        self._update_params_flag = False

                    # 画像取得
                    image, meta = cam.image(image_index=-1)
                    frame_count = meta.get('recorder_image_number', 0)

                    # --- 【修正点1】 保存用キューへの登録 ---
                    if self.is_recording:
                        try:
                            # put_nowait: 待たずに登録を試みる。
                            # キューが満杯(maxsize)なら queue.Full エラーが出る。
                            self.data_queue.put_nowait((image.copy(), frame_count))
                        except queue.Full:
                            # 満杯の場合の処理
                            # ここに来る＝ディスク書き込みがカメラ速度に負けている
                            # PCをクラッシュさせないため、泣く泣くこのフレームの保存をあきらめる
                            print(f"WARNING: Disk too slow! Dropped frame {frame_count}")
                            self.status_signal.emit("Warning: Disk buffer full! Frames dropped.")

                    # --- 【修正点2】 表示更新の間引き (GUIフリーズ対策) ---
                    current_time = time.time()
                    if (current_time - self.last_display_time) > self.display_interval:
                        # 前回の表示から一定時間(33ms)経っている場合のみGUIに送る
                        self.new_frame_signal.emit(image, meta)
                        self.last_display_time = current_time

                cam.stop()
                
        except Exception as e:
            self.status_signal.emit(f"Camera Error: {e}")
            print(f"CameraWorker Error: {e}")
    
    def _apply_camera_settings(self, cam):
        """カメラの設定を適用する内部メソッド"""
        try:
            # 露出時間の設定
            cam.exposure_time = self._exposure_time
            
            # FPSから遅延時間を計算して設定 (Delay = 1/FPS - Exposure)
            # ※注: 読み出し時間(readout time)を考慮すると厳密にはこれより低くなりますが簡易計算です
            calc_delay = (1.0 / self._target_fps) - self._exposure_time
            if calc_delay < 0:
                calc_delay = 0
            
            # もしユーザーが手動でDelayを設定したい場合はここを調整
            # 今回は「FPS設定」を優先してDelayを自動計算するロジックにしています
            cam.delay_time = calc_delay
            
            # 実際の値を反映
            self._exposure_time = cam.exposure_time
            self._delay_time = cam.delay_time
            
        except Exception as e:
            print(f"Setting Update Error: {e}")

    # --- GUIから操作するためのスロット群 ---
    def set_exposure(self, value):
        self._exposure_time = value
        self._update_params_flag = True

    def set_fps(self, value):
        self._target_fps = value
        self._update_params_flag = True
    
    def start_recording(self):
        self.is_recording = True
        print("CameraWorker: Recording ON")

    def stop_recording(self):
        self.is_recording = False
        print("CameraWorker: Recording OFF")

    def stop(self):
        self.is_running = False
        self.wait()