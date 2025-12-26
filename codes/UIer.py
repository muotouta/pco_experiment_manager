#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
pcoカメラによる計測用アプリケーション「pco_experiment_manager」のUI周りの機能を実装するファイル
"""

__author__ = 'Tao Muto'
__version__ = '0.1.0'
__date__ = '2025.12.24'


import pco
import queue
import cv2
import numpy as np
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QFormLayout, QDoubleSpinBox, 
                             QPushButton, QLabel, QMessageBox, QGroupBox,
                             QRadioButton, QButtonGroup, QWidget, QHBoxLayout)
from PyQt6.QtCore import QThread, pyqtSignal, pyqtSlot, Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap


class UIer(QMainWindow):
    """
    UIを司るクラス
    """

    time_unit = {
        "s" : 1,
        "ms" : 1000,
        "μs" : 1000000
    }
    time_unit_id = "ms"


    def __init__(self, a_camera_handler):
        """
        コンストラクタ
        """

        super().__init__()

        self.a_camera_handler = a_camera_handler

        # シグナル接続
        self.a_camera_handler.new_frame_signal.connect(self.update_display)
        self.a_camera_handler.status_signal.connect(self.update_status)

        self.setWindowTitle("pco experiment manager")
        self.resize(1100, 700)
        self.designUI()


    def designUI(self):
        """
        UIのデザインを司るメソッド
        """

        # 土台
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)  # 画面を左右に分割

        # --- 左側: 画像表示エリア ---
        self.image_label = QLabel("Initializing Camera...")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background-color: #222; color: #888; font-size: 20px;")
        self.image_label.setMinimumSize(640, 480)
        main_layout.addWidget(self.image_label, stretch=4)

        # --- 右側: コントロールパネル ---
        panel_widget = QWidget()
        panel_layout = QVBoxLayout(panel_widget)
        panel_widget.setFixedWidth(300)
        
        # 1. パラメータ設定グループ
        settings_group = QGroupBox("Camera")
        form_layout = QFormLayout()
        self.radio_group = QButtonGroup(self)

        # カメラの名前
        self.camera_name = QLabel()
        self.camera_name.setText(f"name :  {self.a_camera_handler.desc['name']}")
        form_layout.addRow(self.camera_name)

        # 露光時間 (Exposure)
        self.spin_exposure = QDoubleSpinBox()
        self.spin_exposure.setRange(self.a_camera_handler.desc["min exposure time"] * self.time_unit[self.time_unit_id], self.a_camera_handler.desc['max exposure time'] * self.time_unit[self.time_unit_id])  # カメラに合わせて露光時間の最大値 / 最小値を設定
        self.spin_exposure.setSingleStep(5)
        self.spin_exposure.setDecimals(3)
        self.spin_exposure.setValue(100)  # デフォルト値
        self.spin_exposure.setSuffix(f" {self.time_unit_id}")
        self.spin_exposure.valueChanged.connect(self.on_exposure_changed)

        self.rb_exposure = QRadioButton()
        self.rb_exposure.setChecked(True) # デフォルトで選択状態にする
        self.radio_group.addButton(self.rb_exposure)

        row_exposure = QWidget()
        lay_exposure = QHBoxLayout(row_exposure)
        lay_exposure.setContentsMargins(0, 0, 0, 0) # 余白を消してスッキリさせる
        lay_exposure.addWidget(self.spin_exposure)
        lay_exposure.addWidget(self.rb_exposure)
        lay_exposure.setAlignment(Qt.AlignmentFlag.AlignRight)
        form_layout.addRow("Exposure :  ", row_exposure)

        self.description_exposure = QLabel()
        self.description_exposure.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.description_exposure.setText(f"{self.a_camera_handler.desc['min exposure time'] * self.time_unit[self.time_unit_id]} ~ {self.a_camera_handler.desc['max exposure time'] * self.time_unit[self.time_unit_id]} (ms)")
        form_layout.addRow(self.description_exposure)

        # フレームレート (fps)
        self.spin_fps = QDoubleSpinBox()
        self.spin_fps.setRange(1.0, 500.0)
        self.spin_fps.setSingleStep(1.0)
        self.spin_fps.setDecimals(3)
        self.spin_fps.setValue(40)  # デフォルト値
        self.spin_fps.setSuffix(" fps")
        self.spin_fps.valueChanged.connect(self.on_fps_changed)
        
        self.rb_fps = QRadioButton()
        self.radio_group.addButton(self.rb_fps)

        row_fps = QWidget()
        lay_fps = QHBoxLayout(row_fps)
        lay_fps.setContentsMargins(0, 0, 0, 0)
        lay_fps.addWidget(self.spin_fps)
        lay_fps.addWidget(self.rb_fps)
        lay_fps.setAlignment(Qt.AlignmentFlag.AlignRight)
        form_layout.addRow("fps :  ", row_fps)

        self.description_fps = QLabel()
        self.description_fps.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.description_fps.setText(f"{self.a_camera_handler.desc['min fps'] * self.time_unit[self.time_unit_id]} ~ {self.a_camera_handler.desc['max fps'] * self.time_unit[self.time_unit_id]} (ms)")
        form_layout.addRow(self.description_fps)

        # 遅延時間 (Delay)
        self.spin_delay = QDoubleSpinBox()
        self.spin_delay.setRange(self.a_camera_handler.desc['min delay time'] * self.time_unit[self.time_unit_id], self.a_camera_handler.desc['max delay time'] * self.time_unit[self.time_unit_id])  # カメラに合わせて露光時間の最大値 / 最小値を設定
        self.spin_delay.setSingleStep(5)
        self.spin_delay.setDecimals(3)
        self.spin_delay.setValue(0.0)  # デフォルト値
        self.spin_delay.setSuffix(f" {self.time_unit_id}")
        self.spin_delay.valueChanged.connect(self.on_delay_changed)
        
        self.rb_delay = QRadioButton()
        self.radio_group.addButton(self.rb_delay)

        row_delay = QWidget()
        lay_delay = QHBoxLayout(row_delay)
        lay_delay.setContentsMargins(0, 0, 0, 0)
        lay_delay.addWidget(self.spin_delay)
        lay_delay.addWidget(self.rb_delay)
        lay_delay.setAlignment(Qt.AlignmentFlag.AlignRight)
        form_layout.addRow("delay :  ", row_delay)

        self.description_delay = QLabel()
        self.description_delay.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.description_delay.setText(f"{self.a_camera_handler.desc['min delay time'] * self.time_unit[self.time_unit_id]} ~ {self.a_camera_handler.desc['max delay time'] * self.time_unit[self.time_unit_id]} (ms)")
        form_layout.addRow(self.description_delay)

        settings_group.setLayout(form_layout)
        panel_layout.addWidget(settings_group)

        # 2. 録画制御グループ
        record_group = QGroupBox("Recording")
        record_layout = QVBoxLayout()
        
        self.btn_record = QPushButton("Start")
        self.btn_record.setCheckable(True) # ON/OFF状態を持つボタンにする
        self.btn_record.setFixedHeight(50)
        self.btn_record.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.btn_record.toggled.connect(self.on_record_toggled)
        
        self.lbl_status = QLabel("Ready")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        record_layout.addWidget(self.btn_record)
        record_layout.addWidget(self.lbl_status)
        record_group.setLayout(record_layout)
        panel_layout.addWidget(record_group)

        # 余白
        panel_layout.addStretch()
        
        main_layout.addWidget(panel_widget, stretch=1)

    # --- 操作イベントハンドラ ---
    def on_exposure_changed(self, val):
        self.a_camera_handler.set_exposure(val / self.time_unit[self.time_unit_id])

    def on_fps_changed(self, val):
        self.a_camera_handler.set_fps(val)

    def on_delay_changed(self, val):
        self.a_camera_handler.set_delay(val / self.time_unit[self.time_unit_id])

    def on_record_toggled(self, checked):
        if checked:
            # 録画開始
            self.btn_record.setText("Stop")
            self.btn_record.setStyleSheet("background-color: #ffcccc; color: red; font-size: 16px; font-weight: bold;")

        else:
            # 録画停止
            self.btn_record.setText("Start")
            self.btn_record.setStyleSheet("font-size: 16px; font-weight: bold;")



    @pyqtSlot(np.ndarray, dict)
    def update_display(self, image_data, meta):
        """
        カメラからのイベント発生を受け付け、それとともに送られてくる画像をGUIに反映するメソッド
        """

        try:
            # メタデータから遅延時間などの実際の値を取得できれば表示更新
            # ここでは簡易的に現在の設定値を表示
            # (実際はCameraWorkerから現在のDelayを送ってもらうのがベスト)
            
            # --- 画像の変換と表示 --- 
            
            height, width = image_data.shape
            q_img = QImage(image_data.data, width, height, width, QImage.Format.Format_Grayscale8)
            
            pixmap = QPixmap.fromImage(q_img)
            self.image_label.setPixmap(pixmap.scaled(
                self.image_label.size(), 
                Qt.AspectRatioMode.KeepAspectRatio, 
                # Qt.TransformationMode.SmoothTransformation  # 画質優先
                Qt.TransformationMode.FastTransformation  # 速度優先
            ))

        except Exception as e:
            print(f"UIer Error in function \"update_display\": {e}")

    @pyqtSlot(str)
    def update_status(self, msg):
        """
        レコーディングの状況に合わせて、「recording」欄の下の表示を変更するメソッド
        """

        self.lbl_status.setText(msg)
