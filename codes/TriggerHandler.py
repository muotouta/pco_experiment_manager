#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
pcoカメラによる計測用アプリケーション「pco_experiment_manager」の実験機器の管理周りの機能を実装するファイル
"""

__author__ = 'Tao Muto'
__version__ = '0.0.2'
__date__ = '2025.12.28'

from DeviceController import Mightex_BLS_Controller

class TriggerHandler():
    """
    実験機器の管理を司るクラス
    """

    def __init__(self):
        self.ttl_triger_1 = Mightex_BLS_Controller(dev_id=0, channel=1)
        self.ttl_triger_2 = Mightex_BLS_Controller(dev_id=0, channel=2)
        self.blue_laser = Mightex_BLS_Controller(dev_id=0, channel=3)
        self.red_laser = Mightex_BLS_Controller(dev_id=0, channel=4)
        self.speaker = None

    # --- 各チャンネル操作用メソッド ---
    def toggle_ttl_trigger_1(self, is_on: bool):
        """
        TTl Trriger 1のON/OFFを切り替える
        """

        if is_on:
            self.ttl_triger_one.on()
        else:
            self.ttl_triger_one.off()

    def toggle_ttl_trigger_2(self, is_on: bool):
        """
        TTl Trriger 2のON/OFFを切り替える
        """

        if is_on:
            self.ttl_triger_two.on()
        else:
            self.ttl_triger_two.off()

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
            self.red_laser.on()
        else:
            self.red_laser.off()
