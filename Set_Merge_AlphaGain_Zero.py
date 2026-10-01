# -*- coding: utf-8 -*-
comp = fusion.GetCurrentComp()
if comp:
    comp.Lock()
    comp.StartUndo("Set Merge Alpha Gain to 0")
    try:
        selected_tools = comp.GetToolList(True)
        count = 0
        for tool in selected_tools.values():
            if "Merge" in str(tool.GetAttrs("TOOLS_RegID")):
                # 正確的內部 Input ID 為 Gain
                inputs = tool.GetInputList() or {}
                gain_input = None
                for inp in inputs.values():
                    if inp.GetAttrs("INPS_ID") == "Gain":
                        gain_input = inp
                        break

                if gain_input:
                    gain_input[comp.CurrentTime] = 0.0
                    count += 1
                else:
                    # 備用屬性賦值
                    try:
                        tool.Gain[comp.CurrentTime] = 0.0
                        count += 1
                    except Exception:
                        pass

        print(">> 已將 {} 個 Merge 節點的 Alpha Gain 設為 0".format(count))
    finally:
        comp.EndUndo(True)
        comp.Unlock()