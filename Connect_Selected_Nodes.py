# -*- coding: utf-8 -*-
comp = fusion.GetCurrentComp()
if not comp:
    exit()

selected = comp.GetToolList(True)
tools = list(selected.values())

# ── 1. 檢查選取數量：少於 2 個直接彈出大字體提示窗 ──
if len(tools) < 2:
    try:
        ui = fu.UIManager
        disp = bmd.UIDispatcher(ui)
        dlg = disp.AddWindow(
            {
                "WindowTitle": "提示",
                "ID": "AlertWin",
                "Geometry": [700, 450, 400, 140],
            },
            [
                ui.VGroup(
                    [
                        ui.VGap(10),
                        ui.Label(
                            {
                                "ID": "AlertLabel",
                                "Text": (
                                    "<div align='center' style='font-size: 16px;"
                                    " font-weight: bold; color: #FFFFFF;'>"
                                    "請至少框選 2 個節點！<br><span"
                                    " style='font-size: 13px; font-weight:"
                                    " normal; color: #AAAAAA;'>以執行智慧連線或斷開</span></div>"
                                ),
                            }
                        ),
                        ui.VGap(15),
                        ui.HGroup(
                            [
                                ui.HGap(),
                                ui.Button(
                                    {
                                        "ID": "OkBtn",
                                        "Text": "確定",
                                        "Weight": 0,
                                        "MinimumSize": [90, 30],
                                    }
                                ),
                                ui.HGap(),
                            ]
                        ),
                        ui.VGap(10),
                    ]
                )
            ],
        )

        def on_close(ev):
            disp.ExitLoop()

        dlg.On.AlertWin.Close = on_close
        dlg.On.OkBtn.Clicked = on_close

        dlg.Show()
        disp.RunLoop()
        dlg.Hide()
    except Exception:
        print("[提示] 請至少框選 2 個節點！")
    exit()

flow = comp.CurrentFrame.FlowView


def get_node_pos(t):
    try:
        pos = flow.GetPosTable(t)
        vals = list(pos.values())
        return (vals[0], vals[1])
    except Exception:
        return (0, 0)


def get_main_output(t):
    out = t.FindMainOutput(1)
    if not out:
        outs = t.GetOutputList()
        if outs:
            out = list(outs.values())[0]
    return out


tool_names = [t.Name for t in tools]
merges_to_kill = []
killed_names = []


def add_merge_to_kill(m_tool):
    if m_tool and m_tool.Name not in killed_names:
        killed_names.append(m_tool.Name)
        merges_to_kill.append(m_tool)


disconnected = False

