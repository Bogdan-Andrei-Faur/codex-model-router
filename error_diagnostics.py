"""Content-free diagnostics from the installed App Server TurnError contract.

Never retain message, additionalDetails, misalignment explanations or arbitrary
strings. Unknown variants stay unknown until explicitly supported.
"""

ERROR_TYPES = frozenset((
    "contextWindowExceeded", "sessionBudgetExceeded", "usageLimitExceeded",
    "rateLimitExceeded", "serverOverloaded", "cyberPolicy",
    "misalignmentPolicyViolation", "internalServerError", "unauthorized",
    "badRequest", "threadRollbackFailed", "sandboxError", "other",
))
HTTP_ERRORS = frozenset(("httpConnectionFailed", "responseStreamConnectionFailed",
                         "responseStreamDisconnected", "responseTooManyFailedAttempts"))
DIAGNOSTIC_FIELDS = ("error_type", "error_code", "error_http_status", "error_source")


def native_error(error):
    result = {"error_type": "unknown", "error_source": "native"}
    if not isinstance(error, dict):
        return result
    info = error.get("codexErrorInfo")
    if isinstance(info, str) and info in ERROR_TYPES:
        result["error_type"] = info
    elif isinstance(info, dict) and len(info) == 1:
        kind = next(iter(info))
        if kind in HTTP_ERRORS or kind == "activeTurnNotSteerable":
            result["error_type"] = kind
            details = info[kind]
            status = details.get("httpStatusCode") if isinstance(details, dict) else None
            if kind in HTTP_ERRORS and type(status) is int and 100 <= status <= 599:
                result["error_http_status"] = status
    return result


def rpc_error(error):
    result = {"error_type": "turn_rejected", "error_source": "native_rpc"}
    code = error.get("code") if isinstance(error, dict) else None
    if type(code) is int and -(2 ** 31) <= code < 2 ** 31:
        result["error_code"] = code
    return result


def clear_error(row):
    for field in DIAGNOSTIC_FIELDS:
        row.pop(field, None)
