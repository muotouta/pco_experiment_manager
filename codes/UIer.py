#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
pcoカメラによる計測用アプリケーション「pco_experiment_manager」のUI周りの機能を実装するファイル
"""

__author__ = 'Tao Muto'
__version__ = '0.1.9'
__date__ = '2025.12.29'


import pco
import queue
import cv2
import numpy as np
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QFormLayout, QDoubleSpinBox, 
                             QPushButton, QLabel, QMessageBox, QGroupBox,
                             QRadioButton, QButtonGroup, QComboBox, QCheckBox,
                             QSizePolicy)
from PyQt6.QtCore import QThread, pyqtSignal, pyqtSlot, Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap, QFont


class ExperimentWorker(QThread):
    """
    Conductorを別スレッドで動かすためのワーカークラス
    """
    
    finished_signal = pyqtSignal()

    def __init__(self, conductor):
        super().__init__()
        self.conductor = conductor

    def run(self):
        # Conductorのrunメソッドを実行。完了するか中断されるまでブロックする。
        self.conductor.run()

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


    def __init__(self, a_camera_handler, a_saver, a_trigger_handler, a_conductor=None):
        """
        コンストラクタ
        """

        super().__init__()

        self.a_camera_handler = a_camera_handler
        self.a_saver = a_saver
        self.a_trigger_handler = a_trigger_handler
        self.a_conductor = a_conductor

        # カウントダウン用タイマーの設定
        self.rec_timer = QTimer(self)
        self.rec_timer.setInterval(1000) # 1秒間隔
        self.rec_timer.timeout.connect(self.on_countdown_tick)
        self.countdown_val = 3

        # シグナル接続
        self.a_camera_handler.new_frame_signal.connect(self.update_display)
        self.a_camera_handler.params_updated_signal.connect(self.on_params_updated)  # カメラの設定更新シグナルの接続

        self.setWindowTitle("pco experiment manager")
        self.resize(1100, 750) # レイアウトが増えたため少し高さを拡張
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
        panel_widget.setFixedWidth(320)
        
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
        self.spin_exposure.setFixedWidth(90)
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
        self.spin_fps.setFixedWidth(90)
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
        self.trigger_group = QGroupBox("Device")
        trigger_layout = QVBoxLayout()
        
        # TTL 1
        self.chk_ttl1 = QCheckBox()
        self.chk_ttl1.toggled.connect(self.a_trigger_handler.toggle_ttl_trigger_1)
        self.spin_ttl1 = self.add_trigger_row("CH1 Analog out", self.chk_ttl1, trigger_layout,
                                         self.a_trigger_handler.ttl_triger_1,
                                         self.a_trigger_handler.set_ttl_trigger_1_value,
                                         0)

        # TTL 2
        self.chk_ttl2 = QCheckBox()
        self.chk_ttl2.toggled.connect(self.a_trigger_handler.toggle_ttl_trigger_2)
        self.spin_ttl2 = self.add_trigger_row("CH2 Analog Out", self.chk_ttl2, trigger_layout,
                                         self.a_trigger_handler.ttl_triger_2,
                                         self.a_trigger_handler.set_ttl_trigger_2_value,
                                         0)

        # Blue Laser
        self.chk_laser1 = QCheckBox()
        self.chk_laser1.toggled.connect(self.a_trigger_handler.toggle_blue_laser)
        self.spin_laser1 = self.add_trigger_row("Blue Laser", self.chk_laser1, trigger_layout,
                                           self.a_trigger_handler.blue_laser,
                                           self.a_trigger_handler.set_blue_laser_value,
                                           0)

        # Red Laser
        self.chk_laser2 = QCheckBox()
        self.chk_laser2.toggled.connect(self.a_trigger_handler.toggle_red_laser)
        self.spin_laser2 = self.add_trigger_row("Red Laser", self.chk_laser2, trigger_layout,
                                           self.a_trigger_handler.red_laser,
                                           self.a_trigger_handler.set_red_laser_value,
                                           0)

        # Speaker
        self.chk_speaker = QCheckBox()
        self.chk_speaker.toggled.connect(self.a_trigger_handler.toggle_speaker)
        
        # ピッチ (Parameter 0)
        self.spin_speaker = self.add_trigger_row("Speaker", self.chk_speaker, trigger_layout,
                                    self.a_trigger_handler.speaker,
                                    self.a_trigger_handler.set_speaker_value_pitch,
                                    0, 0)

        # 音量 (Parameter 1)
        self.spin_speaker_vol = self.add_sub_parameter_row("", trigger_layout,
                                    self.a_trigger_handler.speaker,
                                    self.a_trigger_handler.set_speaker_value_volume,
                                    1)

        self.trigger_group.setLayout(trigger_layout)
        panel_layout.addWidget(self.trigger_group)
        
        


        self.trigger_group.setLayout(trigger_layout)
        panel_layout.addWidget(self.trigger_group)

        panel_layout.addStretch()

        # 3. 録画制御グループ
        record_group = QGroupBox("Recording")
        record_layout = QVBoxLayout()

        # 録画モード選択プルダウン
        self.combo_rec_mode = QComboBox()
        self.combo_rec_mode.addItems(["manual", "program"])
        self.combo_rec_mode.setFixedHeight(30)
        font_combo = QFont()
        self.combo_rec_mode.setFont(font_combo)
        self.combo_rec_mode.currentTextChanged.connect(self.on_rec_mode_changed)  # 変更があったら on_rec_mode_changed
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

        self.lbl_countdown = QLabel("")
        self.lbl_countdown.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_countdown.setFixedHeight(40)
        font_cd = QFont()
        font_cd.setPointSize(24)
        font_cd.setBold(True)
        self.lbl_countdown.setFont(font_cd)
        self.lbl_countdown.setStyleSheet("color: red;")
        
        record_layout.addWidget(self.lbl_countdown)
        record_group.setLayout(record_layout)
        panel_layout.addWidget(record_group)

        # 余白
        main_layout.addWidget(panel_widget, stretch=1)

        # 初期状態の反映
        self.toggle_inputs()
        self.update_delay_display()

    @pyqtSlot(np.ndarray, dict)
    def update_display(self, image_data, meta):
        try:
            label_h = self.image_label.height()
            label_w = self.image_label.width()
            h, w = image_data.shape
            scale = label_h / h
            new_w = int(w * scale)
            new_h = int(h * scale)
            
            if new_w > label_w:
                scale = label_w / w
                new_w = int(w * scale)
                new_h = int(h * scale)

            if scale < 1.0:
                image_data = cv2.resize(image_data, (new_w, new_h), interpolation=cv2.INTER_NEAREST)
            
            height, width = image_data.shape
            q_img = QImage(image_data.data, width, height, width, QImage.Format.Format_Grayscale8)
            self.image_label.setPixmap(QPixmap.fromImage(q_img))

        except Exception as e:
            print(f"UIer Error in function \"update_display\": {e}")

    def add_trigger_row(self, label_text, checkbox, trigger_layout, device, value_setter, param, margin_bottom=10):
        """
        トリガー設定行を生成するヘルパー関数
        device引数からmax/min/unitを取得して表示・設定に反映する
        """
        # 親コンテナ (縦並び: 上段[Check, Spin], 下段[Label])
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, margin_bottom) # 次の行との間隔
        container_layout.setSpacing(0)

        # デバイス情報の取得 (Noneガード)
        min_val = 0.0
        max_val = 100.0
        curr_val = 0.0
        unit = ""
        
        if device:
            # 最小値
            tmp = device.min_value(param)
            if tmp is not None: min_val = tmp
            # 最大値
            tmp = device.max_value(param)
            if tmp is not None: max_val = tmp
            # 現在値
            tmp = device.current_value(param)
            if tmp is not None: curr_val = tmp
            else: curr_val = min_val # 現在値がNoneなら最小値にしておく
            # 単位
            tmp = device.unit(param)
            if tmp is not None: unit = tmp

        # --- 上段: チェックボックスとSpinBox ---
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        checkbox.setText(label_text)
        top_layout.addWidget(checkbox)
        top_layout.addStretch()
        
        spin = QDoubleSpinBox()
        spin.setRange(float(min_val), float(max_val))
        spin.setSingleStep(1.0)
        spin.setDecimals(1) # 小数点以下桁数 (必要に応じて0にする等調整可)
        if int(max_val) == max_val and int(min_val) == min_val and device and unit != "%":
             spin.setDecimals(0) # 整数のみのデバイスの場合
             
        spin.setValue(float(curr_val))
        spin.setFixedWidth(90)
        
        # デバイスがない場合は無効化
        if device is None:
            spin.setEnabled(False)
            checkbox.setEnabled(False)

        spin.valueChanged.connect(value_setter)
        top_layout.addWidget(spin)

        container_layout.addWidget(top_widget)

        # --- 下段: 説明ラベル (Min ~ Max (Unit)) ---
        if device: # デバイスがある場合のみ表示
            bottom_widget = QWidget()
            bottom_layout = QHBoxLayout(bottom_widget)
            bottom_layout.setContentsMargins(0, 0, 0, 0)
            
            desc_label = QLabel()
            desc_label.setText(f"{min_val} ~ {max_val} ({unit})")
            desc_label.setStyleSheet("color: #666; font-size: 11px;")
            
            bottom_layout.addStretch() # 右寄せ
            bottom_layout.addWidget(desc_label)
            
            container_layout.addWidget(bottom_widget)

        trigger_layout.addWidget(container)
        return spin
    
    def add_sub_parameter_row(self, label_text, parent_layout, device, value_setter, param):
        """
        チェックボックスを持たない、従属パラメータ用の入力行を追加するヘルパー関数
        """
        # 親コンテナ
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(20, 0, 0, 10) # 左に20pxインデントをつける
        container_layout.setSpacing(0)

        # デバイス情報の取得
        min_val, max_val, curr_val, unit = 0.0, 100.0, 0.0, ""
        if device:
            min_val = device.min_value(param) if device.min_value(param) is not None else 0.0
            max_val = device.max_value(param) if device.max_value(param) is not None else 100.0
            curr_val = device.current_value(param) if device.current_value(param) is not None else min_val
            unit = device.unit(param) if device.unit(param) is not None else ""

        # --- 上段: ラベルとSpinBox ---
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        lbl = QLabel(label_text)
        top_layout.addWidget(lbl)
        top_layout.addStretch()
        
        spin = QDoubleSpinBox()
        spin.setRange(float(min_val), float(max_val))
        spin.setSingleStep(1.0) # 音量は整数ステップが見やすい
        
        # 小数点以下の表示制御 (単位が % の場合などは整数表示が見やすい)
        if int(max_val) == max_val and int(min_val) == min_val:
             spin.setDecimals(0)
             
        spin.setValue(float(curr_val))
        spin.setFixedWidth(90)
        
        if device is None:
            spin.setEnabled(False)

        spin.valueChanged.connect(value_setter)
        top_layout.addWidget(spin)

        container_layout.addWidget(top_widget)

        # --- 下段: 説明ラベル ---
        if device:
            bottom_widget = QWidget()
            bottom_layout = QHBoxLayout(bottom_widget)
            bottom_layout.setContentsMargins(0, 0, 0, 0)
            
            desc_label = QLabel()
            desc_label.setText(f"{min_val} ~ {max_val} ({unit})")
            desc_label.setStyleSheet("color: #666; font-size: 11px;")
            
            bottom_layout.addStretch()
            bottom_layout.addWidget(desc_label)
            
            container_layout.addWidget(bottom_widget)

        parent_layout.addWidget(container)
        return spin

    def closeEvent(self, event):
        """
        ウィンドウの「×」ボタンが押されたときに呼ばれるイベントハンドラ
        """

        # タイマー停止
        if self.rec_timer.isActive():
            self.rec_timer.stop()

        # Conductorの停止
        if self.a_conductor:
            self.a_conductor.is_running = False
        
        # 録画の停止
        if self.a_camera_handler:
            try:
                self.a_camera_handler.stop_recording()
                self.a_camera_handler.stop() # スレッド停止
            except Exception as e:
                print(f"UIer Error in \"closeEvent\": {e}")

        # Saverの停止
        if self.a_saver:
            try:
                self.a_saver.stop()
               
                # もしキューにデータが残っていれば、保存中であることをユーザーに伝える
                if not self.a_saver.data_queue.empty():
                    self.lbl_countdown.setText("Saving...") # 画面に表示
                    QApplication.processEvents()  # wait()すると画面がフリーズして「Saving...」が表示されないことがあるため、強制的に描画イベントを処理させる

                self.a_saver.wait()
            except Exception as e:
                print(f"UIer Error in \"closeEvent\": {e}")

        # 実験機器の強制OFF
        if self.a_trigger_handler:
            self.a_trigger_handler.close_all()

        # ウィンドウを閉じる処理を受け入れる
        event.accept()


    # --- 操作イベントハンドラ ---
    def toggle_inputs(self):
        """
        ラジオボタンの状態を見て、入力欄の有効/無効を切り替える
        """
        
        if self.rb_exposure.isChecked():
            self.spin_exposure.setEnabled(False)
            self.spin_fps.setEnabled(True)
        else:
            self.spin_exposure.setEnabled(True)
            self.spin_fps.setEnabled(False)

        self.update_limit_ranges()

    def on_exposure_changed(self, val):
        self.a_camera_handler.set_exposure(val / self.time_unit[self.time_unit_id])
        self.update_delay_display()
        self.update_limit_ranges()

    def on_fps_changed(self, val):
        self.update_delay_display()
        self.update_limit_ranges()

    def update_delay_display(self):
        try:
            fps = self.spin_fps.value()
            exposure_ms = self.spin_exposure.value()
            exposure_s = exposure_ms / self.time_unit[self.time_unit_id]

            if fps > 0:
                frame_time_s = 1.0 / fps
                delay_s = frame_time_s - exposure_s
                
                if delay_s < 0:
                    delay_s = 0.0
                
                self.a_camera_handler.set_delay(delay_s)

                delay_ms = delay_s * self.time_unit[self.time_unit_id]
                self.lbl_delay_val.setText(f"{delay_ms:.3f} {self.time_unit_id}")

        except Exception as e:
            print(f"Delay calc error: {e}")
    
    def update_limit_ranges(self):
        try:
            min_delay_s = self.a_camera_handler.desc.get("min delay time", 0.0)
            
            hw_max_exp_s = self.a_camera_handler.desc.get("max exposure time", 10.0)
            if hw_max_exp_s <= 0: hw_max_exp_s = 10.0
            
            hw_max_fps = self.a_camera_handler.desc.get("max fps", 500.0)
            if hw_max_fps <= 0: hw_max_fps = 500.0
            
            curr_exp_val = self.spin_exposure.value()
            curr_exp_s = curr_exp_val / self.time_unit[self.time_unit_id]
            curr_fps = self.spin_fps.value()

            if (curr_exp_s + min_delay_s) > 0:
                calc_max_fps = 1.0 / (curr_exp_s + min_delay_s)
            else:
                calc_max_fps = hw_max_fps
            
            real_max_fps = min(hw_max_fps, calc_max_fps)
            if real_max_fps < 0.001: real_max_fps = 0.001

            if curr_fps > 0:
                calc_max_exp_s = (1.0 / curr_fps) - min_delay_s
            else:
                calc_max_exp_s = hw_max_exp_s
            
            if calc_max_exp_s < 0: calc_max_exp_s = 0
            real_max_exp_s = min(hw_max_exp_s, calc_max_exp_s)
            
            disp_max_exp = real_max_exp_s * self.time_unit[self.time_unit_id]
            disp_min_exp = self.a_camera_handler.desc["min exposure time"] * self.time_unit[self.time_unit_id]

            if self.rb_exposure.isChecked():
                fps_limit = max(real_max_fps, self.spin_fps.minimum())
                self.spin_fps.setMaximum(fps_limit)
                hw_max_exp_val = hw_max_exp_s * self.time_unit[self.time_unit_id]
                self.spin_exposure.setMaximum(hw_max_exp_val)

            else:
                exp_limit = max(disp_max_exp, self.spin_exposure.minimum())
                self.spin_exposure.setMaximum(exp_limit)
                self.spin_fps.setMaximum(hw_max_fps)

            self.description_exposure.setText(f"{disp_min_exp:.3f} ~ {disp_max_exp:.3f} ({self.time_unit_id})")
            self.description_fps.setText(f"~  {real_max_fps:.3f} (fps)")

        except Exception as e:
            print(f"Update limit ranges error: {e}")

    def on_params_updated(self):
        try:
            true_exp_val = self.a_camera_handler.desc["exposure time"] * self.time_unit[self.time_unit_id]
            true_delay_val = self.a_camera_handler.desc["delay time"] * self.time_unit[self.time_unit_id]
            true_fps_val = self.a_camera_handler.desc["fps"]
            
            self.lbl_delay_val.setText(f"{true_delay_val:.3f} {self.time_unit_id}")

            if not self.spin_exposure.hasFocus() or not self.spin_exposure.isEnabled():
                self.spin_exposure.blockSignals(True)
                self.spin_exposure.setValue(true_exp_val)
                self.spin_exposure.blockSignals(False)

            if not self.spin_fps.hasFocus() or not self.spin_fps.isEnabled():
                self.spin_fps.blockSignals(True)
                self.spin_fps.setValue(true_fps_val)
                self.spin_fps.blockSignals(False)

            self.update_limit_ranges()

        except Exception as e:
            print(f"UIer Error in function \"on_params_updated\": {e}")
        
    def on_record_toggled(self, checked):
        if checked:
            current_mode = self.combo_rec_mode.currentText().strip() # 空白除去を追加
            self.combo_rec_mode.setEnabled(False)
            if self.combo_rec_mode.currentText() == "program":
                self.settings_group.setEnabled(False)
                self.trigger_group.setEnabled(False)
            
            self.countdown_val = 3
            font = self.lbl_countdown.font()
            font.setPointSize(16)
            self.lbl_countdown.setFont(font)
            
            self.btn_record.setText("Cancel")
            self.lbl_countdown.setText(str(self.countdown_val))
            
            self.rec_timer.start()
        else:
            if not self.rec_timer.isActive():
                self.a_saver.end_current_recording()

            self.rec_timer.stop()
            self.lbl_countdown.clear()
            self.btn_record.setText("Start")
            self.btn_record.setStyleSheet("")

            # プルダウンを有効化した後、現在のモードに合わせて入力欄の状態を更新
            self.combo_rec_mode.setEnabled(True)
            self.on_rec_mode_changed(self.combo_rec_mode.currentText()) 

            self.a_camera_handler.set_camera_mode("shot")
            self.a_camera_handler.stop_recording()

            # プログラム実行中の場合、Conductorを停止させる
            if self.a_conductor and self.a_conductor.is_running:
                self.a_conductor.is_running = False  # Conductor側のwaitループを抜けさせる。スレッドが終了するのを待つ必要があれば wait() を呼ぶが、GUIをブロックしないよう、ここではフラグを折るだけにする

    def on_countdown_tick(self):
        self.countdown_val -= 1
        
        if self.countdown_val > 0:
            self.lbl_countdown.setText(str(self.countdown_val))
        else:
            self.rec_timer.stop()
            font = self.lbl_countdown.font()
            font.setPointSize(14)
            self.lbl_countdown.setFont(font)
            
            # 空白を除去してモードを取得
            current_mode = self.combo_rec_mode.currentText().strip()

            # --- "program" モードの場合 ---
            if current_mode == "program":
                if self.a_conductor:
                    self.lbl_countdown.setText("RUN") # 表示をRUNに変更
                    self.btn_record.setText("Stop")
                    self.btn_record.setStyleSheet("background-color: #ffcccc; color: red; font-weight: bold;")

                    # スレッドを作成してConductorを実行
                    self.program_thread = ExperimentWorker(self.a_conductor)
                    self.program_thread.finished.connect(self.on_program_finished)
                    self.program_thread.start()
                else:
                    # Conductorが渡されていない場合のエラー表示
                     self.lbl_countdown.setText("No Conductor")
                     self.btn_record.setChecked(False) # ボタンを戻してキャンセル扱いにする

            # --- "manual" モードなどの場合（既存の処理） ---
            else:
                self.lbl_countdown.setText("REC")
                self.btn_record.setText("Stop")
                self.btn_record.setStyleSheet("background-color: #ffcccc; color: red; font-weight: bold;")
                
                try:
                    self.a_saver.start_new_recording(current_mode)
                    self.a_camera_handler.set_camera_mode("queue")
                    self.a_camera_handler.start_recording()
                except Exception as e:
                    self.lbl_countdown.setText("Error")
                    print(f"UIer Error in function \"on_countdown_tick\": {e}")
    
    def on_program_finished(self):
        """
        Conductorの実行が終わったときに呼ばれる関数
        """

        # Startボタンの状態を解除（＝Stop扱いにする）ことで、on_record_toggled(False) が呼ばれ
        # 録画停止やGUIのリセットが行われる
        if self.btn_record.isChecked():
            self.btn_record.setChecked(False)

    def on_rec_mode_changed(self, text):
        """
        録画モードが変更されたときに呼ばれる処理のメソッド
        "program" なら設定入力を無効化、"manual" なら有効化する
        """

        mode = text.strip()
        if mode == "program":
            self.settings_group.setEnabled(False)
            self.trigger_group.setEnabled(False)
        else:
            self.settings_group.setEnabled(True)
            self.trigger_group.setEnabled(True)