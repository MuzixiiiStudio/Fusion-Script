=====================================================
Fusion 輔助自動化腳本工具包 安裝與使用說明 260929
=====================================================

【腳本工具清單】
1. Connect_Selected_Nodes.py   : 多節點智慧依序合併連線 (快捷鍵: Alt + C)
2. Refresh_Loader_Duration.py  : 一鍵自動更新 Loader 序列圖長度 (快捷鍵: Alt + V)


【事前環境確認】
若你的 Fusion 為舊版本（如 Fusion 16 / 17 / 早期 18），系統僅綁定 Python 3.6。



【安裝步驟】

1. 放置 Python 腳本檔案
   請將以下兩個腳本：
   - Connect_Selected_Nodes.py
   - Refresh_Loader_Duration.py

   複製貼到以下公用路徑：
   C:\ProgramData\Blackmagic Design\Fusion\Scripts\Comp\
   (若無 Comp 資料夾請手動建立)


2. 覆蓋快捷鍵與設定檔 (User.fu & hotkeys)
   * 請先【完全關閉 Fusion】軟體。
   * 按下鍵盤 Win + R，貼入以下路徑按 Enter 開啟資料夾：
     %APPDATA%\Blackmagic Design\Fusion\Profiles\Default\
   * 將隨附的以下兩個檔案直接複製並貼上取代原本的檔案：
     - User.fu
     - hotkeys.fu
