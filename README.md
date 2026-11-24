## Fusion 輔助自動化腳本工具包 安裝與使用說明 (261124 更新版)

【腳本工具清單】
1. Connect_Selected_Nodes.py   : 多節點智慧依序合併連線 (快捷鍵: Alt + C)
   - 支援直排/重疊自動橫向攤開，以及橫排節點垂直落線與背景主幹的正交交集佈局
   - 自動將新建立的 Merge 節點 Alpha Gain 設為 0
   - 選取的節點已經連在一起時，再按一次會拆開：只拆掉選取節點之間的 Merge，
     有接到其他（未選取）節點的 Merge 會保留，原本接在下游的節點會自動接回主幹
   - 整個動作可以用 Ctrl + Z 一次復原
2. Refresh_Loader_Duration.py  : 一鍵自動更新 Loader 序列圖長度 (快捷鍵: Alt + V)
   - 自動修正 Trim (0 起算至最後幀)，強制將 Hold First/Last Frame 歸零，並同步校正 Global In/Out
   - 可替換路徑文字（不分大小寫）：先找整條路徑替換後的檔案；找不到時改用新資料夾內的原檔名；
     「替換為新文字」也可以直接貼目標資料夾的完整路徑，會在那裡（含兩層子資料夾）找同名序列；
     再找不到時，若新資料夾裡只有一組同副檔名的序列就用那一組。換不成功時，結果視窗會列出原因
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

2. 設定快捷鍵 (Alt + C / Alt + V)
   *【建議】點兩下自動設定：*
   * 請先【完全關閉 Fusion】軟體（電腦需連上 N 槽）。
   * 點兩下工具包裡的 `修復Fusion快捷鍵.bat`（NAS：`N:\Temp\YITING\FUSION SCRIPT\`）。
   * 工具會自動找到你自己的 Fusion 設定資料夾（不同 Windows 使用者名稱也適用），把快捷鍵指向 N 槽腳本，
     並保留你自己設定的其他快捷鍵；修改前會先備份成 `*.bak-日期時間`。
   * 看到 `[完成]` 或 `[OK]` 後，重新啟動 Fusion 即可使用快捷鍵。

   *手動方式（會覆蓋你在 Fusion 裡自訂過的快捷鍵）：*
   * 請先【完全關閉 Fusion】軟體。
   * 按下鍵盤 Win + R，貼入以下路徑按 Enter 開啟資料夾：
     `%APPDATA%\Blackmagic Design\Fusion\Profiles\Default\`
   * 將隨附的以下兩個檔案直接複製並貼上取代原本的檔案：
     - `User.fu`
     - `hotkeys.fu`
   * 重新啟動 Fusion 即可直接使用快捷鍵。

---

【常見問題】

* Alt + C 可以用，但 Alt + V 沒反應？
  261007 版的 `User.fu` 把 Alt + V 指向本機 `C:\ProgramData\...\Scripts\Comp\`，
  而安裝步驟 1 會刪除那裡的舊腳本，所以 Alt + V 會找不到檔案。
  關閉 Fusion 後點兩下 `修復Fusion快捷鍵.bat`，再重新開啟 Fusion 即可。

* 按 Alt + C 想連線，卻把旁邊原本的 Merge 拆掉了？
  261019 以前的版本只要選到的節點有接進任何 Merge，就會把它下游的 Merge 全部刪掉，而且不會建立新連線。
  261029 版已修正，只會拆掉選取節點之間的 Merge。腳本直接從 N 槽讀取，更新後不用重新安裝。

* 按 Alt + V 替換路徑失敗，只顯示「未符合替換條件」？
  舊版會把路徑裡每個符合的文字都換掉（包含檔名），換完的檔案不存在就直接放棄。
  261105 版會改找新資料夾裡的實際檔案，真的換不了時也會列出原因。