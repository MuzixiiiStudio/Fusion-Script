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
    # 回傳 (第一格, 最後一格, 第一格檔名)，找不到檔案時全部為 None
    if not file_path or not os.path.exists(os.path.dirname(file_path)):
        return None, None, None

    dir_name = os.path.dirname(file_path)
    base_name = os.path.basename(file_path)

    # 移除 padding 標籤
    cleaned_name = re.sub(r"\[\d+-\d+\]", "0000", base_name)
    cleaned_name = re.sub(r"%\d*d", "0000", cleaned_name)

    match = re.search(r"^(.*?)([-_.]?)(\d+)(\.[a-zA-Z0-9]+)$", cleaned_name)
    if not match:
        # 檔名結尾沒有數字：視為單張圖
        if os.path.isfile(file_path):
            return 0, 0, base_name
        return None, None, None

    prefix, delimiter, _, ext = match.groups()
    pattern = re.compile(
        r"^{}{}(\d+){}$".format(re.escape(prefix), re.escape(delimiter), re.escape(ext)),
        re.IGNORECASE,
    )

    frames = {}
    try:
        for fname in os.listdir(dir_name):
            m = pattern.match(fname)
            if m:
                frames[int(m.group(1))] = fname
    except OSError:
        return None, None, None

    if not frames:
        return None, None, None

    first = min(frames)
    return first, max(frames), frames[first]


def split_clip(clip):
    # 拆成資料夾與檔名，資料夾部分保留原本寫法（可能是 Comp: 等 Path Map 路徑）
    idx = max(clip.rfind("\\"), clip.rfind("/"), clip.rfind(":"))
    return clip[: idx + 1], clip[idx + 1 :]


SEQ_RE = re.compile(r"^(.*?)([-_.]?)(\d+)(\.[a-zA-Z0-9]+)$")


def sequence_name(fname):
    # 序列名稱：去掉幀號與副檔名（單張圖就是整個檔名）
    m = SEQ_RE.search(fname)
    return m.group(1) + m.group(2) if m else fname


def list_sequences(dir_path, ext):
    # 資料夾內同副檔名的序列：{序列名稱: 第一格檔名}
    seqs = {}
    for fname in os.listdir(dir_path):
        if not fname.lower().endswith(ext.lower()):
            continue
        m = SEQ_RE.search(fname)
        frame = int(m.group(3)) if m else 0
        key = sequence_name(fname)
        if key not in seqs or frame < seqs[key][0]:
            seqs[key] = (frame, fname)
    return {k: v[1] for k, v in seqs.items()}


def find_same_sequence(root, old_file, max_depth=2):
    # 在 root 與底下 max_depth 層子資料夾找同名序列：[(相對資料夾, 第一格檔名)]
    ext = os.path.splitext(old_file)[1]
    name = sequence_name(old_file).lower()
    found = []
    for dirpath, dirnames, _ in os.walk(root):
        rel = os.path.relpath(dirpath, root)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        if depth >= max_depth:
            dirnames[:] = []
        dirnames.sort()
        for key, first in list_sequences(dirpath, ext).items():
            if key.lower() == name:
                found.append(("" if rel == "." else rel, first))
    return found


def resolve_swap(raw_clip):
    # 回傳 (新路徑, None)，或失敗時回傳 (None, 原因)
    whole = re.sub(re.escape(find_str), lambda m: replace_str, raw_clip, flags=re.IGNORECASE)
    new_dir, new_file = split_clip(whole)
    old_dir, old_file = split_clip(raw_clip)
    ext = os.path.splitext(old_file)[1]
    real_dir = os.path.dirname(comp.MapPath(whole))
    dir_exists = os.path.isdir(real_dir)
    dir_changed = new_dir.lower() != old_dir.lower()

    # 1. 整條路徑（含檔名）替換後的檔案存在
    if dir_exists and get_sequence_bounds(comp.MapPath(whole))[0] is not None:
        return whole, None

    # 2. 資料夾換了，檔名維持原本的名稱
    if dir_exists and dir_changed:
        keep_name = new_dir + old_file
        if get_sequence_bounds(comp.MapPath(keep_name))[0] is not None:
            return keep_name, None

    # 3. 「替換為新文字」是現有資料夾的完整路徑時，到那裡（含兩層子資料夾）找同名序列
    target_root = comp.MapPath(replace_str) if replace_str else ""
    if not (os.path.isabs(target_root) and os.path.isdir(target_root)):
        target_root = None
    if target_root:
        matches = find_same_sequence(target_root, old_file)
        if len(matches) == 1:
            rel, first = matches[0]
            return os.path.join(replace_str, rel, first) if rel else os.path.join(replace_str, first), None
        if len(matches) > 1:
            names = "、".join(os.path.join(r, f) for r, f in matches[:5])
            return None, f"{target_root} 內有 {len(matches)} 組同名序列，無法判斷要用哪一組（{names}）"

    # 4. 新資料夾裡只有一組同副檔名的序列，就用那一組（資料夾沒換時只會找回舊素材，所以跳過）
    candidates = []
    if dir_exists and dir_changed:
        candidates.append((new_dir, real_dir))
    if target_root and os.path.normcase(os.path.normpath(target_root)) != os.path.normcase(os.path.normpath(real_dir)):
        candidates.append((os.path.join(replace_str, ""), target_root))
    for clip_dir, scan_dir in candidates:
        seqs = list_sequences(scan_dir, ext)
        if len(seqs) == 1:
            return clip_dir + list(seqs.values())[0], None

    # 失敗原因
    if candidates:
        scan_dir = candidates[0][1]
        seqs = list_sequences(scan_dir, ext)
        if seqs:
            names = "、".join(sorted(seqs.values())[:5])
            return None, f"{scan_dir} 內有 {len(seqs)} 組序列，無法判斷要用哪一組（{names}）"
        if target_root:
            return None, f"{target_root}（含兩層子資料夾）內找不到 {sequence_name(old_file)}{ext}，也沒有可直接使用的 {ext} 序列"
        return None, f"{scan_dir} 內沒有 {ext} 檔案"
    if dir_exists:
        return None, f"資料夾內找不到 {new_file}"
    return None, f"找不到資料夾 {real_dir}"


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

