// Offline publisher utility. Private Ed25519 bytes never leave macOS Keychain.
import Foundation
import Security
import CryptoKit

let service = "local.codex-model-router.release-signing.v1"
let account = "ed25519-publisher"
func query() -> [String: Any] {
    return [kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service, kSecAttrAccount as String: account]
}
func fail() -> Never {
    FileHandle.standardError.write(Data("No se pudo acceder a la clave de firma del proyecto.\n".utf8))
    exit(1)
}
func readKey() -> Curve25519.Signing.PrivateKey? {
    var q = query(); q[kSecReturnData as String] = true; q[kSecMatchLimit as String] = kSecMatchLimitOne
    var result: CFTypeRef?
    let status = SecItemCopyMatching(q as CFDictionary, &result)
    if status == errSecItemNotFound { return nil }
    guard status == errSecSuccess, let data = result as? Data,
          let key = try? Curve25519.Signing.PrivateKey(rawRepresentation: data) else { fail() }
    return key
}
let action = CommandLine.arguments.count == 2 ? CommandLine.arguments[1] : ""
guard ["create", "public", "sign"].contains(action) else { fail() }
var stored = readKey()
if stored == nil && action == "create" {
    let key = Curve25519.Signing.PrivateKey()
    var item = query()
    item[kSecValueData as String] = key.rawRepresentation
    item[kSecAttrLabel as String] = "Codex Model Router — firma de actualizaciones"
    item[kSecAttrAccessible as String] = kSecAttrAccessibleWhenUnlockedThisDeviceOnly
    guard SecItemAdd(item as CFDictionary, nil) == errSecSuccess else { fail() }
    stored = key
}
guard let key = stored else { fail() }
if action == "sign" {
    // Exactly the versioned release domain, never a general-purpose signing oracle.
    let data = FileHandle.standardInput.readDataToEndOfFile()
    let prefix = Data("codex-model-router/release-manifest/v1\0".utf8)
    guard data.count <= 65536, data.starts(with: prefix),
          let signature = try? key.signature(for: data) else { fail() }
    print(signature.base64EncodedString())
} else {
    print(key.publicKey.rawRepresentation.base64EncodedString())
}
