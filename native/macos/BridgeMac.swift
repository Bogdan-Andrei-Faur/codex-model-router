// Native signed launcher: preserves argv/stdin/stdout and uses only bundled code.
import Darwin
import Foundation
import MachO

var required: UInt32 = 0
_ = _NSGetExecutablePath(nil, &required)
var buffer = [CChar](repeating: 0, count: Int(required))
guard _NSGetExecutablePath(&buffer, &required) == 0 else { exit(1) }
let executable = URL(fileURLWithPath: String(cString: buffer)).resolvingSymlinksInPath()
let contents = executable.deletingLastPathComponent().deletingLastPathComponent()
let runtime = contents.appendingPathComponent("Helpers/RouterRuntime.app/Contents/MacOS/router-runtime").path
let arguments = [runtime, "bridge"] + Array(CommandLine.arguments.dropFirst())
var pointers: [UnsafeMutablePointer<CChar>?] = arguments.map { strdup($0) }
pointers.append(nil)
execv(runtime, &pointers)
fputs("No se pudo iniciar el runtime del enrutador.\n", stderr)
exit(1)
