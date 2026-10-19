param(
    # Only overridden for testing; normal runs use the current user's %APPDATA%
    [string]$AppDataRoot = $env:APPDATA
)

$ErrorActionPreference = 'Stop'

# Shared script folder on the NAS (N: = \\muzi-serveA\muzi_save)
$ScriptDir = 'N:\Temp\YITING\FUSION SCRIPT\Comp'

$Hotkeys = [ordered]@{
    'ALT_C' = 'Connect_Selected_Nodes'
    'ALT_V' = 'Refresh_Loader_Duration'
}
$KnownScripts = @('Connect_Selected_Nodes', 'Refresh_Loader_Duration', 'Set_Merge_AlphaGain_Zero')
$AllowedWords = @('Hotkeys', 'Target', 'ALT_C', 'ALT_V', 'CONTROL_H')
$AllowedTargets = @('FlowView', 'FuFrame')

$Utf8NoBom = New-Object System.Text.UTF8Encoding $false
$Stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$NL = "`r`n"
$script:Problems = 0
$script:AnyChanged = $false

function Say([string]$msg, [string]$color = 'Gray') {
    Write-Host $msg -ForegroundColor $color
}

# N: folder written with the given separator; .fu strings need four backslashes
function Get-FuDir([string]$sep) {
    'N:' + $sep + 'Temp' + $sep + 'YITING' + $sep + 'FUSION SCRIPT' + $sep + 'Comp' + $sep
}

function Get-RunScript([string]$name) {
    "RunScript{ Name = '$name', filename = '" + (Get-FuDir ('\' * 4)) + "$name.py' }"
}

function Get-StandardHotkeys([bool]$withCtrlH) {
    $t = '{' + $NL + "`tHotkeys {" + $NL + "`t`tTarget = `"FlowView`"," + $NL
    foreach ($k in $Hotkeys.Keys) {
        $t += "`t`t$k = `"" + (Get-RunScript $Hotkeys[$k]) + "`"," + $NL
    }
    $t += "`t}," + $NL
    if ($withCtrlH) {
        $t += "`tHotkeys {" + $NL + "`t`tTarget = `"FuFrame`"," + $NL
        $t += "`t`tCONTROL_H = `"App_CustomizeHotkeys`"," + $NL + "`t}," + $NL
    }
    $t += '}' + $NL
    $t
}

# Point every known script at the N: folder, keeping the file's own backslash escaping
$namesPattern = ($KnownScripts | ForEach-Object { [regex]::Escape($_) }) -join '|'
$PathRegex = [regex]('(filename\s*=\s*\\?[''"])(.*?)((?:' + $namesPattern + ')\.py)')

function Repair-Paths([string]$text) {
    $PathRegex.Replace($text, [System.Text.RegularExpressions.MatchEvaluator] {
            param($m)
            $sep = [regex]::Match($m.Groups[2].Value, '\\+|/')
            $s = '\' * 4
            if ($sep.Success) { $s = $sep.Value }
            $m.Groups[1].Value + (Get-FuDir $s) + $m.Groups[3].Value
        })
}

function Get-KeyValues([string]$text, [string]$key) {
    $re = '(?<![A-Za-z0-9_])' + $key + '\s*=\s*(?:"((?:[^"\\]|\\.)*)"|''((?:[^''\\]|\\.)*)'')'
    foreach ($m in [regex]::Matches($text, $re)) {
        $m.Groups[1].Value + $m.Groups[2].Value
    }
}

function Remove-Strings([string]$text) {
    [regex]::Replace($text, '"(?:[^"\\]|\\.)*"|''(?:[^''\\]|\\.)*''', '""')
}

# True when hotkeys.fu holds nothing but this tool's own hotkeys, so it is safe to rewrite cleanly
function Test-OnlyOurs([string]$text) {
    foreach ($w in [regex]::Matches((Remove-Strings $text), '[A-Za-z_][A-Za-z0-9_]*')) {
        if ($AllowedWords -notcontains $w.Value) { return $false }
    }
    foreach ($m in [regex]::Matches($text, 'Target\s*=\s*"([^"]*)"')) {
        if ($AllowedTargets -notcontains $m.Groups[1].Value) { return $false }
    }
    foreach ($k in $Hotkeys.Keys) {
        foreach ($v in (Get-KeyValues $text $k)) {
            if ($v -notmatch [regex]::Escape($Hotkeys[$k])) { return $false }
        }
    }
    foreach ($v in (Get-KeyValues $text 'CONTROL_H')) {
        if ($v -ne 'App_CustomizeHotkeys') { return $false }
    }
    return $true
}

function Add-Keys([string]$text, [string[]]$keys) {
    $lines = ($keys | ForEach-Object { "`t`t$_ = `"" + (Get-RunScript $Hotkeys[$_]) + "`"," }) -join $NL
    $m = [regex]::Match($text, 'Target\s*=\s*"FlowView"(?:[ \t]*,)?')
    if ($m.Success) {
        $insert = $NL + $lines
        if (-not $m.Value.EndsWith(',')) { $insert = ',' + $insert }
        return $text.Insert($m.Index + $m.Length, $insert)
    }
    $first = $text.IndexOf('{')
    if ($first -lt 0) { return $null }
    $block = $NL + "`tHotkeys {" + $NL + "`t`tTarget = `"FlowView`"," + $NL + $lines + $NL + "`t},"
    return $text.Insert($first + 1, $block)
}

function Test-Braces([string]$text) {
    ([regex]::Matches($text, '\{')).Count -eq ([regex]::Matches($text, '\}')).Count
}

