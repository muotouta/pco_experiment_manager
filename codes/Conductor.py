#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
pcoカメラによる計測用アプリケーション「pco_experiment_manager」の実験遂行周りの機能を実装するファイル
"""

__author__ = 'Tao Muto'
__version__ = '0.0.1'
__date__ = '2025.12.27'





class Conductor():
    """
    実験の遂行を司るクラス
    """

    time_unit = {
        "s" : 1,
        "ms" : 1000,
        "μs" : 1000000
    }
    time_unit_id = "ms"


    def __init__(self):
        pass