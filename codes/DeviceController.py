#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
pcoカメラによる計測用アプリケーション「pco_experiment_manager」の実験機器を表現するための機能を実装するファイル
"""

__author__ = 'Tao Muto'
__version__ = '0.0.4'
__date__ = '2025.12.29'


import traceback


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

        self.value = [None, None, None]
        self.value_max = [None, None, None]
        self.value_min = [None, None, None]
        self.value_unit = [None, None, None]

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

        if self.on_function:
            try:
                self.on_function()
            except Exception as e:
                print(f"DeviceController Error in on(): {e}")
                traceback.print_exc() 
        else:
            print("DeviceController Error: \"on_function\" is not defined")

    def off(self):
        """
        呼び出されると自身をOFFにするメソッド
        """

        self.state = False

        if self.off_function:
            try:
                self.off_function()
            except Exception as e:
                print(f"DeviceController Error in on(): {e}")
                traceback.print_exc() 
        else:
            print("DeviceController Error: \"off_function\" is not defined")

    def is_active(self):
        """
        自身の状態(onかoffか)を返すメソッド
        """

        return self.state
    
    def set_value(self, param, val):
        """
        自身の値を引数の値に変更するメソッド
        """

        if self.value[param] is None:
            print(f"DeveiceController Error in functon \"set_value\":  Device \"{self.device_type}\" has no numeric parameter")
        else:
            self.value[param] = val

    def current_value(self, param):
        """
        自身の現在の値を答えるメソッド
        値を持たないデバイスでは、Noneが返る。
        """

        if self.value[param] is None:
            print(f"DeveiceController Error in functon \"current_value\":  Device \"{self.device_type}\" has no numeric parameter")
            return None
        else:
            return self.value[param]
    
    def max_value(self, param):
        """
        自身の最大の値を答えるメソッド
        値を持たないデバイスでは、Noneが返る。
        """

        if self.value[param] is None:
            print(f"DeveiceController Error in functon \"max_value\":  Device \"{self.device_type}\" has no numeric parameter")
            return None
        else:
            return self.value_max[param]
    
    def min_value(self, param):
        """
        自身の最小の値を答えるメソッド
        値を持たないデバイスでは、Noneが返る。
        """

        if self.value[param] is None:
            print(f"DeveiceController Error in functon \"min_value\":  Device \"{self.device_type}\" has no numeric parameter")
            return None
        else:
            return self.value_min[param]

    def unit(self, param):
        """
        自身の値の単位を答えるメソッド
        値を持たないデバイスでは、Noneが返る。
        """
        if self.value[param] is None:
            print(f"DeveiceController Error in functon \"value_unit\":  Device \"{self.device_type}\" has no numeric parameter")
            return None
        else:
            return self.value_unit[param]


class Mightex_BLS_Controller(DeviceController):
    """
    Mightex BLSD Driverにより、Mightex BLS led controllerの一つのチャンネルを制御するクラス
    対象機器のdllとデバイスハンドルを外部プログラムから与え、またチャンネルを指定することで、対象機器の特定のチャンネルを扱うインスタンスを得る。
    Mightexが公開するライブラリのdllを、標準のpythonラッパではなく、ctypesにより制御する。それにより、Pythonバージョン非依存にする。
    """

    DISABLE_MODE = 0
    NORMAL_MODE = 1

    def __init__(self, dll, dev_handle, channel, param):
        """
        コンストラクタ
        """

        super().__init__()

        # 親クラスのフィールドを設定
        self.device_type = "Mightex BLS led controller"
        self.state = False
        self.on_functon = None
        self.off_function = None
        self.value[param] = 7
        self.value_max[param] = 1000
        self.value_min[param] = 0
        self.value_unit[param] = "0.1%"

        # 子クラスのフィールドを設定
        self.param = param
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
        self.dll.MTUSB_BLSDriverSetNormalCurrent(self.dev_handle, self.channel, int(self.value[self.param]))
        
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



import numpy as np
import sounddevice as sd

class adafruit_3369_Controller(DeviceController):
    """
    adafruit 3369 をコントロールするためのクラス
    ピッチと音量を指定することができる
    """

    DEVICE_ID = 1 # Windowsが認識するオーディオ出力先のデバイスID番号を指定する。

    def __init__(self):
        """
        コンストラクタ
        """

        super().__init__()

        # Windowsのオーディオデバイスの標準設定のサンプリングレートを取得
        try:
            dev_info = sd.query_devices(self.DEVICE_ID, 'output')
            self.actual_sample_rate = dev_info['default_samplerate']
        except Exception as e:
            print(f"adafruit_3369_Controller Error in \"__init__\": {e}")
            self.actual_sample_rate = 44100 # 取得失敗時のフォールバック

        # 親クラスのフィールドを設定
        self.device_type = "adafruit 3369"
        self.state = False
        self.on_function = False
        self.off_function = False
        self.value[0] = 440  # value[0]はピッチ
        self.value_max[0] = self.actual_sample_rate / 2  # これより高い周波数ではエイリアシングが起きる。
        self.value_min[0] = 0
        self.value_unit[0] = "Hz"
        self.value[1] = 20  # value[1]は音量。Windowsのマスターボリュームの何%か、という値。
        self.value_max[1] = 100
        self.value_min[1] = 0
        self.value_unit[1] = "%"

        # ストリーム制御用の変数を初期化
        self.stream = None
        self.current_phase = 0.0

        # このクラスを、DeviceCOntrollerクラスの関数で扱えるようにするための設定
        self.on_function = self.sound_on
        self.off_function = self.sound_off

    def sound_on(self):
        """
        音の出力を開始するための関数
        """

        if self.stream and self.stream.active:
            return

        try:
            # samplerate=None を指定して、デバイスのネイティブなレートを使わせる
            self.stream = sd.OutputStream(
                samplerate=None, 
                channels=1,
                callback=self._audio_callback,
                device=self.DEVICE_ID
            )
            
            # ストリームが決定した「本当のサンプリングレート」を取得して更新
            if self.stream.samplerate:
                self.actual_sample_rate = self.stream.samplerate
                self._update_limits()

            self.stream.start()
            
        except Exception as e:
            print(f"adafruit_3369_Controller Error in \"sound_on\": {e}")
    
    def sound_off(self):
        """
        音の出力を停止するための関数
        """

        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        self.current_phase = 0.0  # 次回再生時に頭から再生するために、位相をリセット

    def _audio_callback(self, outdata, frames, time, status):
        """
        音声データをリアルタイム生成するコールバック関数
        """

        # 現在の設定値を取得
        freq = self.value[0]
        vol_percent = self.value[1]

        if freq is None: freq = 440.0
        if vol_percent is None: vol_percent = 0.0
        
        amp = vol_percent / 100.0

        # 位相を計算
        phase_increment = 2 * np.pi * freq / self.actual_sample_rate  # 1フレームあたりの位相変化量
        t = np.arange(frames)  # 時間軸(フレーム数分)の配列を作成
        phases = self.current_phase + t * phase_increment  # 現在の位相からの変化を足す
        self.current_phase = (self.current_phase + frames * phase_increment) % (2 * np.pi)  # 次の呼び出しのために最終位相を保存 (2πで割った余りにしてオーバーフロー防止)

        # サイン波の生成
        sine_wave = amp * np.sin(phases)
        
        # 出力バッファに書き込み
        outdata[:] = sine_wave.astype(np.float32).reshape(-1, 1)  # float32型にキャストして書き込むことで、データ型の不一致を防止

    def _update_limits(self):
        """
        最大値・最小値を現在のレートに基づいて更新するメソッド
        """
        
        self.value_max[0] = self.actual_sample_rate / 2
        self.value_min[0] = 0
        self.value_max[1] = 100
        self.value_min[1] = 0