#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
pcoカメラによる計測用アプリケーション「pco_experiment_manager」の実験機器の管理周りの機能を実装するファイル
"""

__author__ = 'Tao Muto'
__version__ = '0.0.3'
__date__ = '2025.12.29'


import os
import ctypes
from DeviceController import Mightex_BLS_Controller


class TriggerHandler():
    """
    実験機器の管理を司るクラス
    """

    def __init__(self):
        """
        コンストラクタ
        """

        dll_0, dev_handle_0 = self._get_Mightex_BLS_led_controller(dev_id=0)  # 一つめのMightex BLS led controllerを引数で指

        self.ttl_triger_1 = Mightex_BLS_Controller(dll=dll_0, dev_handle=dev_handle_0, channel=1)
        self.ttl_triger_2 = Mightex_BLS_Controller(dll=dll_0, dev_handle=dev_handle_0, channel=2)
        self.blue_laser = Mightex_BLS_Controller(dll=dll_0, dev_handle=dev_handle_0, channel=3)
        self.red_laser = Mightex_BLS_Controller(dll=dll_0, dev_handle=dev_handle_0, channel=4)
        self.speaker = None

    # --- 各チャンネル操作用メソッド ---
    def toggle_ttl_trigger_1(self, is_on: bool):
        """
        TTl Trriger 1のON/OFFを切り替える
        """

        if is_on:
            self.ttl_triger_1.on()
        else:
            self.ttl_triger_1.off()

    def toggle_ttl_trigger_2(self, is_on: bool):
        """
        TTl Trriger 2のON/OFFを切り替える
        """

        if is_on:
            self.ttl_triger_2.on()
        else:
            self.ttl_triger_2.off()

    def toggle_blue_laser(self, is_on: bool):
        """
        Blue LaserのON/OFFを切り替える
        """

        if is_on:
            self.blue_laser.on()
        else:
            self.blue_laser.off()
    
    def toggle_red_laser(self, is_on: bool):
        """
        Red LaserのON/OFFを切り替える
        """

        if is_on:
            self.red_laser.on()
        else:
            self.red_laser.off()
    
    def toggle_speaker(self, is_on: bool):
        """
        スピーカーのON/OFFを切り替える
        """

        if is_on:
            self.speaker.on()
        else:
            self.speaker.off()

    def _get_Mightex_BLS_led_controller(self, dev_id):
        """
        Mightex BLS led controllerのdllとデバイスハンドルを求めるメソッド
        """

        # dllファイルの読み込み
        dll_name = "Mightex_BLSDriver_SDK.dll"  # このファイルがクラスファイルと同じ場所にある必要がある。
        if os.path.exists(dll_name):
            try:
                dll = ctypes.CDLL(os.path.abspath(dll_name))  # CDLLを使ってDLLをロード
            except Exception as e:
                print(f"Class Mightex_BLS_Controller Error in \"__init__\": Failed to load DLL. {e}")
        else:
            print(f"Class Mightex_BLS_Controller Error in \"__init__\": {dll_name} is not found in same directory with class file.")

        # デバイスとの接続
        try:
            num_devices = dll.MTUSB_BLSDriverInitDevices()  # デバイスの初期化 (InitDevices)
        
            if num_devices <= 0:
                print(f"Class Mightex_BLS_Controller Error in \"__init__\": No found Mightex device(s).")

            if num_devices > 0:
                dev_handle = dll.MTUSB_BLSDriverOpenDevice(dev_id) # デバイスをオープン。失敗すると-1が返ってくる。
                if dev_handle < 0:
                    print(f"Class Mightex_BLS_Controller Error in \"__init__\": Failed to open device {dev_id}.")
            else:
                print("Class Mightex_BLS_Controller in \"__init__\": No Mightex devices found.")

        except Exception as e:
            print(f"Class Mightex_BLS_Controller Error in \"__init__\": {e}")

        
        return dll, dev_handle

