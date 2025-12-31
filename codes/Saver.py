#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
pcoカメラによる計測用アプリケーション「pco_experiment_manager」の計測結果保存周りの機能を実装するファイル
"""

__author__ = 'Tao Muto'
__version__ = '0.1.4'
__date__ = '2025.12.28'


import os
import queue
import datetime
import cv2
import numpy as np
import time
from PyQt6.QtCore import QThread, pyqtSignal, pyqtSlot, Qt, QTimer


BASE_DIR = "../out/"  # 画像保存先フォルダ
ROW_FORMAT = "tif"
IMG_FORMAT = "jpg"

class Saver(QThread):
    """
    キューに溜まった画像データをディスクに保存するクラス。
    """

    def __init__(self, data_queue, a_camera_handler):
        super().__init__()
        self.data_queue = data_queue
        self.is_running = True
        self.is_new_recording = False

        self.a_camera_handler = a_camera_handler
        
        # 記録を管理するための変数群
        self.experiment_mode = "manual"
        self.record_dir = None   # レコーディングごとの保存ディレクトリのpathを保存するためのフィールド
        self.trial_num = 0  # 現在何トライアル目であるかを把握するためのフィールド
        self.frame_drop_info = f"---------- Frame-Drop Information ----------" + "\n"  # トライアル毎のフレーム落ちの情報を記録するための変数
        self.other_info = f"---------- Other Information ----------" + "\n"  # その他の情報を記録するための変数
        self.last_frame_num = -1
        self.recording_start_time = datetime.datetime.now()
        self.conductor_program_name = "unknown"
        self.total_frames_in_this_record = 0


    def run(self):
        row_format_dir = None
        img_format_dir = None
        current_trial = -1
        frame_in_trial_num = 0
        self.total_frames_in_this_record = 0

        while self.is_running or not self.data_queue.empty():
            if self.record_dir is None:
                time.sleep(0.1)
                continue

            try:
                image_data, frame_num, trial_id = self.data_queue.get(timeout=0.1)  # キューからデータを取り出す (ビジーウェイト軽減のために、タイムアウト付きでブロック)。data = (image_array, frame_number)。

                if current_trial != trial_id:
                    current_trial = trial_id
                    frame_in_trial_num = 0
                    
                    # 保存先パスの生成(送られてきた trial_id を使って、データが正しいトライアルのディレクトリに保存されるようにする)
                    record_dir = os.path.join(self.record_dir, str(current_trial))

                    if not os.path.exists(record_dir):
                        try:
                            os.makedirs(record_dir)
                        except OSError as e:
                            print(f"Saver Error: {e}")

                    row_format_dir = os.path.join(record_dir, ROW_FORMAT)
                    if not os.path.exists(row_format_dir):
                        try:
                            os.makedirs(row_format_dir)
                        except OSError as e:
                            print(f"Saver Error: {e}")

                    img_format_dir = os.path.join(record_dir, IMG_FORMAT)
                    if not os.path.exists(img_format_dir):
                        try:
                            os.makedirs(img_format_dir)
                        except OSError as e:
                            print(f"Saver Error: {e}")

                # 圧縮なしデータを保存
                row_format_filename = os.path.join(row_format_dir, f"{frame_in_trial_num:06d}.{ROW_FORMAT}")  # ファイル名を生成
                cv2.imwrite(row_format_filename, image_data)  # pcoのrawデータはuint16が多く、cv2.imwriteはuint16のTIFF保存に対応しているので、OpenCVを使用。

                # 画像保存
                img_format_filename = os.path.join(img_format_dir, f"{frame_in_trial_num:06d}.{IMG_FORMAT}")  # ファイル名を生成
                cv2.imwrite(img_format_filename, self._trans_img(image_data))

                # フレーム落ちが発生していた場合、それを記録する。
                if self.last_frame_num != -1 and frame_num - self.last_frame_num > 1:  # フレーム落ちが発生していた場合には、そのことを記録
                    self._write_frame_out(self.total_frames_in_this_record, frame_num - self.last_frame_num - 1)
                    print(f"dorpeed now!! frame_num: {frame_num}, drops: {frame_num - self.last_frame_num - 1}")
                
                self.last_frame_num = frame_num

                # 保存したフレーム数を更新
                frame_in_trial_num += 1
                self.total_frames_in_this_record += 1

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
        self.last_frame_num = -1
        self.a_camera_handler.set_trial_id(0)  # トライアル番号が0であることをカメラに伝える

    def next_trial(self):
        """
        トライアル管理のためのメソッド
        このメソッドが呼び出されると、インスタンス内の何トライアル目かの情報が更新される。
        """

        self.trial_num += 1
        self.last_frame_num = -1
        self.a_camera_handler.set_trial_id(self.trial_num)

    @pyqtSlot()
    def start_new_recording(self, mode):
        """
        新しいレコーディングを始めるためのメソッド
        """

        # 受け取ったモードを保存
        self.experiment_mode = mode

        # 変数のリセット
        self.total_frames_in_this_record = 0
        self.reset_trial()

        # レコーディングごとの保存ディレクトリを作成
        self.recording_start_time = datetime.datetime.now()
        start_time = self.recording_start_time
        self.record_dir = os.path.join(BASE_DIR, start_time.strftime('%Y%m%d%H%M%S'))

        if not os.path.exists(self.record_dir):  # 保存用ディレクトリが存在しない場合は作成する。
            try:
                os.makedirs(self.record_dir)
            except OSError as e:
                print(f"Saver Error in function \"start_new_recording\": {e}")

        self.make_memo()

    @pyqtSlot()
    def end_current_recording(self):
        """
        現在のレコーディングを終了させるメソッド
        """

        self.end_memo()

    def make_memo(self):
        """
        実験の背景情報の記録用メモを作成するメソッド
        """

        # メモの内容を作成
        content = (
            f"---------- Basic Information ----------" + "\n"
            f"Date and Time: {self.recording_start_time}" + "\n"
            f"Recording Method: {self.experiment_mode}" + "\n"
            )
        if self.experiment_mode == "program":
            content += f"    program file: {self.conductor_program_name}" + "\n"
        content += (
            f"Camera Settings:" + "\n"
            f"    camera name: {self.a_camera_handler.desc['name']}" + "\n"
        )
        if self.experiment_mode == "manual":
            content += (
                f"    exposure time: not static because recording method is \"manual\"" + "\n"
                f"    delay time: not static because recording method is \"manual\"" + "\n"
                f"    fps: not static because recording method is \"manual\"" + "\n"
            )
        elif self.experiment_mode == "program":
            content += (
                f"    exposure time: {self.a_camera_handler.desc['exposure time']} ({self.a_camera_handler.time_unit_id})" + "\n"
                f"    delay time: {self.a_camera_handler.desc['delay time']} ({self.a_camera_handler.time_unit_id})" + "\n"
                f"    fps: {self.a_camera_handler.desc['fps']}" + "\n"
            )
        content += (
            f"    bit scale: {self.a_camera_handler.desc['bit scale']}" + "\n"
            f"" + "\n"
        )

        # ファイルへの書き出し
        memo_path = os.path.join(self.record_dir, "memo.txt")
        try:
            with open(memo_path, mode='w') as f:
                f.write(content)

        except Exception as e:
            print(f"Saver Error in function \"make_memo\": {e}")

    def write_info(self, a_line: str):
        """
        引数で受け取る文字列を1行の文字列として、タイムスタンプなどの情報と共に、その他の情報メモの末尾に追加するメソッド
        """

        time_stamp = datetime.datetime.now()
        self.other_info += f"{time_stamp}, trial {self.trial_num} : {a_line}" + "\n"

    def end_memo(self):
        """
        別々に保存しているメモの要素を統合して一つのメモを完成させるメソッド
        """

        # 書き込む情報を作成
        content = self.frame_drop_info + "\n" + self.other_info + "\n"

        recording_time = datetime.datetime.now() - self.recording_start_time
        content += (
            f"---------- End Information ----------" + "\n"
            f"Recording Time: {recording_time}" + "\n"
        )

        # ファイルへの書き込み
        memo_path = os.path.join(self.record_dir, "memo.txt")
        try:
            with open(memo_path, mode='a') as f:
                f.write(content)
        except Exception as e:
            print(f"Saver Error in function \"end_memo\": {e}")

    def set_program_name(self, program_name):
        """
        Conductorのプログラムの名前を設定するための変数
        """

        self.conductor_program_name = program_name

    def _trans_img(self, image_data):
        """
        画像をUI用に8ビット表示にするメソッド
        カメラの撮影ビットスケールに合わせて変換する。
        """
        
        if image_data.dtype == np.uint16:  # 形式が16bit(uint16)なら画面表示用に8bit (uint8) に変換
            display_img = (image_data / self.a_camera_handler.desc["bit scale"] * 255).astype(np.uint8)
        elif image_data.dtype == np.uint8:
            display_img = image_data
        else:  # その他の型の場合は正規化
            display_img = cv2.normalize(image_data, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

        return display_img

    def _write_frame_out(self, total_frames_in_this_record, frame_num):
        """
        memoファイルにフレーム落ち情報を記入するためのメソッド
        lost_frameがフレーム落ちが起こる前の最後のフレームの番号(そのレコーディング中における通算フレーム数)、frame_numがフレーム落ちした枚数
        """

        content = f"{frame_num} frame(s) lost after {total_frames_in_this_record}" + "\n"
        self.frame_drop_info += content
