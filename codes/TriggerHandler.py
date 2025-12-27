#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
pcoカメラによる計測用アプリケーション「pco_experiment_manager」の実験機器の管理周りの機能を実装するファイル
"""

__author__ = 'Tao Muto'
__version__ = '0.0.5'
__date__ = '2025.12.27'

import ctypes
import os

class TriggerHandler():
    """
    実験機器（Mightex BioLED Controller）の管理を司るクラス
    SDKのDLLを直接読み込んで制御を行う (Pythonバージョン非依存)
    """

    # 定数定義 (SDKヘッダーファイルより)
    DISABLE_MODE = 0
    NORMAL_MODE = 1
    TRIGGER_MODE = 3

    def __init__(self):
        self.dev_handle = -1
        self.dll = None
        self.load_sdk()
        self.connect_device()

    def load_sdk(self):
        """
        SDKのDLLファイルを読み込む
        """
        # ★重要: このファイルが Example.py と同じ場所にある必要があります
        dll_name = "Mightex_BLSDriver_SDK.dll"
        
        if os.path.exists(dll_name):
            try:
                # CDLLを使ってDLLをロード
                self.dll = ctypes.CDLL(os.path.abspath(dll_name))
                print(f"TriggerHandler: Loaded {dll_name}")
            except Exception as e:
                print(f"TriggerHandler Error: Failed to load DLL. {e}")
        else:
            print(f"TriggerHandler Error: {dll_name} not found in current directory.")

    def connect_device(self):
        """
        デバイスを初期化し、接続する
        """
        if self.dll is None:
            return

        try:
            # 1. デバイスの初期化 (InitDevices)
            num_devices = self.dll.MTUSB_BLSDriverInitDevices()
            print(f"TriggerHandler: Found {num_devices} Mightex device(s).")

            if num_devices > 0:
                # 2. 0番目のデバイスをオープン (OpenDevice)
                self.dev_handle = self.dll.MTUSB_BLSDriverOpenDevice(0)
                if self.dev_handle >= 0:
                    print(f"TriggerHandler: Device opened successfully. Handle={self.dev_handle}")
                else:
                    print("TriggerHandler Error: Failed to open device.")
            else:
                print("TriggerHandler: No Mightex devices found. Check USB connection.")

        except Exception as e:
            print(f"TriggerHandler Error during connection: {e}")

    def close(self):
        """
        通信を切断する
        """
        if self.dll and self.dev_handle >= 0:
            self.dll.MTUSB_BLSDriverCloseDevice(self.dev_handle)
            print("TriggerHandler: Device closed.")
            self.dev_handle = -1

    # --- 各チャンネル操作用メソッド ---

    def toggle_blue_laser(self, is_on: bool):
        """
        Blue Laser (Channel 1) のON/OFFを切り替える
        """
        if self.dll is None or self.dev_handle < 0:
            print("TriggerHandler: Device not connected, cannot toggle laser.")
            return

        channel = 4 # Channel 1

        if is_on:
            print("TriggerHandler: Turning Blue Laser ON")
            
            # 手順1: 電流値を設定 (SetNormalCurrent)
            # 単位は 0.1% なので、1000 = 100%, 100 = 10%
            current_val = 100 
            self.dll.MTUSB_BLSDriverSetNormalCurrent(self.dev_handle, channel, current_val)
            
            # 手順2: モードをNORMAL(常時点灯)にする (SetMode)
            self.dll.MTUSB_BLSDriverSetMode(self.dev_handle, channel, self.NORMAL_MODE)
            
        else:
            print("TriggerHandler: Turning Blue Laser OFF")
            
            # モードをDISABLE(消灯)にする
            self.dll.MTUSB_BLSDriverSetMode(self.dev_handle, channel, self.DISABLE_MODE)