Say '=== Fusion 快捷鍵修復（Alt+C 連接節點 / Alt+V 更新 Loader 長度）===' 'Cyan'
Say "Windows 使用者：$env:USERNAME"
Say ''

# 1. The scripts on N: must be reachable from this computer
$missing = @()
foreach ($n in $Hotkeys.Values) {
    if (-not (Test-Path -LiteralPath (Join-Path $ScriptDir "$n.py"))) { $missing += "$n.py" }
}
if ($missing.Count -gt 0) {
    Say "[錯誤] 找不到 N 槽上的腳本：$($missing -join ', ')" 'Red'
    Say '        請確認這台電腦有 N 槽（\\muzi-serveA\muzi_save），連上後再執行一次。' 'Red'
    exit 1
}

# 2. Fusion profile folders of this Windows user
$profilesRoot = Join-Path $AppDataRoot 'Blackmagic Design\Fusion\Profiles'
$profiles = @()
if (Test-Path -LiteralPath $profilesRoot) {
    $profiles = @(Get-ChildItem -LiteralPath $profilesRoot -Directory)
}
if ($profiles.Count -eq 0) {
    Say "[錯誤] 找不到 Fusion 設定資料夾：$profilesRoot" 'Red'
    Say '        請先開啟、再關閉 Fusion 一次，然後重新執行這個工具。' 'Red'
    exit 1
}

foreach ($p in $profiles) {
    Say "設定檔：$($p.FullName)" 'Cyan'
    $userFu = Join-Path $p.FullName 'User.fu'
    $hotFu = Join-Path $p.FullName 'hotkeys.fu'

    $orig = @{}
    $cur = @{}
    foreach ($f in @($userFu, $hotFu)) {
        if (Test-Path -LiteralPath $f) {
            $orig[$f] = [System.IO.File]::ReadAllText($f)
            $cur[$f] = Repair-Paths $orig[$f]
        }
    }

    # Which of our hotkeys exist (in either file), and are any of them taken by something else?
    $missingKeys = @()
    foreach ($k in $Hotkeys.Keys) {
        $state = 'missing'
        foreach ($f in @($userFu, $hotFu)) {
            if (-not $cur.ContainsKey($f)) { continue }
            foreach ($v in (Get-KeyValues $cur[$f] $k)) {
                if ($v -match [regex]::Escape($Hotkeys[$k])) {
                    if ($state -eq 'missing') { $state = 'ok' }
                }
                else {
                    $state = 'conflict'
                    Say "  [注意] $k 在 $(Split-Path $f -Leaf) 已被設定成其他功能，這個按鍵不更動。" 'Yellow'
                    $script:Problems++
                }
            }
        }
        if ($state -eq 'missing') { $missingKeys += $k }
    }

    if (-not $cur.ContainsKey($hotFu)) {
        if ($missingKeys.Count -gt 0) { $cur[$hotFu] = Get-StandardHotkeys $false }
    }
    elseif (Test-OnlyOurs $cur[$hotFu]) {
        $withCtrlH = @(Get-KeyValues $cur[$hotFu] 'CONTROL_H').Count -gt 0
        $cur[$hotFu] = Get-StandardHotkeys $withCtrlH
    }
    elseif ($missingKeys.Count -gt 0) {
        $added = Add-Keys $cur[$hotFu] $missingKeys
        if ($null -eq $added) {
            Say '  [注意] hotkeys.fu 的格式無法辨識，沒有加入快捷鍵。' 'Yellow'
            $script:Problems++
        }
        else { $cur[$hotFu] = $added }
    }

    $changed = $false
    foreach ($f in @($userFu, $hotFu)) {
        if (-not $cur.ContainsKey($f)) { continue }
        $name = Split-Path $f -Leaf
        $isNew = -not $orig.ContainsKey($f)
        if (-not $isNew -and $cur[$f] -ceq $orig[$f]) { continue }
        if (-not (Test-Braces $cur[$f])) {
            Say "  [注意] $name 修改後括號不成對，已放棄修改。" 'Yellow'
            $script:Problems++
            continue
        }
        if ($isNew) {
            [System.IO.File]::WriteAllText($f, $cur[$f], $Utf8NoBom)
            Say "  [完成] 建立 $name" 'Green'
        }
        else {
            $bak = "$f.bak-$Stamp"
            Copy-Item -LiteralPath $f -Destination $bak -Force
            [System.IO.File]::WriteAllText($f, $cur[$f], $Utf8NoBom)
            Say "  [完成] 更新 $name（原檔備份為 $(Split-Path $bak -Leaf)）" 'Green'
        }
        $changed = $true
        $script:AnyChanged = $true
    }
    if (-not $changed) { Say '  [OK] 設定已經正確，不需要更動。' 'Green' }

    foreach ($k in $Hotkeys.Keys) {
        $label = $k.Replace('ALT_', 'Alt+')
        Say "  $label -> $($Hotkeys[$k]).py"
    }
    Say ''
}

if ($script:AnyChanged) {
    if (Get-Process -Name 'Fusion' -ErrorAction SilentlyContinue) {
        Say 'Fusion 正在執行中：請先存檔，再關掉 Fusion 重新開啟，快捷鍵才會生效。' 'Yellow'
    }
    else {
        Say '下次開啟 Fusion 就會生效。' 'Green'
    }
}
if ($script:Problems -gt 0) {
    Say "有 $($script:Problems) 個項目需要手動確認，請把這個視窗截圖給負責的人。" 'Yellow'
    exit 2
}
exit 0
