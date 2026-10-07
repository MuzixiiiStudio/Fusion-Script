## Fusion 輔助自動化腳本工具包 安裝與使用說明 (261007 更新版)

【腳本工具清單】
1. Connect_Selected_Nodes.py   : 多節點智慧依序合併連線 (快捷鍵: Alt + C)
   - 支援直排/重疊自動橫向攤開，以及橫排節點垂直落線與背景主幹的正交交集佈局
   - 自動將新建立的 Merge 節點 Alpha Gain 設為 0
2. Refresh_Loader_Duration.py  : 一鍵自動更新 Loader 序列圖長度 (快捷鍵: Alt + V)
   - 自動修正 Trim (0 起算至最後幀)，強制將 Hold First/Last Frame 歸零，並同步校正 Global In/Out
3. Set_Merge_AlphaGain_Zero.py : 多 Merge 節點批次將 Alpha Gain 設為 0 (無快捷鍵)

【事前環境確認】
若你的 Fusion 為舊版本（如 Fusion 16 / 17 / 早期 18），系統僅綁定 Python 3.6。

---

【安裝步驟】

1. 集中管理與放置 Python 腳本檔案 (NAS 共用目錄)
   本工具包腳本放置於伺服器共用路徑：
   `Nas:\yourpath\Comp`

   包含以下腳本：
   - `Connect_Selected_Nodes.py`
   - `Refresh_Loader_Duration.py`
   - `Set_Merge_AlphaGain_Zero.py`

   *【Fusion 路徑設定 (Path Map)】*：
   若要直接使用共用目錄的最新腳本：
   1. 開啟 Fusion，點選頂部功能表 `File` -> `Preferences...` (或按 `Ctrl + ,`)。
   2. 點選左側選單的 `Path Map`，在中央清單中找到 `Scripts:`。
   3. 在下方 `To:` 輸入框末端加上分號 `;`，填入共用目錄最外層路徑：
      `UserPaths:Scripts;N:\Temp\YITING\FUSION SCRIPT`
   4. 點選右下角 `Save` 儲存設定。
   *(注意：請將本機 `C:\ProgramData\Blackmagic Design\Fusion\Scripts\Comp\` 內的同名舊腳本刪除，避免版本衝突)*

2. 覆蓋快捷鍵與設定檔 (User.fu & hotkeys)
   * 請先【完全關閉 Fusion】軟體。
   * 按下鍵盤 Win + R，貼入以下路徑按 Enter 開啟資料夾：
     `%APPDATA%\Blackmagic Design\Fusion\Profiles\Default\`
   * 將隨附的以下兩個檔案直接複製並貼上取代原本的檔案：
     - `User.fu`
     - `hotkeys.fu`
   * 重新啟動 Fusion 即可直接使用快捷鍵。