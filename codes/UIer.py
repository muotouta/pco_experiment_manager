#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
pcoカメラによる計測用アプリケーション「pco_experiment_manager」のUI周りの機能を実装するファイル
"""

__author__ = 'Tao Muto'
__version__ = '0.1.4'
__date__ = '2025.12.27'


import pco
import queue
import cv2
import numpy as np
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QFormLayout, QDoubleSpinBox, 
                             QPushButton, QLabel, QMessageBox, QGroupBox,
                             QRadioButton, QButtonGroup, QWidget, QHBoxLayout,
                             QComboBox, QCheckBox)
from PyQt6.QtCore import QThread, pyqtSignal, pyqtSlot, Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap, QFont


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


    def __init__(self, a_camera_handler, a_saver):
        """
        コンストラクタ
        """

        super().__init__()

        self.a_camera_handler = a_camera_handler
        self.a_saver = a_saver

        # シグナル接続
        self.a_camera_handler.new_frame_signal.connect(self.update_display)
        self.a_camera_handler.params_updated_signal.connect(self.on_params_updated)  # カメラの設定更新シグナルの接続

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
        main_layout = QHBoxLayout(central_widget)

        # --- 左側: 画像表示エリア ---
        self.image_label = QLabel("Initializing Camera...")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background-color: #222; color: #888;")
        font_img = QFont()
        font_img.setPointSize(20)
        self.image_label.setFont(font_img)
        self.image_label.setMinimumSize(640, 480)
        main_layout.addWidget(self.image_label, stretch=4)

        # --- 右側: コントロールパネル ---
        panel_widget = QWidget()
        panel_layout = QVBoxLayout(panel_widget)
        panel_widget.setFixedWidth(300)
        
        # 1. パラメータ設定グループ
        self.settings_group = QGroupBox("Camera")
        form_layout = QFormLayout()
        
        # ラジオボタンのグループ（Exposure と FPS の排他選択用）
        self.radio_group = QButtonGroup(self)
        self.radio_group.buttonToggled.connect(self.toggle_inputs) # 切り替え時にロック処理を実行

        # --- カメラの名前 ---
        self.camera_name = QLabel()
        self.camera_name.setText(f"name :  {self.a_camera_handler.desc['name']}")
        form_layout.addRow(self.camera_name)

        # --- 露光時間 (Exposure) ---
        self.spin_exposure = QDoubleSpinBox()

        # 範囲設定
        min_exp = self.a_camera_handler.desc["min exposure time"] * self.time_unit[self.time_unit_id]
        max_exp = self.a_camera_handler.desc['max exposure time'] * self.time_unit[self.time_unit_id]
        self.spin_exposure.setRange(min_exp, max_exp)
        self.spin_exposure.setSingleStep(0.05)
        self.spin_exposure.setDecimals(3)
        self.spin_exposure.setValue(25)  # 初期値
        self.spin_exposure.setSuffix(f" {self.time_unit_id}")
        self.spin_exposure.valueChanged.connect(self.on_exposure_changed)

        self.rb_exposure = QRadioButton()
        self.radio_group.addButton(self.rb_exposure)

        row_exposure = QWidget()
        lay_exposure = QHBoxLayout(row_exposure)
        lay_exposure.setContentsMargins(0, 0, 0, 0)
        lay_exposure.addWidget(self.spin_exposure)
        lay_exposure.addWidget(self.rb_exposure)
        lay_exposure.setAlignment(Qt.AlignmentFlag.AlignRight)
        form_layout.addRow("Exposure :  ", row_exposure)

        self.description_exposure = QLabel()
        self.description_exposure.setAlignment(Qt.AlignmentFlag.AlignRight)
        tmp = f"{min_exp:.3f}"
        self.description_exposure.setText(f"{tmp} ~ {max_exp} ({self.time_unit_id})")
        form_layout.addRow(self.description_exposure)

        # --- フレームレート (fps) ---
        self.spin_fps = QDoubleSpinBox()
        self.spin_fps.setRange(1.0, 500.0)
        self.spin_fps.setSingleStep(1.0)
        self.spin_fps.setDecimals(3)
        self.spin_fps.setValue(40)  # 初期値
        self.spin_fps.setSuffix(" fps")
        self.spin_fps.valueChanged.connect(self.on_fps_changed)
        
        self.rb_fps = QRadioButton()
        self.rb_fps.setChecked(True)  # デフォルトでこちらを選択
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
        self.description_fps.setText(f"Max: {self.a_camera_handler.desc['max fps']:.1f} fps")
        form_layout.addRow(self.description_fps)

        # --- 遅延時間 (Delay) ---
        self.lbl_delay_val = QLabel() # 値表示用
        self.lbl_delay_val.setAlignment(Qt.AlignmentFlag.AlignRight)
        form_layout.addRow("Delay : ", self.lbl_delay_val)

        self.settings_group.setLayout(form_layout)
        panel_layout.addWidget(self.settings_group)

        # 2. トリガー設定グループ (Trigger)
        self.trigger_group = QGroupBox("Trigger")
        trigger_layout = QVBoxLayout()
        
        self.chk_laser1 = QCheckBox("Blue Laser")
        self.chk_laser2 = QCheckBox("Red Laser")
        self.chk_speaker = QCheckBox("Speaker")
        self.chk_ttl = QCheckBox("5V TTL")
        
        trigger_layout.addWidget(self.chk_laser1)
        trigger_layout.addWidget(self.chk_laser2)
        trigger_layout.addWidget(self.chk_speaker)
        trigger_layout.addWidget(self.chk_ttl)
        
        self.trigger_group.setLayout(trigger_layout)
        panel_layout.addWidget(self.trigger_group)

        panel_layout.addStretch()


        # 3. 録画制御グループ
        record_group = QGroupBox("Recording")
        record_layout = QVBoxLayout()

        # 録画モード選択プルダウン (Startボタンの上に追加)
        self.combo_rec_mode = QComboBox()
        self.combo_rec_mode.addItems(["manual", "program"])
        self.combo_rec_mode.setFixedHeight(30) # 少し高さを確保して押しやすく
        font_combo = QFont()
        self.combo_rec_mode.setFont(font_combo)
        record_layout.addWidget(self.combo_rec_mode)
        
        self.btn_record = QPushButton("Start")
        self.btn_record.setCheckable(True)
        self.btn_record.setFixedHeight(50)
        self.btn_record.setStyleSheet("font-weight: bold;")
        font_btn = QFont()
        font_btn.setPointSize(16)
        font_btn.setBold(True)
        self.btn_record.setFont(font_btn)
        self.btn_record.toggled.connect(self.on_record_toggled)
        
        record_layout.addWidget(self.btn_record)
        record_group.setLayout(record_layout)
        panel_layout.addWidget(record_group)

        # 余白
        main_layout.addWidget(panel_widget, stretch=1)

        # 初期状態の反映（ロック状態の適用とDelay計算）
        self.toggle_inputs()
        self.update_delay_display()


    # --- 操作イベントハンドラ ---
    def toggle_inputs(self):
        """
        ラジオボタンの状態を見て、入力欄の有効/無効を切り替える
        """
        
        if self.rb_exposure.isChecked():  # Exposureが選択されている -> Exposure固定(入力不可)、FPS変更可
            self.spin_exposure.setEnabled(False)
            self.spin_fps.setEnabled(True)
        else:  # FPSが選択されている -> FPS固定(入力不可)、Exposure変更可
            self.spin_exposure.setEnabled(True)
            self.spin_fps.setEnabled(False)

        # 切り替え時に制限値（最大値）と説明文を更新する
        self.update_limit_ranges()

    def on_exposure_changed(self, val):
        """
        Exposure変更時の処理
        """

        self.a_camera_handler.set_exposure(val / self.time_unit[self.time_unit_id])
        self.update_delay_display()
        self.update_limit_ranges()  # FPSの上限（説明文と制限）も即座に再計算して表示

    def on_fps_changed(self, val):
        """
        FPS変更時の処理
        """

        self.update_delay_display()
        self.update_limit_ranges()  # 値が変わったので、Exposureの上限（説明文と制限）も即座に再計算して表示する

    def update_delay_display(self):
        """
        現在のFPSとExposureからDelayを逆算して表示する
        簡易的に Delay = (1/FPS) - Exposure として計算し表示
        """

        try:
            fps = self.spin_fps.value()
            exposure_ms = self.spin_exposure.value()
            exposure_s = exposure_ms / self.time_unit[self.time_unit_id]

            if fps > 0:
                frame_time_s = 1.0 / fps
                delay_s = frame_time_s - exposure_s  # Delay = フレーム時間 - 露光時間
                
                # マイナスになる場合は0クリップ（またはFPS/Exposure設定が矛盾している）
                if delay_s < 0:
                    delay_s = 0.0
                
                # ハンドラにセット
                self.a_camera_handler.set_delay(delay_s)

                # 表示更新
                delay_ms = delay_s * self.time_unit[self.time_unit_id]
                self.lbl_delay_val.setText(f"{delay_ms:.3f} {self.time_unit_id}")

        except Exception as e:
            print(f"Delay calc error: {e}")
    
    def update_limit_ranges(self):
        """
        現在の設定値に基づいて、物理的に可能な最大値を計算し、
        入力制限と説明ラベルを更新するメソッド（安全装置付き修正版）
        """
        try:
            # --- 1. 共通の定数・現在値の取得 ---
            # 物理的な最小遅延時間（秒）
            min_delay_s = self.a_camera_handler.desc.get("min delay time", 0.0)
            
            # ハードウェアとしての最大値（秒）
            # もしカメラ情報が 0 や None だった場合、安全なデフォルト値(100s, 500fps)を使う
            hw_max_exp_s = self.a_camera_handler.desc.get("max exposure time", 10.0)
            if hw_max_exp_s <= 0: hw_max_exp_s = 10.0
            
            hw_max_fps = self.a_camera_handler.desc.get("max fps", 500.0)
            if hw_max_fps <= 0: hw_max_fps = 500.0
            
            # 現在の入力値
            curr_exp_val = self.spin_exposure.value()
            curr_exp_s = curr_exp_val / self.time_unit[self.time_unit_id]
            curr_fps = self.spin_fps.value()

            # --- 2. 相互の制限値を計算 ---
            
            # A. 現在のExposure値における、理論上の最大FPS
            if (curr_exp_s + min_delay_s) > 0:
                calc_max_fps = 1.0 / (curr_exp_s + min_delay_s)
            else:
                calc_max_fps = hw_max_fps
            
            # ハードウェア限界を超えないようにクリップ
            real_max_fps = min(hw_max_fps, calc_max_fps)
            if real_max_fps < 0.001: real_max_fps = 0.001  # 最大値が0以下にならないようにガード


            # B. 現在のFPS値における、理論上の最大Exposure
            if curr_fps > 0:
                calc_max_exp_s = (1.0 / curr_fps) - min_delay_s
            else:
                calc_max_exp_s = hw_max_exp_s
            
            # 0以下やハードウェア限界のチェック
            if calc_max_exp_s < 0: calc_max_exp_s = 0
            real_max_exp_s = min(hw_max_exp_s, calc_max_exp_s)
            
            # 表示用に単位変換
            disp_max_exp = real_max_exp_s * self.time_unit[self.time_unit_id]
            disp_min_exp = self.a_camera_handler.desc["min exposure time"] * self.time_unit[self.time_unit_id]


            # --- 3. 入力フォームの制限 (SpinBox) ---
            if self.rb_exposure.isChecked():  # Exposure固定モード（FPS可変）
                fps_limit = max(real_max_fps, self.spin_fps.minimum())
                self.spin_fps.setMaximum(fps_limit)
                
                # Exposure入力欄はハードウェア限界まで
                hw_max_exp_val = hw_max_exp_s * self.time_unit[self.time_unit_id]
                self.spin_exposure.setMaximum(hw_max_exp_val)

            else:  # FPS固定モード（Exposure可変）
                # setMaximumする値が、現在のminimumより小さいと挙動がおかしくなるためチェック
                exp_limit = max(disp_max_exp, self.spin_exposure.minimum())
                self.spin_exposure.setMaximum(exp_limit)
                
                # FPS入力欄はハードウェア限界まで
                self.spin_fps.setMaximum(hw_max_fps)


            # --- 4. 説明ラベルの更新 (Label) ---
            self.description_exposure.setText(f"{disp_min_exp:.3f} ~ {disp_max_exp:.3f} ({self.time_unit_id})")
            self.description_fps.setText(f"~  {real_max_fps:.3f} (fps)")

        except Exception as e:
            print(f"Update limit ranges error: {e}")

    def on_params_updated(self):
        """
        CameraHandlerで設定が反映された後、その実際の値を取得してUIを更新する
        """
        try:
            # カメラ側の真の値を取得 (単位は秒なので、UIに合わせて変換)
            true_exp_val = self.a_camera_handler.desc["exposure time"] * self.time_unit[self.time_unit_id]
            true_delay_val = self.a_camera_handler.desc["delay time"] * self.time_unit[self.time_unit_id]
            true_fps_val = self.a_camera_handler.desc["fps"]
            
            # --- Delayラベルの更新 ---
            self.lbl_delay_val.setText(f"{true_delay_val:.3f} {self.time_unit_id}")

            # --- 入力フォームの更新 ---
            # 「入力が終わったタイミング」＝「フォーカスが外れている」または「操作不可(ロック中)」のときのみ更新する
            # 入力中に勝手に数値が変わると操作しにくいため。

            # Exposureの更新
            if not self.spin_exposure.hasFocus() or not self.spin_exposure.isEnabled():
                self.spin_exposure.blockSignals(True) # 無限ループ防止（値セットでvalueChangedが呼ばれないようにする）
                self.spin_exposure.setValue(true_exp_val)
                self.spin_exposure.blockSignals(False)

            # FPSの更新 (FPSはHandler側で丸め処理をしていない場合はそのままですが、念のため)
            # 必要であれば desc["fps"] も CameraHandler側で更新するように実装してください
            if not self.spin_fps.hasFocus() or not self.spin_fps.isEnabled():
                self.spin_fps.blockSignals(True) # 無限ループ防止（値セットでvalueChangedが呼ばれないようにする）
                self.spin_fps.setValue(true_fps_val)
                self.spin_fps.blockSignals(False)

            # 値が確定したので、それに基づいて制限範囲も再計算して表示を更新する
            self.update_limit_ranges()

        except Exception as e:
            print(f"UIer Error in function \"on_params_updated\": {e}")
        
    def on_record_toggled(self, checked):
        if checked:
            # 録画開始
            self.btn_record.setText("Stop")
            self.btn_record.setStyleSheet("background-color: #ffcccc; color: red; font-weight: bold;")

            # 録画中はプルダウンを無効化
            self.combo_rec_mode.setEnabled(False)
            
            # programモードなら設定項目全体をロック
            if self.combo_rec_mode.currentText() == "program":
                self.settings_group.setEnabled(False)
                self.trigger_group.setEnabled(False)
            
            # カメラのモードを変更
            self.a_camera_handler.set_camera_mode("queue")
            self.a_camera_handler.start_recording()

        else:
            # 録画停止
            self.btn_record.setText("Start")
            self.btn_record.setStyleSheet("")

            # プルダウンを有効化
            self.combo_rec_mode.setEnabled(True)
            
            # 設定項目のロックを解除（有効化）
            self.settings_group.setEnabled(True)
            self.trigger_group.setEnabled(True)
            
            # Cameraグループを有効化した後、ラジオボタンの排他制御が崩れないよう再適用
            self.toggle_inputs()

            # カメラのモードを変更
            self.a_camera_handler.set_camera_mode("shot")
            self.a_camera_handler.stop_recording()



    @pyqtSlot(np.ndarray, dict)
    def update_display(self, image_data, meta):
        """
        カメラからのイベント発生を受け付け、それとともに送られてくる画像をGUIに反映するメソッド
        """

        try:
            # ラベルのサイズを取得（ウィンドウサイズに合わせて変動）
            label_h = self.image_label.height()
            label_w = self.image_label.width()
            
            # 現在の画像サイズ
            h, w = image_data.shape
            
            # アスペクト比を維持して、ラベルの高さに合わせる
            scale = label_h / h
            new_w = int(w * scale)
            new_h = int(h * scale)
            
            # もし横幅がはみ出るなら、横幅に合わせて再計算
            if new_w > label_w:
                scale = label_w / w
                new_w = int(w * scale)
                new_h = int(h * scale)

            # OpenCVでリサイズ (INTER_NEARESTは画質は粗いが最速。綺麗にしたいならINTER_LINEAR)
            if scale < 1.0: # 画像が画面より大きい場合のみリサイズ
                image_data = cv2.resize(image_data, (new_w, new_h), interpolation=cv2.INTER_NEAREST)
            
            # 3. QImage変換
            height, width = image_data.shape
            q_img = QImage(image_data.data, width, height, width, QImage.Format.Format_Grayscale8)
            
            # 4. 表示
            self.image_label.setPixmap(QPixmap.fromImage(q_img))

        except Exception as e:
            print(f"UIer Error in function \"update_display\": {e}")