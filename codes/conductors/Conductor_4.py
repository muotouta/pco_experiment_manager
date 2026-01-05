#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
pcoカメラによる計測用アプリケーション「pco_experiment_manager」の実験遂行周りの機能を実装するファイル
"""

__author__ = 'Tao Muto'
__version__ = '0.0.3'
__date__ = '2026.1.5'


import time
import os
import datetime
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QEventLoop, QTimer
from DeviceController import Mightex_BLS_Controller
from DeviceController import adafruit_3369_Controller

import random

BASE_DIR = "../out/"  # 画像保存先フォルダ


class Conductor():
    """
    実験の遂行を司るクラス
    """

    def __init__(self, a_camera_handler, a_saver, a_trigger_handler):
        """
        コンストラクタ
        """

        self.desc = {
            'program name' : "program 4",
        }
        self.is_running = False
        self.recording_start_time = datetime.datetime.now()

        self.a_camera_handler = a_camera_handler
        self.a_saver = a_saver
        self.a_saver.set_program_name(self.desc['program name'])
        self.a_trigger_handler = a_trigger_handler

        self.ttl_triger_1 = a_trigger_handler.ttl_triger_1
        self.ttl_triger_2 = a_trigger_handler.ttl_triger_2
        self.blue_laser = a_trigger_handler.blue_laser
        self.red_laser = a_trigger_handler.red_laser
        self.speaker = a_trigger_handler.speaker

    def run(self):
        """
        外部プログラムから呼び出すためのメソッド。
        このメソッドを呼び出すことで、プログラムが実行された後、処理が呼び出し元に戻る。
        """

        self.is_running = True # 実行開始フラグを立てる
        
        try:
            # プログラムを実行
            self.a_saver.start_new_recording("program")  # 初期化処理を Saver に一任
            self.program()

        except Exception as e:
            # program実行中に何かが起こっても、エラー内容を表示・記録して、アプリを落とさずに終了処理へ進む
            error_msg = f"Conductor Error in \"run\" while executing program: {e}"
            print(error_msg)
            try:
                self.memo(error_msg)
            except:
                pass # memoへの書き込み自体が失敗した場合は無視

        finally:
            # 終了操作
            self.is_running = False
            
            # 安全のため、機器の停止や設定の復帰を行う
            try:
                self.end_record()
                self.a_camera_handler.camera_mode = "shot"
            except Exception as e:
                print(f"Conductor Error in \"run\" while finalize: {e}")

    def next_trial(self):
        """
        新しいトライアルを始める。
        そのために、トライアル用のディレクトリを追加したりする。
        """

        self.a_saver.last_frame_num = -1
        self.a_saver.next_trial()

    def start_record(self):
        """
        レコーディング（記録データの書き出し）を始める。
        """

        self.a_saver.last_frame_num = -1
        self.a_camera_handler.camera_mode = "queue"
        self.a_camera_handler.start_recording()  # 録画開始命令を送る

    def end_record(self):
        """
        レコーディング（記録データの書き出し）を止める。
        """

        self.a_camera_handler.camera_mode = "shot"
        self.a_camera_handler.stop_recording()  # 録画停止命令を送る

    def wait(self, num):
        """
        プログラムをnumミリ秒停止する。
        GUIからの停止命令(is_running=False)を受け付けるため、小刻みにsleepする。
        """

        if num <= 0: return

        # 待機用イベントループを作成
        loop = QEventLoop()
        
        # 指定時間後にループを抜けるタイマーを設定
        QTimer.singleShot(num, loop.quit)
        
        # 途中停止チェック用のタイマー（小刻みにチェック）
        check_timer = QTimer()
        check_timer.setInterval(100) # 100msごとにチェック
        
        def check_stop():
            if not self.is_running:
                loop.quit() # 強制終了
                
        check_timer.timeout.connect(check_stop)
        check_timer.start()

        # ループ開始（ここでブロックするが、裏でUIイベントは処理される）
        loop.exec()
        
        check_timer.stop()

        if not self.is_running:
             raise InterruptedError("Stopped by user")

    def memo(self, a_line):
        """
        文字列a_lineをタイムスタンプ情報と共にmemoに記録する。
        """

        self.a_saver.write_info(a_line)

    def end(self):
        """
        プログラムを終了させるためのメソッド
        呼び出すとprogram()が終了し、run()に戻る。
        """

    def program(self):
        """
        実験の進行をコンピュータで管理するためのメソッド
        """
        # 各関数の名前を短くする
        next_trial = self.next_trial
        start_record = self.start_record
        end_record = self.end_record
        wait = self.wait
        memo = self.memo
        end = self.end

        # 各機器を表す変数名を、人間が読みやすい短いものに変更
        camera = self.a_camera_handler
        ttl_1 = self.ttl_triger_1
        ttl_2 = self.ttl_triger_2
        blue_laser = self.blue_laser
        red_laser = self.red_laser
        speaker = self.speaker


        """""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
        以降が、実験の進行を表すプログラム。
        使い方は以下の通り。
            next_trial() : 現在のトライアルを終わらせ、新しいトライアルを始める。
            start_record() : レコーディング（記録データの書き出し）を始める。
            end_record() : レコーディング（記録データの書き出し）を止める。
            wait(num) : プログラムをnumミリ秒停止する。
            memo(a_line) : 文字列a_lineをタイムスタンプ情報と共にmemoに記録する。
            end() : これを呼び出すと、プログラムがその場で終了する。

            camera : カメラ制御
                set_exposure() : 露光時間を設定する。
                set_fps() : fpsを設定する。
                set_delay() : 遅延時間を設定する。
                desc : 各種状態値の辞書
                    "name" : カメラの名前
                    "bit resolution" : カメラのADCビット数 (画像に使用するビット数)
                    "bit scale" : 画像のスケーリングに用いる数値（諧調数）
                    "exposure time" : 現在の露光時間 (単位は秒(s))
                    "min exposure time" : 露光時間の最大値 (カメラに設定可能な値。fpsあるいはdelay timeとの兼ね合いで変化する) (単位は秒(s))
                    "max exposure time" : 露光時間の最小値 (カメラに設定可能な値。fpsあるいはdelay timeとの兼ね合いで変化する) (単位は秒(s))
                    "current min exposure time" : fpsあるいはdelay timeとの兼ね合いで決まる、現在の露光時間の最大値 (単位は秒(s))
                    "current max exposure time" : fpsあるいはdelay timeとの兼ね合いで決まる、現在の露光時間の最小値 (単位は秒(s))
                    "fps" : 現在のfpsの設定値
                    "min fps" : 1 / (self.a_cam.description["max exposure time"] + self.a_cam.description["min delay time"])
                    "max fps" : self._get_max_fps()
                    "current max fps" : self._get_max_fps()
                    "current min fps" : 1 / (self.a_cam.description["max exposure time"] + self.a_cam.description["min delay time"])
                    "delay time" : 0.0 / self.time_unit[self.time_unit_id] (単位は秒(s))
                    "min delay time" : self.a_cam.description["min delay time"] (単位は秒(s))
                    "max delay time" : self.a_cam.description["max delay time"] (単位は秒(s))

            ttl系、laser系、speaker系 : 機器制御
                関数 : 
                    on() : 機器をONにする。
                    off() : 機器をOFFにする。
                    is_active() : 機器がONならTrue、OFFならFalseを返す。
                    set_value(param:int, value) : 機器がパラメータ(機器内ではparamで区別)を持つ場合に、その値をvalueに設定する。
                    current_value(param:int) : 機器がパラメータ(機器内ではparamで区別)を持つ場合に、その現在の値を設定する。
                    value_max(param:int) / value_min(param:int) : 機器がパラメータ(機器内ではparamで区別)を持つ場合に、その値の最大値 / 最小値を返す。
                    value_unit(param:int) : 機器がパラメータ(機器内ではparamで区別)を持つ場合に、その単位を返す。
                paramについて : 
                    ttl系 : 
                        0 : analog out
                        1 : digital out (未実装)
                        2 : ttl (未実装)
                    laser系 : 
                        0 : 光量
                        1、2 : なし
                    speaker系 : 
                        0 : ピッチ
                        1 : 音量
                        2 : なし
        """""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

        speaker.set_value(0, 440)
        speaker.set_value(1, 100)

        
        memo(f"pitch: {speaker.current_value(0)}(Hz), volume: {speaker.current_value(1)}(%)")

        exporsure_set = [0.6]
        max = 11

        
        for each in exporsure_set:
            print("start trial")
            camera.set_exposure(each / 1000)
            camera.set_delay(0.00007)
            print(f"exporsure: {camera.desc['exposure time']}, fps: {camera.desc['fps']}, delay: {camera.desc['delay time']}")
            memo(f"exporsure: {camera.desc['exposure time']}, fps: {camera.desc['fps']}, delay: {camera.desc['delay time']}")
            wait(1000)
            
            ari = 0
            nashi = 0
            total = 0
            while True:
                blue_laser.on()
                wait(1000)

                start_record()
                wait(1000)

                coin = random.randint(0, 1)
                if (coin == 0 and ari < max + 1) or (coin == 1 and nashi >= max + 1):
                    ari += 1
                    speaker.on()
                elif (coin == 0 and ari >= max + 1) or (coin == 1 and nashi < max + 1):
                    nashi += 1


                wait(100)
                speaker.off()
                wait(3900)
                end_record()
                blue_laser.off()

                memo(f"coin{coin}")

                wait(10000)



                if ari < max + 1 and nashi < max + 1:
                    total += 1
                    next_trial()
                elif ari >= max + 1 and nashi >= max + 1:
                    break

        end()