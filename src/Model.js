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

function humanDate(value) {
  if (typeof value !== "string" || value.length < 10) return ""
  var year = value.slice(0, 4)
  var month = Number(value.slice(5, 7))
  var day = Number(value.slice(8, 10))
  var months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
  if (!/^\d{4}$/.test(year) || month < 1 || month > 12 || day < 1 || day > 31)
    return value.slice(0, 10)
  return String(day) + " " + months[month - 1] + " " + year
}

function isReaderArticle(story) {
  if (!story) return false
  var type = String(story.type || "")
  if (type === "youtube-video") return false
  if (type === "omarchy-news") return true
  return !!(story.classification && String(story.classification.section || "") === "core")
}

function usesQuietCard(section, story) {
  var id = String(section || "")
  if (id === "core") return true
  if (id === "front-page") return isReaderArticle(story)
  return false
}

function acceptedHttpsUrl(value) {
  if (typeof value !== "string") return ""
  var url = value.replace(/^\s+|\s+$/g, "").replace(/[.,;:)\]}>]+$/g, "")
  if (url.indexOf("https://") !== 0) return ""
  if (url.length < 10 || url.length > 2048) return ""
  if (/[<>"\s]/.test(url)) return ""
  if (/^https:\/\/(localhost|127\.|0\.|10\.|192\.168\.)/i.test(url)) return ""
  return url
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
}

function articleSegments(value) {
  var raw = typeof value === "string" ? value : ""
  var events = []
  var occupied = []
  var markerRe = /\[([^\]\n]{1,160})\]\((https:\/\/[^)\s]{8,2048})\)/g
  var match
  while ((match = markerRe.exec(raw)) !== null) {
    var href = acceptedHttpsUrl(match[2])
    if (!href) continue
    var label = match[1].replace(/\s+/g, " ").replace(/^\s+|\s+$/g, "") || href
    events.push({ start: match.index, end: match.index + match[0].length, kind: "link", text: label, url: href })
    occupied.push({ start: match.index, end: match.index + match[0].length })
  }
  function taken(position) {
    for (var index = 0; index < occupied.length; index++) {
      if (position >= occupied[index].start && position < occupied[index].end) return true
    }
    return false
  }
  var bareRe = /https:\/\/[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251})[A-Za-z0-9](?::443)?(?:\/[^\s<>"']*)?/g
  while ((match = bareRe.exec(raw)) !== null) {
    if (taken(match.index)) continue
    href = acceptedHttpsUrl(match[0])
    if (!href) continue
    var trailing = match[0].length - match[0].replace(/[.,;:)\]}>]+$/g, "").length
    var end = match.index + match[0].length - trailing
    if (end <= match.index) continue
    events.push({ start: match.index, end: end, kind: "link", text: href, url: href })
  }
  events.sort(function(left, right) { return left.start - right.start })
  var segments = []
  var cursor = 0
  for (var eventIndex = 0; eventIndex < events.length; eventIndex++) {
    var event = events[eventIndex]
    if (event.start < cursor) continue
    if (event.start > cursor) segments.push({ kind: "text", text: raw.slice(cursor, event.start) })
    segments.push({ kind: "link", text: event.text, url: event.url })
    cursor = event.end
  }
  if (cursor < raw.length) segments.push({ kind: "text", text: raw.slice(cursor) })
  if (segments.length) return segments
  return raw ? [{ kind: "text", text: raw }] : []
}

function cssColor(value) {
  if (!value) return ""
  if (typeof value === "string") {
    var raw = value.replace(/\s+/g, "")
    if (raw.charAt(0) === "#" && (raw.length === 7 || raw.length === 4)) return raw
    return ""
  }
  if (typeof value.r !== "number" || typeof value.g !== "number" || typeof value.b !== "number")
    return ""
  function hex(channel) {
    var n = Math.max(0, Math.min(255, Math.round(channel * 255)))
    var h = n.toString(16)
    return h.length === 1 ? "0" + h : h
  }
  return "#" + hex(value.r) + hex(value.g) + hex(value.b)
}

function articleBodyHtml(segments, linkColor) {
  if (!segments || !segments.length) return ""
  var color = cssColor(linkColor)
  var parts = []
  for (var index = 0; index < segments.length; index++) {
    var segment = segments[index]
    var text = escapeHtml(String(segment && segment.text ? segment.text : ""))
    var url = segment && segment.kind === "link" ? acceptedHttpsUrl(String(segment.url || "")) : ""
    if (url) {
      // Bake theme color into the tag: Qt RichText often ignores Text.linkColor.
      var style = color
        ? ' style="color: ' + color + '; text-decoration: underline;"'
        : ""
      parts.push('<a href="' + escapeHtml(url) + '"' + style + ">" + text + "</a>")
    } else {
      parts.push(text)
    }
  }
  return parts.join("")
}

function articlePlainText(segments) {
  if (!segments || !segments.length) return ""
  var parts = []
  for (var index = 0; index < segments.length; index++)
    parts.push(String(segments[index] && segments[index].text ? segments[index].text : ""))
  return parts.join("")
}
