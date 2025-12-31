#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
pcoカメラによる計測用アプリケーション「pco_experiment_manager」のカメラ制御周りの機能を実装するファイル
修正版: 録画フラグとスレッド生存フラグの分離、バッファオーバーフロー検知機能追加
"""

__author__ = 'Tao Muto'
__version__ = '0.1.5' # Version updated for fix
__date__ = '2025.12.31'


import pco
import numpy as np
import queue
import time
import cv2
from PyQt6.QtCore import QThread, pyqtSignal, pyqtSlot, Qt, QTimer


SAVE_SECOND = 60  # pcoカメラの撮影の、リングバッファのサイズ。SAVE_SECOND秒分は保存するようにする。

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
        
        # --- 修正: フラグの役割分担 ---
        self.is_running = True     # スレッド自体の生存フラグ (アプリ終了までTrue)
        self.is_recording = False  # データの保存を行うかどうかのフラグ (トライアル中のみTrue)

        self.current_trial_id = 0  # トライアルID(現在が何トライアル目かを表す番号)を保存するための変数


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

            # リングバッファの設定
            req_buffer_size = int(self.desc["fps"] * SAVE_SECOND)
            if req_buffer_size < 1: req_buffer_size = 1
            
            # デバッグ用: 実際に要求するサイズを表示
            # print(f"DEBUG: Calculated Buffer Size = {req_buffer_size}")

            self.a_cam.record(mode='ring buffer', number_of_images=req_buffer_size)
            
            # pcoライブラリが要求通りのサイズを確保したと仮定
            buffer_size = req_buffer_size

            # 最初の画像を待つ
            try:
                if hasattr(self.a_cam, 'wait_for_first_image'):
                    self.a_cam.wait_for_first_image()
                else:
                    time.sleep(0.5)
            except Exception as e:
                print(f"Wait First Image Warning: {e}")

            # 最初の1フレームを取得して初期化
            last_processed_frame_count = -1
            try:
                image, meta = self.a_cam.image(data_format=self.DATA_FORMAT, image_index=-1)
                
                display_img = self._trans_img(image)
                self.new_frame_signal.emit(display_img, meta)
                
                last_processed_frame_count = meta['recorder image number']
                
            except Exception as e:
                print(f"CameraHandler Error in \"run\" while first frame fetch: {e}")

            # --- メインループ ---
            # 修正: is_running (スレッド生存フラグ) でループを回す
            while self.is_running:
                if self._update_params_flag:
                    self._apply_camera_settings(self.a_cam)
                    self._update_params_flag = False

                time.sleep(0.001) # ポーリング間隔

                try:
                    # 最新画像の情報を取得
                    latest_image, latest_meta = self.a_cam.image(data_format=self.DATA_FORMAT, image_index=-1)
                    current_cam_frame_count = latest_meta['recorder image number']
                    
                    if current_cam_frame_count <= last_processed_frame_count:
                        continue

                    # 未処理分の回収ループ
                    start_frame = last_processed_frame_count + 1
                    
                    # --- バッファオーバーフロー検知 ---
                    if current_cam_frame_count - start_frame > buffer_size:
                        dropped_count = current_cam_frame_count - start_frame - buffer_size
                        # print(f"[BUFFER OVERFLOW] Skipped {dropped_count} frames! BufferSize: {buffer_size}")
                        # 救出可能な最古のフレームまでインデックスを進める
                        start_frame = current_cam_frame_count - buffer_size + 1

                    for f_num in range(start_frame, current_cam_frame_count + 1):
                        
                        # 最新画像の場合
                        if f_num == current_cam_frame_count:
                            target_image = latest_image
                            target_meta = latest_meta
                        else:
                            # 過去画像の場合：インデックスを計算して取得
                            b_idx = (f_num - 1) % buffer_size
                            try:
                                target_image, target_meta = self.a_cam.image(data_format=self.DATA_FORMAT, image_index=b_idx)
                                
                                # --- 整合性チェックと詳細ログ ---
                                rec_num = target_meta['recorder image number']
                                if rec_num != f_num:
                                    # ここでログが出る場合、バッファサイズの認識ズレか、インデックス計算の不一致
                                    # print(f"[CRITICAL DROP] Want: {f_num}, Got: {rec_num} (Diff: {rec_num - f_num}), Index: {b_idx}")
                                    continue 

                            except Exception as e:
                                print(f"[FETCH ERROR] Index: {b_idx}, Error: {e}")
                                continue

                        # --- 処理実行 ---
                        if self.camera_mode == "shot":
                            if f_num == current_cam_frame_count:
                                display_img = self._trans_img(target_image)
                                self.new_frame_signal.emit(display_img, target_meta)
                        
                        elif self.camera_mode == "queue":
                            # 画面更新は間引く
                            if f_num % 2 == 0: 
                                display_img = self._trans_img(target_image)
                                self.new_frame_signal.emit(display_img, target_meta)

                            # 修正: 録画中 (is_recording) の場合のみキューに入れる
                            if self.is_recording:
                                try:
                                    self.data_queue.put_nowait((target_image.copy(), f_num, self.current_trial_id))
                                except queue.Full:
                                    print(f"QUEUE FULL ERROR: Frame {f_num} dropped!")
                                    pass
                            else:
                                # 録画中でなければ何もしない（捨てる）
                                pass
                    
                    last_processed_frame_count = current_cam_frame_count
                
                except Exception as e:
                    print(f"CameraHandler Error in \"run\": {e}")
                    continue
            
            # ループを抜けたら停止
            if self.a_cam:
                self.a_cam.stop()
                print("Camera Stopped.")
                
        except Exception as e:
            self.status_signal.emit(f"Camera Error: {e}")
            print(f"CameraHandler Error in function \"run\": {e}")

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

    def set_trial_id(self, trial_id):
        """
        トライアルIDを外部からセットするメソッド
        """

        self.current_trial_id = trial_id

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
        """
        録画開始: is_recordingフラグを立てる。
        スレッド自体はrunで回り続けているので、フラグを変えるだけでよい。
        """
        self.is_recording = True
        self.record_started_signal.emit()  # 録画開始シグナルを発信
        print("Recording Started.")

    def stop_recording(self):
        """
        録画停止: is_recordingフラグを下ろす。
        スレッドは停止させない。
        """
        self.is_recording = False
        print("Recording Stopped.")

    def stop(self):
        """
        アプリケーション終了用: スレッド自体を停止させる
        """
        self.is_recording = False
        self.is_running = False # ループを抜けるように指示
        self.wait() # スレッドの完全停止を待つ


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