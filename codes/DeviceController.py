#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
pcoカメラによる計測用アプリケーション「pco_experiment_manager」の実験機器を表現するための機能を実装するファイル
"""

__author__ = 'Tao Muto'
__version__ = '0.0.4'
__date__ = '2025.12.29'


class DeviceController():
    """
    実験機器を表現するクラス
    """

    def __init__(self):
        """
        コンストラクタ
        """

        self.device_type: str = None

        self.state: bool = False
        self.on_function = None
        self.off_function = None

        self.value = None
        self.value_max = None
        self.value_min = None
        self.value_unit: str = None

    def type(self):
        """
        自身の機器としての種類を返すメソッド
        """

        if self.device_type is None:
            tmp = "unknown"
        else:
            tmp = self.device_type

        return tmp

    def on(self):
        """
        呼び出されると自身をONにするメソッド
        """

        self.state = True

        try:
            self.on_function()
        except:
            print("DeviceContoroller Error: \"on_function\" is not defined")

    def off(self):
        """
        呼び出されると自身をOFFにするメソッド
        """

        self.state = False

        try:
            self.off_function()
        except:
            print("DeviceContoroller Error: \"off_function\" is not defined")

    def is_active(self):
        """
        自身の状態を返すメソッド
        """

        return self.state
    
    def set_value(self, val):
        """
        自身の値を引数の値に変更するメソッド
        """

        if self.value is None:
            print(f"DeveiceController Error in functon \"set_value\":  Device \"{self.device_type}\" has no numeric parameter")
        else:
            self.value = val

    def current_value(self):
        """
        自身の現在の値を答えるメソッド
        値を持たないデバイスでは、Noneが返る。
        """

        if self.value is None:
            print(f"DeveiceController Error in functon \"current_value\":  Device \"{self.device_type}\" has no numeric parameter")
            tmp = None
        else:
            tmp = self.value

        return tmp
    
    def max_value(self):
        """
        自身の最大の値を答えるメソッド
        値を持たないデバイスでは、Noneが返る。
        """

        if self.value is None:
            print(f"DeveiceController Error in functon \"max_value\":  Device \"{self.device_type}\" has no numeric parameter")
            tmp = None
        else:
            tmp = self.value_max

        return tmp
    
    def min_value(self):
        """
        自身の最小の値を答えるメソッド
        値を持たないデバイスでは、Noneが返る。
        """

        if self.value is None:
            print(f"DeveiceController Error in functon \"min_value\":  Device \"{self.device_type}\" has no numeric parameter")
            tmp = None
        else:
            tmp = self.value_min

    def value_unit(self):
        """
        自身の値の単位を答えるメソッド
        値を持たないデバイスでは、Noneが返る。
        """
        if self.value is None:
            print(f"DeveiceController Error in functon \"value_unit\":  Device \"{self.device_type}\" has no numeric parameter")
            tmp = None
        else:
            tmp = self.value_unit

        return tmp    


class Mightex_BLS_Controller(DeviceController):
    """
    Mightex BLSD Driverにより、Mightex BLS led controllerの一つのチャンネルを制御するクラス
    対象機器のdllとデバイスハンドルを外部プログラムから与え、またチャンネルを指定することで、対象機器の特定のチャンネルを扱うインスタンスを得る。
    Mightexが公開するライブラリのdllを、標準のpythonラッパではなく、ctypesにより制御する。それにより、Pythonバージョン非依存にする。
    """

    DISABLE_MODE = 0
    NORMAL_MODE = 1

    def __init__(self, dll, dev_handle, channel):
        """
        コンストラクタ
        """

        super().__init__()

        # 親クラスのフィールドを設定
        self.device_type = "Mightex BLS led controller"
        self.state = False
        self.on_functon = None
        self.off_function = None
        self.value: int = 7
        self.value_max: int = 1000
        self.value_min: int = 0
        self.value_unit = "0.1%"

        # 子クラスのフィールドを設定
        self.channel = channel
        self.dev_handle = dev_handle
        self.dll = dll

        # このクラスを、DeviceCOntrollerクラスの関数で扱えるようにするための設定
        self.on_function = self.analog_out_on
        self.off_function = self.analog_out_off

    def analog_out_on(self):
        """
        レーザーの照射を開始するためのメソッド
        """
        # 電流値を設定
        self.dll.MTUSB_BLSDriverSetNormalCurrent(self.dev_handle, self.channel, self.value)
        
        # モードをNORMAL(常時点灯)にする
        self.dll.MTUSB_BLSDriverSetMode(self.dev_handle, self.channel, self.NORMAL_MODE)

    def analog_out_off(self):
        """
        レーザーの照射を停止するためのメソッド
        """

        # モードをDISABLE(消灯)にする
        self.dll.MTUSB_BLSDriverSetMode(self.dev_handle, self.channel, self.DISABLE_MODE)

    def __del__(self):
        """
        デストラクタ
        機器との通信の切断に責任を持つ
        """

        # デバイスとの通信を切断
        if self.dll and self.dev_handle >= 0:
            self.dll.MTUSB_BLSDriverCloseDevice(self.dev_handle)
            self.dev_handle = -1
