import cv2
import os
import glob

def create_video_from_images(image_dir, output_file, fps=30):
    """
    指定したディレクトリ内のjpg画像を連番順に結合してmp4動画を作成する関数
    Args:
        image_dir (str): 画像が入っているディレクトリのパス
        output_file (str): 出力する動画のファイル名 (例: 'output.mp4')
        fps (int): 動画のフレームレート (1秒間の画像枚数)
    """
    
    # 画像ファイルのリストを取得 (jpgまたはjpeg)
    # globを使ってパスを取得し、ソートする
    image_files = sorted(glob.glob(os.path.join(image_dir, "*.jpg")))
    
    # 画像が見つからなかった場合の処理
    if not image_files:
        print(f"エラー: ディレクトリ '{image_dir}' に.jpgファイルが見つかりませんでした。")
        return

    print(f"{len(image_files)} 枚の画像を検出しました。動画変換を開始します...")

    # 最初の画像を読み込んで、動画の解像度（幅・高さ）を決定する
    first_image = cv2.imread(image_files[0])
    height, width, layers = first_image.shape
    size = (width, height)

    # 動画書き出し用のオブジェクトを作成
    # mp4v は mp4形式で保存するためのコーデックです
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_file, fourcc, fps, size)

    # 画像を1枚ずつ読み込んで動画に追加
    for i, filename in enumerate(image_files):
        img = cv2.imread(filename)
        
        # 読み込みエラーのチェック
        if img is None:
            print(f"警告: {filename} を読み込めませんでした。スキップします。")
            continue
            
        # サイズチェック（動画作成には全ての画像が同じサイズである必要があります）
        h, w, _ = img.shape
        if (w, h) != size:
            print(f"警告: {filename} のサイズが異なります。リサイズして追加します。")
            img = cv2.resize(img, size)

        out.write(img)
        
        # 進捗を表示 (10枚ごとに表示)
        if (i + 1) % 10 == 0:
            print(f"処理中... {i + 1}/{len(image_files)}")

    # 後処理
    out.release()
    print(f"完了しました。 '{output_file}' として保存されました。")

if __name__ == "__main__":
    # === 設定 ===
    # 画像が入っているフォルダのパスを指定してください
    target_dir_name = "20251229" 
    target_path = "./" + target_dir_name
    
    # 出力するファイル名
    result_file = f"{target_dir_name}.mp4"
    
    # フレームレート（1秒間に何枚めくるか）
    frame_rate = 40
    # ============

    create_video_from_images(target_path, result_file, frame_rate)