# 整個動作可用 Ctrl+Z 一次復原
comp.StartUndo("Refresh Loader Duration")
comp.Lock()
count = 0
swapped_count = 0
matched_count = 0
result_logs = []

try:
    for loader in loaders:
        raw_clip = loader.Clip[comp.CurrentTime]
        if not raw_clip:
            continue

        target_clip = raw_clip
        path_swapped = False

        if do_replace:
            if find_str.lower() in raw_clip.lower():
                matched_count += 1
                candidate_clip, fail_reason = resolve_swap(raw_clip)
                if candidate_clip:
                    target_clip = candidate_clip
                    path_swapped = True
                else:
                    result_logs.append(f"⚠ {loader.Name}：{fail_reason}，未替換路徑")
            elif not process_all:
                result_logs.append(f"⚠ {loader.Name}：路徑內沒有「{find_str}」，未替換路徑")

        real_path = comp.MapPath(target_clip)
        first_frame, last_frame, first_name = get_sequence_bounds(real_path)

        if first_frame is None or last_frame is None:
            result_logs.append(f"⚠ {loader.Name}：找不到素材 {os.path.basename(real_path)}")
            continue

        # 新序列的起始格不同時，Clip 要指向實際存在的第一格
        if not os.path.exists(real_path):
            target_clip = split_clip(target_clip)[0] + first_name
            real_path = comp.MapPath(target_clip)

        seq_len = last_frame - first_frame + 1

        if path_swapped:
            loader.Clip[comp.CurrentTime] = target_clip

        gin = loader.GetAttrs("TOOLNT_ClipGlobalIn")
        if gin is None:
            gin = loader.GlobalIn[comp.CurrentTime]
       # 1. 計算總長度
        trim_out = seq_len - 1

        # 2. 強制重置 Loader 素材長度範圍 (透過 Clip 重新載入序列)
        try:
            # 重新賦予 Clip 完整路徑，強制觸發 Fusion 的序列剖析器
            loader.Clip[comp.CurrentTime] = target_clip
        except Exception:
            pass

        # 3. 設定 ClipTimeEnd 與清除 Hold (關鍵：直接指定為非動畫參數或帶時間索引)
        try:
            loader.HoldLastFrame[comp.CurrentTime] = 0
            loader.HoldFirstFrame[comp.CurrentTime] = 0
        except Exception:
            pass

        # 4. 同步更新內部屬性與時間軸範圍
        loader.SetAttrs({
            "TOOLNT_ClipGlobalIn": gin,
            "TOOLNT_ClipGlobalOut": gin + trim_out,
            "TOOLNT_ClipTrimIn": 0,
            "TOOLNT_ClipTrimOut": trim_out,
        })

        try:
            loader.GlobalIn[comp.CurrentTime] = gin
            loader.GlobalOut[comp.CurrentTime] = gin + trim_out
            loader.ClipTimeEnd[comp.CurrentTime] = trim_out
        except Exception:
            pass
        

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
        if path_swapped:
            swapped_count += 1

        # 顯示格式：• 原始檔名 (節點名稱) : 影格範圍
        log_item = f"• {display_name} ({loader.Name}){swap_note}：{first_frame} ~ {last_frame} (共 {seq_len} 格)"
        result_logs.append(log_item)
        print(f"✔ [{display_name} | {loader.Name}] 更新成功 -> {first_frame} ~ {last_frame}")
        count += 1
finally:
    comp.Unlock()
    comp.EndUndo(True)

# ----------------------------------------------------------------------
# 4. 結果通知框 (顯示原本檔名)
# ----------------------------------------------------------------------
if do_replace and process_all and matched_count == 0:
    result_logs.insert(0, f"⚠ 所有 Loader 的路徑內都沒有「{find_str}」，未替換路徑")

if count > 0:
    swap_part = f"（其中 {swapped_count} 個已換路徑）" if do_replace else ""
    summary_msg = f"共更新 {count} 個節點{swap_part}：\n\n" + "\n".join(result_logs)
elif result_logs:
    summary_msg = "沒有節點被更新：\n\n" + "\n".join(result_logs)
else:
    summary_msg = "找到節點，但未符合替換條件或序列長度無變化。"

result_spec = {
    1: {
        1: "Summary",
        "Name": "更新結果",
        2: "Text",
        "Lines": min(max(len(result_logs) + 2, 4), 14),
        "Readonly": True,
        "Default": summary_msg,
    }
}

comp.AskUser("序列更新完成", result_spec)