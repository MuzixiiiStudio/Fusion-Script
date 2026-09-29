# -*- coding: utf-8 -*-
import os
import re

comp = fusion.GetCurrentComp()
if not comp:
    exit()

# ----------------------------------------------------------------------
# 1. 內建原生操作框
# ----------------------------------------------------------------------
selected_tools = comp.GetToolList(True)
has_selection = (
    len(
        [
            t
            for t in selected_tools.values()
            if t.GetAttrs("TOOLS_RegID") == "Loader"
        ]
    )
    > 0
)

dialog_spec = {
    1: {
        1: "TargetScope",
        "Name": "更新範圍",
        2: "Dropdown",
        "Options": [
            "僅更新目前選取的 Loader 節點",
            "更新全部 (整個 Comp 內所有 Loader)",
        ],
        "Default": 0 if has_selection else 1,
    },
    2: {
        1: "FindStr",
        "Name": "尋找路徑文字",
        2: "Text",
        "Default": "",
    },
    3: {
        1: "ReplaceStr",
        "Name": "替換為新文字",
        2: "Text",
        "Default": "",
    },
}

ret = comp.AskUser("更新圖像序列長度與路徑", dialog_spec)
if not ret:
    exit()

choice = ret.get("TargetScope", ret.get(1, 0))
process_all = choice == 1 or choice == 1.0

find_str = ret.get("FindStr", ret.get(2, "")).strip()
replace_str = ret.get("ReplaceStr", ret.get(3, "")).strip()
do_replace = len(find_str) > 0


# ----------------------------------------------------------------------
# 2. 序列影格辨識函式
# ----------------------------------------------------------------------
def get_sequence_bounds(file_path):
    if not file_path or not os.path.exists(os.path.dirname(file_path)):
        return None, None

    dir_name = os.path.dirname(file_path)
    base_name = os.path.basename(file_path)

    # 移除 padding 標籤
    cleaned_name = re.sub(r"\[\d+-\d+\]", "0000", base_name)
    cleaned_name = re.sub(r"%\d*d", "0000", cleaned_name)

    match = re.search(r"^(.*?)([-_.]?)(\d+)(\.[a-zA-Z0-9]+)$", cleaned_name)
    if not match:
        return None, None

    prefix, delimiter, _, ext = match.groups()
    pattern = re.compile(
        r"^{}{}(\d+){}$".format(re.escape(prefix), re.escape(delimiter), re.escape(ext)),
        re.IGNORECASE,
    )

    frames = []
    try:
        for fname in os.listdir(dir_name):
            m = pattern.match(fname)
            if m:
                frames.append(int(m.group(1)))
    except OSError:
        return None, None

    if not frames:
        return None, None

    return min(frames), max(frames)


# ----------------------------------------------------------------------
# 3. 取得目標節點並執行更新
# ----------------------------------------------------------------------
if process_all:
    tools = comp.GetToolList(False)
else:
    tools = comp.GetToolList(True)
    if not tools:
        tools = comp.GetToolList(False)

loaders = [
    t for t in tools.values() if t.GetAttrs("TOOLS_RegID") == "Loader"
]

if not loaders:
    comp.AskUser(
        "提示",
        {
            1: {
                1: "Msg",
                "Name": "訊息",
                2: "Text",
                "Readonly": True,
                "Default": "未找到任何 Loader 節點。",
            }
        },
    )
    exit()

comp.Lock()
count = 0
result_logs = []

try:
    for loader in loaders:
        raw_clip = loader.Clip[comp.CurrentTime]
        if not raw_clip:
            continue

        target_clip = raw_clip
        path_swapped = False

        if do_replace and (find_str in raw_clip):
            candidate_clip = raw_clip.replace(find_str, replace_str)
            candidate_real_path = comp.MapPath(candidate_clip)

            if os.path.exists(os.path.dirname(candidate_real_path)):
                target_clip = candidate_clip
                path_swapped = True
            else:
                result_logs.append(
                    f"⚠ {loader.Name}：找不到目標目錄，未替換路徑"
                )

        real_path = comp.MapPath(target_clip)
        first_frame, last_frame = get_sequence_bounds(real_path)

        if first_frame is None or last_frame is None:
            continue

        seq_len = last_frame - first_frame + 1

        if path_swapped:
            loader.Clip[comp.CurrentTime] = target_clip

        gin = loader.GetAttrs("TOOLNT_ClipGlobalIn")
        if gin is None:
            gin = loader.GlobalIn[comp.CurrentTime]

        loader.ClipTimeStart = first_frame
        loader.ClipTimeEnd = last_frame
        loader.HoldFirstFrame = 0
        loader.HoldLastFrame = 0

        loader.GlobalIn[comp.CurrentTime] = gin
        loader.GlobalOut[comp.CurrentTime] = gin + seq_len - 1

        # --- 取得原本素材的檔案名稱 ---
        file_base_name = os.path.basename(real_path)
        # 去掉結尾的 .0001.exr 或 _0001.exr，只保留純檔名主體
        match_clean = re.search(
            r"^(.*?)([-_.]?)\d+(\.[a-zA-Z0-9]+)$", file_base_name
        )
        if match_clean:
            display_name = f"{match_clean.group(1)}{match_clean.group(3)}"
        else:
            display_name = file_base_name

        swap_note = " (已換路徑)" if path_swapped else ""

        # 顯示格式：• 原始檔名 (節點名稱) : 影格範圍
        log_item = f"• {display_name} ({loader.Name}){swap_note}：{first_frame} ~ {last_frame} (共 {seq_len} 格)"
        result_logs.append(log_item)
        print(f"✔ [{display_name} | {loader.Name}] 更新成功 -> {first_frame} ~ {last_frame}")
        count += 1
finally:
    comp.Unlock()

# ----------------------------------------------------------------------
# 4. 結果通知框 (顯示原本檔名)
# ----------------------------------------------------------------------
if count > 0:
    summary_msg = f"共成功更新 {count} 個節點：\n\n" + "\n".join(result_logs)
else:
    summary_msg = "找到節點，但未符合替換條件或序列長度無變化。"

result_spec = {
    1: {
        1: "Summary",
        "Name": "更新結果",
        2: "Text",
        "Lines": min(max(count + 2, 4), 14),
        "Readonly": True,
        "Default": summary_msg,
    }
}

comp.AskUser("序列更新完成", result_spec)