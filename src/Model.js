.pragma library

function parseResponse(raw) {
  if (typeof raw !== "string" || raw.length === 0 || raw.length > 3 * 1024 * 1024)
    return { protocolVersion: 1, status: "failed", message: "Helper output was empty or exceeded its bound." }
  try {
    var parsed = JSON.parse(raw)
    if (!parsed || parsed.protocolVersion !== 1 || typeof parsed.status !== "string")
      return { protocolVersion: 1, status: "failed", message: "Helper response used an unsupported protocol." }
    return parsed
  } catch (error) {
    return { protocolVersion: 1, status: "failed", message: "Helper response was invalid JSON." }
  }
}

function sourceHealth(feed) {
  if (!feed || !Array.isArray(feed.sources)) return "No validated source status"
  var failed = []
  var stale = []
  var latestCheckedAt = ""
  for (var index = 0; index < feed.sources.length; index++) {
    var source = feed.sources[index]
    if (source.status === "failed") failed.push(source.id)
    if (source.status === "stale") stale.push(source.id)
    if (typeof source.checkedAt === "string" && source.checkedAt > latestCheckedAt)
      latestCheckedAt = source.checkedAt
  }
  if (failed.length) return "Partial · " + failed.join(", ")
  if (stale.length) return "Stale · " + stale.join(", ")
  return latestCheckedAt
    ? "All available sources succeeded at " + latestCheckedAt
    : "All available sources succeeded"
}