# ── 2. 核心邏輯：鎖定畫布進行分析與操作 ──
comp.Lock()
try:
    # A. 深度追蹤下游 Merge 節點
    queue = list(tools)
    visited_names = set(tool_names)

    while queue:
        current_node = queue.pop(0)
        curr_out = get_main_output(current_node)
        if not curr_out:
            continue

        connected_inputs = curr_out.GetConnectedInputs() or {}
        for inp in connected_inputs.values():
            down_tool = inp.GetTool()
            if down_tool:
                reg_id = str(down_tool.GetAttrs("TOOLS_RegID"))
                if "Merge" in reg_id:
                    add_merge_to_kill(down_tool)
                    if down_tool.Name not in visited_names:
                        visited_names.add(down_tool.Name)
                        queue.append(down_tool)

    # B. 若選取範圍直接包含 Merge
    for t in tools:
        if "Merge" in str(t.GetAttrs("TOOLS_RegID")):
            add_merge_to_kill(t)

    # C. 檢查直連節點
    for t_dst in tools:
        if "Merge" in str(t_dst.GetAttrs("TOOLS_RegID")):
            continue
        inputs = t_dst.GetInputList() or {}
        for inp in inputs.values():
            out = inp.GetConnectedOutput()
            if out:
                src_tool = out.GetTool()
                if src_tool and src_tool.Name in tool_names:
                    inp.ConnectTo()
                    disconnected = True
                    print(">< 斷開連接: {} --X--> {}".format(src_tool.Name, t_dst.Name))

    # D. 如果有需要刪除的 Merge，先將連線拔除並刪除
    if merges_to_kill:
        for m in merges_to_kill:
            m_name = m.Name
            try:
                m.Delete()
                print("[!] 已徹底清除 Merge [{}]".format(m_name))
            except Exception:
                pass
        disconnected = True

    # E. 若沒有任何斷開動作，代表彼此尚未連線 -> 執行智慧連線與排版！
    # E. 若沒有任何斷開動作，代表彼此尚未連線 -> 執行智慧連線與排版！
    if not disconnected:
        # 計算節點在 X 與 Y 方向的跨度，判斷使用者是「水平排列」還是「垂直排列」
        all_x = [get_node_pos(t)[0] for t in tools]
        all_y = [get_node_pos(t)[1] for t in tools]
        delta_x = max(all_x) - min(all_x)
        delta_y = max(all_y) - min(all_y)

        is_vertical = delta_y > delta_x

        if is_vertical:
            # 垂直排列：由上至下排序 (Y 由小到大)
            tools.sort(key=lambda t: get_node_pos(t)[1])
        else:
            # 水平排列：由左至右排序 (X 由小到大)
            tools.sort(key=lambda t: get_node_pos(t)[0])

        # 情況 1：直連效果節點 (例如 Loader -> Blur)
        connected_direct = False
        if len(tools) == 2:
            reg_id = str(tools[1].GetAttrs("TOOLS_RegID"))
            generators = [
                "TextPlus",
                "FastNoise",
                "Background",
                "Loader",
                "Plasma",
                "Merge",
            ]
            if not any(g in reg_id for g in generators):
                main_in = tools[1].FindMainInput(1)
                src_out = get_main_output(tools[0])
                if main_in and src_out:
                    main_in.ConnectTo(src_out)
                    connected_direct = True
                    print(">< 直連成功: {} -> {}".format(tools[0].Name, tools[1].Name))

        # 情況 2：建立 Merge 依序合併、智慧排版並將 Alpha Gain 設為 0
        if not connected_direct:
            all_x = [get_node_pos(t)[0] for t in tools]
            all_y = [get_node_pos(t)[1] for t in tools]
            delta_x = max(all_x) - min(all_x)
            delta_y = max(all_y) - min(all_y)

            # 判斷是否為「垂直排列」或「重疊」
            is_vertical_or_stacked = (delta_x < 0.5) or (delta_y > delta_x)

            if is_vertical_or_stacked:
                tools.sort(key=lambda t: get_node_pos(t)[1])
            else:
                tools.sort(key=lambda t: get_node_pos(t)[0])

            base_bg_tool = tools[0]
            fg_candidates = tools[1:]
            current_main_out = get_main_output(base_bg_tool)

            bg_x, bg_y = get_node_pos(base_bg_tool)
            x_spacing = 2.0  # 橫向展開間距
            y_spacing = 1.5  # 縱向展開間距

            # 垂直/重疊時橫向整齊展開成第一排；否則維持在交集高度
            if is_vertical_or_stacked:
                for i, t in enumerate(tools):
                    flow.SetPos(t, bg_x + (i * x_spacing), bg_y)
                merge_y = bg_y + y_spacing
            else:
                merge_y = bg_y

            created_merges = []
            merge_count = 0

            # 依序產生 Merge 並設定參數
            for i, fg_tool in enumerate(fg_candidates):
                fg_out = get_main_output(fg_tool)
                if not fg_out:
                    continue

                merge_tool = comp.AddTool("Merge")

                # 1. 設置座標：X 對齊前景節點，Y 對齊主幹高度
                fg_x, fg_y = get_node_pos(fg_tool)
                flow.SetPos(merge_tool, fg_x, merge_y)

                # 2. 自動將 Alpha Gain 設為 0
                inputs = merge_tool.GetInputList() or {}
                gain_input = None
                for inp in inputs.values():
                    if inp.GetAttrs("INPS_ID") == "Gain":
                        gain_input = inp
                        break

                if gain_input:
                    gain_input[comp.CurrentTime] = 0.0
                else:
                    try:
                        merge_tool.Gain[comp.CurrentTime] = 0.0
                    except Exception:
                        pass

                # 3. 連接節點
                merge_tool.Background.ConnectTo(current_main_out)
                merge_tool.Foreground.ConnectTo(fg_out)

                current_main_out = merge_tool.FindMainOutput(1)
                created_merges.append(merge_tool)
                merge_count += 1

            print(">> 成功連線: 已建立 {} 個 Merge (Alpha Gain 已設為 0)".format(merge_count))

finally:
    comp.Unlock()