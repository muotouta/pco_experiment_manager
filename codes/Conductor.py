#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
pcoカメラによる計測用アプリケーション「pco_experiment_manager」の実験遂行周りの機能を実装するファイル
"""

__author__ = 'Tao Muto'
__version__ = '0.0.2'
__date__ = '2025.12.29'


import time
from DeviceController import Mightex_BLS_Controller

class Conductor():
    """
    実験の遂行を司るクラス
    """

    desc = {
        'program name' : str,
        
    }

    def __init__(self, a_camera_handler, a_saver):
        """
        コンストラクタ
        """
        self.ttl_triger_1 = Mightex_BLS_Controller(dev_id=0, channel=1)
        self.ttl_triger_2 = Mightex_BLS_Controller(dev_id=0, channel=2)
        self.blue_laser = Mightex_BLS_Controller(dev_id=0, channel=3)
        self.red_laser = Mightex_BLS_Controller(dev_id=0, channel=4)
        self.speaker = None
        self.a_camera_handler = a_camera_handler
        self.a_saver = a_saver

    def run(self):
        """
        外部プログラムから呼び出すためのメソッド。
        このメソッドを呼び出すことで、プログラムが実行された後、処理が呼び出し元に戻る。
        """

        # プログラムを実行
        self.program()

        # 終了操作
            # UIの表示を戻す？

    def start(self):
        """
        実験を始めるときに呼び出す。
        各種初期化を行う。
        """

        # トライアル情報を初期化する。
        self.a_saver.reset_trial()

    def next_trial(self):
        """
        新しいトライアルを始める。
        """

        self.a_saver.next_trial()

    def start_record(self):
        """
        レコーディング（記録データの書き出し）を始める。
        """

        self.a_camera_handler.camera_mode = "queue"

    def end_record(self):
        """
        レコーディング（記録データの書き出し）を止める。
        """

        self.a_camera_handler.camera_mode = "shot"

    def wait(self, num):
        """
        プログラムをnumミリ秒停止する。
        """

        unit = 1000  # 単位はミリ秒
        time.sleep(num * unit)

    def memo(self, a_line):
        """
        文字列a_lineをタイムスタンプ情報と共にmemoに記録する。
        """

        self.a_saver.write_memo(a_line)

    def end(self):
        """
        プログラムを終了させるためのメソッド
        呼び出すとUIerに実行権が移る。
        """

    def program(self):
        """
        実験の進行をコンピュータで管理するためのメソッド
        """

        # 各機器を表す変数名を、人間が読みやすい短いものに変更
        ttl_1 = self.ttl_triger_1
        ttl_2 = self.ttl_triger_2
        laser_blue = self.blue_laser
        laser_red = self.red_laser
        speaker = self.speaker
        camera = self.a_camera_handler
        saver = self.a_saver


        """""""""""""""""""""""""""""""""""""""""""""
        以降が、実験の進行を表すプログラム。
        使い方は以下の通り。
            start() : 実験を始めるときに呼び出し、初期化を行う。
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
                    "exposure time" : 現在の露光時間
                    "min exposure time" : 露光時間の最大値 (カメラに設定可能な値。fpsあるいはdelay timeとの兼ね合いで変化する)
                    "max exposure time" : 露光時間の最小値 (カメラに設定可能な値。fpsあるいはdelay timeとの兼ね合いで変化する)
                    "current min exposure time" : fpsあるいはdelay timeとの兼ね合いで決まる、現在の露光時間の最大値
                    "current max exposure time" : fpsあるいはdelay timeとの兼ね合いで決まる、現在の露光時間の最小値
                    "fps" : 現在のfpsの設定値
                    "min fps" : 1 / (self.a_cam.description["max exposure time"] + self.a_cam.description["min delay time"]),
                    "max fps" : self._get_max_fps(),
                    "current max fps" : self._get_max_fps(),
                    "current min fps" : 1 / (self.a_cam.description["max exposure time"] + self.a_cam.description["min delay time"]),
                    "delay time" : 0.0 / self.time_unit[self.time_unit_id],
                    "min delay time" : self.a_cam.description["min delay time"],
                    "max delay time" : self.a_cam.description["max delay time"]

            ttl系、laser系、speaker系 : 機器制御
                on() : 機器をONにする。
                off() : 機器をOFFにする。
                is_active() : 機器がONならTrue、OFFならFalseを返す。
                set_value() : 機器がパラメータを持つ場合に、その値を設定する。
                current_value() : 機器がパラメータを持つ場合に、その現在の値を設定する。
                value_max() / value_min : 機器がパラメータを持つ場合に、その値の最大値 / 最小値を返す。
                value_unit() : 機器がパラメータを持つ場合に、その単位を返す。
        """""""""""""""""""""""""""""""""""""""""""""



        
