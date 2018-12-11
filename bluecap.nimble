# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

version       = "0.3"
author        = "Ryan Gonzalez"
description   = "A new awesome nimble package"
license       = "MPL-2.0"
srcDir        = "src"
bin           = @["bluecap"]
binDir        = "build"


requires "nim >= 0.19.0"
requires "uuids"


import options, ospaths, strformat, strutils

when fileExists "build/config.nim":
  include "build/config.nim"

  proc install(perms: int, source, targetdir: string) =
    let command = ["install", "-Dm", $perms, source, targetdir / source.tailDir]
    echo fmt"+ {quoteShellCommand(command)}"
    exec quoteShellCommand(command)

template setIfNone(vr: untyped, default: typed) =
  if vr.isNone:
    vr = some default

proc die(msg: string) {.noreturn.} = raise newException(Exception, msg)

proc allFilesExist(files: varargs[string]): bool =
  for file in files:
    if not fileExists file:
      return false

  return true

task config, "configure the bluecap installation":
  var prefix, bindir, datadir, sysconfdir, sharedstatedir: Option[string]

  for i in 2..paramCount():
    let param = paramStr i
    if param.contains '=':
      let parts = param.split('=', 1)
      let (key, value) = (parts[0], parts[1])

      if not value.isAbsolute:
        die fmt"Only absolute paths can be used, not: {value}"

      case key
      of "prefix": prefix = some value
      of "bindir": bindir = some value
      of "datadir": datadir = some value
      of "sysconfdir": sysconfdir = some value
      of "sharedstatedir": sharedstatedir = some value
      else: die fmt"Invalid key: {key}=..."
    else: die fmt"Invalid argument: {param}"

  prefix.setIfNone "/usr"
  bindir.setIfNone prefix.get/"bin"
  datadir.setIfNone prefix.get/"share"
  sysconfdir.setIfNone "/etc"
  sharedstatedir.setIfNone "/var/lib"

  echo "***** INSTALLATION CONFIG *****"
  echo fmt"version        : {version}"
  echo fmt"prefix         : {prefix.get}"
  echo fmt"bindir         : {bindir.get}"
  echo fmt"datadir        : {datadir.get}"
  echo fmt"sysconfdir     : {sysconfdir.get}"
  echo fmt"sharedstatedir : {sharedstatedir.get}"

  writeFile "build/config.nim", fmt"""
# THIS FILE WAS GENERATED VIA 'nimble config'
# DO NOT EDIT

const
  Version              = "{version}"
  Config               = true
  ConfigBindir         = r"{bindir.get}"
  ConfigDatadir        = r"{datadir.get}"
  ConfigSysconfdir     = r"{sysconfdir.get}"
  ConfigSharedstatedir = r"{sharedstatedir.get}"
"""

  let policy = readFile "data/com.refi64.Bluecap.policy.in"
  writeFile "build/com.refi64.Bluecap.policy", policy.replace("${bindir}", bindir.get)

task sysinstall, "install system-wide":
  when declared(Config) and allFilesExist("build/bluecap", "build/com.refi64.Bluecap.policy"):
    var destdir =
      case paramCount()
      of 1: ""
      of 2: paramStr(2)
      else: die "At most one argument can be given (a destdir)"

    install 755, "build/bluecap", destdir / ConfigBindir
    install 644, "build/com.refi64.Bluecap.policy",
            destdir / ConfigDatadir / "polkit-1" / "actions"
    install 644, "data/defaults.json", destdir / ConfigSysconfdir / "bluecap"
  else:
    die "Make sure you run 'nimble config' and 'nimble build' before attempting to sysinstall."

# task fedpkg, "":
