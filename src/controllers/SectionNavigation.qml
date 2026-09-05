import QtQuick

// Canonical section visibility, filters, and per-section pagination.
Item {
  id: root
  property int sectionIndex: 0

  property string requestedSection: "front-page"

  property int pageSize: 12

  property var sectionLimits: ({
    "front-page": 12,
    "for-you": 12,
    "core": 12,
    "plugins": 12,
    "youtube": 12,
    "saved": 12
  })

  readonly property var canonicalSections: [
    Object.assign({ id: "front-page" }, root.defaultSectionProfile("front-page")),
    Object.assign({ id: "for-you" }, root.defaultSectionProfile("for-you")),
    Object.assign({ id: "core" }, root.defaultSectionProfile("core")),
    Object.assign({ id: "plugins" }, root.defaultSectionProfile("plugins")),
    Object.assign({ id: "youtube" }, root.defaultSectionProfile("youtube")),
    Object.assign({ id: "saved" }, root.defaultSectionProfile("saved"))
  ]

  readonly property var hideableSections: ["core", "plugins", "youtube"]

  readonly property var sectionVisibility: session.preferences.sectionVisibility
    ? session.preferences.sectionVisibility
    : ({ core: true, plugins: true, youtube: true })

  readonly property var sections: visibleSections(canonicalSections, sectionVisibility)

  readonly property string currentSection: sections.length
    ? sections[Math.max(0, Math.min(sectionIndex, sections.length - 1))].id
    : "front-page"

  readonly property var currentProfile: sections.length
    ? sections[Math.max(0, Math.min(sectionIndex, sections.length - 1))]
    : root.defaultSectionProfile("front-page")

  readonly property var currentFilter: session.preferences.sectionFilters
    && session.preferences.sectionFilters[currentSection]
      ? session.preferences.sectionFilters[currentSection]
      : ({ period: "all", significance: "all", unreadOnly: false, imagesOnly: false, types: [] })

  required property var session
  signal sectionSelected(bool preserveInitialCandidate)
  function sectionIsVisible(sectionId, visibility) {
    var current = visibility || ({})
    if (sectionId !== "core" && sectionId !== "plugins" && sectionId !== "youtube")
      return true
    return current[sectionId] !== false
  }

  function visibleSections(allSections, visibility) {
    var result = []
    for (var index = 0; index < allSections.length; index++) {
      if (root.sectionIsVisible(allSections[index].id, visibility))
        result.push(allSections[index])
    }
    return result
  }

  function defaultSectionProfile(section) {
    var values = {
      "front-page": { name: "Front Page", icon: "newspaper", tone: "clear" },
      "for-you": { name: "For You", icon: "spark", tone: "clear" },
      "core": { name: "Core", icon: "core", tone: "clear" },
      "plugins": { name: "Plugins", icon: "plugins", tone: "clear" },
      "youtube": { name: "YouTube", icon: "youtube", tone: "clear" },
      "saved": { name: "Saved", icon: "saved", tone: "clear" }
    }
    return values[section]
  }

  function sectionIndexFor(sectionId) {
    for (var index = 0; index < sections.length; index++) {
      if (sections[index].id === sectionId) return index
    }
    return -1
  }

  function ensureVisibleSection() {
    if (!sections.length) return
    var current = sectionIndexFor(requestedSection)
    if (current >= 0) {
      if (sectionIndex !== current) sectionIndex = current
      return
    }
    var fallback = sectionIndexFor("front-page")
    if (fallback < 0) fallback = 0
    selectSection(fallback, true)
  }

  function cycleSection(delta) {
    var next = (sectionIndex + delta) % sections.length
    if (next < 0) next += sections.length
    selectSection(next)
  }

  function resetSectionLimit(section) {
    var limits = Object.assign({}, sectionLimits)
    limits[section] = pageSize
    sectionLimits = limits
  }

  function selectSection(index, preserveInitialCandidate) {
    if (index < 0 || index >= sections.length) return
    sectionIndex = index
    requestedSection = sections[index].id
    sectionSelected(preserveInitialCandidate === true)
  }
  function extendLimit() {
    var limits = Object.assign({}, sectionLimits)
    limits[currentSection] = Math.min(500, Number(limits[currentSection] || pageSize) + pageSize)
    sectionLimits = limits
  }
}
